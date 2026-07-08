"""Self-healing analysis agent.

Evaluates auto-heal runbooks, actions status, and suggests automation.
Produces: runbook effectiveness, action success rate, automation gaps.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.core.models.analysis import AnalysisResult
from app.core.models.self_healing import AutoHealAction, Runbook

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def analyze_self_healing(
    db: AsyncSession,
) -> AnalysisResult:
    """Analyze self-healing system: runbook coverage, action success rate, gaps."""
    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []

    # 1. Runbook coverage
    rb_result = await db.execute(select(Runbook))
    runbooks = rb_result.scalars().all()
    rb_count = len(runbooks)
    runbooks_by_service: dict[str, int] = {}
    for rb in runbooks:
        svc = rb.service or "unknown"
        runbooks_by_service[svc] = runbooks_by_service.get(svc, 0) + 1

    if rb_count == 0:
        findings.append(
            {"type": "runbook_coverage", "severity": "critical", "detail": "No runbooks defined"}
        )
        recommendations.append("Create runbooks for top incident types")
    else:
        findings.append(
            {
                "type": "runbook_coverage",
                "count": rb_count,
                "by_service": runbooks_by_service,
                "severity": "info",
            }
        )
        recommendations.append(f"{rb_count} runbooks exist — good coverage baseline")

    # 2. Action effectiveness
    action_result = await db.execute(select(AutoHealAction))
    actions = action_result.scalars().all()
    total = len(actions)
    approved = sum(1 for a in actions if a.status == "approved")
    rejected = sum(1 for a in actions if a.status == "rejected")
    pending = sum(1 for a in actions if a.status == "pending")

    findings.append(
        {
            "type": "action_status",
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
        }
    )
    if total > 0:
        approval_rate = approved / total * 100
        if approval_rate < 50:
            recommendations.append("Action approval rate < 50% — review runbook quality")
        if pending > 3:
            recommendations.append(f"{pending} actions pending — review and process them")

    # 3. Action type distribution
    action_types: dict[str, int] = {}
    for a in actions:
        action_types[a.action_type] = action_types.get(a.action_type, 0) + 1
    if action_types:
        findings.append({"type": "action_types", "distribution": action_types})

    # 4. Automation opportunity assessment
    has_dd = False
    try:
        from app.datadog.client import DatadogClient

        client = DatadogClient()
        monitors = client.list_monitors()
        has_dd = len(monitors) > 0
    except Exception:
        pass

    if rb_count > 0 and not has_dd:
        recommendations.append(
            "Runbooks defined but no Datadog monitors connected — enable monitor triggers"
        )

    # Score
    score = 50
    if rb_count >= 3:
        score += 20
    if total > 0:
        score += min(approved * 5, 20)
    score = min(score, 100)

    analysis = AnalysisResult(
        domain="self_healing",
        action="analyze",
        target_id=None,
        title="Self-Healing System Analysis",
        summary=(
            f"{rb_count} runbooks, {total} total actions "
            f"({approved} approved, {rejected} rejected, {pending} pending). "
            f"Score: {score}/100."
        ),
        findings=findings,
        recommendations=recommendations,
        score=score,
        severity="critical" if rb_count == 0 else "warning" if score < 50 else "info",
        raw_data={
            "runbook_count": rb_count,
            "action_total": total,
            "action_approved": approved,
            "action_rejected": rejected,
            "action_pending": pending,
        },
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis
