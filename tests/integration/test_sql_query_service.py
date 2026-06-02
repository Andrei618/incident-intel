"""Integration tests for SQL query."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.service import Service
from incident_intel.models.ticket import Ticket, TicketPriority
from incident_intel.schemas.classification import SqlAction, SQLIntent, TicketFilters
from incident_intel.services.sql_query_service import query_tickets


async def _create_ticket(
    test_session: AsyncSession,
    sample_service: Service,
    title: str,
    priority: TicketPriority = TicketPriority.P1,
) -> Ticket:
    """Create and persist a ticket, return the ORM instance."""
    ticket = Ticket(
        service_id=sample_service.id,
        title=title,
        priority=priority,
    )
    test_session.add(ticket)
    await test_session.commit()


async def test_count_returns_correct_number(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """COUNT action returns the exact number of matching tickets."""
    # Arrange
    await _create_ticket(test_session, sample_service, "Title 1")
    await _create_ticket(test_session, sample_service, "Title 2")
    await _create_ticket(test_session, sample_service, "Title 3")

    test_intent = SQLIntent(
        action=SqlAction.COUNT, filters=TicketFilters(priority=TicketPriority.P1)
    )

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "There are 3 tickets" in result
    assert "priority: p1" in result


async def test_list_returns_correct_tickets(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """LIST action returns only tickets matching the priority filter."""
    # Arrange
    await _create_ticket(test_session, sample_service, "Title 1", priority=TicketPriority.P1)
    await _create_ticket(test_session, sample_service, "Title 2", priority=TicketPriority.P1)
    await _create_ticket(test_session, sample_service, "Title 3", priority=TicketPriority.P2)

    test_intent = SQLIntent(
        action=SqlAction.LIST, filters=TicketFilters(priority=TicketPriority.P1)
    )

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "Found 2 tickets" in result
    assert "[p1]" in result
    assert "[p2]" not in result


async def test_service_name_filter_via_join(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Service name filter JOINs services table and filters correctly."""
    # Arrange
    await _create_ticket(test_session, sample_service, "Title 1")
    await _create_ticket(test_session, sample_service, "Title 2")
    await _create_ticket(test_session, sample_service, "Title 3")

    test_intent = SQLIntent(
        action=SqlAction.COUNT, filters=TicketFilters(service_name="test-service")
    )

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "There are 3 tickets" in result
    assert "service: test-service" in result


async def test_since_filter_includes_recent_tickets(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Since filter returns tickets created after the cutoff."""
    # Arrange
    await _create_ticket(test_session, sample_service, "Title 1")
    await _create_ticket(test_session, sample_service, "Title 2")
    await _create_ticket(test_session, sample_service, "Title 3")

    test_since = datetime(2026, 3, 1, tzinfo=UTC)
    test_intent = SQLIntent(action=SqlAction.COUNT, filters=TicketFilters(since=test_since))

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "There are 3 tickets" in result
    assert "since 2026-03-01" in result


async def test_service_name_case_mismatch_returns_zero(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Exact-match service name filter returns 0 for wrong case."""
    # Arrange
    await _create_ticket(test_session, sample_service, "Title 1")
    await _create_ticket(test_session, sample_service, "Title 2")
    await _create_ticket(test_session, sample_service, "Title 3")

    test_intent = SQLIntent(
        action=SqlAction.COUNT, filters=TicketFilters(service_name="Test-Service")
    )

    # Act
    result = await query_tickets(session=test_session, intent=test_intent)

    # Assert
    assert "There are 0 tickets" in result
    assert "service: Test-Service" in result
