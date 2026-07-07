"""Incident analysis agent.

Correlates Datadog monitors + events + logs to enrich incidents.
Produces: severity assessment, service impact, timeline correlation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.analysis import AnalysisResult
from app.core.models.incident import Incident, IncidentTimeline
from app.datadog.client import DatadogClient

logger = logging.getLogger(__name__)


async def analyze_incident(
    incident_id: str,
    db: AsyncSession,
) -> AnalysisResult:
    """Analyze an incident: enrich with Datadog context, detect patterns, assess severity."""
    from uuid import UUID

    uid = UUID(incident_id)
    result = await db.execute(select(Incident).where(Incident.id == uid))
    incident = result.scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []

    # 1. Check timeline for coverage
    tl_result = await db.execute(
        select(IncidentTimeline).where(IncidentTimeline.incident_id == uid)
    )
    timeline = tl_result.scalars().all()
    if len(timeline) < 2:
        recommendations.append("Add more timeline events — at minimum detection, response, and resolution")

    # 2. Query Datadog for related monitors
    dd_events = []
    try:
        client = DatadogClient()
        now = int(datetime.now(UTC).timestamp())
        from_ts = now - 3600 * 24 * 7  # 7 days
        events = client.events.list_events(
            start=from_ts,
            end=now,
            tags=f"severity:{incident.severity.lower()}" if incident.severity else None,
        )
        dd_data = events.to_dict()
        dd_events = dd_data.get("events", [])
    except Exception as e:
        logger.warning("Datadog query failed: %s", e)
        findings.append({"type": "datadog", "severity": "warning", "detail": f"Datadog unavailable: {e}"})

    # 3. Assess severity correctness
    severity_mismatch = _assess_severity(incident, dd_events)
    if severity_mismatch:
        findings.append(severity_mismatch)
        recommendations.append(
            f"Review severity: {severity_mismatch['detail']}"
        )

    # 4. MTTR heuristic
    if incident.resolved_at and incident.started_at:
        mttr_min = (incident.resolved_at - incident.started_at).total_seconds() / 60
        findings.append({
            "type": "mttr",
            "value": round(mttr_min, 1),
            "unit": "minutes",
            "severity": "info",
        })
        if mttr_min > 120:
            recommendations.append(
                f"MTTR is {mttr_min:.0f} min — consider automation to reduce resolution time"
            )
    else:
        findings.append({"type": "mttr", "detail": "No resolution timestamp — incident may still be active"})

    # 5. Service impact assessment
    if incident.service:
        findings.append({
            "type": "service_impact",
            "service": incident.service,
            "severity": incident.severity,
        })

    severity_parts = incident.severity.removeprefix("SEV-")
    score = max(10, 100 - int(severity_parts) * 20) if severity_parts.isdigit() else 50
    if incident.status == "resolved":
        score = min(score + 20, 100)

    analysis = AnalysisResult(
        domain="incident",
        action="analyze",
        target_id=uid,
        title=f"Incident Analysis: {incident.title}",
        summary=_build_summary(incident, len(timeline), len(dd_events)),
        findings=findings,
        recommendations=recommendations,
        score=score,
        severity="critical" if incident.severity in ("SEV-1", "SEV-2") else "info",
        raw_data={"timeline_count": len(timeline), "dd_events_found": len(dd_events)},
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis


def _assess_severity(incident: Incident, dd_events: list) -> dict | None:
    """Check if Datadog event severity matches incident severity."""
    if not dd_events:
        return None
    dd_sevs = set(e.get("alert_type", "") for e in dd_events if e.get("alert_type"))
    if incident.severity == "SEV-1" and "error" not in dd_sevs:
        return {
            "type": "severity_mismatch",
            "incident_severity": incident.severity,
            "datadog_alert_types": list(dd_sevs),
            "severity": "warning",
            "detail": "SEV-1 incident but no 'error' alerts found in related Datadog events",
        }
    return None


def _build_summary(incident: Incident, timeline_count: int, dd_count: int) -> str:
    return (
        f"Incident '{incident.title}' ({incident.severity}, {incident.status}). "
        f"{timeline_count} timeline events. "
        f"{dd_count} related Datadog events found."
    )
