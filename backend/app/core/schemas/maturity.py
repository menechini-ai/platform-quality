"""Pydantic schemas for maturity assessments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MaturityDimension(BaseModel):
    name: str
    score: float  # 0-100
    weight: float = 1.0
    findings: list[str] = []
    recommendations: list[str] = []


class MaturityAssessmentRead(BaseModel):
    id: UUID
    overall_level: int
    overall_score: float
    dimensions: dict
    findings: dict | None = None
    summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
