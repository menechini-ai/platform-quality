"""Datadog events router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.datadog.client import DatadogClient
from app.datadog.write_guard import assert_write_allowed

router = APIRouter()


@router.get("/datadog/events")
async def list_events(
    start: int | None = None,
    end: int | None = None,
    priority: str | None = None,
    sources: str | None = None,
    tags: str | None = None,
):
    """List Datadog events with optional filters."""
    kwargs: dict[str, object] = {}
    if start:
        kwargs["start"] = start
    if end:
        kwargs["end"] = end
    if priority:
        kwargs["priority"] = priority
    if sources:
        kwargs["sources"] = sources.replace(",", ",")
    if tags:
        kwargs["tags"] = tags

    client = DatadogClient()
    r = client.events.list_events(**kwargs)
    return r.to_dict()


@router.get("/datadog/events/{event_id}")
async def get_event(event_id: int):
    """Get a single event by ID."""
    client = DatadogClient()
    try:
        r = client.events.get_event(event_id=event_id)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


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
    client = DatadogClient()
    body = {}
    if title is not None:
        body["title"] = title
    if text is not None:
        body["text"] = text
    try:
        r = client.events.update_event(event_id=event_id, body=body)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/datadog/events/{event_id}")
async def delete_event(event_id: int):
    """Delete an event."""
    assert_write_allowed()
    client = DatadogClient()
    try:
        client.events.delete_event(event_id=event_id)
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
