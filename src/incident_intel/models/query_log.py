"""Model for query analytics logging."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from incident_intel.models.base import Base

if TYPE_CHECKING:
    from incident_intel.models.conversation import Conversation


class Route(enum.Enum):
    """Routes of app used by API."""

    SQL = "sql"
    VECTOR = "vector"
    HYBRID = "hybrid"
    CLARIFY = "clarify"


class QueryLog(Base):
    """Query log entity.

    Query logs related to conversations, but could exist itself.
    """

    __tablename__ = "query_logs"
    __table_args__ = (
        CheckConstraint(
            "route_used IN ('sql', 'vector', 'hybrid', 'clarify')",
            name="valid_route",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        default=None,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text)
    route_used: Mapped[Route] = mapped_column(
        SQLEnum(
            Route,
            native_enum=False,
            validate_strings=True,
            create_constraint=False,
            length=20,
        ),
        index=True,
    )
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    latency_ms: Mapped[int]
    category: Mapped[str | None] = mapped_column(String(50), default=None)
    is_synthetic: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
    )
    # Relationship
    conversation: Mapped["Conversation | None"] = relationship(
        back_populates="query_logs",
        lazy="selectin",
    )
