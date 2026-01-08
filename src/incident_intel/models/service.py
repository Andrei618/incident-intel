"""Service model representing IT systems/applications with SLA targets.

Part of the core domain model for ticket management and incident routing.
"""

import uuid

from sqlalchemy import String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from incident_intel.models.base import Base, TimestampMixin


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
    sla_p1_minutes: Mapped[int] = mapped_column(default=60)  # P1:  1 hour
    sla_p2_minutes: Mapped[int] = mapped_column(default=240)  # P2:  4 hours
    sla_p3_minutes: Mapped[int] = mapped_column(default=1440)  # P3: 24 hours
    sla_p4_minutes: Mapped[int] = mapped_column(default=4320)  # P4: 72 hours
