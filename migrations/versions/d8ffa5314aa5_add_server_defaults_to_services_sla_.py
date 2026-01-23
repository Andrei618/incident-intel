"""Add server defaults to services SLA columns.

Revision ID: d8ffa5314aa5
Revises: 87ac12c3e8f2
Create Date: 2026-01-22 21:32:42.043684

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8ffa5314aa5"
down_revision: str | Sequence[str] | None = "87ac12c3e8f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add server defaults to SLA columns to match SQLAlchemy model."""
    op.execute("ALTER TABLE services ALTER COLUMN sla_p1_minutes SET DEFAULT 60")
    op.execute("ALTER TABLE services ALTER COLUMN sla_p2_minutes SET DEFAULT 240")
    op.execute("ALTER TABLE services ALTER COLUMN sla_p3_minutes SET DEFAULT 1440")
    op.execute("ALTER TABLE services ALTER COLUMN sla_p4_minutes SET DEFAULT 4320")


def downgrade() -> None:
    """Remove server defaults from SLA columns."""
    op.execute("ALTER TABLE services ALTER COLUMN sla_p1_minutes DROP DEFAULT")
    op.execute("ALTER TABLE services ALTER COLUMN sla_p2_minutes DROP DEFAULT")
    op.execute("ALTER TABLE services ALTER COLUMN sla_p3_minutes DROP DEFAULT")
    op.execute("ALTER TABLE services ALTER COLUMN sla_p4_minutes DROP DEFAULT")
