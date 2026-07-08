"""Tests for APM dependencies and service definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_service_definition(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/apm/services/api-gateway/definition")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_get_service_dependencies(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/apm/services/api-gateway/dependencies")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_list_all_dependencies(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/apm/dependencies")
    assert resp.status_code in (200, 502)
