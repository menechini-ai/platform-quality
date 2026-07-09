"""Alembic migration: add RCA pipeline columns (confidence, dependency_chain).

Revision: a3_rca_pipeline
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a3_rca_pipeline"
down_revision = "a2_runbook_service"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rca_reports",
        sa.Column("confidence", sa.Float(), nullable=True, server_default=sa.text("0.0")),
    )
    op.add_column(
        "rca_reports",
        sa.Column("dependency_chain", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rca_reports", "dependency_chain")
    op.drop_column("rca_reports", "confidence")
