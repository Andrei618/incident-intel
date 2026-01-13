"""Junction table for QueryLogs and DocumentChunks.

Allows M:N relationship between QueryLogs and DocumentChunks with metadata.
Used for RAG traceability.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Float,
    ForeignKey,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from incident_intel.models.base import Base

if TYPE_CHECKING:
    from incident_intel.models.document import DocumentChunk
    from incident_intel.models.query_log import QueryLog


class QuerySource(Base):
    """Junction entity for M:N relationship.

    Establishes relationship to both parents: QueryLogs and DocumentChunks.
    Parent models have relationships to junction entity.
    """

    __tablename__ = "query_sources"
    __table_args__ = (
        UniqueConstraint("query_log_id", "chunk_id"),
        UniqueConstraint("query_log_id", "rank"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    query_log_id: Mapped[int] = mapped_column(
        ForeignKey("query_logs.id", ondelete="CASCADE"),
        index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        index=True,
    )
    rank: Mapped[int]
    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        default=None,
    )
    was_used: Mapped[bool | None] = mapped_column(default=False)

    # Relationships
    query_log: Mapped["QueryLog"] = relationship(
        back_populates="query_sources",
        lazy="joined",
    )
    document_chunk: Mapped["DocumentChunk"] = relationship(
        back_populates="query_sources",
        lazy="joined",
    )
