"""Service layer for chat - core orchestration."""

import json
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any
from uuid import UUID

import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.logging import get_logger
from incident_intel.exceptions import ConversationNotFoundError
from incident_intel.llm.openai_provider import OPENAI_MODEL_CHAT, OpenAIChatProvider
from incident_intel.llm.provider import ChatMessage, ChatProvider
from incident_intel.models.conversation import Conversation, Message, MessageRole
from incident_intel.models.query_log import QueryLog, Route
from incident_intel.models.query_source import QuerySource
from incident_intel.schemas.classification import DispatchResult
from incident_intel.services.classification_service import classify_query
from incident_intel.services.dispatch import dispatch

logger = get_logger(__name__)
_encoder = tiktoken.encoding_for_model(OPENAI_MODEL_CHAT)
MAX_HISTORY_TOKENS = 4000


def count_tokens(text: str) -> int:
    """Return the number of tokens in a text string."""
    return len(_encoder.encode(text))


def get_history_window(messages: Sequence[Message], budget: int) -> list[Message]:
    """Get slice of newest messages that fits budget."""
    result = []
    accumulated = 0
    for message in reversed(messages):
        tokens = count_tokens(message.content)
        if accumulated + tokens > budget:
            break
        accumulated += tokens
        result.append(message)
    return list(reversed(result))


def _build_messages(context: str, message: str, history: list[Message]) -> list[ChatMessage]:
    """Build list of messages for chat from user message and context."""
    system_message_content = f"""\
You are an IT operations assistant. Answer the user's question using ONLY
the context provided below. Cite sources by number (e.g., [1], [2]).
If the context does not contain enough information, say so clearly.
Do not make up information or citations not present in the provided context.

Context:
{context}
"""
    history_messages = [ChatMessage(role=m.role.value, content=m.content) for m in history]
    return [
        ChatMessage(role="system", content=system_message_content),
        *history_messages,
        ChatMessage(role="user", content=message),
    ]


async def _persist_chat_records(
    session: AsyncSession,
    message: str,
    conversation_id: UUID,
    answer: str,
    result: DispatchResult,
    confidence: float,
    t_start: float,
) -> tuple[UUID, UUID]:
    # Save persistence records
    user_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=message,
        token_count=count_tokens(message),
    )
    session.add(user_message)

    assistant_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=answer,
        token_count=count_tokens(answer),
    )
    session.add(assistant_message)

    query_log = QueryLog(
        conversation_id=conversation_id,
        query_text=message,
        message=assistant_message,
        route_used=Route(result.route),
        confidence=confidence,
        latency_ms=int((time.perf_counter() - t_start) * 1000),
    )
    session.add(query_log)

    await session.flush()

    for i, chunk in enumerate(result.sources, 1):
        query_source = QuerySource(
            query_log_id=query_log.id,
            chunk_id=chunk["id"],
            rank=i,
            relevance_score=chunk["score"],
            was_used=True,
        )
        session.add(query_source)
    await session.flush()

    await session.commit()

    return (conversation_id, assistant_message.id)


async def handle_chat(
    session: AsyncSession,
    message: str,
    conversation_id: UUID | None = None,
    limit: int = 5,
    provider: ChatProvider | None = None,
) -> dict[str, Any]:
    """Handle non-streaming chat."""
    # Default provider created here, not in param default, for test injection
    if provider is None:
        active_provider: ChatProvider = OpenAIChatProvider()
    else:
        active_provider = provider

    logger.info("processing_chat", conversation_id=conversation_id, message_length=len(message))
    # Resolve/create Conversation
    if conversation_id is None:
        conversation = Conversation()
        session.add(conversation)
        await session.flush()
        history = []
    else:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        found = await session.scalar(stmt)
        if found is None:
            raise ConversationNotFoundError(conversation_id)
        conversation = found
        stmt_messages = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        result_cursor = await session.execute(stmt_messages)
        prior_messages = result_cursor.scalars().all()
        history = get_history_window(prior_messages, MAX_HISTORY_TOKENS)

    try:
        # Latency timer
        t_start = time.perf_counter()

        # Classify query
        intent = await classify_query(query=message)
        t_classify = time.perf_counter()
        logger.info("timing_classify", duration_ms=int((t_classify - t_start) * 1000))

        # Dispatch to handler
        result = await dispatch(
            session=session,
            intent=intent,
            original_query=message,
            limit=limit,
        )
        t_dispatch = time.perf_counter()
        logger.info("timing_dispatch", duration_ms=int((t_dispatch - t_classify) * 1000))

        logger.info(
            "chat_routed",
            route=result.route,
            sources_count=len(result.sources),
            confidence=intent.confidence,
        )

        # Clarify short-circuit OR build prompt + call LLM
        if result.route == "clarify":
            answer = result.context
        else:
            messages = _build_messages(result.context, message=message, history=history)
            answer = await active_provider.generate(messages=messages)
        t_generate = time.perf_counter()
        logger.info("timing_generate", duration_ms=int((t_generate - t_dispatch) * 1000))

        conversation_id, assistant_message_id = await _persist_chat_records(
            session=session,
            message=message,
            conversation_id=conversation.id,
            answer=answer,
            result=result,
            confidence=intent.confidence,
            t_start=t_start,
        )

        t_persist = time.perf_counter()
        logger.info("timing_persist", duration_ms=int((t_persist - t_generate) * 1000))
        logger.info(
            "timing_summary",
            classify_ms=int((t_classify - t_start) * 1000),
            dispatch_ms=int((t_dispatch - t_classify) * 1000),
            generate_ms=int((t_generate - t_dispatch) * 1000),
            persist_ms=int((t_persist - t_generate) * 1000),
            total_ms=int((t_persist - t_start) * 1000),
            route=result.route,
            stream=False,
        )

        return {
            "conversation_id": conversation_id,
            "message_id": assistant_message_id,
            "answer": answer,
            "sources": result.sources,
            "route_used": result.route,
            "confidence": intent.confidence,
        }

    except Exception:
        logger.error("chat_processing_failed", exc_info=True)
        await session.rollback()
        raise


