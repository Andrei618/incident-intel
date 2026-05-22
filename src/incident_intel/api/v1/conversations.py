"""API endpoints for conversation management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import get_session
from incident_intel.exceptions import ConversationNotFoundError
from incident_intel.models.conversation import Message, MessageRole
from incident_intel.schemas.chat import SourceItem
from incident_intel.schemas.conversation import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from incident_intel.services.conversation_service import (
    delete_conversation,
    get_conversation,
    list_conversations,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _build_message_response(m: Message) -> MessageResponse | None:
    """Build message response with sources."""
    if m.role == MessageRole.SYSTEM:
        return None
    sources = [
        SourceItem(
            chunk_id=qs.chunk_id,
            document_id=qs.document_chunk.document_id,
            document_title=qs.document_chunk.document.title,
            chunk_index=qs.document_chunk.chunk_index,
            relevance_score=qs.relevance_score or 0.0,
        )
        for log in m.query_logs
        for qs in log.query_sources
    ]
    return MessageResponse(
        id=m.id,
        role=m.role,
        content=m.content,
        created_at=m.created_at,
        sources=sources,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_endpoint(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ConversationDetailResponse:
    """Get conversation by ID.

    Raises:
        HTTPException (404) if conversation not gound.
    """
    try:
        conversation = await get_conversation(
            conversation_id=conversation_id,
            session=session,
        )
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return ConversationDetailResponse(
        id=conversation.id,
        created_at=conversation.created_at,
        messages=[
            response
            for m in conversation.messages
            if (response := _build_message_response(m)) is not None
        ],
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations_endpoint(
    session: AsyncSession = Depends(get_session),
) -> ConversationListResponse:
    """List conversations.

    Return:
        ConversationListResponse: List of conversations.
    """
    conversations, total = await list_conversations(
        session=session,
    )
    return ConversationListResponse(
        items=[ConversationResponse.model_validate(conversation) for conversation in conversations],
        total=total,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_endpoint(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete conversation by ID.

    Raises:
        HTTPException (404) if conversation not found.
    """
    try:
        await delete_conversation(
            conversation_id=conversation_id,
            session=session,
        )
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
