"""Service layer for (IT) service operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.logging import get_logger
from incident_intel.models.service import Service

logger = get_logger(__name__)


async def list_services(session: AsyncSession) -> list[Service]:
    """Get a list of services.

    Args:
        session: Active database session.

    Returns:
        The list of services.
    """
    stmt = select(Service).order_by(Service.name)

    result = await session.execute(stmt)
    services = list(result.scalars().all())

    logger.debug("services_listed", count=len(services))

    return services
