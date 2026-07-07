"""Pydantic schemas for RCA reports."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


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
    timeline: dict | None = None
    metrics_snapshot: dict | None = None
    logs_snapshot: dict | None = None
    changes: dict | None = None
    recommendations: list[str] | None = None
    similar_incidents: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
