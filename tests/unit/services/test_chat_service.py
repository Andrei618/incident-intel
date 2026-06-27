"""Unit tests for chat service."""

import json
import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from incident_intel.exceptions import ConversationNotFoundError
from incident_intel.llm.provider import ChatMessage
from incident_intel.models.conversation import Conversation
from incident_intel.schemas.classification import (
    DispatchResult,
    QueryIntent,
    SqlAction,
    SQLIntent,
    TicketFilters,
    TicketPriority,
    TicketStatus,
)
from incident_intel.services.chat_service import (
    _build_messages,
    count_tokens,
    get_history_window,
    handle_chat,
    handle_chat_stream,
)


def test_count_tokens_returns_exact_count_for_known_string() -> None:
    """Test count_tokens returns exact count for known short string."""
    # Arrange + Act
    result = count_tokens("Hello world")

    # Assert
    assert result == 2


def test_count_tokens_returns_zero_for_empty_string() -> None:
    """Test count_tokens returns zero for ampty string."""
    # Arrange + Act
    result = count_tokens("")

    # Assert
    assert result == 0


def test_get_history_window_all_messages_fit() -> None:
    """Test get_history_window returns all messages if budget is large enough."""
    # Arrange
    msg1 = MagicMock(content="Hello world")
    msg2 = MagicMock(content="How are you")
    budget = 5

    # Act
    result = get_history_window([msg1, msg2], budget)

    # Assert
    assert len(result) == 2
    assert result[0].content == "Hello world"
    assert result[1].content == "How are you"


def test_get_history_window_budget_exceeded() -> None:
    """Test get_history_window returns only messages that do not exceed budget."""
    # Arrange
    msg1 = MagicMock(content="Hello world")
    msg2 = MagicMock(content="How are you")
    msg3 = MagicMock(content="I am fine")
    budget = 6

    # Act
    result = get_history_window([msg1, msg2, msg3], budget)

    # Assert
    assert len(result) == 2
    assert result[0].content == "How are you"
    assert result[1].content == "I am fine"


def test_get_history_window_empty_list() -> None:
    """Test get_history_window returns empty list if empty list is geven."""
    # Arrange + Act
    result = get_history_window([], 10)

    # Assert
    assert len(result) == 0


@patch("incident_intel.services.chat_service.classify_query", new_callable=AsyncMock)
@patch("incident_intel.services.chat_service.dispatch", new_callable=AsyncMock)
async def test_handle_chat_hybrid_route(mock_dispatch, mock_classify_query) -> None:
    """Test handle_chat returns correct dict with hybrid route."""
    # Arrange
    test_query_intent = QueryIntent(
        route="hybrid",
        confidence=0.9,
        sql_intent=SQLIntent(
            action=SqlAction.COUNT,
            filters=TicketFilters(priority=TicketPriority.P1, status=TicketStatus.OPEN),
        ),
    )
    mock_classify_query.return_value = test_query_intent

    test_chunk_id = uuid.uuid4()
    test_dispatch_result = DispatchResult(
        context="test context",
        sources=[{"id": test_chunk_id, "score": 0.85, "title": "Test chunk"}],
        route="hybrid",
    )
    mock_dispatch.return_value = test_dispatch_result

    test_conversation_id = uuid.uuid4()

    test_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    test_session.execute.return_value = mock_execute_result
    test_session.scalar.return_value = Conversation(id=test_conversation_id)
    test_session.add = MagicMock()
    test_session.flush = AsyncMock()
    test_session.commit = AsyncMock()

    test_provider = AsyncMock()
    test_provider.generate.return_value = "test answer"

    # Act
    result = await handle_chat(
        session=test_session,
        message="test message",
        conversation_id=test_conversation_id,
        limit=5,
        provider=test_provider,
    )

    # Assert
    assert result["conversation_id"] == test_conversation_id
    assert "message_id" in result
    assert result["answer"] == "test answer"
    assert result["sources"][0]["id"] == test_chunk_id
    assert result["route_used"] == "hybrid"
    assert result["confidence"] == 0.9

    test_provider.generate.assert_called_once()
    assert test_session.add.call_count == 4
    test_session.flush.assert_called()
    test_session.commit.assert_called()


