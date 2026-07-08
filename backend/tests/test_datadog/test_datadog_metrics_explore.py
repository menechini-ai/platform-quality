"""Tests for Datadog metrics exploration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_available_metrics(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/metrics/list?filter_tags=*")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_metric_tag_fields(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/metrics/system.cpu.user/fields")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_metric_tag_values(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/metrics/system.cpu.user/values?field_name=env")
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_metric_tag_values_missing_field(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/metrics/system.cpu.user/values")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_metric_tag_fields_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/datadog/metrics/nonexistent.metric/fields")
    assert resp.status_code in (200, 502)
