"""Router for health check."""

import asyncio

from fastapi import APIRouter

from incident_intel.core.database import check_database_connection
from incident_intel.core.redis import check_redis_connection

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return application health status for monitoring and load balancers."""
    db_ok, redis_ok = await asyncio.gather(
        check_database_connection(),
        check_redis_connection(),
    )

    return {
        "status": "healthy" if (db_ok and redis_ok) else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
    }
