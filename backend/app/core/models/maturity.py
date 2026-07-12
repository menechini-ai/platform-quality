"""Maturity assessment model for SRE observability maturity (Levels 0-5)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MaturityAssessment(Base):
    """SRE observability maturity assessment run."""

    __tablename__ = "maturity_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    overall_level: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Per-dimension scores (0-100)
    dimensions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Raw data from Datadog queries
    findings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
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
