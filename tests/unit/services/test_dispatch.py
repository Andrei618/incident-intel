"""Unit tests for dispatch service."""

from unittest.mock import AsyncMock, patch

from incident_intel.schemas.classification import QueryIntent, SqlAction, SQLIntent
from incident_intel.services.dispatch import dispatch


@patch("incident_intel.services.dispatch.query_tickets", new_callable=AsyncMock)
@patch("incident_intel.services.dispatch.hybrid_search", new_callable=AsyncMock)
async def test_dispatch_sql_route_with_valid_intent(mock_hybrid_search, mock_query_tickets) -> None:
    """Test dispatch returns 'sql' route with correct SQLIntent."""
    # Arrange
    mock_query_tickets.return_value = "1. [p1] Test titel - test service_name (open) 2026-03-14"
    # Act
    result = await dispatch(
        session=AsyncMock(),
        intent=QueryIntent(
            route="sql",
            confidence=0.9,
            sql_intent=SQLIntent(action=SqlAction.COUNT),
        ),
        original_query="test original query",
    )

    # Assert
    assert result.context == "1. [p1] Test titel - test service_name (open) 2026-03-14"
    assert result.sources == []
    assert result.route == "sql"


@patch("incident_intel.services.dispatch.query_tickets", new_callable=AsyncMock)
@patch("incident_intel.services.dispatch.hybrid_search", new_callable=AsyncMock)
async def test_dispatch_sql_route_with_sql_intent_none(
    mock_hybrid_search, mock_query_tickets
) -> None:
    """Test dispatch falls back to hybrid handler when SQLIntent is None."""
    # Arrange
    mock_hybrid_search.return_value = [{"title": "Test chunk", "content": "test content"}]
    # Act
    result = await dispatch(
        session=AsyncMock(),
        intent=QueryIntent(
            route="sql",
            confidence=0.9,
            sql_intent=None,
        ),
        original_query="test original query",
    )

    # Assert
    assert result.context == "1. Title: Test chunk, content: test content"
    assert result.sources[0] == {"title": "Test chunk", "content": "test content"}
    assert result.route == "hybrid"


@patch("incident_intel.services.dispatch.query_tickets", new_callable=AsyncMock)
@patch("incident_intel.services.dispatch.hybrid_search", new_callable=AsyncMock)
async def test_dispatch_hybrid_route(mock_hybrid_search, mock_query_tickets) -> None:
    """Test dispatch calls 'hybrid' route correctly."""
    # Arrange
    mock_hybrid_search.return_value = [{"title": "Test chunk", "content": "test content"}]
    test_session = AsyncMock()
    # Act
    result = await dispatch(
        session=test_session,
        intent=QueryIntent(
            route="hybrid",
            confidence=0.9,
            document_query="some search query",
        ),
        original_query="test original query",
    )

    # Assert
    assert result.context == "1. Title: Test chunk, content: test content"
    assert result.sources[0] == {"title": "Test chunk", "content": "test content"}
    assert result.route == "hybrid"

    mock_hybrid_search.assert_called_once_with(
        session=test_session,
        query="some search query",
        limit=5,
    )


@patch("incident_intel.services.dispatch.query_tickets", new_callable=AsyncMock)
@patch("incident_intel.services.dispatch.hybrid_search", new_callable=AsyncMock)
async def test_dispatch_clarify_route(mock_hybrid_search, mock_query_tickets) -> None:
    """Test dispatch calls 'clarify' route correctly."""
    # Arrange
    # Act
    result = await dispatch(
        session=AsyncMock(),
        intent=QueryIntent(
            route="clarify",
            confidence=0.5,
            clarify_question="some question that need clarification",
        ),
        original_query="test original query",
    )

    # Assert
    assert result.context == "some question that need clarification"
    assert result.sources == []
    assert result.route == "clarify"


@patch("incident_intel.services.dispatch.query_tickets", new_callable=AsyncMock)
@patch("incident_intel.services.dispatch.hybrid_search", new_callable=AsyncMock)
async def test_dispatch_unknown_route(mock_hybrid_search, mock_query_tickets) -> None:
    """Test dispatch calls 'hybrid' route when route is unknown."""
    # Arrange
    mock_hybrid_search.return_value = [{"title": "Test chunk", "content": "test content"}]
    test_intent = QueryIntent(
        route="hybrid",
        confidence=0.9,
    )
    test_intent.route = (
        "unknown"  # bypass Pydantic validation, after construction, we can set any value
    )
    # Act
    result = await dispatch(
        session=AsyncMock(),
        intent=test_intent,
        original_query="test original query",
    )

    # Assert
    assert result.context == "1. Title: Test chunk, content: test content"
    assert result.sources[0] == {"title": "Test chunk", "content": "test content"}
    assert result.route == "hybrid"


@patch("incident_intel.services.dispatch.query_tickets", new_callable=AsyncMock)
@patch("incident_intel.services.dispatch.hybrid_search", new_callable=AsyncMock)
async def test_dispatch_hybrid_falls_back_to_original_query(
    mock_hybrid_search, mock_query_tickets
) -> None:
    """Test hybrid handler uses original_query when document_query is None."""
    # Arrange
    mock_hybrid_search.return_value = []
    test_session = AsyncMock()

    # Act
    await dispatch(
        session=test_session,
        intent=QueryIntent(
            route="hybrid",
            confidence=0.9,
        ),
        original_query="test original query",
    )

    # Assert
    mock_hybrid_search.assert_called_once_with(
        session=test_session,
        query="test original query",
        limit=5,
    )
