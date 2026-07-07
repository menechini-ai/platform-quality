"""Health / SLO models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class Slo(Base):
    __tablename__ = "slos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dd_id = Column(String(255), nullable=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    target = Column(Float, nullable=False)
    time_window = Column(String(10), nullable=False)  # 7d, 30d, 90d
    service = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service = Column(String(200), nullable=False, index=True)
    sli_name = Column(String(300), nullable=False)
    slo_target = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    burn_rate = Column(Float, nullable=True)
    error_budget_remaining = Column(Float, nullable=True)
    status = Column(String(20), nullable=True)  # healthy, warning, critical
    snapshot_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
