"""Tests for the RCA API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_rca_empty(client: AsyncClient):
    """GET /api/v1/rca returns empty list initially."""
    response = await client.get("/api/v1/rca")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_rca_report(client: AsyncClient):
    """POST /api/v1/rca creates an RCA report for an incident."""
    # First create an incident
    inc_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Production outage", "severity": "SEV-1"},
    )
    incident_id = inc_resp.json()["id"]

    # Create RCA
    payload = {
        "incident_id": incident_id,
        "summary": "DNS misconfiguration caused routing failure",
        "root_cause": "Incorrect A record pointing to old LB",
        "recommendations": ["Audit DNS records weekly", "Add DNS change approval"],
    }
    response = await client.post("/api/v1/rca", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["summary"] == payload["summary"]
    assert data["root_cause"] == payload["root_cause"]
    assert data["recommendations"] == payload["recommendations"]
    assert "id" in data


@pytest.mark.asyncio
async def test_rca_duplicate_incident(client: AsyncClient):
    """Creating RCA for same incident twice returns 409."""
    inc_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Degraded perf", "severity": "SEV-3"},
    )
    incident_id = inc_resp.json()["id"]

    await client.post(
        "/api/v1/rca",
        json={"incident_id": incident_id, "summary": "First RCA"},
    )
    response = await client.post(
        "/api/v1/rca",
        json={"incident_id": incident_id, "summary": "Second RCA"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_rca_by_id(client: AsyncClient):
    """GET /api/v1/rca/:id returns the RCA report."""
    inc_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "Latency spike", "severity": "SEV-2"},
    )
    create_resp = await client.post(
        "/api/v1/rca",
        json={
            "incident_id": inc_resp.json()["id"],
            "root_cause": "DB connection pool exhausted",
        },
    )
    rca_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/rca/{rca_id}")
    assert response.status_code == 200
    assert response.json()["root_cause"] == "DB connection pool exhausted"
