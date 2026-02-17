"""Service layer for ticket operations."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import ColumnElement

from incident_intel.core.logging import get_logger
from incident_intel.exceptions import ServiceNotFoundError, TicketNotFoundError
from incident_intel.models.ticket import Ticket, TicketPriority, TicketStatus
from incident_intel.schemas.ticket import TicketCreate, TicketUpdate

logger = get_logger(__name__)


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
        ServiceNotFoundError: If service_id does not exist.
        HTTPException: 400 if data violates business rule constraints.
    """
    # Production-safe: identifiers only, no PII
    logger.info("ticket_creating", service_id=str(data.service_id))
    # Development only: includes user content for debugging
    logger.debug("ticket_creating_detail", title=data.title, service_id=str(data.service_id))

    ticket_dict = data.model_dump()
    new_ticket = Ticket(**ticket_dict)

    session.add(new_ticket)

    try:
        await session.commit()
        await session.refresh(new_ticket)  # Reload to get the generated ID
        logger.info("ticket_created", ticket_id=str(new_ticket.id))
    except IntegrityError as e:
        await session.rollback()
        error_msg = str(e.orig)
        logger.error(
            "ticket_creation_failed",
            service_id=str(data.service_id),
            error_type=type(e).__name__,
        )
        logger.debug("ticket_creation_failed_detail", error=str(e))

        if "fk_tickets_service_id_services" in error_msg:
            raise ServiceNotFoundError(data.service_id) from e

        # TODO Replace all HTTPExceptions with domain exceptions in service layer.
        # Related issue - #16.
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
        TicketNotFoundError: If ticket does not exist.
    """
    logger.debug("ticket_fetching", ticket_id=str(ticket_id))

    # Build and execute query
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    ticket = await session.scalar(stmt)

    # Handle not found
    if ticket is None:
        logger.warning("ticket_not_found", ticket_id=str(ticket_id))
        raise TicketNotFoundError(ticket_id)

    logger.debug("ticket_found", ticket_id=str(ticket_id))
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
        TicketNotFoundError: If ticket does not exist.
        HTTPException: 400 if data violates business rule constraints.
    """
    # Get existing ticket (raises TicketNotFoundError if not found)
    ticket = await get_ticket(session, ticket_id)

    # Get only the fields that were provided
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return ticket
    logger.info("ticket_updating", ticket_id=str(ticket_id), fields=list(update_dict.keys()))
    logger.debug(
        "ticket_updating_detail",
        ticket_id=str(ticket_id),
        fields=list(update_dict.keys()),
        title=update_dict.get("title"),
    )

    # Apply business logic for resolved_at
    if "status" in update_dict:
        if update_dict["status"] in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            # Auto-set resolved_at when resolving or closing
            ticket.resolved_at = datetime.now(UTC)
        elif update_dict["status"] in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]:
            # Clear resolved_at when reopening
            ticket.resolved_at = None

    # Update each field
    for field, value in update_dict.items():
        setattr(ticket, field, value)

    # Commit with error handling
    try:
        await session.commit()
        await session.refresh(ticket)
        logger.info("ticket_updated", ticket_id=str(ticket_id))
    except IntegrityError as e:
        await session.rollback()
        error_msg = str(e.orig)
        logger.error(
            "ticket_update_failed",
            ticket_id=str(ticket_id),
            fields=list(update_dict.keys()),
            error_type=type(e).__name__,
        )
        logger.debug("ticket_update_failed_detail", error=error_msg)

        if "ck_" in error_msg or "resolved_requires_status" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Data violates business rules (e.g., resolved_at without proper status)",
            ) from e
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid data: constraint violation",
            ) from e

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
    # Build filter conditions
    filters: list[ColumnElement[bool]] = []
    log_meta: dict[str, str] = {}  # for logging filter conditions applied
    if status is not None:
        filters.append(Ticket.status == status)
        log_meta["status"] = status.value
    if priority is not None:
        filters.append(Ticket.priority == priority)
        log_meta["priority"] = priority.value
    if service_id is not None:
        filters.append(Ticket.service_id == service_id)
        log_meta["service_id"] = str(service_id)

    # Main query
    stmt = select(Ticket).where(*filters)
    stmt = stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc())
    stmt = stmt.limit(limit).offset(offset)

    # Execute main query
    result = await session.execute(stmt)
    tickets = list(result.scalars().all())

    # Count query
    count_stmt = select(func.count()).select_from(Ticket).where(*filters)
    total = await session.scalar(count_stmt) or 0

    logger.debug(
        "ticket_listed",
        count=len(tickets),
        total=total,
        **log_meta,
    )
    return tickets, total
