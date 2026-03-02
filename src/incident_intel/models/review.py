"""Model for human-in-the-loop (HITL) review.

Includes review model and review statuses dict.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from incident_intel.models.base import Base

if TYPE_CHECKING:
    from incident_intel.models.conversation import Conversation


class ReviewStatus(str, enum.Enum):
    """Status of a pending review."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"


class PendingReview(Base):
    """Review entity representing content and life cycle of HITL review.

    Reviews are created when AI confidence is below threshold.
    May be associated with a conversation or standalone.
    """

    __tablename__ = "pending_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'revised')",
            name="valid_review_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    question: Mapped[str] = mapped_column(Text)
    generated_answer: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float)
    sources: Mapped[dict[str, Any] | None] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=None,
    )
    status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(
            ReviewStatus,
            native_enum=False,
            validate_strings=True,
            create_constraint=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=ReviewStatus.PENDING,
        index=True,
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # Relationship
    conversation: Mapped["Conversation | None"] = relationship(
        back_populates="pending_reviews",
        lazy="selectin",
    )
