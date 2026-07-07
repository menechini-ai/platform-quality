"""Pydantic schemas for Incidents."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    status: str = Field(default="active", pattern=r"^(active|stable|resolved)$")
    severity: str = Field(default="SEV-3", pattern=r"^SEV-[1-5]$")
    service: str | None = Field(default=None, max_length=200)
    failure_pattern: str | None = Field(default=None, pattern=r"^(deploy|resource|latency|dependency|data_corruption)$")
    tags: list[str] | None = None
    dd_event_id: str | None = None
    dd_monitor_id: str | None = None


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|stable|resolved)$")
    severity: str | None = Field(default=None, pattern=r"^SEV-[1-5]$")
    service: str | None = Field(default=None, max_length=200)
    failure_pattern: str | None = Field(default=None, pattern=r"^(deploy|resource|latency|dependency|data_corruption)$")
    tags: list[str] | None = None
    dd_event_id: str | None = None
    dd_monitor_id: str | None = None


class TimelineEventCreate(BaseModel):
    event_type: str
    content: str | None = None
    author: str | None = None
    metadata: dict | None = None


class TimelineEventRead(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    event_type: str
    content: str | None = None
    author: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    severity: str
    status: str
    service: str | None = None
    failure_pattern: str | None = None
    tags: list[str] | None = None
    dd_event_id: str | None = None
    dd_monitor_id: str | None = None
    started_at: datetime | None = None
    timeline: list[TimelineEventRead] = []
    created_at: datetime
    updated_at: datetime | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}
