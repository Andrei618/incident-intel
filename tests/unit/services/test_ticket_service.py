"""Unit tests for ticket service."""

from incident_intel.schemas.ticket import TicketCreate, TicketPriority, TicketStatus
from incident_intel.services.ticket_service import create_ticket


async def test_create_ticket(test_session, sample_service) -> None:
    """Test ticket service."""
    # test_service = sample_service()

    test_data = TicketCreate(
        service_id=sample_service.id,
        title="Test",
        status=TicketStatus.OPEN,
        priority=TicketPriority.P1,
    )
    # Act
    created_ticket = await create_ticket(session=test_session, data=test_data)

    # Assert
    assert created_ticket.id is not None
    assert created_ticket.title == "Test"
    assert created_ticket.service_id == sample_service.id
