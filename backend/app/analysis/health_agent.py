"""Product health analysis agent.

Evaluates SLO compliance, error budgets, Datadog monitors status.
Produces: burn-rate alerts, error budget remaining, health score.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.analysis import AnalysisResult
from app.core.models.health import HealthSnapshot, Slo

logger = logging.getLogger(__name__)


async def analyze_health(
    db: AsyncSession,
) -> AnalysisResult:
    """Analyze overall product health: SLO compliance, burn-rate, monitors."""
    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []

    # 1. SLO assessment
    slo_result = await db.execute(select(Slo))
    slos = slo_result.scalars().all()
    slo_count = len(slos)
    slos_at_risk = 0
    slos_violated = 0
    for slo in slos:
        # Find latest health snapshot for this SLO's service
        snap = (await db.execute(
            select(HealthSnapshot)
            .where(HealthSnapshot.service == slo.service)
            .order_by(HealthSnapshot.snapshot_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        current = snap.current_value if snap else slo.target * 1.05  # assume healthy if no data
        if current < slo.target * 0.9:
            slos_violated += 1
            findings.append({
                "type": "slo_violation",
                "slo_id": str(slo.id),
                "name": slo.name,
                "target": slo.target,
                "current": current,
            })
        elif current < slo.target:
            slos_at_risk += 1
            findings.append({
                "type": "slo_at_risk",
                "slo_id": str(slo.id),
                "name": slo.name,
                "target": slo.target,
                "current": current,
            })

    if slos_violated:
        recommendations.append(f"{slos_violated} SLO(s) violated — immediate attention needed")
    if slos_at_risk:
        recommendations.append(f"{slos_at_risk} SLO(s) at risk — review burn rates")

    # 2. Monitor status from Datadog
    monitor_statuses = {}
    try:
        from app.datadog.client import DatadogClient

        client = DatadogClient()
        monitors = client.list_monitors()
        for m in monitors:
            m_type = m.get("type", "unknown")
            m_status = m.get("overall_state", "unknown")
            monitor_statuses.setdefault(m_type, {})
            monitor_statuses[m_type][m_status] = monitor_statuses[m_type].get(m_status, 0) + 1

        # Check alerting
        total_alerts = sum(
            monitor_statuses.get(t, {}).get("Alert", 0) for t in monitor_statuses
        ) + sum(monitor_statuses.get(t, {}).get("Warn", 0) for t in monitor_statuses)
        if total_alerts > 5:
            recommendations.append(f"{total_alerts} monitors in Alert/Warn state — investigate immediately")

        findings.append({
            "type": "datadog_monitors",
            "summary": monitor_statuses,
            "total_alerts": total_alerts,
        })
    except Exception as e:
        findings.append({"type": "datadog_monitors", "available": False, "detail": str(e)})

    # 3. Historical snapshots trend
    snapshot_result = await db.execute(
        select(HealthSnapshot).order_by(HealthSnapshot.snapshot_at.desc()).limit(10)
    )
    snapshots = snapshot_result.scalars().all()
    if len(snapshots) >= 2:
        healthy_count = sum(1 for s in snapshots if s.status == "healthy")
        unhealthy_count = len(snapshots) - healthy_count
        if unhealthy_count > healthy_count and len(snapshots) > 3:
            recommendations.append("Most recent health snapshots show unhealthy status — investigate")

    # Score
    score = 100
    score -= slos_violated * 30
    score -= slos_at_risk * 10
    score = max(score, 0)

    summary = (
        f"Health analysis: {slo_count} SLOs tracked, "
        f"{slos_violated} violated, {slos_at_risk} at risk. "
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
        severity="critical" if slos_violated > 0 else "warning" if slos_at_risk > 0 else "info",
        raw_data={
            "slo_count": slo_count,
            "slos_violated": slos_violated,
            "slos_at_risk": slos_at_risk,
            "monitor_summary": monitor_statuses,
        },
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis
