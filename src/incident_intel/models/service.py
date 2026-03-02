"""Service model representing IT systems/applications with SLA targets.

Part of the core domain model for ticket management and incident routing.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from incident_intel.models.base import Base, TimestampMixin

# Avoid circular import - only import for type checking
if TYPE_CHECKING:
    from incident_intel.models.document import Document
    from incident_intel.models.ticket import Ticket


class Service(Base, TimestampMixin):
    """Service entity representing an IT system or application.

    Each service has associated tickets, documents, and SLA targets.
    """

    __tablename__ = "services"

    # UUID generation: Both defaults ensure IDs are generated regardless of insertion method
    # - default=uuid.uuid4: Used by ORM (tests, normal app usage)
    # - server_default=text(...): Used by raw SQL (migrations, manual inserts)
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # SLA targets in minutes by priority level
    sla_p1_minutes: Mapped[int] = mapped_column(default=60)  # P1: 1 hour
    sla_p2_minutes: Mapped[int] = mapped_column(default=240)  # P2: 4 hours
    sla_p3_minutes: Mapped[int] = mapped_column(default=1440)  # P3: 24 hours
    sla_p4_minutes: Mapped[int] = mapped_column(default=4320)  # P4: 72 hours

    # Relationships
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="service",
        lazy="selectin",
        cascade="all, delete-orphan",  # ORM-level cascade
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="service",
        lazy="selectin",
        # Let DB handle ON DELETE SET NULL
        # Without it, SQLAlchemy may issue extra SELECT/UPDATE queries when deleting a Service
        passive_deletes=True,
    )
