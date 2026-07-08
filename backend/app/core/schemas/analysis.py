"""Pydantic schemas for analysis results."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AnalysisResultRead(BaseModel):
    id: UUID
    domain: str
    action: str
    target_id: UUID | None = None
    title: str
    summary: str | None = None
    findings: list[Any] | None = None
    recommendations: list[str] | None = None
    score: float | None = None
    severity: str | None = None
    raw_data: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
