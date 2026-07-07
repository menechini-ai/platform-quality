"""Datadog events router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.datadog.client import DatadogClient

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
    client = DatadogClient()
    r = client.create_event(
        title=title,
        text=text,
        tags=tags or [],
        alert_type=alert_type,
        priority=priority,
    )
    return r
