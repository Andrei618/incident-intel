"""Unit tests for ticket service."""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.service import Service
from incident_intel.schemas.ticket import (
    TicketCreate,
    TicketPriority,
    TicketStatus,
    TicketUpdate,
)
from incident_intel.services.ticket_service import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket,
)


async def test_create_ticket_success(test_session: AsyncSession, sample_service: Service) -> None:
    """Test ticket service can create a ticket."""
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    # Act
    created_ticket = await create_ticket(session=test_session, data=data)

    # Assert
    assert created_ticket.id is not None
    assert created_ticket.title == "Test"
    assert created_ticket.service_id == sample_service.id


async def test_create_ticket_nonexistent_service(test_session: AsyncSession) -> None:
    """Test ticket service returns correct exception during creating ticket.

    Returns 400 exception by creating a ticket if service_id does not exist.
    """
    # Arrange
    data = TicketCreate(
        service_id=uuid.uuid4(),
        title="Test",
        priority=TicketPriority.P1,
    )
    # Act
    with pytest.raises(HTTPException) as exc_info:
        await create_ticket(session=test_session, data=data)

    # Assert
    assert exc_info.value.status_code == 400
    assert "Service with ID" in exc_info.value.detail


async def test_get_ticket_success(test_session: AsyncSession, sample_service: Service) -> None:
    """Test ticket service can get existing ticket."""
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    created_ticket = await create_ticket(session=test_session, data=data)

    # Act
    got_ticket = await get_ticket(session=test_session, ticket_id=created_ticket.id)

    # Assert
    assert got_ticket.id == created_ticket.id


async def test_get_ticket_nonexistent_ticket(test_session: AsyncSession) -> None:
    """Test ticket service returns correct exception during getting ticket.

    Returns 404 exception by getting a ticket if ticket id does not exist.
    """
    # Arrange
    nonexistent_id = uuid.uuid4()

    # Act
    with pytest.raises(HTTPException) as exc_info:
        await get_ticket(session=test_session, ticket_id=nonexistent_id)

    # Assert
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


async def test_update_ticket_success(test_session: AsyncSession, sample_service: Service) -> None:
    """Test ticket service can update ticket."""
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    created_ticket = await create_ticket(session=test_session, data=data)
    update_data = TicketUpdate(title="Updated title")
    # Act
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert
    assert updated_ticket.title == "Updated title"


async def test_update_ticket_empty_update(
    test_session: AsyncSession, sample_service: Service
) -> None:
    """Test ticket service makes no update when update data were not provided."""
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    created_ticket = await create_ticket(session=test_session, data=data)
    update_data = TicketUpdate()
    # Act
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert
    assert updated_ticket.title == "Test"


