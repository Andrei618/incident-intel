"""Pydantic schemas for (IT) service operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ServiceResponse(BaseModel):
    """Response schema for a single service."""

    id: UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
