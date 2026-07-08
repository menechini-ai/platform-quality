"""Incidents router."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 — needed at runtime for FastAPI path param resolution

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.db import get_db
from app.core.models.incident import Incident, IncidentTimeline
from app.core.schemas.incident import (
    IncidentCreate,
    IncidentRead,
    IncidentUpdate,
    TimelineEventCreate,
    TimelineEventRead,
)

if TYPE_CHECKING:
    from app.auth.schemas import UserInfo

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentRead])
async def list_incidents(
    status: str | None = Query(None, pattern=r"^(active|stable|resolved)$"),
    severity: str | None = Query(None, pattern=r"^SEV-[1-5]$"),
    service: str | None = None,
    failure_pattern: str | None = Query(
        None, pattern=r"^(deploy|resource|latency|dependency|data_corruption)$"
    ),
    tags: str | None = Query(
        None,
        description="Comma-separated tags filter — matches incidents with ANY of these tags (JSON array contains)",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List incidents with optional filters."""
    stmt = select(Incident).order_by(Incident.created_at.desc())
    if status:
        stmt = stmt.where(Incident.status == status)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if service:
        stmt = stmt.where(Incident.service == service)
    if failure_pattern:
        stmt = stmt.where(Incident.failure_pattern == failure_pattern)
    if tags:
        for tag in tags.split(","):
            tag = tag.strip()
            if tag:
                stmt = stmt.where(cast(Incident.tags, String).contains(tag))
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/incidents/summary")
async def incident_summary(db: AsyncSession = Depends(get_db)):
    """Return counts by severity, status, service, failure_pattern."""
    sev = (
        await db.execute(
            select(Incident.severity, func.count(Incident.id).label("cnt")).group_by(
                Incident.severity
            )
        )
    ).all()
    status = (
        await db.execute(
            select(Incident.status, func.count(Incident.id).label("cnt")).group_by(Incident.status)
        )
    ).all()
    svc = (
        await db.execute(
            select(Incident.service, func.count(Incident.id).label("cnt"))
            .where(Incident.service.isnot(None))
            .group_by(Incident.service)
        )
    ).all()
    pattern = (
        await db.execute(
            select(Incident.failure_pattern, func.count(Incident.id).label("cnt"))
            .where(Incident.failure_pattern.isnot(None))
            .group_by(Incident.failure_pattern)
        )
    ).all()
    return {
        "by_severity": {r.severity: r.cnt for r in sev},
        "by_status": {r.status: r.cnt for r in status},
        "by_service": {r.service: r.cnt for r in svc},
        "by_failure_pattern": {r.failure_pattern: r.cnt for r in pattern},
    }


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
async def get_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific incident."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/incidents", response_model=IncidentRead, status_code=201)
async def create_incident(
    data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    _: UserInfo = Depends(get_current_user),
):
    """Create a new incident."""
    incident = Incident(
        title=data.title,
        description=data.description,
        status=data.status,
        severity=data.severity,
        service=data.service,
        failure_pattern=data.failure_pattern,
        tags=data.tags or [],
        dd_event_id=data.dd_event_id,
        dd_monitor_id=data.dd_monitor_id,
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)
    return incident


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
async def update_incident(
    incident_id: UUID,
    data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    _: UserInfo = Depends(get_current_user),
):
    """Update an incident."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)
    await db.flush()
    await db.refresh(incident)
    return incident


@router.delete("/incidents/{incident_id}", status_code=204)
async def delete_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: UserInfo = Depends(get_current_user),
):
    """Delete an incident."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    await db.delete(incident)
    await db.flush()


# --- Timeline sub-resource ---


@router.get(
    "/incidents/{incident_id}/timeline",
    response_model=list[TimelineEventRead],
)
async def list_timeline(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """List timeline events for an incident."""
    result = await db.execute(
        select(IncidentTimeline)
        .where(IncidentTimeline.incident_id == incident_id)
        .order_by(IncidentTimeline.created_at)
    )
    return result.scalars().all()


@router.post(
    "/incidents/{incident_id}/timeline",
    response_model=TimelineEventRead,
    status_code=201,
)
async def create_timeline_event(
    incident_id: UUID,
    data: TimelineEventCreate,
    db: AsyncSession = Depends(get_db),
    _: UserInfo = Depends(get_current_user),
):
    """Add a timeline event to an incident."""
    event = IncidentTimeline(
        incident_id=incident_id,
        event_type=data.event_type,
        content=data.content,
        author=data.author,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event
