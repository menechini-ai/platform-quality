"""Reports router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.models.report import Report
from app.core.schemas.report import ReportCreate, ReportRead
from app.maturity.reports import generate_postmortem, generate_report

router = APIRouter()


@router.get("/reports", response_model=list[ReportRead])
async def list_reports(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all reports."""
    result = await db.execute(
        select(Report).order_by(Report.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.get("/reports/{report_id}", response_model=ReportRead)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific report by ID."""
    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID") from None

    result = await db.execute(select(Report).where(Report.id == uid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/reports", response_model=ReportRead, status_code=201)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a report manually (use /reports/postmortem/:id for auto-generated)."""
    if data.content:
        # Free-form report with custom content
        report = Report(
            report_type=data.report_type,
            title=data.title,
            content=data.content,
            tags=data.tags,
            metadata_={"incident_id": data.incident_id} if data.incident_id else {},
        )
        db.add(report)
        await db.flush()
        await db.refresh(report)
        return report
    report = await generate_report(
        db,
        data.report_type,
        data.title,
        tags=data.tags,
        metadata={"incident_id": data.incident_id} if data.incident_id else {},
    )
    return report


@router.post("/reports/postmortem/{incident_id}", response_model=ReportRead, status_code=201)
async def create_postmortem(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate postmortem from incident + RCA data."""
    try:
        report = await generate_postmortem(db, incident_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return report
