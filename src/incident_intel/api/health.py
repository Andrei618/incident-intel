"""Router for health check."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Return application health status for monitoring and load balancers."""
    return {"status": "ok"}
