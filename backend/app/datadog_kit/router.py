"""Investigation endpoint — parallel Datadog signal fetch + structured RCA."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.db import get_db
from app.core.models.rca import RcaReport
from app.core.schemas.rca import RcaReportRead
from app.datadog_kit.collector import fetch_all
from app.datadog_kit.config import DatadogKitConfig
from app.datadog_kit.diagnosis import analyze
from app.datadog_kit.models import InvestigationRequest  # noqa: TC001

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datadog", tags=["datadog-investigate"])


@router.post("/investigate", response_model=RcaReportRead)
async def investigate(
    request: InvestigationRequest,
    db: AsyncSession = Depends(get_db),
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

    # Step 4: Save to DB
    report = RcaReport(
        incident_id=None,  # optional — can be linked later
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
