"""Test health endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from incident_intel.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for each test."""
    return TestClient(app)


@patch("incident_intel.api.health.check_redis_connection")
@patch("incident_intel.api.health.check_database_connection")
def test_health_endpoint_returns_healthy_status(
    mock_db: MagicMock,
    mock_redis: MagicMock,
    client: TestClient,
) -> None:
    """Health endpoint returns healthy status if both services connected."""
    # Arrange (setup mocks)
    mock_db.return_value = True
    mock_redis.return_value = True
    # Act (call endpoint)
    response = client.get("/health")
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
    }


@patch("incident_intel.api.health.check_redis_connection")
@patch("incident_intel.api.health.check_database_connection")
def test_health_endpoint_database_down(
    mock_db: MagicMock,
    mock_redis: MagicMock,
    client: TestClient,
) -> None:
    """Health endpoint returns unhealthy status if database is disconnected."""
    # Arrange (setup mocks)
    mock_db.return_value = False
    mock_redis.return_value = True
    # Act (call endpoint)
    response = client.get("/health")
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "unhealthy",
        "database": "disconnected",
        "redis": "connected",
    }


@patch("incident_intel.api.health.check_redis_connection")
@patch("incident_intel.api.health.check_database_connection")
def test_health_endpoint_redis_down(
    mock_db: MagicMock,
    mock_redis: MagicMock,
    client: TestClient,
) -> None:
    """Health endpoint returns unhealthy status if redis is disconnected."""
    # Arrange (setup mocks)
    mock_db.return_value = True
    mock_redis.return_value = False
    # Act (call endpoint)
    response = client.get("/health")
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "unhealthy",
        "database": "connected",
        "redis": "disconnected",
    }


@patch("incident_intel.api.health.check_redis_connection")
@patch("incident_intel.api.health.check_database_connection")
def test_health_endpoint_database_and_redis_down(
    mock_db: MagicMock,
    mock_redis: MagicMock,
    client: TestClient,
) -> None:
    """Health endpoint returns unhealthy status if redis is disconnected."""
    # Arrange (setup mocks)
    mock_db.return_value = False
    mock_redis.return_value = False
    # Act (call endpoint)
    response = client.get("/health")
    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "unhealthy",
        "database": "disconnected",
        "redis": "disconnected",
    }