async def test_update_ticket_status_resolved_sets_resolved_at(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test ticket service sets resolved time if status is RESOLVED.

    Verifies resolved_at is auto-set on status change to RESOLVED.
    """
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    created_ticket = await create_ticket(session=test_session, data=data)

    # Verify initial state
    assert created_ticket.status == TicketStatus.OPEN
    assert created_ticket.resolved_at is None

    update_data = TicketUpdate(status=TicketStatus.RESOLVED)

    # Act
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert after updating
    assert updated_ticket.status == TicketStatus.RESOLVED
    assert updated_ticket.resolved_at is not None


async def test_update_ticket_status_closed_sets_resolved_at(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test ticket service sets resolved time if status is CLOSED.

    Verifies resolved_at is auto-set on status change to CLOSED.
    """
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    created_ticket = await create_ticket(session=test_session, data=data)

    # Verify initial state
    assert created_ticket.status == TicketStatus.OPEN
    assert created_ticket.resolved_at is None

    update_data = TicketUpdate(status=TicketStatus.CLOSED)

    # Act
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert after updating
    assert updated_ticket.status == TicketStatus.CLOSED
    assert updated_ticket.resolved_at is not None


async def test_update_ticket_status_open_clears_resolved_at(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test ticket service clears resolved time if status is set to OPEN.

    Verifies resolved_at is auto-set on status change to RESOLVED/OPEN.
    Needs the chain of statuses:
        OPEN (resolved_at is None) ->
        RESOLVED (resolved_at is not None) ->
        OPEN again (resolved_at is None).
    """
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    # status default - OPEN
    created_ticket = await create_ticket(session=test_session, data=data)

    # Verify initial state
    assert created_ticket.status == TicketStatus.OPEN
    assert created_ticket.resolved_at is None

    # status - RESOLVED
    update_data = TicketUpdate(status=TicketStatus.RESOLVED)

    # Act 1
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert after updating
    assert updated_ticket.status == TicketStatus.RESOLVED
    assert updated_ticket.resolved_at is not None

    # status - OPEN
    update_data = TicketUpdate(status=TicketStatus.OPEN)

    # Act 2
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert after updating
    assert updated_ticket.status == TicketStatus.OPEN
    assert updated_ticket.resolved_at is None


async def test_update_ticket_status_in_progress_clears_resolved_at(
    test_session: AsyncSession,
    sample_service: Service,
) -> None:
    """Test ticket service clears resolved time if status is set to IN_PROGRESS.

    Verifies resolved_at is auto-set on status change to RESOLVED/IN_PROGRESS.
    Needs the chain of statuses:
        OPEN (resolved_at is None) ->
        RESOLVED (resolved_at is not None) ->
        IN_PROGRESS (resolved_at is None).
    """
    # Arrange
    data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        priority=TicketPriority.P1,
    )
    # status default - OPEN
    created_ticket = await create_ticket(session=test_session, data=data)

    # Verify initial state
    assert created_ticket.status == TicketStatus.OPEN
    assert created_ticket.resolved_at is None

    # status - RESOLVED
    update_data = TicketUpdate(status=TicketStatus.RESOLVED)

    # Act 1
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert after updating
    assert updated_ticket.status == TicketStatus.RESOLVED
    assert updated_ticket.resolved_at is not None

    # status - OPEN
    update_data = TicketUpdate(status=TicketStatus.IN_PROGRESS)

    # Act 2
    updated_ticket = await update_ticket(
        session=test_session,
        ticket_id=created_ticket.id,
        update_data=update_data,
    )

    # Assert after updating
    assert updated_ticket.status == TicketStatus.IN_PROGRESS
    assert updated_ticket.resolved_at is None


async def test_update_ticket_nonexistent_ticket(test_session: AsyncSession) -> None:
    """Test ticket service returns correct exception during updating ticket.

    Returns 404 exception by updating a ticket if ticket not found.
    """
    # Arrange
    nonexistent_id = uuid.uuid4()
    update_data = TicketUpdate(title="Updated title")

    # Act
    with pytest.raises(HTTPException) as exc_info:
        await update_ticket(
            session=test_session,
            ticket_id=nonexistent_id,
            update_data=update_data,
        )

    # Assert
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


async def test_list_tickets_no_filters(test_session: AsyncSession, sample_service: Service) -> None:
    """Test ticket service can return list of all existing tickets.

    Without filters and pagination arguments it returns the full list of tickets.
    """
    # Arrange
    data_1 = TicketCreate(
        service_id=sample_service.id,
        title="Test_1",
        priority=TicketPriority.P1,
    )
    data_2 = TicketCreate(
        service_id=sample_service.id,
        title="Test_2",
        priority=TicketPriority.P1,
    )
    await create_ticket(session=test_session, data=data_1)
    await create_ticket(session=test_session, data=data_2)

    # Act
    tickets, total = await list_tickets(test_session)

    # Assert
    assert len(tickets) == 2
    assert total == 2


async def test_list_tickets_filter_by_status(
    test_session: AsyncSession, sample_service: Service
) -> None:
    """Test ticket service filters list of tickets by status."""
    # Arrange
    # - create two tickets
    data_1 = TicketCreate(
        service_id=sample_service.id,
        title="Test_1",
        priority=TicketPriority.P1,
    )
    data_2 = TicketCreate(
        service_id=sample_service.id,
        title="Test_2",
        priority=TicketPriority.P1,
    )
    await create_ticket(session=test_session, data=data_1)
    created_ticket_2 = await create_ticket(session=test_session, data=data_2)

    # - change status of second ticket to RESOLVED
    update_data = TicketUpdate(status=TicketStatus.RESOLVED)
    await update_ticket(
        session=test_session,
        ticket_id=created_ticket_2.id,
        update_data=update_data,
    )

    # Act
    tickets, total = await list_tickets(
        test_session,
        status=TicketStatus.OPEN,
    )

    # Assert
    assert len(tickets) == 1
    assert total == 1
    assert tickets[0].title == "Test_1"


async def test_list_tickets_filter_by_priority(
    test_session: AsyncSession, sample_service: Service
) -> None:
    """Test ticket service filters list of tickets by priority."""
    # Arrange
    # - create two tickets
    data_1 = TicketCreate(
        service_id=sample_service.id,
        title="Test_1",
        priority=TicketPriority.P1,
    )
    data_2 = TicketCreate(
        service_id=sample_service.id,
        title="Test_2",
        priority=TicketPriority.P2,
    )
    await create_ticket(session=test_session, data=data_1)
    await create_ticket(session=test_session, data=data_2)

    # Act
    tickets, total = await list_tickets(
        test_session,
        priority=TicketPriority.P1,
    )

    # Assert
    assert len(tickets) == 1
    assert total == 1
    assert tickets[0].title == "Test_1"


async def test_list_tickets_filter_by_service_id(
    test_session: AsyncSession, sample_service: Service
) -> None:
    """Test ticket service filters list of tickets by service_id."""
    # Arrange
    # - create two tickets
    service_1_id = sample_service.id

    data_1 = TicketCreate(
        service_id=service_1_id,
        title="Test_1",
        priority=TicketPriority.P1,
    )

    # Create the second service_id
    service_2 = Service(name="test-service-2", description="Test service 2")
    test_session.add(service_2)
    await test_session.commit()
    await test_session.refresh(service_2)

    data_2 = TicketCreate(
        service_id=service_2.id,
        title="Test_2",
        priority=TicketPriority.P2,
    )
    await create_ticket(session=test_session, data=data_1)
    await create_ticket(session=test_session, data=data_2)

    # Act
    tickets, total = await list_tickets(
        test_session,
        service_id=service_1_id,
    )

    # Assert
    assert len(tickets) == 1
    assert total == 1
    assert tickets[0].title == "Test_1"


async def test_list_tickets_empty(test_session: AsyncSession) -> None:
    """Test ticket service can return empty list when no tickets exist."""
    # Act
    tickets, total = await list_tickets(session=test_session)

    # Assert
    assert len(tickets) == 0
    assert total == 0


async def test_list_tickets_pagination(test_session: AsyncSession, sample_service: Service) -> None:
    """Test ticket service can return list of ticket with limit and offset."""
    # Arrange
    data_1 = TicketCreate(
        service_id=sample_service.id,
        title="Test_1",
        priority=TicketPriority.P1,
    )
    data_2 = TicketCreate(
        service_id=sample_service.id,
        title="Test_2",
        priority=TicketPriority.P1,
    )
    data_3 = TicketCreate(
        service_id=sample_service.id,
        title="Test_3",
        priority=TicketPriority.P1,
    )
    await create_ticket(session=test_session, data=data_1)
    await create_ticket(session=test_session, data=data_2)
    await create_ticket(session=test_session, data=data_3)

    # Act 1
    tickets, total = await list_tickets(
        session=test_session,
        limit=2,
        offset=0,
    )

    # Assert 1
    assert len(tickets) == 2
    assert total == 3

    # Act 2
    tickets, total = await list_tickets(
        session=test_session,
        limit=2,
        offset=2,
    )

    # Assert 2
    assert len(tickets) == 1
    assert total == 3
