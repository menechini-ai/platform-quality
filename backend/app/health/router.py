"""Health / SLO router: product health tracking, resource catalog."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text

from app.core.db import get_db
from app.core.models.health import HealthSnapshot, Slo
from app.core.models.incident import Incident
from app.core.models.rca import RcaReport
from app.core.models.report import Report
from app.core.models.self_healing import AutoHealAction, Runbook
from app.core.schemas.health import HealthSnapshotRead, SloCreate, SloRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ─── Liveness / Readiness ──────────────────────────────


@router.get("/health")
async def health_liveness():
    """Liveness probe — always 200 if the process is alive."""
    from app.core.config import settings

    return {
        "status": "ok",
        "version": "0.1.0",
        "app": settings.APP_NAME,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/readyz")
async def health_readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe — checks DB connectivity and critical config."""
    from app.core.config import settings

    checks: dict[str, str] = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "up"
    except Exception:
        checks["database"] = "down"

    # Datadog config check (informational only — not required for readiness)
    checks["datadog"] = "configured" if settings.DATADOG_API_KEY else "not_configured"

    all_ok = checks["database"] == "up"
    status_code = 200 if all_ok else 503
    status_str = "ok" if all_ok else "degraded"

    from starlette.responses import JSONResponse

    return JSONResponse(
        content={"status": status_str, "checks": checks},
        status_code=status_code,
    )


# --- SLOs ---


