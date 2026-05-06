"""API endpoint for service management."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import get_session
from incident_intel.models.service import Service
from incident_intel.schemas.service import ServiceResponse
from incident_intel.services.service_service import list_services

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceResponse])
async def list_services_endpoint(session: AsyncSession = Depends(get_session)) -> list[Service]:
    """List services.

    Returns:
        list[Services]
    """
    return await list_services(session=session)
