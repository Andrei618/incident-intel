"""Unit tests for SQL query service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from incident_intel.schemas.classification import (
    SqlAction,
    SQLIntent,
    TicketFilters,
    TicketPriority,
)
from incident_intel.services.sql_query_service import _build_where_clause, query_tickets


# =========== _build_where_clause ==========================
def test_build_where_clause_service_name_filter_needs_join() -> None:
    """Test _build_where_clause sets need_join = True when 'service_name' in filters."""
    # Arrange
    test_filters = TicketFilters(service_name="test_service_name")

    # Act
    result = _build_where_clause(filters=test_filters)

    # Assert
    # needs_join=True, "s.name = :service_name" in sql, correct param value
    assert result.needs_join is True
    assert "s.name = :service_name" in result.sql
    assert result.params["service_name"] == "test_service_name"


def test_build_where_clause_since_filter_uses_gte_operator() -> None:
    """Test _build_where_clause uses >= operator when 'since' in filters."""
    # Arrange
    test_since = datetime(2026, 3, 1, tzinfo=UTC)
    test_filters = TicketFilters(since=test_since)

    # Act
    result = _build_where_clause(filters=test_filters)

    # Assert
    # "created_at >= :since" in sql, "created_at <" NOT in sql, correct param
    assert "t.created_at >= :since" in result.sql
    assert "t.created_at < :until" not in result.sql
    assert result.params["since"] == test_since


def test_build_where_clause_until_filter_uses_exclusive_lt_operator() -> None:
    """Test _build_where_clause uses < operator when 'until' in filters."""
    # Arrange
    test_until = datetime(2026, 3, 1, tzinfo=UTC)
    test_filters = TicketFilters(until=test_until)

    # Act
    result = _build_where_clause(filters=test_filters)

    # Assert
    # "created_at < :until" in sql (NOT <=), ">=" NOT in sql, correct param
    assert "t.created_at < :until" in result.sql
    assert "t.created_at >= :since" not in result.sql
    assert result.params["until"] == test_until


def test_build_where_clause_no_filters_produces_empty_clause() -> None:
    """Test _build_where_clause produces empty clause when filters not provided."""
    # Arrange
    test_filters = TicketFilters()

    # Act
    result = _build_where_clause(filters=test_filters)

    # Assert
    # 	sql is "", params is {}, needs_join=False
    assert result.sql == ""
    assert result.params == {}
    assert result.needs_join is False


def test_build_where_clause_since_greater_than_until_swaps_values() -> None:
    """Test _build_where_clause swaps values of 'since' and 'until' when 'since' > 'until'."""
    # Arrange
    test_since = datetime(2026, 3, 2, tzinfo=UTC)
    test_until = datetime(2026, 3, 1, tzinfo=UTC)
    test_filters = TicketFilters(since=test_since, until=test_until)

    # Act
    result = _build_where_clause(filters=test_filters)

    # Assert
    # Both operators present, params["since"] is the earlier date,
    # params["until"] is the later date
    assert result.params["since"] == test_until
    assert result.params["until"] == test_since


# =========== query_tickets ==========================
async def test_query_tickets_count_with_priority_filter() -> None:
    """Test query_tickets returns formatted text with the count number + filter mention."""
    # Arrange
    test_session = AsyncMock()
    test_intent = SQLIntent(
        action=SqlAction.COUNT,
        filters=TicketFilters(priority=TicketPriority.P1),
    )
    response = MagicMock()
    response.scalar_one.return_value = 10

    test_session.execute.return_value = response

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "10" in result
    assert "priority" in result


async def test_query_tickets_list_with_multiple_filters() -> None:
    """Test query_tickets returns formatted numbered list with ticket data."""
    # Arrange
    test_session = AsyncMock()
    test_intent = SQLIntent(
        action=SqlAction.LIST,
        filters=TicketFilters(priority=TicketPriority.P1),
    )
    response = MagicMock()
    response.mappings.return_value.all.return_value = [
        {
            "priority": "p1",
            "title": "test_title",
            "service_name": "test-service_name",
            "status": "test_status",
            "created_at": "2026-03-01",
        }
    ]

    test_session.execute.return_value = response

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "p1" in result
    assert "Found 1 tickets" in result
    assert "test_title" in result
    assert "test-service_name" in result


async def test_query_tickets_empty_list_result() -> None:
    """Test query_tickets returns "No tickets found ..." message."""
    # Arrange
    test_session = AsyncMock()
    test_intent = SQLIntent(
        action=SqlAction.LIST,
        filters=TicketFilters(priority=TicketPriority.P1),
    )
    response = MagicMock()
    response.mappings.return_value.all.return_value = []

    test_session.execute.return_value = response

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "No tickets found matching your filters." in result
