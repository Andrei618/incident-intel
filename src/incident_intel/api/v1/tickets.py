"""API endpoints for ticket management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import get_session
from incident_intel.exceptions import (
    BusinessRuleViolationError,
    ServiceNotFoundError,
    TicketNotFoundError,
)
from incident_intel.models.ticket import Ticket, TicketPriority, TicketStatus
from incident_intel.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from incident_intel.services.ticket_service import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(
    ticket: TicketCreate,
    session: AsyncSession = Depends(get_session),
) -> Ticket:
    """Create a new ticket.

    Raises:
        HTTPException(400) if service_id not found: FK constraint violation.
        HTTPException(400) if business rules violated.
    """
    try:
        return await create_ticket(
            data=ticket,
            session=session,
        )
    except ServiceNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket_endpoint(
    ticket_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Ticket:
    """Get ticket by ID.

    Raises:
        HTTPException(404) if ticket not found.
    """
    try:
        return await get_ticket(
            ticket_id=ticket_id,
            session=session,
        )
    except TicketNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket_endpoint(
    ticket_id: UUID,
    update_data: TicketUpdate,
    session: AsyncSession = Depends(get_session),
) -> Ticket:
    """Update ticket by ID. Accepts partial updates.

    Raises:
        HTTPException(404) if ticket not found.
        HTTPException(400) if business rules violated.
    """
    try:
        return await update_ticket(
            ticket_id=ticket_id,
            update_data=update_data,
            session=session,
        )
    except TicketNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except BusinessRuleViolationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=TicketListResponse)
async def list_tickets_endpoint(
    status: TicketStatus | None = Query(None, description="Filter by status"),
    priority: TicketPriority | None = Query(None, description="Filter by priority"),
    service_id: UUID | None = Query(None, description="Filter by service ID"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    session: AsyncSession = Depends(get_session),
) -> TicketListResponse:
    """List tickets with optional filters and pagination.

    Returns:
        TicketListResponse: Paginated list of tickets with metadata.
    """
    tickets, total = await list_tickets(
        status=status,
        priority=priority,
        service_id=service_id,
        limit=limit,
        offset=offset,
        session=session,
    )
    return TicketListResponse(
        items=[
            TicketResponse.model_validate(ticket) for ticket in tickets
        ],  # Explicit for mypy --strict
        total=total,
        limit=limit,
        offset=offset,
    )