@router.get("/slos", response_model=list[SloRead])
async def list_slos(
    service: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all SLOs."""
    stmt = select(Slo)
    if service:
        stmt = stmt.where(Slo.service == service)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/slos", response_model=SloRead, status_code=201)
async def create_slo(data: SloCreate, db: AsyncSession = Depends(get_db)):
    """Create a new SLO."""
    slo = Slo(**data.model_dump())
    db.add(slo)
    await db.flush()
    await db.refresh(slo)
    return slo


# --- Health Snapshots ---


@router.get("/health/snapshots", response_model=list[HealthSnapshotRead])
async def list_health_snapshots(
    service: str | None = Query(None),
    status: str | None = Query(None, pattern=r"^(healthy|warning|critical)$"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List health snapshots."""
    stmt = select(HealthSnapshot).order_by(HealthSnapshot.snapshot_at.desc())
    if service:
        stmt = stmt.where(HealthSnapshot.service == service)
    if status:
        stmt = stmt.where(HealthSnapshot.status == status)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/health/summary")
async def health_summary(db: AsyncSession = Depends(get_db)):
    """Get a summary of current health status per service."""
    # Get latest snapshot per service
    subq = (
        select(
            HealthSnapshot.service,
            func.max(HealthSnapshot.snapshot_at).label("max_snapshot_at"),
        )
        .group_by(HealthSnapshot.service)
        .subquery()
    )

    stmt = (
        select(HealthSnapshot)
        .join(
            subq,
            (HealthSnapshot.service == subq.c.service)
            & (HealthSnapshot.snapshot_at == subq.c.max_snapshot_at),
        )
        .order_by(HealthSnapshot.service)
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    # Aggregate
    summary: dict[str, dict] = {}
    for snap in snapshots:
        if snap.service not in summary:
            summary[snap.service] = {
                "service": snap.service,
                "status": snap.status,
                "slis": [],
            }
        summary[snap.service]["slis"].append(
            {
                "sli_name": snap.sli_name,
                "current_value": snap.current_value,
                "slo_target": snap.slo_target,
                "burn_rate": snap.burn_rate,
                "error_budget_remaining": snap.error_budget_remaining,
            }
        )

    return list(summary.values())


# --- Resource Catalog: all resources tagged and linked ---


@router.get("/health/catalog")
async def health_catalog(
    days: int | None = Query(None, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Return a unified catalog of all observability resources, tagged and linked.

    Each resource has: type, id, name, service, tags, failure_pattern (if incident),
    and relationships to other resources.
    """
    catalog: list[dict] = []

    # Incidents — optionally filtered by recency
    inc_stmt = select(Incident)
    if days:
        from datetime import datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(days=days)
        inc_stmt = inc_stmt.where(Incident.started_at >= cutoff)
    inc_stmt = inc_stmt.order_by(Incident.created_at.desc())
    incidents = (await db.execute(inc_stmt)).scalars().all()
    for inc in incidents:
        item = {
            "type": "incident",
            "id": str(inc.id),
            "name": inc.title,
            "service": inc.service,
            "severity": inc.severity,
            "status": inc.status,
            "failure_pattern": inc.failure_pattern,
            "tags": inc.tags or [],
            "started_at": inc.started_at.isoformat() if inc.started_at else None,
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "relationships": {
                "has_rca": None,  # populated below
                "has_postmortem": None,
            },
        }
        catalog.append(item)

    # RCAs
    rcas = (await db.execute(select(RcaReport))).scalars().all()
    rca_by_incident = {str(r.incident_id): r for r in rcas}
    for item in catalog:
        if item["type"] == "incident":
            rca = rca_by_incident.get(item["id"])
            if rca:
                item["relationships"]["has_rca"] = str(rca.id)

    # Reports / Postmortems
    reports = (await db.execute(select(Report))).scalars().all()
    for rep in reports:
        item = {
            "type": "report",
            "id": str(rep.id),
            "name": rep.title,
            "service": None,
            "tags": rep.tags or [],
            "report_type": rep.report_type,
            "created_at": rep.created_at.isoformat() if rep.created_at else None,
            "relationships": {},
        }
        catalog.append(item)

    # Runbooks
    runbooks = (await db.execute(select(Runbook))).scalars().all()
    for rb in runbooks:
        item = {
            "type": "runbook",
            "id": str(rb.id),
            "name": rb.name,
            "service": None,
            "tags": [],
            "is_active": rb.is_active,
            "steps_count": len(rb.steps or []),
            "created_at": rb.created_at.isoformat() if rb.created_at else None,
            "relationships": {},
        }
        catalog.append(item)

    # Auto-heal actions
    actions = (await db.execute(select(AutoHealAction))).scalars().all()
    for a in actions:
        item = {
            "type": "auto_heal_action",
            "id": str(a.id),
            "name": f"{a.action_type} ({a.triggered_by})",
            "incident_id": str(a.incident_id) if a.incident_id else None,
            "tags": [],
            "action_type": a.action_type,
            "status": a.status,
            "created_at": a.requested_at.isoformat() if a.requested_at else None,
            "relationships": {
                "incident": str(a.incident_id) if a.incident_id else None,
            },
        }
        catalog.append(item)

    # SLOs
    slos = (await db.execute(select(Slo))).scalars().all()
    for s in slos:
        item = {
            "type": "slo",
            "id": str(s.id),
            "name": s.name,
            "service": s.service,
            "tags": [],
            "target": s.target,
            "time_window": s.time_window,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "relationships": {},
        }
        catalog.append(item)

    return catalog


@router.get("/health/stats")
async def health_stats(
    days: int | None = Query(None, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated statistics across all resource types: error counts, frequency by
    service, by failure pattern, by severity. One-stop shop for the health dashboard.
    """
    base_inc = select(Incident)
    if days:
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        time_filter = Incident.started_at >= cutoff
        base_inc = base_inc.where(time_filter)
    else:
        time_filter = None

    def _apply_time_filter(stmt):
        return stmt.where(time_filter) if time_filter is not None else stmt

    # Incident counts by service
    inc_by_service = (
        await db.execute(
            _apply_time_filter(
                select(Incident.service, func.count(Incident.id).label("cnt"))
                .where(Incident.service.isnot(None))
                .group_by(Incident.service)
                .order_by(func.count(Incident.id).desc())
            )
        )
    ).all()

    # Incident counts by failure pattern
    inc_by_pattern = (
        await db.execute(
            _apply_time_filter(
                select(Incident.failure_pattern, func.count(Incident.id).label("cnt"))
                .where(Incident.failure_pattern.isnot(None))
                .group_by(Incident.failure_pattern)
                .order_by(func.count(Incident.id).desc())
            )
        )
    ).all()

    # Incident counts by severity
    inc_by_severity = (
        await db.execute(
            _apply_time_filter(
                select(Incident.severity, func.count(Incident.id).label("cnt"))
                .group_by(Incident.severity)
                .order_by(func.count(Incident.id).desc())
            )
        )
    ).all()

    # Incident counts by status
    inc_by_status = (
        await db.execute(
            _apply_time_filter(
                select(Incident.status, func.count(Incident.id).label("cnt")).group_by(
                    Incident.status
                )
            )
        )
    ).all()

    # Incidents without RCA (gaps)
    no_rca = (
        await db.execute(
            _apply_time_filter(
                select(func.count(Incident.id))
                .outerjoin(RcaReport, RcaReport.incident_id == Incident.id)
                .where(RcaReport.id.is_(None))
            )
        )
    ).scalar() or 0

    # Report counts by type
    reports_by_type = (
        await db.execute(
            select(Report.report_type, func.count(Report.id).label("cnt")).group_by(
                Report.report_type
            )
        )
    ).all()

    # Runbooks
    runbook_count = (
        await db.execute(select(func.count(Runbook.id)).where(Runbook.is_active.is_(True)))
    ).scalar() or 0

    # Auto-heal action counts by status
    heal_by_status = (
        await db.execute(
            select(AutoHealAction.status, func.count(AutoHealAction.id).label("cnt")).group_by(
                AutoHealAction.status
            )
        )
    ).all()

    # SLO count
    slo_count = (await db.execute(select(func.count(Slo.id)))).scalar() or 0

    return {
        "total_incidents": sum(r.cnt for r in inc_by_status),
        "active_incidents": next((r.cnt for r in inc_by_status if r.status == "active"), 0),
        "incidents_without_rca": no_rca,
        "by_service": {r.service: r.cnt for r in inc_by_service},
        "by_failure_pattern": {r.failure_pattern: r.cnt for r in inc_by_pattern},
        "by_severity": {r.severity: r.cnt for r in inc_by_severity},
        "by_status": {r.status: r.cnt for r in inc_by_status},
        "reports_by_type": {r.report_type: r.cnt for r in reports_by_type},
        "total_runbooks": runbook_count,
        "heal_actions_by_status": {r.status: r.cnt for r in heal_by_status},
        "total_slos": slo_count,
    }


@router.get("/health/forecast")
async def health_forecast(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Forward-looking health indicators: incident frequency, MTBF trend,
    SLO burn-rate projection, metric degradation signals.

    Not ML — honest trend math a manager can understand.
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    lookback = now - timedelta(days=days)

    # --- Incident frequency per service ---
    incs = (
        (
            await db.execute(
                select(Incident)
                .where(Incident.started_at >= lookback)
                .order_by(Incident.started_at)
            )
        )
        .scalars()
        .all()
    )

    by_svc: dict[str, list] = {}
    for inc in incs:
        svc = inc.service or "unknown"
        by_svc.setdefault(svc, []).append(inc)

    freq: list[dict] = []
    for svc, items in sorted(by_svc.items()):
        n = len(items)

        # Normalize all timestamps to naive UTC
        def _naive(dt):
            return dt.replace(tzinfo=None) if dt else dt

        # MTBF = total days / (incidents - 1), or None if < 2
        if n >= 2:
            first = _naive(items[0].started_at)
            last = _naive(items[-1].started_at)
            span_h = (last - first).total_seconds() / 3600
            mtbf_h = round(span_h / (n - 1), 1) if n > 1 else None
        else:
            mtbf_h = None

        # Project next incident estimate if pattern exists
        next_estimate = None
        if mtbf_h:
            next_estimate = (items[-1].started_at + timedelta(hours=mtbf_h)).isoformat()

        # Group by failure pattern
        patterns: dict[str, int] = {}
        for i in items:
            p = i.failure_pattern or "unknown"
            patterns[p] = patterns.get(p, 0) + 1

        freq.append(
            {
                "service": svc,
                "total": n,
                "mtbf_hours": mtbf_h,
                "next_incident_estimate": next_estimate,
                "by_pattern": patterns,
                "last_incident": items[-1].started_at.isoformat() if items else None,
            }
        )

    # --- SLO burn-rate projection ---
    slos = (await db.execute(select(Slo))).scalars().all()
    burn = []
    for s in slos:
        # Look up latest health snapshot for this service
        snap = (
            await db.execute(
                select(HealthSnapshot)
                .where(HealthSnapshot.service == s.service)
                .order_by(HealthSnapshot.snapshot_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if snap and snap.burn_rate and snap.burn_rate > 0:
            remaining = snap.error_budget_remaining or 0
            days_to_exhaust = round(remaining / snap.burn_rate, 1) if snap.burn_rate > 0 else None
        else:
            days_to_exhaust = None

        burn.append(
            {
                "name": s.name,
                "service": s.service,
                "target": s.target,
                "burn_rate": snap.burn_rate if snap else None,
                "error_budget_remaining_pct": round((snap.error_budget_remaining or 0) * 100, 1)
                if snap
                else None,
                "days_to_exhaustion": days_to_exhaust,
            }
        )

    # --- Risk scoring ---
    risk = []
    # High-frequency services (recurring)
    for svc in freq:
        score = 0
        reasons = []
        if svc["total"] >= 2:
            score += 2
            reasons.append(f"recurring ({svc['total']} incidents in {days}d)")
        # SEV-1 presence
        for inc in by_svc.get(svc["service"], []):
            if inc.severity == "SEV-1":
                score += 2
                reasons.append("SEV-1 present")
                break
        # Multiple failure patterns
        if len(svc["by_pattern"]) >= 2:
            score += 1
            reasons.append("multi-pattern")
        # SLO exhaustion
        for b in burn:
            if (
                b["service"] == svc["service"]
                and b["days_to_exhaustion"]
                and b["days_to_exhaustion"] <= 14
            ):
                score += 2
                reasons.append(f"SLO burn imminent ({b['days_to_exhaustion']}d)")
        # Active incidents
        active = sum(1 for inc in by_svc.get(svc["service"], []) if inc.status == "active")
        if active >= 2:
            score += 1
            reasons.append(f"{active} active incidents")

        risk.append(
            {
                "service": svc["service"],
                "score": score,
                "level": "high" if score >= 4 else "medium" if score >= 2 else "low",
                "reasons": reasons,
                "mtbf_hours": svc["mtbf_hours"],
                "next_incident_estimate": svc["next_incident_estimate"],
            }
        )

    return {
        "window_days": days,
        "frequency": freq,
        "slo_burn": burn,
        "risk": risk,
        "generated_at": now.isoformat(),
    }
