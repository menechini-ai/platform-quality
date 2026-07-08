"""Pydantic schemas for RCA reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class RcaReportCreate(BaseModel):
    incident_id: uuid.UUID
    summary: str | None = None
    root_cause: str | None = None
    recommendations: list[str] | None = None


class RcaReportRead(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    summary: str | None = None
    root_cause: str | None = None
    timeline: Any | None = None
    metrics_snapshot: Any | None = None
    logs_snapshot: Any | None = None
    changes: Any | None = None
    recommendations: list[str] | None = None
    similar_incidents: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
