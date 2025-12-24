"""Test health endpoint."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from incident_intel.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for each test."""
    return TestClient(app)


def test_health_endpoint_returns_ok_status(client: TestClient) -> None:
    """Health endpoint returns proper response."""
    # Arrange & Act
    response = client.get("/health")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
