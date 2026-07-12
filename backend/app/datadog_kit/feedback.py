"""Feedback API for marking resolution and updating embeddings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.db import get_db
from app.core.models.incident import Incident
from app.core.models.incident_embedding import IncidentEmbedding
from app.core.models.rca import RcaReport
from app.datadog_kit.embeddings import upsert_incident_embedding
from app.datadog_kit.models import RcaDiagnosis

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class ResolutionFeedback(BaseModel):
    """Resolution feedback for an investigation."""

    report_id: str
    resolved: bool = True
    resolution_summary: str = Field(..., min_length=10, max_length=2000)
    root_cause_verified: bool = True
    actual_root_cause: str | None = None
    actual_category: str | None = None
    remediation_taken: list[str] = Field(default_factory=list)
    time_to_resolve_minutes: int | None = None
    lessons_learned: str | None = None


class ResolutionResponse(BaseModel):
    """Response after submitting resolution feedback."""

    success: bool
    report_id: str
    incident_id: str | None = None
    embedding_updated: bool = False
    message: str = ""


class IncidentFeedback(BaseModel):
    """Direct incident feedback (without investigation report)."""

    incident_id: str
    title: str
    service: str | None = None
    environment: str | None = None
    severity: str = "P3"
    failure_pattern: str | None = None
    root_cause: str
    root_cause_category: str = "dependency"
    causal_chain: list[str] = Field(default_factory=list)
    remediation_steps: list[str] = Field(default_factory=list)
    resolved_at: datetime | None = None
    time_to_resolve_minutes: int | None = None
    lessons_learned: str | None = None


@router.post("/resolve", response_model=ResolutionResponse)
async def submit_resolution(
    feedback: ResolutionFeedback,
    db: AsyncSession = Depends(get_db),
) -> ResolutionResponse:
    """Mark investigation as resolved and update embeddings for future similarity."""
    import uuid

    try:
        report_uid = uuid.UUID(feedback.report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID") from None

    # Fetch the report
    result = await db.execute(select(RcaReport).where(RcaReport.id == report_uid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Investigation report not found")

    incident_id = str(report.incident_id) if report.incident_id else None

    # Update report with resolution
    report.resolved_at = datetime.now(UTC)
    report.resolution_summary = feedback.resolution_summary
    report.resolution_verified = "true" if feedback.root_cause_verified else "false"
    if feedback.actual_root_cause:
        report.root_cause = feedback.actual_root_cause
    if feedback.actual_category:
        timeline = report.timeline or {}
        timeline["category"] = feedback.actual_category
        report.timeline = timeline
    if feedback.remediation_taken:
        report.recommendations = feedback.remediation_taken
    if feedback.time_to_resolve_minutes:
        timeline = report.timeline or {}
        timeline["time_to_resolve_minutes"] = feedback.time_to_resolve_minutes
        report.timeline = timeline
    if feedback.lessons_learned:
        timeline = report.timeline or {}
        timeline["lessons_learned"] = feedback.lessons_learned
        report.timeline = timeline

    await db.flush()

    # If linked to incident, update incident and embedding
    embedding_updated = False
    if incident_id:
        try:
            inc_result = await db.execute(
                select(Incident).where(Incident.id == uuid.UUID(incident_id))
            )
            incident = inc_result.scalar_one_or_none()

            if incident:
                # Update incident with verified root cause
                if feedback.actual_root_cause:
                    incident.title = feedback.actual_root_cause[:255]
                if feedback.actual_category:
                    incident.failure_pattern = feedback.actual_category
                incident.resolved = feedback.resolved
                incident.resolved_at = datetime.now(UTC) if feedback.resolved else None
                incident.resolution_summary = feedback.resolution_summary

                # Build updated diagnosis for embedding
                diagnosis = RcaDiagnosis(
                    root_cause=feedback.actual_root_cause or report.root_cause or "unknown",
                    root_cause_category=feedback.actual_category
                    or (report.timeline or {}).get("category", "unknown"),
                    causal_chain=(report.timeline or {}).get("causal_chain", []),
                    severity=(report.timeline or {}).get("severity", "P3"),
                    confidence=0.95,  # high confidence after human verification
                    evidence_refs=report.changes or {},
                    remediation_steps=feedback.remediation_taken
                    or (
                        []
                        if not isinstance(report.recommendations, list)
                        else report.recommendations
                    )
                    or [],
                    inconclusive=False,
                )

                # Update embedding with verified resolution
                embedding = await upsert_incident_embedding(
                    incident=incident,
                    diagnosis=diagnosis,
                )
                if embedding:
                    embedding.resolution_verified = (
                        "true" if feedback.root_cause_verified else "false"
                    )
                    embedding.resolution_summary = feedback.resolution_summary
                    embedding.remediation_effective = (
                        "true" if feedback.root_cause_verified else "false"
                    )
                    await db.commit()
                    embedding_updated = True
                    logger.info("Updated embedding for incident %s with resolution", incident_id)
        except Exception as exc:
            logger.warning("Failed to update embedding for incident %s: %s", incident_id, exc)

    await db.commit()
    await db.refresh(report)

    return ResolutionResponse(
        success=True,
        report_id=feedback.report_id,
        incident_id=incident_id,
        embedding_updated=embedding_updated,
        message="Resolution recorded" + (" and embedding updated" if embedding_updated else ""),
    )


@router.post("/incident", response_model=ResolutionResponse)
async def submit_incident_feedback(
    feedback: IncidentFeedback,
    db: AsyncSession = Depends(get_db),
) -> ResolutionResponse:
    """Submit direct incident feedback (creates incident + embedding)."""
    import uuid

    try:
        incident_uid = uuid.UUID(feedback.incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format") from None

    # Check if incident exists
    result = await db.execute(select(Incident).where(Incident.id == incident_uid))
    incident = result.scalar_one_or_none()

    if not incident:
        # Create new incident
        incident = Incident(
            id=incident_uid,
            title=feedback.title,
            service=feedback.service,
            environment=feedback.environment,
            severity=feedback.severity,
            failure_pattern=feedback.failure_pattern,
            resolved=True,
            resolved_at=feedback.resolved_at or datetime.now(UTC),
            resolution_summary=feedback.lessons_learned or "Manual feedback entry",
        )
        db.add(incident)
        await db.flush()

    # Build diagnosis for embedding
    diagnosis = RcaDiagnosis(
        root_cause=feedback.root_cause,
        root_cause_category=feedback.root_cause_category,
        causal_chain=feedback.causal_chain,
        severity=feedback.severity,
        confidence=0.95,
        evidence_refs={},
        remediation_steps=feedback.remediation_steps,
        inconclusive=False,
    )

    # Create/update embedding
    embedding = await upsert_incident_embedding(
        incident=incident,
        diagnosis=diagnosis,
    )

    await db.commit()

    return ResolutionResponse(
        success=True,
        report_id="",
        incident_id=feedback.incident_id,
        embedding_updated=embedding is not None,
        message="Incident feedback recorded and embedding created"
        if embedding
        else "Incident recorded (embedding failed)",
    )


@router.get("/report/{report_id}")
async def get_report_feedback(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get resolution feedback for a report."""
    import uuid

    try:
        report_uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID") from None

    result = await db.execute(select(RcaReport).where(RcaReport.id == report_uid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "report_id": report_id,
        "resolved": report.resolved_at is not None,
        "resolved_at": report.resolved_at,
        "resolution_summary": getattr(report, "resolution_summary", None),
        "resolution_verified": getattr(report, "resolution_verified", None),
        "root_cause": report.root_cause,
        "recommendations": report.recommendations,
        "timeline": report.timeline,
    }


@router.get("/incident/{incident_id}/embedding")
async def get_incident_embedding_status(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get embedding status for an incident."""
    import uuid

    try:
        inc_uid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID") from None

    result = await db.execute(
        select(IncidentEmbedding).where(IncidentEmbedding.incident_id == inc_uid)
    )
    embedding = result.scalar_one_or_none()

    if not embedding:
        return {"incident_id": incident_id, "has_embedding": False}

    return {
        "incident_id": incident_id,
        "has_embedding": True,
        "embedding_id": str(embedding.id),
        "source_text": embedding.source_text[:200] + "..."
        if len(embedding.source_text) > 200
        else embedding.source_text,
        "root_cause_category": embedding.root_cause_category,
        "severity": embedding.severity,
        "service": embedding.service,
        "environment": embedding.environment,
        "resolution_verified": embedding.resolution_verified,
        "resolution_summary": embedding.resolution_summary,
        "remediation_effective": embedding.remediation_effective,
        "created_at": embedding.created_at,
        "updated_at": embedding.updated_at,
    }
