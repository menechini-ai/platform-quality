"""Add v4 resolution tracking fields and incident_embeddings table.

Trims the Alembic autogenerate output to ONLY the additive, safe changes
needed to reconcile the ORM models with the database after the v4-t5/v4-t6
commits (which added resolution fields but never shipped a migration):

- create the missing `incident_embeddings` table
- add resolution columns to `incidents` and `rca_reports`

All NOT NULL / constraint alterations detected by autogenerate were dropped:
they are false-positive drift (model defaults vs existing schema) and would
fail or corrupt data if applied. The `incidents.embedding` column is also
preserved (it is intentionally not mapped on the Incident model).
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision = "ce1b3f5a0f6c"
down_revision = "a3_rca_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("incident_id", sa.UUID(), nullable=False),
        sa.Column("rca_report_id", sa.UUID(), nullable=True),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("root_cause_category", sa.String(length=50), nullable=True),
        sa.Column("severity", sa.String(length=10), nullable=True),
        sa.Column("service", sa.String(length=100), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_verified", sa.String(length=10), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("remediation_effective", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rca_report_id"], ["rca_reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_incident_embeddings_incident_id"),
        "incident_embeddings",
        ["incident_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_incident_embeddings_rca_report_id"),
        "incident_embeddings",
        ["rca_report_id"],
        unique=False,
    )

    op.add_column("incidents", sa.Column("resolution_summary", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("resolution_outcome", sa.String(length=50), nullable=True))
    op.add_column("incidents", sa.Column("resolution_notes", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("resolved_by", sa.String(length=200), nullable=True))

    op.add_column(
        "rca_reports", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("rca_reports", sa.Column("resolution_summary", sa.Text(), nullable=True))
    op.add_column(
        "rca_reports", sa.Column("resolution_verified", sa.String(length=10), nullable=True)
    )
    op.add_column(
        "rca_reports", sa.Column("resolution_outcome", sa.String(length=50), nullable=True)
    )
    op.add_column("rca_reports", sa.Column("resolution_notes", sa.Text(), nullable=True))
    op.add_column("rca_reports", sa.Column("resolved_by", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("rca_reports", "resolved_by")
    op.drop_column("rca_reports", "resolution_notes")
    op.drop_column("rca_reports", "resolution_outcome")
    op.drop_column("rca_reports", "resolution_verified")
    op.drop_column("rca_reports", "resolution_summary")
    op.drop_column("rca_reports", "resolved_at")

    op.drop_column("incidents", "resolved_by")
    op.drop_column("incidents", "resolution_notes")
    op.drop_column("incidents", "resolution_outcome")
    op.drop_column("incidents", "resolution_summary")

    op.drop_index(op.f("ix_incident_embeddings_rca_report_id"), table_name="incident_embeddings")
    op.drop_index(op.f("ix_incident_embeddings_incident_id"), table_name="incident_embeddings")
    op.drop_table("incident_embeddings")
