"""Pydantic schemas for maturity assessments."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
    findings: Optional[dict] = None
    summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
