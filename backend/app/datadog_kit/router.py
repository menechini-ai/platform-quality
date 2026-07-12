"""Investigation endpoint — parallel Datadog signal fetch + structured RCA."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_db
from app.core.models.rca import RcaReport
from app.core.schemas.rca import RcaReportRead
from app.datadog.client import DatadogClient
from app.datadog_kit.agent import investigate_react
from app.datadog_kit.collector import fetch_all
from app.datadog_kit.config import DatadogKitConfig
from app.datadog_kit.diagnosis import analyze
from app.datadog_kit.embeddings import get_similar_incidents_context, search_similar_incidents
from app.datadog_kit.models import InvestigationRequest, InvestigationRequestV3  # noqa: TC001
from app.datadog_kit.playbook_executor import (
    PlaybookExecutor,
    PlaybookStep,
    StepType,
    build_playbook_from_runbook,
)
from app.datadog_kit.notifications import (
    NotificationChannel,
    NotificationDispatcher,
    NotificationPayload,
    NotificationPriority,
    build_incident_notification,
    build_playbook_notification,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datadog", tags=["datadog-investigate"])


def check_feature_enabled(feature: str):
    """Dependency to check if a V4 feature is enabled."""
    def _check():
        if not getattr(settings, feature, True):
            raise HTTPException(status_code=503, detail=f"Feature {feature} is disabled")
    return Depends(_check)


@router.post("/investigate", response_model=RcaReportRead)
async def investigate(
    request: InvestigationRequest,
    db: AsyncSession = Depends(get_db),
    _: None = check_feature_enabled("ENABLE_REACT_AGENT"),
) -> RcaReport:
    """Run a full investigation: fetch 4 Datadog signals in parallel,
    then produce a structured RCA diagnosis. Result is saved as an RCA report."""
    config = DatadogKitConfig(
        default_time_range_minutes=request.time_range_minutes,
    )

    # Step 1: Collect signals
    investigation = await fetch_all(request, config)

    # Step 2: Diagnose using LLM
    diagnosis = await analyze(investigation)

    # Step 3: Build evidence snapshots
    error_logs = [
        entry.model_dump()
        for entry in investigation.logs.logs
        if entry.status.lower() in ("error", "critical", "fatal")
    ]

    # Step 4: Link Datadog incident if provided
    incident_id = request.incident_id
    if incident_id:
        client = DatadogClient()
        try:
            incident_data = await client.call(client.get_incident, incident_id=incident_id)
            logger.info(f"Linked incident {incident_id}: {incident_data.get('title', '')}")
        except Exception as exc:
            logger.warning(f"Failed to fetch incident {incident_id}: {exc}")

    # Step 5: Save to DB
    report = RcaReport(
        incident_id=incident_id,  # optional — linked if provided
        summary=f"Investigation for: {request.query}",
        root_cause=diagnosis.root_cause,
        recommendations=diagnosis.remediation_steps,
        timeline={
            "causal_chain": diagnosis.causal_chain,
            "severity": diagnosis.severity,
            "confidence": diagnosis.confidence,
            "inconclusive": diagnosis.inconclusive,
            "category": diagnosis.root_cause_category,
        },
        metrics_snapshot={
            "series": [s.model_dump() for s in investigation.metrics.series],
            "total_duration_ms": investigation.total_duration_ms,
        },
        logs_snapshot={
            "total": investigation.logs.total,
            "errors": error_logs[:20],
            "query": investigation.query,
        },
        changes=diagnosis.evidence_refs,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    logger.info(
        "Investigation complete: query=%s confidence=%.2f duration=%dms",
        request.query,
        diagnosis.confidence,
        investigation.total_duration_ms,
    )

    return report


@router.post("/investigate/v3", response_model=RcaReportRead)
async def investigate_v3(
    request: InvestigationRequestV3,
    db: AsyncSession = Depends(get_db),
    _: None = check_feature_enabled("ENABLE_REACT_AGENT"),
) -> RcaReport:
    """Run ReAct investigation loop: iterative tool use + LLM reasoning.
    Returns enhanced RCA with react_trace, runbook, and MTTR breakdown.
    """
    # Use new ReAct agent
    result = await investigate_react(request)

    # Step: Link Datadog incident if provided
    incident_id = request.incident_id
    if incident_id:
        client = DatadogClient()
        try:
            incident_data = await client.call(client.get_incident, incident_id=incident_id)
            logger.info("Linked incident %s: %s", incident_id, incident_data.get("title", ""))
        except Exception as exc:
            logger.warning("Failed to fetch incident %s: %s", incident_id, exc)

    # Build error logs snapshot
    error_logs = [
        entry.model_dump()
        for entry in result.logs.logs
        if entry.status.lower() in ("error", "critical", "fatal")
    ]

    # Save to DB with V3 enhancements
    report = RcaReport(
        incident_id=incident_id,
        summary=f"ReAct Investigation for: {request.query}",
        root_cause=result.diagnosis.root_cause if result.diagnosis else "Unknown",
        recommendations=result.diagnosis.remediation_steps if result.diagnosis else [],
        timeline={
            "causal_chain": result.diagnosis.causal_chain if result.diagnosis else [],
            "severity": result.diagnosis.severity if result.diagnosis else "P3",
            "confidence": result.diagnosis.confidence if result.diagnosis else 0.0,
            "inconclusive": result.diagnosis.inconclusive if result.diagnosis else True,
            "category": result.diagnosis.root_cause_category if result.diagnosis else "dependency",
            "react_trace": [
                t.model_dump() for t in result.react_trace
            ] if result.react_trace else [],
            "runbook": result.runbook.model_dump() if result.runbook else None,
            "mttr_breakdown": (
                result.mttr_breakdown.model_dump() if result.mttr_breakdown else None
            ),
        },
        metrics_snapshot={
            "series": [s.model_dump() for s in result.metrics.series],
            "total_duration_ms": result.total_duration_ms,
        },
        logs_snapshot={
            "total": result.logs.total,
            "errors": error_logs[:20],
            "query": result.query,
        },
        changes=result.diagnosis.evidence_refs if result.diagnosis else {},
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    logger.info(
        "ReAct investigation complete: query=%s turns=%d duration=%dms",
        request.query,
        len(result.react_trace),
        result.total_duration_ms,
    )

    return report


@router.post("/playbooks/execute")
async def execute_playbook(
    request: dict,
    dry_run: bool = True,
    auto_confirm: bool = False,
    _: None = check_feature_enabled("ENABLE_PLAYBOOK_EXECUTOR"),
):
    """Execute a playbook from runbook mitigation steps.

    Body: { "runbook": {...}, "dry_run": true, "auto_confirm": false }
    """
    runbook = request.get("runbook")
    if not runbook:
        raise HTTPException(status_code=400, detail="runbook required")

    steps = build_playbook_from_runbook(runbook)
    executor = PlaybookExecutor(dry_run=dry_run, auto_confirm=auto_confirm)
    execution = await executor.execute(steps)

    return {
        "overall_status": execution.overall_status.value,
        "duration_seconds": execution.duration_seconds,
        "steps": [
            {
                "step_name": s.step_name,
                "status": s.status.value,
                "output": s.output,
                "error": s.error,
                "duration_seconds": s.duration_seconds,
            }
            for s in execution.steps
        ],
    }


@router.post("/playbooks/steps")
async def execute_playbook_steps(
    request: dict,
    dry_run: bool = True,
    auto_confirm: bool = False,
    _: None = check_feature_enabled("ENABLE_PLAYBOOK_EXECUTOR"),
):
    """Execute custom playbook steps directly.

    Body: {
        "steps": [
            {
                "type": "kubectl|helm|scale_deployment|restart_deployment|flip_feature_flag|run_script|http_request",
                "name": "step name",
                "params": {...},
                "requires_confirmation": true
            }
        ],
        "dry_run": true
    }
    """
    steps_data = request.get("steps", [])
    if not steps_data:
        raise HTTPException(status_code=400, detail="steps required")

    steps = [PlaybookStep(**s) for s in steps_data]
    executor = PlaybookExecutor(dry_run=dry_run, auto_confirm=auto_confirm)
    execution = await executor.execute(steps)

    return {
        "overall_status": execution.overall_status.value,
        "duration_seconds": execution.duration_seconds,
        "steps": [
            {
                "step_name": s.step_name,
                "status": s.status.value,
                "output": s.output,
                "error": s.error,
                "duration_seconds": s.duration_seconds,
            }
            for s in execution.steps
        ],
    }


@router.post("/notifications/send")
async def send_notification(
    payload: NotificationPayload,
    channels: list[NotificationChannel] | None = None,
    _: None = check_feature_enabled("ENABLE_NOTIFICATIONS"),
):
    """Send notification to configured channels.

    Body: NotificationPayload
    Query: channels=[slack,telegram,pagerduty] (optional, defaults to all configured)
    """
    dispatcher = NotificationDispatcher()
    results = await dispatcher.send(payload, channels)
    return {
        "results": [
            {
                "channel": r.channel.value,
                "success": r.success,
                "external_id": r.external_id,
                "message": r.message,
                "error": r.error,
            }
            for r in results
        ]
    }


@router.post("/notifications/incident")
async def notify_incident(
    request: dict,
    channels: list[NotificationChannel] | None = None,
    _: None = check_feature_enabled("ENABLE_NOTIFICATIONS"),
):
    """Build and send incident notification from investigation result.

    Body: {
        "incident_title": "...",
        "diagnosis": {...},  # RcaDiagnosis dict
        "incident_id": "...",
        "runbook_url": "...",
        "investigation_url": "..."
    }
    """
    dispatcher = NotificationDispatcher()
    notification = build_incident_notification(
        incident_title=request["incident_title"],
        diagnosis=request["diagnosis"],
        incident_id=request.get("incident_id"),
        runbook_url=request.get("runbook_url"),
        investigation_url=request.get("investigation_url"),
    )
    results = await dispatcher.send(notification, channels)
    return {
        "results": [
            {
                "channel": r.channel.value,
                "success": r.success,
                "external_id": r.external_id,
                "message": r.message,
                "error": r.error,
            }
            for r in results
        ]
    }


@router.post("/notifications/playbook")
async def notify_playbook(
    request: dict,
    channels: list[NotificationChannel] | None = None,
    _: None = check_feature_enabled("ENABLE_NOTIFICATIONS"),
):
    """Build and send playbook execution notification.

    Body: {
        "playbook_title": "...",
        "execution": {...},  # PlaybookExecution dict
        "investigation_url": "..."
    }
    """
    dispatcher = NotificationDispatcher()
    notification = build_playbook_notification(
        playbook_title=request["playbook_title"],
        execution=request["execution"],
        investigation_url=request.get("investigation_url"),
    )
    results = await dispatcher.send(notification, channels)
    return {
        "results": [
            {
                "channel": r.channel.value,
                "success": r.success,
                "external_id": r.external_id,
                "message": r.message,
                "error": r.error,
            }
            for r in results
        ]
    }


@router.get("/investigate/{report_id}", response_model=RcaReportRead)
async def get_investigation_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> RcaReport:
    """Retrieve a saved investigation report by ID."""
    import uuid

    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID") from None

    result = await db.execute(select(RcaReport).where(RcaReport.id == uid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Investigation report not found")
    return report


@router.get("/similar-incidents/{incident_id}")
async def get_similar_incidents(
    incident_id: str,
    threshold: float = 0.75,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    _: None = check_feature_enabled("ENABLE_VECTOR_SEARCH"),
):
    """Get similar historical incidents for an incident ID."""
    import uuid

    try:
        uid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID") from None

    # Get the incident's embedding text
    from app.core.models.incident import Incident
    from app.core.models.incident_embedding import IncidentEmbedding
    from sqlalchemy import select

    result = await db.execute(
        select(IncidentEmbedding)
        .join(Incident, IncidentEmbedding.incident_id == Incident.id)
        .where(Incident.id == uid)
    )
    embedding = result.scalar_one_or_none()

    if not embedding:
        return {"similar_incidents": [], "message": "No embedding found for this incident"}

    similar = await search_similar_incidents(
        query_text=embedding.source_text,
        limit=limit,
        threshold=threshold,
        root_cause_category=embedding.root_cause_category,
    )

    return {
        "incident_id": incident_id,
        "similar_incidents": [
            {
                "incident_id": str(e.incident_id),
                "rca_report_id": str(e.rca_report_id) if e.rca_report_id else None,
                "summary": e.source_text[:200] + "..." if len(e.source_text) > 200 else e.source_text,
                "root_cause_category": e.root_cause_category,
                "severity": e.severity,
                "service": e.service,
                "similarity": round(score, 3),
            }
            for e, score in similar
        ],
    }
