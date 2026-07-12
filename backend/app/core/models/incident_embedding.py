"""Incident embedding model for vector similarity search."""
import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class IncidentEmbedding(Base):
    """Vector embedding of an incident for similarity search.

    Stores the incident summary + root cause as an embedding vector
    using pgvector. Enables finding similar historical incidents
    during ReAct investigation.
    """
    __tablename__ = "incident_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    rca_report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rca_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Embedding vector (using text-embedding-3-small = 1536 dimensions)
    embedding = Column(Vector(1536), nullable=False)
    # Source text used for embedding
    source_text = Column(Text, nullable=False)
    # Model used for embedding
    model = Column(String(100), nullable=False, default="text-embedding-3-small")
    # Root cause category for filtering
    root_cause_category = Column(String(50), nullable=True)
    severity = Column(String(10), nullable=True)
    service = Column(String(100), nullable=True)
    environment = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    incident = relationship("Incident", back_populates="embedding")
    rca_report = relationship("RcaReport", back_populates="embeddings")
