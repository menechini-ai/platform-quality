"""Datadog events router."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.filters import compose_filters, to_domain_kwargs
from app.datadog.formatters import fmt_events, maybe_human
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import (
    assert_write_allowed,
    friendly_datadog_error,
    get_datadog_url,
    get_headers,
    sanitize_error_message,
)

router = APIRouter()


@router.get("/datadog/events")
async def list_events(
    start: int | None = None,
    end: int | None = None,
    priority: str | None = None,
    sources: str | None = None,
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    human: bool = Query(False, alias="human"),
):
    """List Datadog events with optional filters."""
    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("events", composed)

    now = int(datetime.now(UTC).timestamp())
    params: dict[str, Any] = {
        "start": fkw.get("start", start or now - 86400),
        "end": fkw.get("end", end or now),
    }
    if priority:
        params["priority"] = priority
    if sources:
        params["sources"] = sources
    if "tags" in fkw:
        params["tags"] = fkw["tags"]

    url = f"{get_datadog_url()}/api/v1/events"
    try:
        resp = httpx.get(url, headers=get_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e

    return maybe_human(data, fmt_events, human)


@router.get("/datadog/events/{event_id}")
async def get_event(event_id: int):
    """Get a single event by ID."""
    client = DatadogClient()
    try:
        r = client.events.get_event(event_id=event_id)
        return r.to_dict()
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e


@router.post("/datadog/events")
async def create_event(
    title: str,
    text: str,
    tags: list[str] | None = None,
    alert_type: str = "info",
    priority: str = "normal",
):
    """Post an event to Datadog."""
    assert_write_allowed()
    client = DatadogClient()
    r = client.create_event(
        title=title,
        text=text,
        tags=tags or [],
        alert_type=alert_type,
        priority=priority,
    )
    return r


@router.put("/datadog/events/{event_id}")
async def update_event(event_id: int, title: str | None = None, text: str | None = None):
    """Update an existing event."""
    assert_write_allowed()
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if text is not None:
        body["text"] = text
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v1/events/{event_id}"
            resp = await hc.put(url, headers=get_headers(), json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=404, detail=sanitize_error_message(str(e))) from e


@router.delete("/datadog/events/{event_id}")
async def delete_event(event_id: int):
    """Delete an event."""
    assert_write_allowed()
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v1/events/{event_id}"
            resp = await hc.delete(url, headers=get_headers())
            resp.raise_for_status()
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=sanitize_error_message(str(e))) from e
