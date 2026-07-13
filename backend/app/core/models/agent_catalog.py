"""Pattern Catalog models for AI SRE Agent (Versus parity)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PatternCatalog(Base):
    """
    Learned log patterns catalog.

    Each unique log pattern discovered by the agent is stored here.
    The agent compares incoming log lines against known patterns.
    New patterns trigger incidents in 'detect' mode.
    """

    __tablename__ = "pattern_catalog"
    __table_args__ = (
        Index("ix_pattern_catalog_source_rule", "source_name", "rule_name"),
        Index("ix_pattern_catalog_signature", "signature"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    rule_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signature: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    example_line: Mapped[str] = mapped_column(Text, nullable=False)
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    sightings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    status: Mapped[Literal["new", "known", "ignored"]] = mapped_column(
        String(20), nullable=False, default="new"
    )
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Redacted version for display
    redacted_example: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PatternCatalog {self.source_name}/{self.rule_name} #{self.sightings}>"


class AgentIncident(Base):
    """
    Incidents created by the AI Agent.

    Separate from user-created incidents - these are auto-detected
    from novel log patterns.
    """

    __tablename__ = "agent_incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pattern_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pattern_catalog.id"), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="SEV-3")
    status: Mapped[Literal["open", "acknowledged", "resolved"]] = mapped_column(
        String(30), nullable=False, default="open"
    )
    log_line: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    pattern: Mapped[PatternCatalog] = relationship("PatternCatalog", lazy="selectin")


class AgentSourceCursor(Base):
    """
    Cursor tracking for each log source.

    Redis-backed in Versus; we use DB for simplicity.
    Stores the last processed position/offset for each source.
    """

    __tablename__ = "agent_source_cursors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cursor_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
