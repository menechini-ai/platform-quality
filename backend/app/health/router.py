"""Health / SLO router: product health tracking."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.models.health import HealthSnapshot, Slo
from app.core.schemas.health import HealthSnapshotRead, SloCreate, SloRead

router = APIRouter()


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


@router.get("/health", response_model=list[HealthSnapshotRead])
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
