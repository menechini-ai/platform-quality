"""Add resolved + environment columns to the incidents table.

Trimming note: the autogenerate also proposed dropping `incidents.embedding`,
altering many NOT NULL constraints, and dropping `rca_reports_incident_id_key`.
Those are pre-existing model/DB drift unrelated to this change and were removed.
Only the two new additive columns are applied.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3414e8aa840c"
down_revision = "ce1b3f5a0f6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("incidents", sa.Column("environment", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "environment")
    op.drop_column("incidents", "resolved")
