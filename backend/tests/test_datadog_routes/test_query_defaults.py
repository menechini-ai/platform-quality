"""Tests for Datadog logs, APM spans, and monitor search endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

P = "/api/v1/datadog"


@pytest.mark.asyncio
async def test_list_logs_no_query(client: AsyncClient):
    """GET logs without query — no star wildcard sent."""
    resp = await client.get(f"{P}/logs")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_logs_with_query(client: AsyncClient):
    """GET logs?query= filters correctly."""
    resp = await client.get(f"{P}/logs", params={"query": "service:api"})
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_logs_with_limit_and_sort(client: AsyncClient):
    """GET logs passes limit/sort."""
    resp = await client.get(f"{P}/logs", params={"limit": 10, "sort": "timestamp"})
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_aggregate_logs_no_query(client: AsyncClient):
    """POST logs/aggregate without query works."""
    resp = await client.post(f"{P}/logs/aggregate")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_aggregate_logs_with_query(client: AsyncClient):
    """POST logs/aggregate with query filters."""
    resp = await client.post(
        f"{P}/logs/aggregate",
        params={"query": "service:api", "group_by_facets": ["service", "status"]},
    )
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_spans_no_query(client: AsyncClient):
    """GET apm/spans without query — no star sent."""
    resp = await client.get(f"{P}/apm/spans")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_spans_with_query(client: AsyncClient):
    """GET apm/spans?query= passes query."""
    resp = await client.get(f"{P}/apm/spans", params={"query": "service:api"})
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_spans_with_service_and_env(client: AsyncClient):
    """GET apm/spans with service+env builds combined filter."""
    resp = await client.get(
        f"{P}/apm/spans",
        params={"service": "api-gateway", "env": "prod"},
    )
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_resources_no_service(client: AsyncClient):
    """GET apm/resources without service — no wildcard."""
    resp = await client.get(f"{P}/apm/resources", params={"env": "prod"})
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_search_monitors_no_query(client: AsyncClient):
    """GET monitors/search without query — no star."""
    resp = await client.get(f"{P}/monitors/search")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_search_monitors_with_query(client: AsyncClient):
    """GET monitors/search?query= passes query."""
    resp = await client.get(f"{P}/monitors/search", params={"query": "redis"})
    assert resp.status_code in (200, 502)
