"""Models for conversation management.

Includes Conversation and Messages.
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
    from incident_intel.models.query_log import QueryLog
    from incident_intel.models.review import PendingReview


class MessageRole(str, enum.Enum):
    """Roles of message authors."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base, TimestampMixin):
    """Conversation entity.

    Conversation has messages.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str | None] = mapped_column(
        String(100),
        default=None,
        index=True,
    )
    # Relationship
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    pending_reviews: Mapped[list["PendingReview"]] = relationship(
        back_populates="conversation",
        lazy="selectin",
        order_by="PendingReview.created_at",
    )
    query_logs: Mapped[list["QueryLog"]] = relationship(
        back_populates="conversation",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="QueryLog.created_at",
    )


class Message(Base):
    """Message entity.

    Messages belong to conversation.
    """

    __tablename__ = "messages"
    __table_args__ = (
        # Composite index
        Index("ix_messages_conversation", "conversation_id", "created_at"),
        # Constraint
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="valid_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(
            MessageRole,
            native_enum=False,
            validate_strings=True,
            create_constraint=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
    )
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    # Relationship
    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
        lazy="joined",
    )
