"""Integration tests for ticket API."""

import uuid

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.models.service import Service


# ============== POST TICKET ===================
async def test_create_ticket_return_201(client: AsyncClient, sample_service: Service) -> None:
    """POST /api/v1/tickets creates ticket and returns 201."""
    # Arrange
    payload = {
        "service_id": str(sample_service.id),
        "title": "Database connection timeout",
        "description": "Cannot connect to production database",
        "priority": "P1",
    }

    # Act
    response = await client.post("/api/v1/tickets", json=payload)

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["service_id"] == str(sample_service.id)
    assert data["title"] == "Database connection timeout"
    assert data["description"] == "Cannot connect to production database"
    assert data["priority"] == "P1"
    assert data["status"] == "OPEN"
    uuid.UUID(data["id"])  # Validates "id" has a valid UUID format
    assert "created_at" in data


async def test_create_ticket_with_invalid_service_id_returns_400(
    client: AsyncClient,
) -> None:
    """POST /api/v1/tickets with non-existent service_id returns 400."""
    # Arrange
    payload = {
        "service_id": str(uuid.uuid4()),
        "title": "Database connection timeout",
        "description": "Cannot connect to production database",
        "priority": "P1",
    }

    # Act
    response = await client.post("/api/v1/tickets", json=payload)

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data
    assert "does not exist" in data["detail"]
    assert str(payload["service_id"]) in data["detail"]


async def test_create_ticket_missing_required_fields_returns_422(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """POST /api/v1/tickets without required fields returns 422."""
    # Arrange
    payload = {
        "service_id": str(sample_service.id),
        "description": "Cannot connect to production database",
    }

    # Act
    response = await client.post("/api/v1/tickets", json=payload)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) == 2  # Missing title and priority


async def test_create_ticket_invalid_priority_returns_422(
    client: AsyncClient,
) -> None:
    """POST /api/v1/tickets with invalid format of enum priority returns 422."""
    # Arrange
    payload = {
        "service_id": str(uuid.uuid4()),
        "title": "Database connection timeout",
        "priority": "INVALID_PRIORITY",
    }

    # Act
    response = await client.post("/api/v1/tickets", json=payload)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


