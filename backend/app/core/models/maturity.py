"""Maturity assessment model for SRE observability maturity (Levels 0-5)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class MaturityAssessment(Base):
    """SRE observability maturity assessment run."""

    __tablename__ = "maturity_assessments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    overall_level = Column(Integer, nullable=False)  # 0-5
    overall_score = Column(Float, nullable=False)  # 0-100

    # Per-dimension scores (0-100)
    dimensions = Column(JSON, nullable=False, default=dict)

    # Raw data from Datadog queries
    findings = Column(JSON, nullable=True)

    summary = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "overall_level": self.overall_level,
            "overall_score": self.overall_score,
            "dimensions": self.dimensions or {},
            "findings": self.findings or {},
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
