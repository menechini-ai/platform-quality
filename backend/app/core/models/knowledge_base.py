"""Knowledge base model for RCA pattern matching."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    symptom_pattern = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    resolution_steps = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
