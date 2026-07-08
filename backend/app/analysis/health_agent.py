"""Product health analysis agent.

Evaluates SLO compliance, error budgets, Datadog monitors status,
and multi-metric SRE health (CPU, memory, latency, errors, disk, network).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.analysis.sre_metrics import SREMetricsAnalyzer
from app.core.models.analysis import AnalysisResult
from app.core.models.health import HealthSnapshot, Slo

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def analyze_health(
    db: AsyncSession,
    tags: str | None = None,
) -> AnalysisResult:
    """Analyze overall product health: SLO compliance, burn-rate, multi-metric SRE."""
    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []

    # ── 1. SLO Assessment ──────────────────────────────────────────
    slo_result = await db.execute(select(Slo))
    slos = slo_result.scalars().all()
    slo_count = len(slos)
    slos_at_risk = 0
    slos_violated = 0
    for slo in slos:
        snap = (
            await db.execute(
                select(HealthSnapshot)
                .where(HealthSnapshot.service == slo.service)
                .order_by(HealthSnapshot.snapshot_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        current = snap.current_value if snap else slo.target * 1.05
        if current < slo.target * 0.9:
            slos_violated += 1
            findings.append(
                {
                    "type": "slo_violation",
                    "slo_id": str(slo.id),
                    "name": slo.name,
                    "target": slo.target,
                    "current": current,
                }
            )
        elif current < slo.target:
            slos_at_risk += 1
            findings.append(
                {
                    "type": "slo_at_risk",
                    "slo_id": str(slo.id),
                    "name": slo.name,
                    "target": slo.target,
                    "current": current,
                }
            )

    if slos_violated:
        recommendations.append(f"{slos_violated} SLO(s) violated — immediate attention needed")
    if slos_at_risk:
        recommendations.append(f"{slos_at_risk} SLO(s) at risk — review burn rates")

    # ── 2. Monitor Status from Datadog ─────────────────────────────
    monitor_statuses: dict[str, dict[str, int]] = {}
    try:
        from app.datadog.client import DatadogClient

        client = DatadogClient()
        monitors = client.list_monitors(tags=tags) if tags else client.list_monitors()
        for m in monitors:
            m_type = m.get("type", "unknown")
            m_status = m.get("overall_state", "unknown")
            monitor_statuses.setdefault(m_type, {})
            monitor_statuses[m_type][m_status] = monitor_statuses[m_type].get(m_status, 0) + 1

        total_alerts = sum(
            monitor_statuses.get(t, {}).get("Alert", 0) for t in monitor_statuses
        ) + sum(monitor_statuses.get(t, {}).get("Warn", 0) for t in monitor_statuses)
        if total_alerts > 5:
            recommendations.append(
                f"{total_alerts} monitors in Alert/Warn state — investigate immediately"
            )

        findings.append(
            {
                "type": "datadog_monitors",
                "summary": monitor_statuses,
                "total_alerts": total_alerts,
            }
        )
    except Exception as e:
        findings.append({"type": "datadog_monitors", "available": False, "detail": str(e)})

    # ── 3. Multi-Metric SRE Analysis ───────────────────────────────
    sre_analyzer = SREMetricsAnalyzer(tags=tags, window_min=60)
    sre_result = sre_analyzer.analyze_all_sync()

    findings.append(
        {
            "type": "sre_analysis",
            "health_score": sre_result.score,
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
                {"rule_id": c.rule_id, "label": c.label, "severity": c.severity}
                for c in sre_result.correlations
            ],
        }
    )

    sre_critical = [m for m in sre_result.metrics if m.status == "critical"]
    sre_warning = [m for m in sre_result.metrics if m.status == "warning"]
    if sre_critical:
        recommendations.append(
            f"SRE: {len(sre_critical)} critical metric(s) detected — "
            f"{', '.join(m.name for m in sre_critical)}"
        )

    recommendations.extend(sre_result.recommendations)

    # ── 4. Historical Snapshots Trend ──────────────────────────────
    snapshot_result = await db.execute(
        select(HealthSnapshot).order_by(HealthSnapshot.snapshot_at.desc()).limit(10)
    )
    snapshots = snapshot_result.scalars().all()
    if len(snapshots) >= 2:
        healthy_count = sum(1 for s in snapshots if s.status == "healthy")
        unhealthy_count = len(snapshots) - healthy_count
        if unhealthy_count > healthy_count and len(snapshots) > 3:
            recommendations.append(
                "Most recent health snapshots show unhealthy status — investigate"
            )

    # ── Score (blended: SLO + SRE metrics) ────────────────────────
    score = 100.0
    score -= slos_violated * 30
    score -= slos_at_risk * 10
    score -= len(sre_critical) * 10
    score -= len(sre_warning) * 3
    score = max(0, round(score, 1))

    summary = (
        f"Health analysis: {slo_count} SLOs tracked, "
        f"{slos_violated} violated, {slos_at_risk} at risk. "
        f"SRE health: {sre_result.score}/100. "
        f"Score: {score}/100."
    )

    analysis = AnalysisResult(
        domain="health",
        action="analyze",
        target_id=None,
        title="Product Health Analysis",
        summary=summary,
        findings=findings,
        recommendations=recommendations,
        score=score,
        severity="critical"
        if slos_violated > 0 or sre_result.score < 50
        else "warning"
        if slos_at_risk > 0 or sre_result.score < 70
        else "info",
        raw_data={
            "slo_count": slo_count,
            "slos_violated": slos_violated,
            "slos_at_risk": slos_at_risk,
            "sre_health_score": sre_result.score,
            "total_monitor_alerts": monitor_statuses.get("query alert", {}).get("Alert", 0)
            if monitor_statuses
            else 0,
        },
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis
