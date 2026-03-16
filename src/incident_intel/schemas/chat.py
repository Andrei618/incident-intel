"""Pydantic schemas for chat."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatOptions(BaseModel):
    """Schema for configuration of response options."""

    limit: int = Field(default=5, ge=1, le=20)
    include_sources: bool = Field(default=True)


class ChatRequest(BaseModel):
    """Request schema for chat."""

    message: str = Field(min_length=1)
    conversation_id: UUID | None = None
    options: ChatOptions = Field(default_factory=ChatOptions)
    stream: bool = False


class SourceItem(BaseModel):
    """Schema for detailed representation of one matching source."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    relevance_score: float


class ChatResponse(BaseModel):
    """Response schema for chat."""

    conversation_id: UUID
    message_id: UUID
    answer: str
    sources: list[SourceItem]
    route_used: Literal["sql", "hybrid", "clarify"]
    confidence: float | None = None
