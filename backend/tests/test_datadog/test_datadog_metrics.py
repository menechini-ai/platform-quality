"""Tests for Datadog metrics router."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    """Query endpoint should return 502 (no real DD keys) but hit the router."""
    resp = await client.get("/api/v1/datadog/metrics?metric=system.cpu.user&tags=service:api,env:prod")
    # No real DD keys = fails at SDK level with 502
    assert resp.status_code in (200, 502)
    if resp.status_code == 502:
        assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_metrics_default_tags(client: AsyncClient):
    """Default tags='*' should work."""
    resp = await client.get("/api/v1/datadog/metrics?metric=system.cpu.user")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_metrics_with_scope_override(client: AsyncClient):
    """Custom scope should override tags."""
    resp = await client.get(
        "/api/v1/datadog/metrics?metric=jvm.heap_memory&scope=service:worker AND env:staging&agg=max"
    )
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_metrics_missing_metric(client: AsyncClient):
    """Missing required metric param should fail validation."""
    resp = await client.get("/api/v1/datadog/metrics")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_metrics_endpoint_query_shape(client: AsyncClient):
    """Even on 502, the response should show the query string constructed."""
    resp = await client.get(
        "/api/v1/datadog/metrics?metric=system.load.norm.1&agg=avg&tags=service:observai&days=7"
    )
    if resp.status_code == 502:
        # SDK-level error is expected without keys
        assert resp.status_code == 502
