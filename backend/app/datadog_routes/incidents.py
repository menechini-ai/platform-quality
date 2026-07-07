"""Datadog incidents router — read + CRUD."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.formatters import fmt_incidents, maybe_human
from app.datadog.write_guard import assert_write_allowed, sanitize_error_message

router = APIRouter()


@router.get("/datadog/incidents")
async def list_datadog_incidents(
    query: str | None = Query(None, description="Search query with tags"),
    page_size: int = Query(10, le=200),
    page_number: int = Query(0, ge=0),
    human: bool = Query(False, alias="human"),
):
    """List Datadog incidents with optional tag-based filtering."""
    client = DatadogClient()
    try:
        data = client.list_incidents(page_size=page_size, page_number=page_number)
        return maybe_human(data, fmt_incidents, human, meta={"total": len(data)})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/incidents/search")
async def search_datadog_incidents(
    query: str = Query(..., description="Incident search query"),
    human: bool = Query(False, alias="human"),
):
    """Search Datadog incidents by query string."""
    client = DatadogClient()
    try:
        data = client.search_incidents(query)
        return maybe_human(data, fmt_incidents, human, meta={"total": len(data)})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/incidents/{incident_id}")
async def get_datadog_incident(incident_id: str):
    """Get a single Datadog incident by ID."""
    client = DatadogClient()
    try:
        return client.get_incident(incident_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=sanitize_error_message(str(e))) from e


@router.post("/datadog/incidents", status_code=201)
async def create_datadog_incident(
    title: str,
    customer_impact: dict[str, Any] | None = None,
):
    """Create a Datadog incident."""
    assert_write_allowed()
    client = DatadogClient()
    attrs: dict[str, Any] = {"title": title}
    if customer_impact:
        attrs["customer_impact"] = customer_impact
    body = {"data": {"attributes": attrs}}
    try:
        r = client.incidents.create_incident(body=body)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e))) from e


@router.put("/datadog/incidents/{incident_id}")
async def update_datadog_incident(incident_id: str, title: str):
    """Update a Datadog incident."""
    assert_write_allowed()
    client = DatadogClient()
    body = {"data": {"attributes": {"title": title}}}
    try:
        r = client.incidents.update_incident(incident_id=incident_id, body=body)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e))) from e


@router.delete("/datadog/incidents/{incident_id}")
async def delete_datadog_incident(incident_id: str):
    """Delete a Datadog incident."""
    assert_write_allowed()
    client = DatadogClient()
    try:
        client.incidents.delete_incident(incident_id=incident_id)
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e))) from e
