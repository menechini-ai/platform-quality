"""Report generator — produces executive, monthly, postmortem, and investigation reports."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from string import Formatter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.incident import Incident
from app.core.models.maturity import MaturityAssessment
from app.core.models.report import Report
from app.core.models.rca import RcaReport

logger = logging.getLogger(__name__)


REPORT_TEMPLATES = {
    "executive": """# Executive Summary — Observability Report

**Generated:** {date}

## Key Metrics
- **Active Incidents:** {active_incidents}
- **Maturity Level:** {maturity_level}/5 ({maturity_score}%)
- **Health Score:** {health_score if health_score else 'N/A'}

## Highlights
{narrative}

## Recommendations
{recommendations}
""",
    "monthly": """# Monthly Observability Metrics Report

**Period:** {period}
**Generated:** {date}

## Incident Summary
- Total Incidents: {total_incidents}
- Resolved: {resolved_incidents}
- Mean Time to Resolution: {mttr or 'N/A'}

## SLO Performance
{slo_summary}

## Action Items
{action_items}
""",
    "postmortem": """# Postmortem: {incident_title}

**Incident ID:** {incident_id}
**Date:** {date}
**Severity:** {severity}
**Root Cause:** {root_cause}

## Timeline
{timeline}

## Impact
{impact}

## Action Items
{action_items}

## Lessons Learned
{lessons}
""",
    "team_health": """# Team Health Report

**Team:** {team}
**Date:** {date}

## Service Ownership
{services}

## Alert Fatigue
- Total Alerts: {total_alerts}
- Paging Alerts: {paging_alerts}
- Noise Ratio: {noise_ratio}%

## On-Call Burden
{burden}
""",
    "investigation": """# Investigation: {title}

**Opened:** {date}
**Related Incident:** {incident_id}

## Hypothesis
{hypothesis}

## Data Sources
{data_sources}

## Findings
{findings}

## Conclusion
{conclusion}
""",
}


async def generate_report(
    db: AsyncSession,
    report_type: str,
    title: str,
    **context,
) -> Report:
    """Generate a report from template and context variables."""
    template = REPORT_TEMPLATES.get(report_type, "")
    if not template:
        raise ValueError(f"Unknown report type: {report_type}")

    context.setdefault("date", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    # Fill missing template placeholders with "N/A"
    placeholders = [key for _, key, _, _ in Formatter().parse(template) if key]
    for placeholder in placeholders:
        context.setdefault(placeholder, "N/A")
    content = template.format(**context)

    report = Report(
        report_type=report_type,
        title=title,
        content=content,
        tags=context.get("tags", []),
        metadata_=context.get("metadata", {}),
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def generate_postmortem(
    db: AsyncSession,
    incident_id: str,
) -> Report:
    """Auto-generate a postmortem from incident + RCA data."""
    from uuid import UUID

    uid = UUID(incident_id)
    result = await db.execute(select(Incident).where(Incident.id == uid))
    incident = result.scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    rca_result = await db.execute(
        select(RcaReport).where(RcaReport.incident_id == uid)
    )
    rca = rca_result.scalar_one_or_none()

    timeline = (
        "\n".join(
            f"- {e.occurred_at.strftime('%H:%M UTC')} — {e.event_type}: {e.content}"
            for e in getattr(incident, "timeline", [])
        )
        or "No timeline recorded"
    )

    return await generate_report(
        db,
        "postmortem",
        f"Postmortem: {incident.title}",
        incident_title=incident.title,
        incident_id=incident_id,
        severity=incident.severity,
        root_cause=rca.root_cause if rca else "Pending investigation",
        timeline=timeline,
        impact=incident.description or "Under assessment",
        action_items=rca.recommendations if rca else "See runbooks",
        lessons="To be filled during postmortem meeting",
    )
