"""Incident embedding model for vector similarity search."""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class IncidentEmbedding(Base):
    """Vector embedding of an incident for similarity search.

    Stores the incident summary + root cause as an embedding vector
    using pgvector. Enables finding similar historical incidents
    during ReAct investigation.
    """

    __tablename__ = "incident_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    rca_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rca_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Embedding vector (using text-embedding-3-small = 1536 dimensions)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    # Source text used for embedding
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Model used for embedding
    model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="text-embedding-3-small"
    )
    # Root cause category for filtering
    root_cause_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    # Resolution feedback fields
    resolution_verified: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # boolean as string
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_effective: Mapped[str | None] = mapped_column(String(10), nullable=True)

    incident = relationship("Incident", back_populates="embedding")
    rca_report = relationship("RcaReport", back_populates="embeddings")
