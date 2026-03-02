"""Models for ticket management.

Includes Ticket and TicketComment.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from incident_intel.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from incident_intel.models.service import Service
    from incident_intel.models.ticket_document import TicketDocument


class TicketStatus(str, enum.Enum):
    """Valid ticket statuses."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    """Ticket priority levels with SLA implications."""

    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class Ticket(Base, TimestampMixin):
    """Ticket entity representing an issue in the support system.

    Each ticket belongs to a service and has associated comments.
    """

    __tablename__ = "tickets"
    __table_args__ = (
        # Index on created_at (inherited from TimestampMixin)
        Index("ix_tickets_created", "created_at"),
        # Business rule: resolved_at must align with status
        CheckConstraint(
            "(resolved_at IS NULL AND status IN ('open', 'in_progress')) OR "
            "(resolved_at IS NOT NULL AND status IN ('resolved', 'closed'))",
            name="resolved_requires_status",
        ),
    )

    # UUID generation: Both defaults ensure IDs are generated regardless of insertion method
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("services.id", ondelete="CASCADE"),  # Database-level cascade
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(
            TicketStatus,
            native_enum=False,
            validate_strings=True,
            create_constraint=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=TicketStatus.OPEN,
        index=True,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SQLEnum(
            TicketPriority,
            native_enum=False,
            validate_strings=True,
            create_constraint=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    assignee: Mapped[str | None] = mapped_column(String(100), default=None)
    reporter: Mapped[str | None] = mapped_column(String(100), default=None)

    # Relationships (string references to avoid circular imports)
    service: Mapped["Service"] = relationship(
        back_populates="tickets",
        lazy="selectin",  # Async-compatible: lazy load (batched), API only uses service_id
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        back_populates="ticket",
        lazy="selectin",
        cascade="all, delete-orphan",  # ORM-level cascade
    )
    ticket_documents: Mapped[list["TicketDocument"]] = relationship(
        back_populates="ticket",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class TicketComment(Base):
    """Comment on a ticket in the support system.

    Comments are immutable and ordered chronologically per ticket.
    """

    __tablename__ = "ticket_comments"
    __table_args__ = (
        # Composite index on ticket_id, created_at
        Index("ix_ticket_comments_ticket", "ticket_id", "created_at"),
    )

    # UUID generation: Both defaults ensure IDs are generated regardless of insertion method
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),  # Database-level cascade
    )
    author: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),  # ORM-level
        server_default=func.now(),  # Database-level default
    )
    # Relationship
    ticket: Mapped["Ticket"] = relationship(
        back_populates="comments",
        lazy="joined",
    )
