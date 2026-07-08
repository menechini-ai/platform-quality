"""Datadog monitors router — read + CRUD."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.formatters import fmt_monitors, maybe_human
from app.datadog.write_guard import assert_write_allowed, sanitize_error_message

router = APIRouter()


@router.get("/datadog/monitors")
async def list_monitors(
    group: str | None = None,
    name: str | None = None,
    tags: str | None = None,
    monitor_tags: str | None = None,
    page_size: int = 50,
    page: int = 0,
    human: bool = Query(False, alias="human"),
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
    r = client.monitors.list_monitors(**kwargs, page_size=page_size, page=page)
    data = [m.to_dict() for m in r]
    return maybe_human(data, fmt_monitors, human, meta={"total": len(data)})


@router.get("/datadog/monitors/search")
async def search_monitors(
    query: str | None = Query(default=None), page: int = 0, per_page: int = 10, human: bool = Query(False, alias="human")
):
    """Search monitors by name/tags."""
    client = DatadogClient()
    kwargs: dict[str, Any] = {}
    if query:
        kwargs["query"] = query
    r = client.monitors.search_monitors(**kwargs, page=page, per_page=per_page)
    data = r.to_dict()
    return maybe_human(data, fmt_monitors, human)


@router.get("/datadog/monitors/{monitor_id}")
async def get_monitor(monitor_id: int):
    """Get a single monitor by ID."""
    client = DatadogClient()
    try:
        r = client.monitors.get_monitor(monitor_id=monitor_id)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/monitors/groups/{monitor_id}")
async def search_monitor_groups(monitor_id: int):
    """Get groups for a specific monitor."""
    client = DatadogClient()
    try:
        r = client.monitors.search_monitor_groups(monitor_id=monitor_id)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=sanitize_error_message(str(e))) from e


@router.post("/datadog/monitors", status_code=201)
async def create_monitor(
    name: str,
    type: str,
    query: str,
    message: str = "",
    tags: list[str] | None = None,
    priority: int | None = None,  # noqa: ARG001
):
    """Create a new Datadog monitor."""
    assert_write_allowed()
    client = DatadogClient()
    from datadog_api_client.v1.model.monitor import Monitor

    body = Monitor(name=name, type=type, query=query, message=message, tags=tags or [])
    try:
        r = client.monitors.create_monitor(body=body)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e))) from e


@router.put("/datadog/monitors/{monitor_id}")
async def update_monitor(
    monitor_id: int,
    name: str | None = None,
    query: str | None = None,
    message: str | None = None,
    tags: list[str] | None = None,
    priority: int | None = None,
):
    """Update a monitor."""
    assert_write_allowed()
    client = DatadogClient()
    from datadog_api_client.v1.model.monitor_update_request import MonitorUpdateRequest

    body = MonitorUpdateRequest(
        name=name, query=query, message=message, tags=tags, priority=priority
    )
    try:
        r = client.monitors.update_monitor(monitor_id=monitor_id, body=body)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e))) from e


@router.delete("/datadog/monitors/{monitor_id}")
async def delete_monitor(monitor_id: int, force: bool = False):
    """Delete a monitor."""
    assert_write_allowed()
    client = DatadogClient()
    try:
        client.monitors.delete_monitor(monitor_id=monitor_id, force=force)
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e))) from e
