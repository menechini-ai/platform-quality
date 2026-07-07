"""Tests for Datadog SLOs proxy."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_datadog_slos(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/slos?tags=env:prod,service:api")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_datadog_slos_no_tags(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/slos")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_get_datadog_slo_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/slos/nonexistent")
    assert resp.status_code in (404, 502)


@pytest.mark.asyncio
async def test_slo_history(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/slos/nonexistent/history")
    assert resp.status_code in (404, 502, 422)


@pytest.mark.asyncio
async def test_slo_corrections(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/slos/corrections")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_slo_corrections_filtered(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/slos/corrections?slo_id=abc")
    assert resp.status_code in (200, 502)
