"""Error Tracking router — direct Datadog Error Tracking API (v2)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.write_guard import get_datadog_url, get_headers, sanitize_error_message

router = APIRouter()


@router.get("/datadog/error-tracking/trackers")
async def list_error_trackers(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """List error trackers from Datadog Error Tracking API."""
    import httpx

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/error_trackers"
            resp = await hc.get(
                url, headers=get_headers(), params={"limit": limit, "offset": offset}
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/error-tracking/trackers/{tracker_id}")
async def get_error_tracker(tracker_id: str):
    """Get a single error tracker by ID."""
    import httpx

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/error_trackers/{tracker_id}"
            resp = await hc.get(url, headers=get_headers())
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.post("/datadog/error-tracking/events")
async def search_error_events(
    query: str = Query("*", description="Error event query (e.g. service:api)"),
    limit: int = Query(50, le=200),
    from_ts: int | None = None,
    to_ts: int | None = None,
    time_range: str = "1h",
):
    """Search error events from Datadog Error Tracking API."""
    from datetime import UTC, datetime

    import httpx

    from app.datadog.utils import parse_time

    now = int(datetime.now(UTC).timestamp())
    from_val = from_ts or parse_time(time_range)
    to_val = to_ts or now

    body = {
        "filter": {"query": query, "from": from_val, "to": to_val},
        "page": {"limit": limit},
        "sort": "-@timestamp",
    }

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/error_events"
            resp = await hc.post(url, headers=get_headers(), json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
