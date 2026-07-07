"""Datadog incidents router — proxy to Datadog Incidents API with tag filtering."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient

router = APIRouter()


@router.get("/datadog/incidents")
async def list_datadog_incidents(
    query: str | None = Query(None, description="Search query with tags, e.g. 'severity:SEV-1 env:prod'"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """List Datadog incidents with optional tag-based filtering.

    Tags follow Unified Service Tagging (UST):
      env:prod/staging/dev, service:<name>, team:<team>, severity:SEV-1..SEV-5

    Example:
      /api/v1/datadog/incidents?query=severity:SEV-1 env:prod&limit=25
    """
    client = DatadogClient()
    kwargs: dict = {"page_limit": limit, "page_offset": offset}
    if query:
        kwargs["query"] = query
    try:
        return client.list_incidents(**kwargs)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/datadog/incidents/{incident_id}")
async def get_datadog_incident(incident_id: str):
    """Get a single Datadog incident by ID."""
    client = DatadogClient()
    try:
        return client.get_incident(incident_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
