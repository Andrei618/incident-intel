"""Service layer for ticket operations."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.ticket import Ticket, TicketPriority, TicketStatus
from incident_intel.schemas.ticket import TicketCreate, TicketUpdate


async def create_ticket(
    session: AsyncSession,
    data: TicketCreate,
) -> Ticket:
    """Create a new ticket.

    Args:
        session: Active database session.
        data: Validated ticket creation data.

    Returns:
        Created ticket with generated ID and timestamps.

    Raises:
        HTTPException: 400 if service_id doesn't exist or data violates constraints.
    """
    ticket_dict = data.model_dump()
    new_ticket = Ticket(**ticket_dict)
    session.add(new_ticket)

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        error_msg = str(e.orig)

        if "fk_tickets_service_id_services" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=f"Service with ID {data.service_id} does not exist",
            ) from e
        elif "ck_" in error_msg or "resolved_requires_status" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Data violates business rules (e.g., resolved_at without proper status)",
            ) from e
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid data: constraint violation",
            ) from e

    await session.refresh(new_ticket)
    return new_ticket


async def get_ticket(
    session: AsyncSession,
    ticket_id: UUID,
) -> Ticket:
    """Get a ticket by ID.

    Args:
        session: Active database session.
        ticket_id: UUID of the ticket to retrieve.

    Returns:
        The requested ticket.

    Raises:
        HTTPException: 404 if ticket not found.
    """
    # Build and execute query
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    ticket = await session.scalar(stmt)

    # Handle not found
    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket {ticket_id} not found",
        )

    return ticket


async def update_ticket(
    session: AsyncSession, ticket_id: UUID, update_data: TicketUpdate
) -> Ticket:
    """Update an existing ticket.

    Args:
        session: Active database session.
        ticket_id: UUID of the ticket to update.
        update_data: Fields to update (partial updates supported).

    Returns:
        Updated ticket.

    Raises:
        HTTPException: 404 if ticket not found.
    """
    # 1. Get existing ticket (raises 404 if not found)
    ticket = await get_ticket(session, ticket_id)

    # 2. Get only the fields that were provided
    update_dict = update_data.model_dump(exclude_unset=True)

    # 3. Apply business logic for resolved_at
    if "status" in update_dict:
        if update_dict["status"] in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            # Auto-set resolved_at when closing
            if ticket.resolved_at is None:
                ticket.resolved_at = datetime.now(UTC)
        elif update_dict["status"] in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]:
            # Clear resolved_at when reopening
            ticket.resolved_at = None

    # 4. Update each field
    for field, value in update_dict.items():
        setattr(ticket, field, value)

    # 5. Commit with error handling
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        error_msg = str(e.orig)

        if "fk_tickets_service_id_services" in error_msg:
            service_id = update_dict.get("service_id", "unknown")
            raise HTTPException(
                status_code=400,
                detail=f"Service with ID {service_id} does not exist",
            ) from e
        elif "ck_" in error_msg or "resolved_requires_status" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Data violates business rules (e.g., resolved_at without proper status)",
            ) from e
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid data: constraint violation",
            ) from e

    await session.refresh(ticket)
    return ticket


async def list_tickets(
    session: AsyncSession,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    service_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Ticket], int]:
    """List tickets with optional filters and pagination.

    Args:
        session: Active database session.
        status: Filter by ticket status (optional).
        priority: Filter by priority level (optional).
        service_id: Filter by service ID (optional).
        limit: Maximum number of tickets to return (default: 20).
        offset: Number of tickets to skip (default: 0).

    Returns:
        Tuple of (list of tickets, total count matching filters).

    Example:
    >>> tickets, total = await list_tickets(
    ...     session,
    ...     status=TicketStatus.OPEN,
    ...     limit=10
    ... )
    >>> print(f"Found {total} open tickets, showing first 10")
    """
    # 1. Build filter conditions
    filters = []
    if status is not None:
        filters.append(Ticket.status == status)
    if priority is not None:
        filters.append(Ticket.priority == priority)
    if service_id is not None:
        filters.append(Ticket.service_id == service_id)

    # 2. Main query
    stmt = select(Ticket).where(*filters)
    stmt = stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc())
    stmt = stmt.limit(limit).offset(offset)

    # 3. Execute main query
    result = await session.execute(stmt)
    tickets = list(result.scalars().all())

    # 4. Count query
    count_stmt = select(func.count()).select_from(Ticket).where(*filters)
    total = await session.scalar(count_stmt) or 0

    # 5. Return results
    return tickets, total
