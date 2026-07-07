"""Incident and timeline models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_event_id = Column(String(255), nullable=True)
    dd_monitor_id = Column(String(255), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="SEV-3")  # SEV-1..5
    status = Column(String(30), nullable=False, default="active")  # active, stable, resolved
    service = Column(String(200), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    timeline = relationship("IncidentTimeline", back_populates="incident", lazy="selectin", cascade="all, delete-orphan")


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)  # status_change, note, action, escalation
    content = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    incident = relationship("Incident", back_populates="timeline")
