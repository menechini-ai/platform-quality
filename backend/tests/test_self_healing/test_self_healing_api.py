"""Tests for self-healing API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_runbooks_empty(client: AsyncClient):
    """GET /api/v1/runbooks returns empty list initially."""
    response = await client.get("/api/v1/runbooks")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_runbook(client: AsyncClient):
    """POST /api/v1/runbooks creates a new runbook."""
    payload = {
        "name": "Restart API Gateway",
        "description": "Restart the API gateway service",
        "steps": [
            {"action": "command", "command": "kubectl rollout restart deployment/api-gateway"},
            {"action": "wait", "duration": 30},
            {"action": "check", "endpoint": "/health"},
        ],
        "is_active": True,
    }
    response = await client.post("/api/v1/runbooks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Restart API Gateway"
    assert len(data["steps"]) == 3
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_actions_empty(client: AsyncClient):
    """GET /api/v1/actions returns empty list initially."""
    response = await client.get("/api/v1/actions")
    assert response.status_code == 200
    assert response.json() == []
