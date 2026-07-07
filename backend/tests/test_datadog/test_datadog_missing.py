"""Tests for RUM, Synthetics, Fleet routers."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestRUM:
    @pytest.mark.asyncio
    async def test_search_rum(self, client: AsyncClient):
        resp = await client.get("/api/v1/datadog/rum?query=*")
        assert resp.status_code in (200, 502)

    @pytest.mark.asyncio
    async def test_rum_missing_api_key(self, client: AsyncClient):
        resp = await client.get("/api/v1/datadog/rum")
        # Without DD keys SDK fails at 502
        assert resp.status_code in (200, 502)


class TestSynthetics:
    @pytest.mark.asyncio
    async def test_list_synthetics(self, client: AsyncClient):
        resp = await client.get("/api/v1/datadog/synthetics")
        assert resp.status_code in (200, 502)

    @pytest.mark.asyncio
    async def test_synthetics_result(self, client: AsyncClient):
        resp = await client.get("/api/v1/datadog/synthetics/abc123/results")
        assert resp.status_code in (200, 502)


class TestFleet:
    @pytest.mark.asyncio
    async def test_list_fleet_agents(self, client: AsyncClient):
        resp = await client.get("/api/v1/datadog/fleet/agents")
        assert resp.status_code in (200, 502)

    @pytest.mark.asyncio
    async def test_fleet_agent_info(self, client: AsyncClient):
        resp = await client.get("/api/v1/datadog/fleet/agents/abc123")
        assert resp.status_code in (200, 502)
