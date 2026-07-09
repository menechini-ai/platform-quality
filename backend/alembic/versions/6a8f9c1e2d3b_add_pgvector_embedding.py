"""Add pgvector extension and embedding columns.

T007 — Enable pgvector support for semantic search.

Revision ID: 6a8f9c1e2d3b
Revises: b4aa597c6610
Create Date: 2026-07-08
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# pgvector Vector type — import works after `pip install pgvector`
try:
    from pgvector.sqlalchemy import Vector

    HAS_PGVECTOR = True
except ImportError:
    Vector = None  # type: ignore[assignment, misc]
    HAS_PGVECTOR = False


revision: str = "6a8f9c1e2d3b"
down_revision: str | None = "b4aa597c6610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if HAS_PGVECTOR:
        op.add_column(
            "incidents",
            sa.Column("embedding", Vector(1536), nullable=True),
        )
        op.add_column(
            "incidents",
            sa.Column("llm_rca", sa.Text(), nullable=True),
        )
        op.add_column(
            "knowledge_base",
            sa.Column("embedding", Vector(1536), nullable=True),
        )


def downgrade() -> None:
    if HAS_PGVECTOR:
        op.drop_column("knowledge_base", "embedding")
        op.drop_column("incidents", "llm_rca")
        op.drop_column("incidents", "embedding")

    op.execute("DROP EXTENSION IF EXISTS vector")
