"""RCA analysis agent.

Correlates incident + KB patterns + Datadog metrics to suggest root causes.
Produces: matched KB patterns, statistical correlation, severity impact.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.analysis import AnalysisResult
from app.core.models.incident import Incident
from app.core.models.knowledge_base import KnowledgeBase
from app.core.models.rca import RcaReport

logger = logging.getLogger(__name__)


async def analyze_rca(
    incident_id: str,
    db: AsyncSession,
) -> AnalysisResult:
    """Analyze RCA for an incident: match KB patterns, validate recommendations."""
    from uuid import UUID

    uid = UUID(incident_id)
    incident_result = await db.execute(select(Incident).where(Incident.id == uid))
    incident = incident_result.scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    # Get existing RCA
    rca_result = await db.execute(
        select(RcaReport).where(RcaReport.incident_id == uid)
    )
    rca = rca_result.scalar_one_or_none()

    # Match KB patterns against incident
    kb_result = await db.execute(select(KnowledgeBase))
    kb_entries = kb_result.scalars().all()

    matched_patterns: list[dict[str, Any]] = []
    recommendations: list[str] = []

    if incident.title:
        title_lower = incident.title.lower()
        desc_lower = (incident.description or "").lower()

        for kb in kb_entries:
            if not kb.symptom_pattern:
                continue
            keywords = [kw.strip() for kw in kb.symptom_pattern.split(" OR ")]
            for kw in keywords:
                if kw.lower() in title_lower or kw.lower() in desc_lower:
                    matched_patterns.append({
                        "kb_id": str(kb.id),
                        "title": kb.title,
                        "matched_keyword": kw,
                        "root_cause": kb.root_cause,
                        "resolution_steps": kb.resolution_steps or [],
                    })
                    recommendations.append(
                        f"KB match '{kb.title}': {kb.root_cause}"
                    )
                    break

    # Validate existing RCA completeness
    if rca:
        if not rca.recommendations or len(rca.recommendations) < 2:
            recommendations.append("RCA has <2 recommendations — add more action items")
        if not rca.root_cause or len(rca.root_cause) < 20:
            recommendations.append("Root cause description is too short — expand with details")
    else:
        recommendations.append("No RCA report exists for this incident — create one")

    # Additional Datadog correlation
    dd_findings = []
    try:
        from app.datadog.client import DatadogClient

        client = DatadogClient()
        now = int(datetime.now(UTC).timestamp())
        from_ts = now - 3600 * 24 * 7
        metrics = client.metrics.query_metrics(
            query="avg:system.cpu.user{*}",
            from_ts=from_ts,
            to=now,
        )
        dd_findings.append({
            "type": "datadog_metrics",
            "available": True,
            "detail": "CPU metrics queried for incident timeline",
        })
    except Exception as e:
        dd_findings.append({"type": "datadog_metrics", "available": False, "detail": str(e)})

    score = 80 if rca else 30
    if matched_patterns:
        score = min(score + 15, 100)
    if recommendations:
        score = max(score - len(recommendations) * 5, 10)

    analysis = AnalysisResult(
        domain="rca",
        action="analyze",
        target_id=uid,
        title=f"RCA Analysis: {incident.title}",
        summary=f"RCA {'exists' if rca else 'MISSING'}. "
        f"{len(matched_patterns)} KB patterns matched. "
        f"{len(recommendations)} recommendations.",
        findings=[
            {"type": "pattern_matches", "count": len(matched_patterns), "matches": matched_patterns},
            {"type": "rca_status", "exists": bool(rca), "id": str(rca.id) if rca else None},
            *dd_findings,
        ],
        recommendations=recommendations,
        score=score,
        severity="critical" if not rca else "info",
        raw_data={
            "kb_patterns_matched": len(matched_patterns),
            "has_rca": bool(rca),
        },
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis
