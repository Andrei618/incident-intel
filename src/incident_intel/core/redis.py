"""Redis connection and session management."""

import os

import redis.asyncio as redis

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

redis_client = redis.from_url(REDIS_URL)


async def check_redis_connection() -> bool:
    """Check if Redis is accessible.

    Returns:
        True if Redis connection is healthy, False otherwise.
    """
    try:
        response: bool = await redis_client.ping()
        return response
    except Exception:
        return False