async def handle_chat_stream(
    session: AsyncSession,
    message: str,
    conversation_id: UUID | None = None,
    limit: int = 5,
    provider: ChatProvider | None = None,
    include_sources: bool = True,
) -> AsyncIterator[str]:
    """Handle streaming chat."""
    # Default provider created here, not in param default, for test injection
    if provider is None:
        active_provider: ChatProvider = OpenAIChatProvider()
    else:
        active_provider = provider

    logger.info("processing_chat", conversation_id=conversation_id, message_length=len(message))
    try:
        # Resolve/create Conversation
        if conversation_id is None:
            conversation = Conversation()
            session.add(conversation)
            await session.flush()
            history = []
        else:
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            found = await session.scalar(stmt)
            if found is None:
                raise ConversationNotFoundError(conversation_id)
            conversation = found
            stmt_messages = (
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )
            result_cursor = await session.execute(stmt_messages)
            prior_messages = result_cursor.scalars().all()
            history = get_history_window(prior_messages, MAX_HISTORY_TOKENS)

        # Latency timer
        t_start = time.perf_counter()

        # Classify query
        intent = await classify_query(query=message)
        t_classify = time.perf_counter()
        logger.info("timing_classify", duration_ms=int((t_classify - t_start) * 1000))

        # Dispatch to handler
        result = await dispatch(
            session=session,
            intent=intent,
            original_query=message,
            limit=limit,
        )
        t_dispatch = time.perf_counter()
        logger.info("timing_dispatch", duration_ms=int((t_dispatch - t_classify) * 1000))

        logger.info(
            "chat_routed",
            route=result.route,
            sources_count=len(result.sources),
            confidence=intent.confidence,
        )
        # Clarify short-circuit OR build prompt + call LLM
        time_to_first_token_ms = 0
        if result.route == "clarify":
            answer = result.context
            yield f"data: {json.dumps({'type': 'token', 'content': answer})}\n\n"
        else:
            messages = _build_messages(result.context, message=message, history=history)
            tokens: list[str] = []
            first_token_logged = False
            async for token in active_provider.generate_stream(messages=messages):
                if not first_token_logged:
                    time_to_first_token_ms = int((time.perf_counter() - t_dispatch) * 1000)
                    logger.info("timing_first_token", time_to_first_token_ms=time_to_first_token_ms)
                    first_token_logged = True
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                tokens.append(token)
            answer = "".join(tokens)

        t_generate = time.perf_counter()
        logger.info("timing_generate", duration_ms=int((t_generate - t_dispatch) * 1000))

        conversation_id, assistant_message_id = await _persist_chat_records(
            session=session,
            message=message,
            conversation_id=conversation.id,
            answer=answer,
            result=result,
            confidence=intent.confidence,
            t_start=t_start,
        )

        t_persist = time.perf_counter()
        logger.info("timing_persist", duration_ms=int((t_persist - t_generate) * 1000))
        logger.info(
            "timing_summary",
            classify_ms=int((t_classify - t_start) * 1000),
            dispatch_ms=int((t_dispatch - t_classify) * 1000),
            generate_ms=int((t_generate - t_dispatch) * 1000),
            persist_ms=int((t_persist - t_generate) * 1000),
            total_ms=int((t_persist - t_start) * 1000),
            time_to_first_token_ms=time_to_first_token_ms,
            route=result.route,
            stream=True,
        )

        sources = []
        if include_sources:
            sources = [
                {
                    "chunk_id": str(chunk["id"]),
                    "document_id": str(chunk["document_id"]),
                    "document_title": chunk["title"],
                    "chunk_index": chunk["chunk_index"],
                    "relevance_score": chunk["score"],
                }
                for chunk in result.sources
            ]
        yield f"data: {
            json.dumps(
                {
                    'type': 'done',
                    'conversation_id': str(conversation_id),
                    'message_id': str(assistant_message_id),
                    'sources': sources,
                    'route_used': result.route,
                    'confidence': intent.confidence,
                }
            )
        }\n\n"

    except ConversationNotFoundError as e:
        logger.error("chat_processing_failed", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    except Exception:
        logger.error("chat_processing_failed", exc_info=True)
        await session.rollback()
        yield f"data: {json.dumps({'type': 'error', 'message': 'An internal error occurred'})}\n\n"