# ============== GET TICKET ===================
async def test_get_ticket_returns_200(
    client: AsyncClient,
    sample_ticket: dict,
) -> None:
    """GET /api/v1/tickets/{ticket_id} gets existing ticket and returns 200."""
    # Arrange
    ticket_id = sample_ticket["id"]

    # Act
    response = await client.get(f"/api/v1/tickets/{ticket_id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == ticket_id
    assert data["title"] == "Test ticket"
    assert data["priority"] == "P1"
    assert data["service_id"] == sample_ticket["service_id"]


async def test_get_ticket_not_found_returns_404(client: AsyncClient) -> None:
    """GET /api/v1/tickets/{ticket_id} with non-existing ticket_id returns 404."""
    # Arrange
    ticket_id = str(uuid.uuid4())

    # Act
    response = await client.get(f"/api/v1/tickets/{ticket_id}")

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"]
    assert ticket_id in data["detail"]


async def test_get_ticket_invalid_uuid_returns_422(
    client: AsyncClient,
) -> None:
    """GET /api/v1/tickets/{ticket_id} with invalide UUID format of ticket_id returns 422."""
    # Act
    response = await client.get("/api/v1/tickets/UUID_INVALID_FORMAT")

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


# ============== UPDATE TICKET ===================
async def test_update_ticket_returns_200(
    client: AsyncClient,
    sample_ticket: dict,
) -> None:
    """PUT /api/v1/tickets/{ticket_id} updates ticket and returns 200."""
    # Arrange
    ticket_id = sample_ticket["id"]

    payload = {
        "title": "Updated test title",
        "description": "Updated test description",
        "priority": "P2",
        "assignee": "Updated test assignee",
    }

    # Act
    response = await client.put(f"/api/v1/tickets/{ticket_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Verify the updated fields changed
    assert data["title"] == "Updated test title"
    assert data["description"] == "Updated test description"
    assert data["priority"] == "P2"
    assert data["assignee"] == "Updated test assignee"
    # Verify unchanged fields stayed the same
    assert data["status"] == "OPEN"
    assert data["reporter"] == "Test reporter"


async def test_update_ticket_empty_input_returns_unchanchaged_ticket(
    client: AsyncClient,
    sample_ticket: dict,
) -> None:
    """PUT /api/v1/tickets/{ticket_id} updates ticket with empty input does not change ticket.

    Get the ticket back unchanged.
    """
    # Arrange
    ticket_id = sample_ticket["id"]

    # Act
    response = await client.put(f"/api/v1/tickets/{ticket_id}", json={})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Test ticket"
    assert data["description"] == "Sample ticket for integration tests"
    assert data["priority"] == "P1"
    assert data["assignee"] == "Test assignee"
    assert data["reporter"] == "Test reporter"


async def test_update_ticket_non_existing_ticket_returns_404(
    client: AsyncClient,
) -> None:
    """PUT /api/v1/tickets/{ticket_id} with non-existing ticket returns 404."""
    # Arrange
    ticket_id = str(uuid.uuid4())
    payload = {"title": "Updated title"}

    # Act
    response = await client.put(f"/api/v1/tickets/{ticket_id}", json=payload)

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"]
    assert ticket_id in data["detail"]


async def test_update_ticket_status_to_resolved_sets_resolved_at(
    client: AsyncClient,
    sample_ticket: dict,
) -> None:
    """PUT /api/v1/tickets/{ticket_id} sets resolved_at when status becomes RESOLVED."""
    # Arrange
    ticket_id = sample_ticket["id"]
    assert sample_ticket["resolved_at"] is None

    # Act
    response = await client.put(f"/api/v1/tickets/{ticket_id}", json={"status": "RESOLVED"})

    # Assert — resolved_at should be auto-set
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "RESOLVED"
    assert data["resolved_at"] is not None


# TODO(II-031): Add test for reopening resolved ticket (clears resolved_at)
# Verify ticket_service.py:146-148 - status change to OPEN/IN_PROGRESS clears resolved_at
# Test: RESOLVED → OPEN, assert resolved_at becomes None

# TODO(II-031): Add test for CLOSED status setting resolved_at
# Verify ticket_service.py:142 - CLOSED also sets resolved_at (currently only RESOLVED tested)
# Test: OPEN → CLOSED, assert resolved_at is set


async def test_update_ticket_invalid_uuid_returns_422(
    client: AsyncClient,
) -> None:
    """PUT /api/v1/tickets/{ticket_id} with invalid UUID format returns 422."""
    # Act
    response = await client.put(
        "/api/v1/tickets/INVALID_UUID",
        json={"title": "Updated title"},
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = response.json()
    assert "detail" in data


# ============== GET LIST OF TICKETS===================
async def test_get_ticket_list_returns_200(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/tickets returns list of tickets with metadata."""
    # Arrange - create 2 tickets
    for title in ["Ticket A", "Ticket B"]:
        await client.post(
            "/api/v1/tickets",
            json={
                "service_id": str(sample_service.id),
                "title": title,
                "priority": "P1",
            },
        )
    # Act
    response = await client.get("/api/v1/tickets")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_get_ticket_list_filter_by_status(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/tickets filters tickets by status."""
    # Arrange - create 2 tickets
    ticket_a = await client.post(
        "/api/v1/tickets",
        json={
            "service_id": str(sample_service.id),
            "title": "Ticket A",
            "priority": "P1",
        },
    )
    await client.post(
        "/api/v1/tickets",
        json={
            "service_id": str(sample_service.id),
            "title": "Ticket B",
            "priority": "P1",
        },
    )
    assert ticket_a.status_code == status.HTTP_201_CREATED

    ticket_a_id = ticket_a.json()["id"]
    # Change status
    await client.put(f"/api/v1/tickets/{ticket_a_id}", json={"status": "IN_PROGRESS"})

    # Act
    response = await client.get("/api/v1/tickets?status=IN_PROGRESS")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "IN_PROGRESS"


async def test_get_ticket_list_filter_by_priority(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/tickets filters tickets by priority."""
    # Arrange - create 2 tickets
    for priority in ["P1", "P3"]:
        response = await client.post(
            "/api/v1/tickets",
            json={
                "service_id": str(sample_service.id),
                "title": "Test title",
                "priority": priority,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    # Act
    response = await client.get("/api/v1/tickets?priority=P1")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["priority"] == "P1"


async def test_get_ticket_list_filter_by_service_id(
    client: AsyncClient,
    sample_service: Service,
    test_session: AsyncSession,
) -> None:
    """GET /api/v1/tickets filters tickets by service_id."""
    # Arrange
    # Create a second service
    service_b = Service(name="service-b", description="Second service")
    test_session.add(service_b)
    await test_session.commit()
    await test_session.refresh(service_b)

    # Create 2 tickets with different services
    ticket_a = await client.post(
        "/api/v1/tickets",
        json={
            "service_id": str(
                sample_service.id
            ),  # with first service (sample_service from fixture)
            "title": "Ticket A",
            "priority": "P1",
        },
    )
    await client.post(
        "/api/v1/tickets",
        json={
            "service_id": str(service_b.id),  # with second service
            "title": "Ticket B",
            "priority": "P1",
        },
    )
    assert ticket_a.status_code == status.HTTP_201_CREATED

    # Act - filter by sample_service
    response = await client.get(f"/api/v1/tickets?service_id={sample_service.id}")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["service_id"] == str(sample_service.id)


async def test_get_ticket_list_pagination_works(
    client: AsyncClient,
    sample_service: Service,
) -> None:
    """GET /api/v1/tickets apply pagination to the tickets list."""
    # Arrange - create 3 tickets
    for title in ["Ticket A", "Ticket B", "Ticket C"]:
        response = await client.post(
            "/api/v1/tickets",
            json={
                "service_id": str(sample_service.id),
                "title": title,
                "priority": "P1",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
    # Act 1 - first page
    response = await client.get("/api/v1/tickets?limit=1&offset=0")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["offset"] == 0

    # Act 2 - second page
    response = await client.get("/api/v1/tickets?limit=1&offset=1")

    # Assert 2
    assert response.status_code == status.HTTP_200_OK
    data_2 = response.json()
    assert len(data_2["items"]) == 1
    assert data_2["total"] == 3
    assert data_2["items"][0]["id"] != data["items"][0]["id"]


# TODO(II-031): Add test verifying pagination ordering contract
# Verify ticket_service.py:236 - results ordered by created_at desc, id desc
# Test: Create tickets with known timestamps, verify first page returns newest first


async def test_get_ticket_list_empty_returns_empty_items(
    client: AsyncClient,
) -> None:
    """GET /api/v1/tickets when zero tickets exist return empty items."""
    # Arrange

    # Act
    response = await client.get("/api/v1/tickets")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 20
    assert data["offset"] == 0


async def test_get_ticket_list_offset_beyond_total(
    client: AsyncClient,
) -> None:
    """GET /api/v1/tickets when offset >= total return accurate total."""
    # Arrange

    # Act
    response = await client.get("/api/v1/tickets?limit=10&offset=999")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 10
    assert data["offset"] == 999
