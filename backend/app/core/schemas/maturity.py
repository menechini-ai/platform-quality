"""Pydantic schemas for maturity assessments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class MaturityDimension(BaseModel):
    name: str
    score: float  # 0-100
    weight: float = 1.0
    findings: list[str] = []
    recommendations: list[str] = []


class MaturityAssessmentRead(BaseModel):
    id: uuid.UUID
    overall_level: int
    overall_score: float
    dimensions: dict
    findings: dict | None = None
    summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
