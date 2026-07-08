"""Tests for health / SLO API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_slos_empty(client: AsyncClient):
    """GET /api/v1/slos returns empty list initially."""
    response = await client.get("/api/v1/slos")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_slo(client: AsyncClient):
    """POST /api/v1/slos creates a new SLO."""
    payload = {
        "name": "API Latency P99",
        "target": 0.995,
        "time_window": "30d",
        "service": "api-gateway",
    }
    response = await client.post("/api/v1/slos", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Latency P99"
    assert data["target"] == 0.995
    assert data["service"] == "api-gateway"


@pytest.mark.asyncio
async def test_health_summary_empty(client: AsyncClient):
    """GET /api/v1/health/summary returns empty when no data."""
    response = await client.get("/api/v1/health/summary")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_health_snapshots(client: AsyncClient):
    """GET /api/v1/health returns snapshots if any exist."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
