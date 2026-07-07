"""Tests for analysis agents."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_analysis_empty(client: AsyncClient):
    resp = await client.get("/api/v1/analysis")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_health_analysis(client: AsyncClient):
    resp = await client.post("/api/v1/analysis/health")
    assert resp.status_code == 201
    data = resp.json()
    assert data["domain"] == "health"
    assert data["action"] == "analyze"
    assert "score" in data
    assert "findings" in data


@pytest.mark.asyncio
async def test_self_healing_analysis(client: AsyncClient):
    resp = await client.post("/api/v1/analysis/self-healing")
    assert resp.status_code == 201
    data = resp.json()
    assert data["domain"] == "self_healing"
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_incident_analysis(client: AsyncClient):
    # Create an incident first
    inc = await client.post(
        "/api/v1/incidents",
        json={"title": "DB crash analysis test", "severity": "SEV-1", "service": "database"},
    )
    inc_id = inc.json()["id"]

    # Analyze
    resp = await client.post(f"/api/v1/analysis/incident/{inc_id}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["domain"] == "incident"
    assert "DB crash analysis test" in data["title"]
    assert "findings" in data


@pytest.mark.asyncio
async def test_rca_analysis(client: AsyncClient):
    # Create incident + RCA
    inc = await client.post(
        "/api/v1/incidents", json={"title": "Memory leak test", "severity": "SEV-2"}
    )
    inc_id = inc.json()["id"]

    await client.post(
        "/api/v1/rca",
        json={
            "incident_id": inc_id,
            "summary": "Memory usage grew over time",
            "root_cause": "GC tuning issue",
            "recommendations": ["Increase heap", "Add memory limits"],
        },
    )

    resp = await client.post(f"/api/v1/analysis/rca/{inc_id}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["domain"] == "rca"
    assert data["score"] >= 10
    assert "Memory leak test" in data["title"]


@pytest.mark.asyncio
async def test_analysis_filter_by_domain(client: AsyncClient):
    await client.post("/api/v1/analysis/health")
    await client.post("/api/v1/analysis/self-healing")

    resp = await client.get("/api/v1/analysis?domain=health")
    data = resp.json()
    assert all(e["domain"] == "health" for e in data)


@pytest.mark.asyncio
async def test_get_analysis_by_id(client: AsyncClient):
    create = await client.post("/api/v1/analysis/health")
    analysis_id = create.json()["id"]

    resp = await client.get(f"/api/v1/analysis/{analysis_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == analysis_id


@pytest.mark.asyncio
async def test_analysis_nonexistent_incident(client: AsyncClient):
    resp = await client.post(
        "/api/v1/analysis/incident/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404
