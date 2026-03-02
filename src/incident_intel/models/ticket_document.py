"""Junction table for Tickets and Documents.

Allows M:N relationship between Tickets and Documents with metadata.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from incident_intel.models.base import Base

if TYPE_CHECKING:
    from incident_intel.models.document import Document
    from incident_intel.models.ticket import Ticket


class TicketDocument(Base):
    """Junction entity for M:N relationship.

    Establishes relationship to both parents: Tickets and Documents.
    Parent models have relationships to junction entity.
    """

    __tablename__ = "ticket_documents"
    __table_args__ = (UniqueConstraint("ticket_id", "document_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )
    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        default=None,
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationship
    ticket: Mapped["Ticket"] = relationship(
        back_populates="ticket_documents",
        lazy="joined",
    )
    document: Mapped["Document"] = relationship(
        back_populates="ticket_documents",
        lazy="joined",
    )
