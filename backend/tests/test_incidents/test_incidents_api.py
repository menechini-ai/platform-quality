"""Tests for the incidents API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_incidents_empty(client: AsyncClient):
    """GET /api/v1/incidents returns empty list when no incidents exist."""
    response = await client.get("/api/v1/incidents")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_incident(client: AsyncClient):
    """POST /api/v1/incidents creates a new incident."""
    payload = {
        "title": "High CPU on production",
        "severity": "SEV-2",
        "status": "active",
        "service": "api-gateway",
    }
    response = await client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "High CPU on production"
    assert data["severity"] == "SEV-2"
    assert data["status"] == "active"
    assert data["service"] == "api-gateway"
    assert "id" in data
    assert data["timeline"] == []


@pytest.mark.asyncio
async def test_create_and_list_incidents(client: AsyncClient):
    """After creating an incident, listing returns it."""
    await client.post(
        "/api/v1/incidents",
        json={"title": "DB connection spike", "severity": "SEV-1"},
    )
    response = await client.get("/api/v1/incidents")
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "DB connection spike"


@pytest.mark.asyncio
async def test_get_incident_by_id(client: AsyncClient):
    """GET /api/v1/incidents/:id returns the incident."""
    create_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Memory leak", "severity": "SEV-3"},
    )
    incident_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/incidents/{incident_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Memory leak"


@pytest.mark.asyncio
async def test_get_incident_not_found(client: AsyncClient):
    """GET /api/v1/incidents/:id returns 404 for unknown ID."""
    response = await client.get("/api/v1/incidents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_incident(client: AsyncClient):
    """PATCH /api/v1/incidents/:id updates fields."""
    create_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Disk full", "severity": "SEV-3", "status": "active"},
    )
    incident_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"status": "resolved", "title": "Disk full (resolved)"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["title"] == "Disk full (resolved)"


@pytest.mark.asyncio
async def test_filter_incidents_by_status(client: AsyncClient):
    """Listing with status filter returns only matching incidents."""
    await client.post(
        "/api/v1/incidents",
        json={"title": "Active issue", "severity": "SEV-2", "status": "active"},
    )
    await client.post(
        "/api/v1/incidents",
        json={"title": "Resolved issue", "severity": "SEV-3", "status": "resolved"},
    )

    response = await client.get("/api/v1/incidents?status=active")
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "active"


@pytest.mark.asyncio
async def test_filter_incidents_by_severity(client: AsyncClient):
    """Listing with severity filter returns only matching incidents."""
    await client.post(
        "/api/v1/incidents",
        json={"title": "SEV-1 issue", "severity": "SEV-1", "status": "active"},
    )
    await client.post(
        "/api/v1/incidents",
        json={"title": "SEV-3 issue", "severity": "SEV-3", "status": "active"},
    )

    response = await client.get("/api/v1/incidents?severity=SEV-1")
    data = response.json()
    assert len(data) == 1
    assert data[0]["severity"] == "SEV-1"


# --- Tag filter ---


@pytest.mark.asyncio
async def test_filter_incidents_by_single_tag(client: AsyncClient):
    """GET /api/v1/incidents?tags=deploy returns only matching incidents."""
    await client.post(
        "/api/v1/incidents",
        json={"title": "Deploy issue", "severity": "SEV-2", "status": "active", "tags": ["deploy"]},
    )
    await client.post(
        "/api/v1/incidents",
        json={
            "title": "DNS problem",
            "severity": "SEV-3",
            "status": "active",
            "tags": ["dependency", "dns"],
        },
    )
    await client.post(
        "/api/v1/incidents",
        json={"title": "No tag incident", "severity": "SEV-4", "status": "active"},
    )

    # Single tag
    resp = await client.get("/api/v1/incidents?tags=deploy")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Deploy issue"


@pytest.mark.asyncio
async def test_filter_incidents_by_multiple_tags_and(client: AsyncClient):
    """?tags=dependency,dns returns only incidents matching ALL tags."""
    await client.post(
        "/api/v1/incidents",
        json={"title": "Deploy fail", "severity": "SEV-2", "status": "active", "tags": ["deploy"]},
    )
    await client.post(
        "/api/v1/incidents",
        json={
            "title": "DNS timeout",
            "severity": "SEV-3",
            "status": "active",
            "tags": ["dependency", "dns"],
        },
    )

    resp = await client.get("/api/v1/incidents?tags=dependency,dns")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "DNS timeout"


@pytest.mark.asyncio
async def test_filter_incidents_by_tag_no_match(client: AsyncClient):
    """?tags=nonexistent returns empty list."""
    await client.post(
        "/api/v1/incidents",
        json={"title": "Any", "severity": "SEV-2", "tags": ["deploy"]},
    )
    resp = await client.get("/api/v1/incidents?tags=nonexistent")
    assert resp.json() == []


@pytest.mark.asyncio
async def test_filter_incidents_tag_combined_with_status(client: AsyncClient):
    """Tags filter combines with status filter."""
    await client.post(
        "/api/v1/incidents",
        json={
            "title": "Active deploy",
            "severity": "SEV-2",
            "status": "active",
            "tags": ["deploy"],
        },
    )
    await client.post(
        "/api/v1/incidents",
        json={
            "title": "Resolved deploy",
            "severity": "SEV-3",
            "status": "resolved",
            "tags": ["deploy"],
        },
    )

    resp = await client.get("/api/v1/incidents?tags=deploy&status=active")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Active deploy"
