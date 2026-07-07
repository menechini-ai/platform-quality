"""Maturity assessment engine — evaluates SRE observability maturity (Levels 0-5)
by querying Datadog API and scoring across 8 dimensions."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.maturity import MaturityAssessment

logger = logging.getLogger(__name__)

# Maturity levels definition
LEVELS = [
    {
        "level": 0,
        "name": "Foundation",
        "focus": "Discovery & Planning",
        "min_score": 0,
    },
    {"level": 1, "name": "Reactive", "focus": "Basic Monitoring & Alerting", "min_score": 20},
    {"level": 2, "name": "Proactive", "focus": "SLO Tracking & Automation", "min_score": 40},
    {"level": 3, "name": "Managed", "focus": "Governance & Optimization", "min_score": 60},
    {"level": 4, "name": "Optimized", "focus": "Self-Healing & Predictive", "min_score": 80},
    {"level": 5, "name": "Excellence", "focus": "AI-Driven Operations", "min_score": 95},
]

# Assessment dimensions with weights
DIMENSIONS = [
    {"name": "infrastructure_coverage", "label": "Infrastructure Coverage", "weight": 1.0},
    {"name": "tagging_standardization", "label": "Tagging & Metadata", "weight": 1.0},
    {"name": "monitoring_alerting", "label": "Monitoring & Alerting", "weight": 1.5},
    {"name": "slo_tracking", "label": "SLO Definition & Tracking", "weight": 1.5},
    {"name": "incident_management", "label": "Incident Management", "weight": 1.2},
    {"name": "log_management", "label": "Log Management & Analytics", "weight": 1.0},
    {"name": "cost_optimization", "label": "Cost Optimization", "weight": 0.8},
    {"name": "automation_self_healing", "label": "Automation & Self-Healing", "weight": 1.0},
]


async def run_assessment(
    db: AsyncSession,
    datadog_data: dict[str, Any] | None = None,
) -> MaturityAssessment:
    """Run full maturity assessment. Scores dimensions and computes overall level.

    If datadog_data is provided, uses real data. Otherwise returns baseline 0.
    """
    scores: dict[str, float] = {}
    findings: dict[str, list[str]] = {}

    for dim in DIMENSIONS:
        name = dim["name"]
        score, dim_findings = _score_dimension(name, datadog_data)
        scores[name] = score
        findings[name] = dim_findings

    total_weight = sum(d["weight"] for d in DIMENSIONS)
    weighted_sum = sum(scores[d["name"]] * d["weight"] for d in DIMENSIONS)
    overall_score = round(weighted_sum / total_weight, 1)

    overall_level = 0
    for lvl in reversed(LEVELS):
        if overall_score >= lvl["min_score"]:
            overall_level = lvl["level"]
            break

    summary = _generate_summary(overall_level, overall_score, scores)

    assessment = MaturityAssessment(
        overall_level=overall_level,
        overall_score=overall_score,
        dimensions=scores,
        findings=findings,
        summary=summary,
    )
    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)
    return assessment


def _score_dimension(
    name: str,
    datadog_data: dict[str, Any] | None,
) -> tuple[float, list[str]]:
    """Score a single dimension 0-100."""
    if not datadog_data or not datadog_data.get(name):
        return (0.0, ["No Datadog data available for this dimension"])

    dim = datadog_data.get(name, {})
    score = min(dim.get("score", 0), 100.0)
    issues = dim.get("findings", [])
    return (score, issues)


def _generate_summary(
    level: int, score: float, scores: dict[str, float]
) -> str:
    """Generate human-readable summary."""
    level_name = LEVELS[level]["name"]
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    bottom = sorted(scores.items(), key=lambda x: x[1])

    lines = [
        "## Maturity Assessment Summary\n",
        f"**Overall Level:** {level} — {level_name}",
        f"**Overall Score:** {score}/100\n",
        "### Strongest Areas",
        *[f"- {d}: {s}/100" for d, s in top[:3]],
        "\n### Needs Improvement",
        *[f"- {d}: {s}/100" for d, s in bottom[:3]],
    ]
    return "\n".join(lines)


def gap_analysis(current_level: int, target_level: int) -> list[dict[str, Any]]:
    """Compare current vs target level, return gaps and recommended steps."""
    if target_level <= current_level:
        return []

    gaps = []
    for level in range(current_level + 1, target_level + 1):
        lvl_def = LEVELS[level]
        gaps.append({
            "target_level": level,
            "name": lvl_def["name"],
            "focus": lvl_def["focus"],
            "required_score": lvl_def["min_score"],
            "steps": _steps_for_level(level),
        })
    return gaps


def _steps_for_level(level: int) -> list[str]:
    """Return recommended implementation steps for a target level."""
    steps = {
        1: [
            "Deploy Datadog agents on ≥80% of production hosts",
            "Create core infrastructure dashboards",
            "Configure ≥5 critical monitors for service availability",
            "Enable log collection from key services",
            "Establish on-call rotation and incident response process",
        ],
        2: [
            "Define and track SLOs for critical user journeys",
            "Implement standardized tagging (env, service, team)",
            "Set up automated alerting with proper routing",
            "Create service-level dashboards with SLO burn-rate",
            "Establish error budgets and release gating",
        ],
        3: [
            "Implement governance policies and RBAC",
            "Set up cost optimization dashboards and budgets",
            "Create automated runbooks for common incidents",
            "Enable security monitoring and compliance reporting",
            "Establish postmortem culture with automated reports",
        ],
        4: [
            "Deploy self-healing automation for known failure modes",
            "Implement predictive analytics for capacity planning",
            "Set up automated remediation pipelines",
            "Create platform engineering self-service capabilities",
            "Implement advanced APM and distributed tracing",
        ],
        5: [
            "AI-driven incident detection and root cause analysis",
            "Fully automated self-healing with approval gates",
            "Cross-service dependency mapping and chaos engineering",
            "Industry benchmarking and continuous improvement",
            "Community contributions and thought leadership",
        ],
    }
    return steps.get(level, [])
