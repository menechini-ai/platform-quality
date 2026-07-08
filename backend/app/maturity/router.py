"""Maturity assessment router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.db import get_db
from app.core.models.maturity import MaturityAssessment
from app.core.schemas.maturity import MaturityAssessmentRead
from app.datadog.client import DatadogClient
from app.maturity.service import DIMENSIONS, LEVELS, gap_analysis, run_assessment

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def _collect_datadog_data() -> dict[str, Any]:
    """Query Datadog APIs and score each maturity dimension (0-100)."""
    try:
        dd = DatadogClient()
    except Exception:
        return {}

    data: dict[str, Any] = {}

    try:
        mons = dd.list_monitors()
        host_count = len({m.get("query", "").split("{")[0] for m in mons if m.get("query")})
        tag_score = 0
        if mons:
            tagged = sum(1 for m in mons if m.get("tags"))
            tag_score = round(tagged / len(mons) * 100, 1)
        alert_count = sum(1 for m in mons if m.get("overall_state") in ("alert", "warn"))
        slos = dd.list_slos()
        incs = dd.list_incidents()
    except Exception as e:
        dd.close()
        return {"infrastructure_coverage": {"score": 0, "findings": [f"Datadog query failed: {e}"]}}

    data["infrastructure_coverage"] = {
        "score": min(len(mons) * 10, 100),
        "findings": [f"{len(mons)} monitors covering {host_count} service types"]
        if mons
        else ["No monitors"],
    }
    data["tagging_standardization"] = {
        "score": tag_score,
        "findings": [f"{int(tag_score * len(mons) / 100)}/{len(mons)} monitors tagged"],
    }
    data["monitoring_alerting"] = {
        "score": min(len(mons) * 8, 100),
        "findings": [f"{len(mons)} monitors, {alert_count} alerting"],
    }
    data["slo_tracking"] = {
        "score": min(len(slos) * 30, 100),
        "findings": [f"{len(slos)} SLOs defined"] if slos else ["No SLOs defined"],
    }
    data["incident_management"] = {
        "score": min(len(incs) * 20, 100),
        "findings": [f"{len(incs)} incidents logged"],
    }
    data["log_management"] = {"score": 15, "findings": ["Log API configured"]}
    data["cost_optimization"] = {
        "score": min(len(mons) * 5, 50),
        "findings": ["Inferred from infra coverage"],
    }
    data["automation_self_healing"] = {"score": 10, "findings": ["Self-healing not yet configured"]}

    dd.close()
    return data


@router.get("/maturity", response_model=list[MaturityAssessmentRead])
async def list_assessments(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MaturityAssessment)
        .order_by(MaturityAssessment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/maturity/latest", response_model=MaturityAssessmentRead | None)
async def latest_assessment(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MaturityAssessment).order_by(MaturityAssessment.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/maturity/assess", response_model=MaturityAssessmentRead, status_code=201)
async def assess_maturity(
    db: AsyncSession = Depends(get_db),
):
    dd_data = _collect_datadog_data()
    assessment = await run_assessment(db, datadog_data=dd_data)
    return assessment


@router.get("/maturity/gap", response_model=list[dict[str, Any]])
async def get_gap_analysis(
    current: int = Query(default=0, ge=0, le=5),
    target: int = Query(default=3, ge=0, le=5),
):
    return gap_analysis(current, target)


@router.get("/maturity/levels")
async def list_levels():
    return {"levels": LEVELS, "dimensions": DIMENSIONS}
