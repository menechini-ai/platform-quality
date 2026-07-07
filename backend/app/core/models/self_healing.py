"""Self-healing models: runbooks and action history."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class Runbook(Base):
    __tablename__ = "runbooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    triggers = Column(JSON, nullable=True)  # conditions to auto-trigger
    steps = Column(JSON, nullable=False)  # ordered list of actions
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AutoHealAction(Base):
    __tablename__ = "auto_heal_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
    )
    monitor_id = Column(String(255), nullable=True)
    action_type = Column(String(50), nullable=False)  # restart, scale, rollback, script, webhook
    action_config = Column(JSON, nullable=True)
    triggered_by = Column(String(20), default="auto")  # auto, manual
    status = Column(
        String(20), default="pending"
    )  # pending, approved, rejected, running, success, failed
    result = Column(JSON, nullable=True)
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    executed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
