"""RCA analysis agent.

Correlates incident + KB patterns + multi-metric Datadog analysis to
suggest root causes. Uses the SRE Metrics Engine for holistic infra
assessment (CPU, memory, latency, errors, disk, network).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.analysis.sre_metrics import SREAnalysisResult, SREMetricsAnalyzer
from app.core.models.analysis import AnalysisResult
from app.core.models.incident import Incident
from app.core.models.knowledge_base import KnowledgeBase
from app.core.models.rca import RcaReport

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _assess_severity(
    sre_result: SREAnalysisResult,
    matched_patterns: list[dict[str, Any]],
    has_rca: bool,
) -> tuple[str, float]:
    """Determine severity and score from all evidence sources."""
    score = 50.0

    # SRE metrics contribution
    critical_metrics = sum(1 for m in sre_result.metrics if m.status == "critical")
    warning_metrics = sum(1 for m in sre_result.metrics if m.status == "warning")

    score += max(0, 30 - critical_metrics * 10)  # -10 per critical metric
    score += max(0, 20 - warning_metrics * 5)  # -5 per warning metric

    # KB match bonus
    if matched_patterns:
        score += 15

    # RCA exists bonus
    if has_rca:
        score += 10

    score = max(0, min(100, score))

    if critical_metrics > 0:
        severity = "critical"
    elif warning_metrics > 1 or not has_rca:
        severity = "warning"
    else:
        severity = "info"

    return severity, round(score, 1)


async def analyze_rca(
    incident_id: str,
    db: AsyncSession,
    tags: str | None = None,
) -> AnalysisResult:
    """Analyze RCA for an incident: multi-metric SRE + KB patterns + correlations."""
    from uuid import UUID

    uid = UUID(incident_id)
    incident_result = await db.execute(select(Incident).where(Incident.id == uid))
    incident = incident_result.scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    # Get existing RCA
    rca_result = await db.execute(select(RcaReport).where(RcaReport.incident_id == uid))
    rca = rca_result.scalar_one_or_none()

    # ── Multi-Metric SRE Analysis ──────────────────────────────────
    sre_analyzer = SREMetricsAnalyzer(
        service=incident.service,
        tags=tags,  # overrides service when set
        window_min=60,
    )
    sre_result = sre_analyzer.analyze_all_sync()

    # ── KB Pattern Matching ────────────────────────────────────────
    kb_result = await db.execute(select(KnowledgeBase))
    kb_entries = kb_result.scalars().all()

    matched_patterns: list[dict[str, Any]] = []
    kb_recommendations: list[str] = []

    if incident.title:
        title_lower = incident.title.lower()
        desc_lower = (incident.description or "").lower()

        for kb in kb_entries:
            if not kb.symptom_pattern:
                continue
            keywords = [kw.strip() for kw in kb.symptom_pattern.split(" OR ")]
            for kw in keywords:
                if kw.lower() in title_lower or kw.lower() in desc_lower:
                    matched_patterns.append(
                        {
                            "kb_id": str(kb.id),
                            "title": kb.title,
                            "matched_keyword": kw,
                            "root_cause": kb.root_cause,
                            "resolution_steps": kb.resolution_steps or [],
                        }
                    )
                    kb_recommendations.append(f"KB match '{kb.title}': {kb.root_cause}")
                    break

    # ── RCA Validation ─────────────────────────────────────────────
    rca_recommendations: list[str] = []
    if rca:
        if not rca.recommendations or len(rca.recommendations) < 2:
            rca_recommendations.append("RCA has <2 recommendations — add more action items")
        if not rca.root_cause or len(rca.root_cause) < 20:
            rca_recommendations.append("Root cause description is too short — expand with details")
    else:
        rca_recommendations.append("No RCA report exists for this incident — create one")

    # ── Combine All Evidence ───────────────────────────────────────
    severity, score = _assess_severity(sre_result, matched_patterns, bool(rca))

    all_recommendations: list[str] = []
    all_recommendations.extend(sre_result.recommendations)
    all_recommendations.extend(kb_recommendations)
    all_recommendations.extend(rca_recommendations)

    # ── Construct Findings ─────────────────────────────────────────
    findings: list[dict[str, Any]] = [
        {
            "type": "sre_analysis",
            "score": sre_result.score,
            "narrative": sre_result.narrative,
            "metrics": [
                {
                    "metric_id": m.metric_id,
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "status": m.status,
                }
                for m in sre_result.metrics
            ],
            "correlations": [
                {
                    "rule_id": c.rule_id,
                    "label": c.label,
                    "severity": c.severity,
                }
                for c in sre_result.correlations
            ],
        },
        {
            "type": "pattern_matches",
            "count": len(matched_patterns),
            "matches": matched_patterns,
        },
        {
            "type": "rca_status",
            "exists": bool(rca),
            "id": str(rca.id) if rca else None,
        },
    ]

    # ── Build summary ──────────────────────────────────────────────
    summary_parts = [
        f"Multi-metric SRE analysis score: {sre_result.score}/100.",
        f"KB patterns matched: {len(matched_patterns)}.",
        f"RCA {'exists' if rca else 'MISSING'}.",
    ]
    critical_sre = [m.name for m in sre_result.metrics if m.status == "critical"]
    if critical_sre:
        summary_parts.append(f"Critical metrics: {', '.join(critical_sre)}.")

    analysis = AnalysisResult(
        domain="rca",
        action="analyze",
        target_id=uid,
        title=f"RCA Analysis: {incident.title}",
        summary=" ".join(summary_parts),
        findings=findings,
        recommendations=all_recommendations,
        score=score,
        severity=severity,
        raw_data={
            "sre_health_score": sre_result.score,
            "kb_patterns_matched": len(matched_patterns),
            "has_rca": bool(rca),
            "critical_metrics": len(critical_sre),
            "total_metrics": len(sre_result.metrics),
        },
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis
