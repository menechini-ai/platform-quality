"""Pydantic schemas for RCA reports."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class RcaReportCreate(BaseModel):
    incident_id: UUID
    summary: str | None = None
    root_cause: str | None = None
    services: list[str] | None = None
    recommendations: list[str] | None = None


class RcaReportRead(BaseModel):
    id: UUID
    incident_id: UUID | None = None
    summary: str | None = None
    root_cause: str | None = None
    confidence: float | None = None
    dependency_chain: Any | None = None
    timeline: Any | None = None
    metrics_snapshot: Any | None = None
    logs_snapshot: Any | None = None
    changes: Any | None = None
    recommendations: Any | None = None
    similar_incidents: Any | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
