"""RCA report model."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class RcaReport(Base):
    __tablename__ = "rca_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=True,
    )
    summary = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    timeline = Column(JSON, nullable=True)
    metrics_snapshot = Column(JSON, nullable=True)
    logs_snapshot = Column(JSON, nullable=True)
    changes = Column(JSON, nullable=True)  # code changes, config changes
    recommendations = Column(JSON, nullable=True)
    similar_incidents = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    embeddings = relationship("IncidentEmbedding", back_populates="rca_report")
