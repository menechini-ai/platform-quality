"""Report / postmortem / notebook models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base

REPORT_TYPES = ("executive", "monthly", "team_health", "postmortem", "investigation")


class Report(Base):
    """Generated report or postmortem."""

    __tablename__ = "reports"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_type = Column(String(50), nullable=False)  # executive | monthly | team_health | postmortem | investigation
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # Markdown
    tags = Column(JSON, nullable=True, default=list)
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
