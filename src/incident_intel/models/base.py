"""Base classes for SQLAlchemy 2.0 ORM models.

Provides DeclarativeBase with constraint naming conventions and
a reusable TimestampMixin for audit fields.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models.

    Configures standardized naming conventions for database constraints,
    ensuring consistent and readable constraint names across migrations.
    """

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class TimestampMixin:
    """Mixin providing created_at and updated_at audit fields.

    Timestamps are stored in UTC and automatically managed:
    - created_at: Set on INSERT
    - updated_at: Set on UPDATE
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(UTC),
    )
