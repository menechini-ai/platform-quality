"""Alembic migration: add service column to runbooks (self-healing scoping).

Revision: a2_runbook_service
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a2_runbook_service"
down_revision = "a1_users_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runbooks",
        sa.Column("service", sa.String(length=200), nullable=True),
    )
    op.create_index("ix_runbooks_service", "runbooks", ["service"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_runbooks_service", table_name="runbooks")
    op.drop_column("runbooks", "service")
