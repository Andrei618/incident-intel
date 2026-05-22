"""Pydantic schema for conversations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from incident_intel.models.conversation import MessageRole
from incident_intel.schemas.chat import SourceItem


class MessageResponse(BaseModel):
    """Response schema for a single message in conversation."""

    id: UUID
    role: Literal[MessageRole.USER, MessageRole.ASSISTANT]  # excludes SYSTEM
    content: str
    created_at: datetime
    sources: list[SourceItem] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Response schema for conversation metadata."""

    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    """Response schema for full conversation details.

    Includes list of messages for a single conversation.
    """

    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    """Reponse schema for conversation list."""

    items: list[ConversationResponse]
    total: int = Field(..., description="Total number of conversations")
