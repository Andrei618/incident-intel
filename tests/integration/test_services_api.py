"""Integration tests for service API."""

from fastapi import status
from httpx import AsyncClient

from incident_intel.models.service import Service


async def test_get_service_list_empty_returns_empty_list(
    client: AsyncClient,
) -> None:
    """GET /api/v1/services when zero services exist returns empty list."""
    # Arrange + Act
    response = await client.get("/api/v1/services")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == []


async def test_get_service_list_retuns_200(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/services return list of services with metadata."""
    # Arrange + Act
    response = await client.get("/api/v1/services")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_service.id)
    assert data[0]["name"] == sample_service.name
    assert data[0]["description"] == sample_service.description
    assert "created_at" in data[0]
