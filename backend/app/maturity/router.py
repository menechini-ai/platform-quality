"""Maturity assessment router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.models.maturity import MaturityAssessment
from app.core.schemas.maturity import MaturityAssessmentRead
from app.maturity.service import gap_analysis, run_assessment

router = APIRouter()


@router.get("/maturity", response_model=list[MaturityAssessmentRead])
async def list_assessments(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List maturity assessments, most recent first."""
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
    """Get the most recent maturity assessment."""
    result = await db.execute(
        select(MaturityAssessment).order_by(MaturityAssessment.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/maturity/assess", response_model=MaturityAssessmentRead, status_code=201)
async def assess_maturity(
    db: AsyncSession = Depends(get_db),
):
    """Run a quick maturity assessment (baseline score without Datadog data)."""
    assessment = await run_assessment(db)
    return assessment


@router.get("/maturity/gap", response_model=list[dict[str, Any]])
async def get_gap_analysis(
    current: int = Query(default=0, ge=0, le=5),
    target: int = Query(default=3, ge=0, le=5),
):
    """Get gap analysis between current and target maturity levels."""
    return gap_analysis(current, target)


@router.get("/maturity/levels")
async def list_levels():
    """List all maturity level definitions."""
    from app.maturity.service import DIMENSIONS, LEVELS

    return {"levels": LEVELS, "dimensions": DIMENSIONS}