@patch("incident_intel.services.chat_service.Conversation")
@patch("incident_intel.services.chat_service.classify_query", new_callable=AsyncMock)
@patch("incident_intel.services.chat_service.dispatch", new_callable=AsyncMock)
async def test_handle_chat_hybrid_route_no_conversation_id_given(
    mock_dispatch,
    mock_classify_query,
    mock_conversation,
) -> None:
    """Test handle_chat creates a new conversation when no ID given."""
    # Arrange
    test_query_intent = QueryIntent(
        route="hybrid",
        confidence=0.9,
        sql_intent=SQLIntent(
            action=SqlAction.COUNT,
            filters=TicketFilters(priority=TicketPriority.P1, status=TicketStatus.OPEN),
        ),
    )
    mock_classify_query.return_value = test_query_intent

    test_chunk_id = uuid.uuid4()
    test_dispatch_result = DispatchResult(
        context="test context",
        sources=[{"id": test_chunk_id, "score": 0.85, "title": "Test chunk"}],
        route="hybrid",
    )
    mock_dispatch.return_value = test_dispatch_result

    test_conversation_id = None
    mock_conversation.return_value.id = uuid.uuid4()

    test_session = AsyncMock()
    test_session.add = MagicMock()
    test_session.flush = AsyncMock()
    test_session.commit = AsyncMock()

    test_provider = AsyncMock()
    test_provider.generate.return_value = "test answer"

    # Act
    result = await handle_chat(
        session=test_session,
        message="test message",
        conversation_id=test_conversation_id,
        limit=5,
        provider=test_provider,
    )

    # Assert
    assert isinstance(result["conversation_id"], uuid.UUID)
    assert "message_id" in result
    assert result["answer"] == "test answer"
    assert result["sources"][0]["id"] == test_chunk_id
    assert result["route_used"] == "hybrid"
    assert result["confidence"] == 0.9

    test_provider.generate.assert_called_once()
    test_session.scalar.assert_not_called()
    assert test_session.add.call_count == 5
    test_session.flush.assert_called()
    test_session.commit.assert_called()


@patch("incident_intel.services.chat_service.classify_query", new_callable=AsyncMock)
@patch("incident_intel.services.chat_service.dispatch", new_callable=AsyncMock)
async def test_handle_chat_clarify_skips_llm(mock_dispatch, mock_classify_query) -> None:
    """Test handle_chat returns clarifing question with clarify route."""
    # Clarify route: uses result.context as answer,
    # provider.generate NOT called, still persists Messages + QueryLog
    # Arrange
    test_query_intent = QueryIntent(
        route="clarify",
        confidence=0.9,
    )
    mock_classify_query.return_value = test_query_intent

    test_dispatch_result = DispatchResult(
        context="Could you clarify what you mean?",
        sources=[],
        route="clarify",
    )
    mock_dispatch.return_value = test_dispatch_result

    test_conversation_id = uuid.uuid4()

    test_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    test_session.execute.return_value = mock_execute_result
    test_session.scalar.return_value = Conversation(id=test_conversation_id)
    test_session.add = MagicMock()
    test_session.flush = AsyncMock()
    test_session.commit = AsyncMock()

    test_provider = AsyncMock()

    # Act
    result = await handle_chat(
        session=test_session,
        message="test message",
        conversation_id=test_conversation_id,
        limit=5,
        provider=test_provider,
    )
    # Assert
    assert result["conversation_id"] == test_conversation_id
    assert "message_id" in result
    assert result["answer"] == "Could you clarify what you mean?"
    assert result["route_used"] == "clarify"
    assert result["confidence"] == 0.9

    test_provider.generate.assert_not_called()
    assert test_session.add.call_count == 3
    test_session.flush.assert_called()
    test_session.commit.assert_called()


async def test_handle_chat_conversation_not_found() -> None:
    """Test handle_chat raises ConversationNotFoundError with non-existing  conversation_id."""
    # Arrange
    test_conversation_id = uuid.uuid4()
    test_session = AsyncMock()
    test_session.scalar.return_value = None

    # Act
    with pytest.raises(ConversationNotFoundError) as e:
        await handle_chat(
            session=test_session,
            message="test message",
            conversation_id=test_conversation_id,
            limit=5,
            provider=None,
        )

    # Assert
    assert f"Conversation {test_conversation_id} not found" in str(e.value)


@patch("incident_intel.services.chat_service.classify_query", new_callable=AsyncMock)
@patch("incident_intel.services.chat_service.dispatch", new_callable=AsyncMock)
async def test_handle_chat_rollback_on_error(mock_dispatch, mock_classify_query) -> None:
    """Test handle_chat makes rollback after error."""
    # LLM raises → session.rollback() called, exception re-raised
    # Arrange
    test_query_intent = QueryIntent(
        route="hybrid",
        confidence=0.9,
        sql_intent=SQLIntent(
            action=SqlAction.COUNT,
            filters=TicketFilters(priority=TicketPriority.P1, status=TicketStatus.OPEN),
        ),
    )
    mock_classify_query.return_value = test_query_intent

    test_dispatch_result = DispatchResult(
        context="test context",
        sources=[],
        route="hybrid",
    )
    mock_dispatch.return_value = test_dispatch_result

    test_conversation_id = uuid.uuid4()

    test_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    test_session.execute.return_value = mock_execute_result
    test_session.scalar.return_value = Conversation(id=test_conversation_id)
    test_session.add = MagicMock()
    test_session.flush = AsyncMock()
    test_session.commit = AsyncMock()

    test_provider = AsyncMock()
    test_provider.generate.side_effect = RuntimeError("LLM failed")

    # Act
    with pytest.raises(RuntimeError):
        await handle_chat(
            session=test_session,
            message="test message",
            conversation_id=test_conversation_id,
            limit=5,
            provider=test_provider,
        )

    # Assert
    test_session.rollback.assert_called_once()


