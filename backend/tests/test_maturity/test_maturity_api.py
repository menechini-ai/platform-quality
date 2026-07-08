"""Tests for maturity assessment API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_assessments_empty(client: AsyncClient):
    resp = await client.get("/api/v1/maturity")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_latest_assessment_empty(client: AsyncClient):
    resp = await client.get("/api/v1/maturity/latest")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_run_assessment(client: AsyncClient):
    resp = await client.post("/api/v1/maturity/assess")
    assert resp.status_code == 201
    data = resp.json()
    # Level depends on whether Datadog is configured; assert a valid range.
    assert data["overall_level"] in range(6)
    assert data["overall_score"] >= 0.0
    assert "dimensions" in data
    assert data["summary"] is not None


@pytest.mark.asyncio
async def test_gap_analysis(client: AsyncClient):
    resp = await client.get("/api/v1/maturity/gap?current=0&target=2")
    assert resp.status_code == 200
    gaps = resp.json()
    assert len(gaps) == 2
    assert gaps[0]["target_level"] == 1
    assert gaps[1]["target_level"] == 2


@pytest.mark.asyncio
async def test_gap_analysis_at_level(client: AsyncClient):
    resp = await client.get("/api/v1/maturity/gap?current=3&target=3")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_levels_endpoint(client: AsyncClient):
    resp = await client.get("/api/v1/maturity/levels")
    assert resp.status_code == 200
    data = resp.json()
    assert "levels" in data
    assert "dimensions" in data
    assert len(data["levels"]) == 6  # 0-5
