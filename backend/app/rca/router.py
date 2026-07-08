"""RCA router: generate and retrieve root cause analysis reports."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.db import get_db
from app.core.models.rca import RcaReport
from app.core.schemas.rca import RcaReportCreate, RcaReportRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/rca", response_model=list[RcaReportRead])
async def list_rca_reports(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all RCA reports."""
    result = await db.execute(
        select(RcaReport).order_by(RcaReport.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.get("/rca/{rca_id}", response_model=RcaReportRead)
async def get_rca_report(rca_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific RCA report."""
    try:
        uid = uuid.UUID(rca_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid RCA ID") from None

    result = await db.execute(select(RcaReport).where(RcaReport.id == uid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="RCA report not found")
    return report


@router.post("/rca", response_model=RcaReportRead, status_code=201)
async def create_rca_report(
    data: RcaReportCreate,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new RCA report for an incident."""
    incident_uid = data.incident_id  # already UUID from Pydantic

    # Check if RCA already exists for this incident
    existing = await db.execute(select(RcaReport).where(RcaReport.incident_id == incident_uid))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="RCA report already exists for this incident")

    report = RcaReport(
        incident_id=incident_uid,
        summary=data.summary,
        root_cause=data.root_cause,
        recommendations=data.recommendations,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report