@patch("incident_intel.services.chat_service.classify_query", new_callable=AsyncMock)
@patch("incident_intel.services.chat_service.dispatch", new_callable=AsyncMock)
async def test_handle_chat_stream_yields_tokens_and_done(
    mock_dispatch, mock_classify_query
) -> None:
    """Test handle_chat yields events with correct shape."""
    # Stream path: yields token events, then done event with correct shape after commit
    # Arrange
    test_query_intent = QueryIntent(
        route="hybrid",
        confidence=0.9,
        sql_intent=SQLIntent(
            action=SqlAction.COUNT,
            filters=TicketFilters(priority=TicketPriority.P1, status=TicketStatus.OPEN),
        ),
    )
    mock_classify_query.return_value = test_query_intent

    test_chunk_id = uuid.uuid4()
    test_dispatch_result = DispatchResult(
        context="test context",
        sources=[{"id": test_chunk_id, "score": 0.85, "title": "Test chunk"}],
        route="hybrid",
    )
    mock_dispatch.return_value = test_dispatch_result

    test_conversation_id = uuid.uuid4()

    test_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    test_session.execute.return_value = mock_execute_result
    test_session.scalar.return_value = Conversation(id=test_conversation_id)
    test_session.add = MagicMock()
    test_session.flush = AsyncMock()
    test_session.commit = AsyncMock()

    test_messages = ["Hello", " world"]

    async def mock_async_gen(**kwargs: list[ChatMessage]) -> AsyncIterator[str]:
        for token in test_messages:
            yield token

    test_provider = AsyncMock()
    test_provider.generate_stream = mock_async_gen

    # Act
    events = [
        event
        async for event in handle_chat_stream(
            session=test_session,
            message="test message",
            conversation_id=test_conversation_id,
            limit=5,
            provider=test_provider,
            include_sources=False,
        )
    ]

    # Assert
    assert len(events) == 3

    # event format: "data: {json.dumps({'type': 'token', 'content': token})}\n\n"
    parsed = [json.loads(event[6:].strip()) for event in events]

    # events[0] - a token event with content "Hello"
    assert parsed[0]["type"] == "token"
    assert parsed[0]["content"] == "Hello"

    # events[1] — a token event with content " world"
    assert parsed[1]["type"] == "token"
    assert parsed[1]["content"] == " world"

    # events[2] — a done event with conversation_id, message_id, sources, route_used, confidence
    assert parsed[2]["type"] == "done"
    assert parsed[2]["route_used"] == "hybrid"
    assert parsed[2]["confidence"] == 0.9
    assert parsed[2]["sources"] == []
    assert "conversation_id" in parsed[2]
    assert "message_id" in parsed[2]

    test_session.commit.assert_called_once()


def test_build_messages_citation_when_sources_exist() -> None:
    """Test _build_messages makes messages with citation, when sources exist."""
    # Arrange
    test_context = "test context"
    test_message = "test message"
    test_history = []
    test_sources = [{"id": "source link"}]
    test_route = "hybrid"

    # Act
    result = _build_messages(
        context=test_context,
        message=test_message,
        history=test_history,
        sources=test_sources,
        route=test_route,
    )

    # Assert
    assert "Cite sources by number" in result[0].content


def test_build_messages_no_citation_when_sources_empty() -> None:
    """Test _build_messages makes messages without citation, when sources are empty."""
    # Arrange
    test_context = "test context"
    test_message = "test message"
    test_history = []
    test_sources = []
    test_route = "hybrid"

    # Act
    result = _build_messages(
        context=test_context,
        message=test_message,
        history=test_history,
        sources=test_sources,
        route=test_route,
    )

    # Assert
    assert "Cite sources by number" not in result[0].content


def test_build_messages_sql_route_contains_database_instruction() -> None:
    """Test _build_message makes message with instruction for database query, when route is sql."""
    # Arrange
    test_context = "test context"
    test_message = "test message"
    test_history = []
    test_sources = []
    test_route = "sql"

    # Act
    result = _build_messages(
        context=test_context,
        message=test_message,
        history=test_history,
        sources=test_sources,
        route=test_route,
    )

    # Assert
    assert "authoritative result of a database query" in result[0].content
    assert "Today's date is" in result[0].content
    assert "If the context does not contain enough information" not in result[0].content


def test_build_messages_hybrid_route_does_not_contain_database_instruction() -> None:
    """Test _build_message makes message without instruction for database query, when route is hybrid."""
    # Arrange
    test_context = "test context"
    test_message = "test message"
    test_history = []
    test_sources = []
    test_route = "hybrid"

    # Act
    result = _build_messages(
        context=test_context,
        message=test_message,
        history=test_history,
        sources=test_sources,
        route=test_route,
    )

    # Assert
    assert "If the context does not contain enough information" in result[0].content
    assert "authoritative result of a database query" not in result[0].content
