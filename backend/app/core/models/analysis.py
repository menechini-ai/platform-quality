"""Analysis models — persists analysis/insight results per domain."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class AnalysisResult(Base):
    """Persisted analysis/insight from an agent."""

    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(50), nullable=False, index=True)  # incident, rca, health, self_healing
    action = Column(String(50), nullable=False)  # analyze, correlate, summarize, predict
    target_id = Column(UUID(as_uuid=True), nullable=True)  # FK to incident/rca/runbook etc.
    title = Column(String(300), nullable=False)
    summary = Column(Text, nullable=True)
    findings = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    score = Column(Float, nullable=True)  # 0-100 confidence / health
    severity = Column(String(20), nullable=True)  # info, warning, critical
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
