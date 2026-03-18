"""API endpoints for chat."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from incident_intel.core.database import get_session
from incident_intel.exceptions import ConversationNotFoundError
from incident_intel.schemas.chat import ChatRequest, ChatResponse, SourceItem
from incident_intel.services.chat_service import handle_chat, handle_chat_stream

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse | StreamingResponse:
    """Handle chat.

    Raises:
        HTTPException(404) if conversation not found.
    """
    if request.stream:
        return StreamingResponse(
            handle_chat_stream(
                session=session,
                message=request.message,
                conversation_id=request.conversation_id,
                limit=request.options.limit,
                include_sources=request.options.include_sources,
            ),
            media_type="text/event-stream",
        )
    else:
        try:
            result = await handle_chat(
                session=session,
                message=request.message,
                conversation_id=request.conversation_id,
                limit=request.options.limit,
            )
        except ConversationNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        return ChatResponse(
            conversation_id=result["conversation_id"],
            message_id=result["message_id"],
            answer=result["answer"],
            sources=[
                SourceItem(
                    chunk_id=source["id"],
                    document_id=source["document_id"],
                    document_title=source["title"],
                    chunk_index=source["chunk_index"],
                    relevance_score=source["score"],
                )
                for source in result["sources"]
            ]
            if request.options.include_sources
            else [],
            route_used=result["route_used"],
            confidence=result["confidence"],
        )
