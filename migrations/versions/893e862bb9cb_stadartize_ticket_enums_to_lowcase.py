"""stadartize ticket enums to lowcase.

Revision ID: 893e862bb9cb
Revises: d8ffa5314aa5
Create Date: 2026-02-17 15:53:10.532601
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "893e862bb9cb"
down_revision: str | Sequence[str] | None = "d8ffa5314aa5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade: convert ticket enums from native PostgreSQL to VARCHAR + lowercase."""
    # Drop the business-logic CHECK constraint (references old enum)
    op.drop_constraint(
        constraint_name=op.f(name="ck_tickets_resolved_requires_status"),
        table_name="tickets",
        type_="check",
    )

    # Change status column from ENUM type → VARCHAR
    op.alter_column(
        table_name="tickets",
        column_name="status",
        existing_type=postgresql.ENUM(
            "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="ticketstatus"
        ),
        type_=sa.String(length=20),  # native_enum=False stores as VARCHAR
        existing_nullable=False,
    )
    op.alter_column(
        table_name="tickets",
        column_name="priority",
        existing_type=postgresql.ENUM("P1", "P2", "P3", "P4", name="ticketpriority"),
        type_=sa.String(length=20),  # native_enum=False stores as VARCHAR
        existing_nullable=False,
    )

    # Convert existing data to lowercase
    op.execute("UPDATE tickets SET status = LOWER(status)")
    op.execute("UPDATE tickets SET priority = LOWER(priority)")
    # Drop the old PostgreSQL ENUM types

    op.execute("DROP TYPE IF EXISTS ticketstatus")
    op.execute("DROP TYPE IF EXISTS ticketpriority")

    # Recreate the resolved_requires_status CHECK constraint
    op.create_check_constraint(
        constraint_name=op.f("ck_tickets_resolved_requires_status"),
        table_name="tickets",
        condition="(resolved_at IS NULL AND status IN ('open', 'in_progress')) "
        "OR (resolved_at IS NOT NULL AND status IN ('resolved', 'closed'))",
    )


def downgrade() -> None:
    """Downgrade: revert to native PostgreSQL enums with uppercase values."""
    # Drop the lowercase CHECK constraint
    op.drop_constraint(
        constraint_name=op.f(name="ck_tickets_resolved_requires_status"),
        table_name="tickets",
        type_="check",
    )

    # Convert data back to UPPERCASE (while still VARCHAR)
    op.execute("UPDATE tickets SET status = UPPER(status)")
    op.execute("UPDATE tickets SET priority = UPPER(priority)")

    # Recreate PostgreSQL ENUM types
    op.execute("CREATE TYPE ticketstatus AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')")
    op.execute("CREATE TYPE ticketpriority AS ENUM ('P1', 'P2', 'P3', 'P4')")

    # Alter columns back to ENUM type
    op.alter_column(
        table_name="tickets",
        column_name="status",
        existing_type=sa.String(length=20),
        type_=postgresql.ENUM("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="ticketstatus"),
        existing_nullable=False,
        postgresql_using="status::ticketstatus",
    )
    op.alter_column(
        table_name="tickets",
        column_name="priority",
        existing_type=sa.String(length=20),
        type_=postgresql.ENUM("P1", "P2", "P3", "P4", name="ticketpriority"),
        existing_nullable=False,
        postgresql_using="priority::ticketpriority",
    )

    # Recreate original CHECK constraint with ENUM casting
    op.create_check_constraint(
        constraint_name=op.f("ck_tickets_resolved_requires_status"),
        table_name="tickets",
        condition="(resolved_at IS NULL AND status IN ('OPEN', 'IN_PROGRESS')) "
        "OR (resolved_at IS NOT NULL AND status IN ('RESOLVED', 'CLOSED'))",
    )
