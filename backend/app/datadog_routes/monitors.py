"""Datadog monitors router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.datadog.client import DatadogClient

router = APIRouter()


@router.get("/datadog/monitors")
async def list_monitors(
    group: str | None = None,
    name: str | None = None,
    tags: str | None = None,
    monitor_tags: str | None = None,
):
    """List Datadog monitors with optional filters."""
    kwargs: dict[str, Any] = {}
    if group:
        kwargs["group"] = group
    if name:
        kwargs["name"] = name
    if tags:
        kwargs["tags"] = tags
    if monitor_tags:
        kwargs["monitor_tags"] = monitor_tags

    client = DatadogClient()
    return client.list_monitors(**kwargs)


@router.get("/datadog/monitors/{monitor_id}")
async def get_monitor(monitor_id: int):
    """Get a single monitor by ID."""
    client = DatadogClient()
    r = client.monitors.get_monitor(monitor_id=monitor_id)
    return r.to_dict()


@router.get("/datadog/monitors/search")
async def search_monitors(query: str = "*", page: int = 0, per_page: int = 10):
    """Search monitors by name/tags."""
    client = DatadogClient()
    r = client.monitors.search_monitors(query=query, page=page, per_page=per_page)
    return r.to_dict()


@router.get("/datadog/monitors/groups/{monitor_id}")
async def search_monitor_groups(monitor_id: int):
    """Get groups for a specific monitor."""
    client = DatadogClient()
    r = client.monitors.search_monitor_groups(monitor_id=monitor_id)
    return r.to_dict()
