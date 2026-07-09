"""Self-healing analysis agent.

Evaluates auto-heal runbooks, actions status, multi-metric SRE health,
and creates AutoHealAction records when issues are detected.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.analysis.sre_metrics import SREMetricsAnalyzer
from app.core.models.analysis import AnalysisResult
from app.core.models.self_healing import AutoHealAction, Runbook

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Mapping from metric categories to auto-heal action types
METRIC_TO_ACTION: dict[str, str] = {
    "cpu": "scale",
    "memory": "scale",
    "latency": "restart",
    "errors": "restart",
    "disk": "script",
    "network": "script",
}

METRIC_TO_RUNBOOK: dict[str, str] = {
    "cpu": "CPU Saturation Response",
    "memory": "Memory Pressure Response",
    "latency": "Latency Spike Response",
    "errors": "Error Rate Response",
    "disk": "Disk Cleanup Response",
    "network": "Network Anomaly Response",
}


async def analyze_self_healing(
    db: AsyncSession,
    tags: str | None = None,
) -> AnalysisResult:
    """Analyze self-healing system: multi-metric SRE + runbook coverage + auto-heal actions.

    When issues are detected and self-healing is enabled, creates
    AutoHealAction records for approval/execution.
    """
    from app.core.config import settings

    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []
    created_actions: list[dict[str, Any]] = []

    # ── 1. Runbook Coverage ────────────────────────────────────────
    rb_result = await db.execute(select(Runbook))
    runbooks = rb_result.scalars().all()
    rb_count = len(runbooks)
    runbooks_by_service: dict[str, int] = {}
    for rb in runbooks:
        svc = "unknown"
        if rb.name:
            name_lower = rb.name.lower()
            for known in (
                "api-gateway",
                "payment",
                "order",
                "user",
                "notification",
                "observai-backend",
                "observai-frontend",
                "observai-worker",
            ):
                if known in name_lower:
                    svc = known
                    break
        runbooks_by_service[svc] = runbooks_by_service.get(svc, 0) + 1

    if rb_count == 0:
        findings.append(
            {
                "type": "runbook_coverage",
                "severity": "critical",
                "detail": "No runbooks defined",
            }
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

    # ── 2. Action Effectiveness ────────────────────────────────────
    action_result = await db.execute(select(AutoHealAction))
    actions = action_result.scalars().all()
    total = len(actions)
    approved = sum(1 for a in actions if a.status == "approved")
    rejected = sum(1 for a in actions if a.status == "rejected")
    pending = sum(1 for a in actions if a.status == "pending")
    failed = sum(1 for a in actions if a.status == "failed")

    findings.append(
        {
            "type": "action_status",
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "failed": failed,
        }
    )
    if total > 0:
        approval_rate = approved / total * 100
        if approval_rate < 50:
            recommendations.append("Action approval rate < 50% — review runbook quality")
        if pending > 3:
            recommendations.append(f"{pending} actions pending — review and process them")
        if failed > 0:
            recommendations.append(f"{failed} action(s) failed — investigate and retry")

    # ── 3. Action Type Distribution ────────────────────────────────
    action_types: dict[str, int] = {}
    for a in actions:
        action_types[a.action_type] = action_types.get(a.action_type, 0) + 1
    if action_types:
        findings.append({"type": "action_types", "distribution": action_types})

    # ── 4. Multi-Metric SRE Analysis ───────────────────────────────
    sre_analyzer = SREMetricsAnalyzer(tags=tags, window_min=30)
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

    # Merge SRE recommendations
    recommendations.extend(sre_result.recommendations)

    # ── 5. Auto-Create AutoHealActions ─────────────────────────────
    healing_enabled = settings.SELF_HEALING_ENABLED
    approval_required = settings.SELF_HEALING_APPROVAL_REQUIRED

    if healing_enabled:
        critical_categories: set[str] = set()
        for m in sre_result.metrics:
            if m.status == "critical":
                critical_categories.add(m.category)

        for cat in sorted(critical_categories):
            action_type = METRIC_TO_ACTION.get(cat, "script")
            runbook_name = METRIC_TO_RUNBOOK.get(cat, "Generic Response")
            action_config: dict[str, Any] = {
                "trigger_reason": f"{cat} metric critical",
                "runbook": runbook_name,
                "auto_generated": True,
                "sre_context": {
                    category: [
                        {"name": m.name, "value": m.value, "unit": m.unit}
                        for m in sre_result.metrics
                        if m.category == category and m.status == "critical"
                    ]
                    for category in critical_categories
                },
            }

            action = AutoHealAction(
                action_type=action_type,
                action_config=action_config,
                triggered_by="auto",
                status="pending" if approval_required else "approved",
            )
            db.add(action)
            await db.flush()
            await db.refresh(action)
            created_actions.append(
                {
                    "id": str(action.id),
                    "action_type": action_type,
                    "category": cat,
                    "status": action.status,
                }
            )

        if created_actions:
            status_label = "pending (awaiting approval)" if approval_required else "auto-approved"
            recommendations.append(
                f"Created {len(created_actions)} auto-heal action(s) ({status_label}) "
                f"for: {', '.join(sorted(critical_categories))}"
            )

    # ── 6. Automation Opportunity Assessment ───────────────────────
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

    if rb_count == 0 and healing_enabled:
        recommendations.append(
            "Self-healing is enabled but no runbooks exist — create at least one runbook"
        )

    # ── Score ──────────────────────────────────────────────────────
    score = 50.0
    if rb_count >= 3:
        score += 15
    if rb_count >= 5:
        score += 5
    if total > 0:
        score += min(approved * 3, 15)
    score -= failed * 5
    score = max(0, min(100, round(score, 1)))

    # ── Build summary ──────────────────────────────────────────────
    summary_parts = [
        f"{rb_count} runbooks, {total} total actions "
        f"({approved} approved, {rejected} rejected, {pending} pending, {failed} failed)."
    ]
    if sre_result.score < 70:
        summary_parts.append(f"SRE health score: {sre_result.score}/100 (degraded).")
    else:
        summary_parts.append(f"SRE health score: {sre_result.score}/100.")

    if created_actions:
        summary_parts.append(f"Auto-heal actions created: {len(created_actions)}.")
    if healing_enabled:
        summary_parts.append("Self-healing is ENABLED.")
    else:
        summary_parts.append(
            "Self-healing is DISABLED (set SELF_HEALING_ENABLED=true to activate)."
        )

    analysis = AnalysisResult(
        domain="self_healing",
        action="analyze",
        target_id=None,
        title="Self-Healing System Analysis",
        summary=" ".join(summary_parts),
        findings=findings,
        recommendations=recommendations,
        score=score,
        severity="critical"
        if rb_count == 0
        else "warning"
        if score < 50 or sre_result.score < 50
        else "info",
        raw_data={
            "runbook_count": rb_count,
            "action_total": total,
            "action_approved": approved,
            "action_rejected": rejected,
            "action_pending": pending,
            "action_failed": failed,
            "sre_health_score": sre_result.score,
            "healing_enabled": healing_enabled,
            "actions_created": len(created_actions),
        },
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis
