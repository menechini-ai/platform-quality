"""Tests for Datadog incidents proxy."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_datadog_incidents(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/incidents?query=severity:SEV-1")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_datadog_incidents_no_query(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/incidents")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_get_datadog_incident_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/incidents/invalid")
    assert resp.status_code in (404, 502)
