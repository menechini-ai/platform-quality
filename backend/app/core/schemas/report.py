"""Pydantic schemas for reports."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    report_type: str = Field(..., pattern=r"^(executive|monthly|team_health|postmortem|investigation)$")
    title: str = Field(..., max_length=500)
    incident_id: Optional[str] = None
    tags: list[str] = []


class ReportRead(BaseModel):
    id: uuid.UUID
    report_type: str
    title: str
    content: str
    tags: Optional[list] = None
    metadata_: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
