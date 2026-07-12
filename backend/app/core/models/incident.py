"""Incident and timeline models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector

    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None  # type: ignore[assignment, misc]

from app.core.db import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dd_monitor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="SEV-3")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    service: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    failure_pattern: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    llm_rca: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resolution tracking fields (V4)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_outcome: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # auto, manual, partial
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    environment: Mapped[str | None] = mapped_column(String(50), nullable=True)

    timeline: Mapped[list["IncidentTimeline"]] = relationship(
        "IncidentTimeline", back_populates="incident", lazy="selectin", cascade="all, delete-orphan"
    )

    embedding = relationship(
        "IncidentEmbedding", back_populates="incident", uselist=False, cascade="all, delete-orphan"
    )


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="timeline")
