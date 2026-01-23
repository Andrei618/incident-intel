"""Pydantic schemas for tickets."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from incident_intel.models.ticket import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    """Request schema for creating a new ticket."""

    service_id: UUID = Field(
        ...,
        description="UUID of the service this ticket belongs to",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Ticket title",
    )
    description: str | None = Field(
        None,
        description="Detailed description of the issue",
    )
    priority: TicketPriority = Field(
        ...,
        description="Priority level",
        examples=["P1", "P2", "P3", "P4"],
    )
    assignee: str | None = Field(
        None,
        max_length=100,
        description="Assigned user",
    )
    reporter: str | None = Field(
        None,
        max_length=100,
        description="User who reported the issue",
    )


class TicketUpdate(BaseModel):
    """Request schema for updating an existing ticket.

    All fields are optional to support partial updates.
    """

    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Ticket title",
    )
    description: str | None = Field(
        None,
        description="Detailed description of the issue",
    )
    status: TicketStatus | None = Field(
        None, description="Ticket status", examples=["open", "in_progress", "resolved", "closed"]
    )
    priority: TicketPriority | None = Field(
        None,
        description="Priority level",
        examples=["P1", "P2", "P3", "P4"],
    )
    assignee: str | None = Field(
        None,
        max_length=100,
        description="Assigned user",
    )
    reporter: str | None = Field(
        None,
        max_length=100,
        description="User who reported the issue",
    )


class TicketResponse(BaseModel):
    """Response schema for a single ticket."""

    id: UUID
    service_id: UUID
    title: str
    description: str | None
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime | None
    resolved_at: datetime | None
    assignee: str | None
    reporter: str | None

    model_config = ConfigDict(from_attributes=True)  # Enables ORM conversion


class TicketListResponse(BaseModel):
    """Response schema for paginated ticket list."""

    items: list[TicketResponse]
    total: int = Field(..., description="Total number of tickets matching filters")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Number of items skipped")
