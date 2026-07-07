"""Analysis router — triggers domain agents for insights."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.models.analysis import AnalysisResult
from app.core.schemas.analysis import AnalysisResultRead

router = APIRouter()


@router.get("/analysis", response_model=list[AnalysisResultRead])
async def list_analysis(
    domain: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List analysis results, optionally filtered by domain."""
    query = select(AnalysisResult).order_by(AnalysisResult.created_at.desc())
    if domain:
        query = query.where(AnalysisResult.domain == domain)
    result = await db.execute(query.offset(offset).limit(limit))
    return result.scalars().all()


@router.get("/analysis/{analysis_id}", response_model=AnalysisResultRead)
async def get_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific analysis result."""
    try:
        uid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID")
    result = await db.execute(select(AnalysisResult).where(AnalysisResult.id == uid))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return entry


@router.post("/analysis/incident/{incident_id}", response_model=AnalysisResultRead, status_code=201)
async def analyze_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run incident analysis agent."""
    from app.analysis.incident_agent import analyze_incident as run

    try:
        return await run(incident_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/analysis/rca/{incident_id}", response_model=AnalysisResultRead, status_code=201)
async def analyze_rca(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run RCA analysis agent."""
    from app.analysis.rca_agent import analyze_rca as run

    try:
        return await run(incident_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/analysis/health", response_model=AnalysisResultRead, status_code=201)
async def analyze_health(
    db: AsyncSession = Depends(get_db),
):
    """Run product health analysis agent."""
    from app.analysis.health_agent import analyze_health as run

    return await run(db)


@router.post("/analysis/self-healing", response_model=AnalysisResultRead, status_code=201)
async def analyze_self_healing(
    db: AsyncSession = Depends(get_db),
):
    """Run self-healing analysis agent."""
    from app.analysis.self_healing_agent import analyze_self_healing as run

    return await run(db)
