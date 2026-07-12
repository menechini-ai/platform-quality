"""Error Tracking router — direct Datadog Error Tracking API (v2)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.datadog.filters import compose_filters, period_to_range, to_domain_kwargs
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import get_datadog_url, get_headers, sanitize_error_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/datadog/error-tracking/trackers")
async def list_error_trackers(
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """List error trackers from Datadog Error Tracking API."""
    import httpx

    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("error_tracking", composed)
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/error_trackers"
            params: dict = {"limit": limit, "offset": offset}
            if "filter[tags]" in fkw:
                params["filter[tags]"] = fkw["filter[tags]"]
            resp = await hc.get(url, headers=get_headers(), params=params)
            if resp.status_code == 404:
                logger.warning(
                    "Datadog Error Tracking endpoint returned 404 (feature unavailable on %s)",
                    get_datadog_url(),
                )
                return []
            resp.raise_for_status()
            return resp.json().get("data", [])
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
            if resp.status_code == 404:
                logger.warning(
                    "Datadog Error Tracking endpoint returned 404 (feature unavailable on %s)",
                    get_datadog_url(),
                )
                raise HTTPException(
                    status_code=404,
                    detail="Error Tracking is not available on this Datadog site/account",
                )
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.post("/datadog/error-tracking/events")
async def search_error_events(
    query: str = Query(default=None, description="Error event query (e.g. service:api)"),
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    limit: int = Query(50, le=200),
    from_ts: int | None = None,
    to_ts: int | None = None,
    time_range: str = "1h",
):
    """Search error events from Datadog Error Tracking API."""
    from datetime import UTC, datetime

    import httpx

    from app.datadog.utils import parse_time

    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    rng = period_to_range(composed.period)

    now = int(datetime.now(UTC).timestamp())
    from_val = from_ts or (rng[0] if rng else parse_time(time_range))
    to_val = to_ts or (rng[1] if rng else now)

    fil: dict[str, Any] = {"from": from_val, "to": to_val}
    tag_parts = [f"tags:{t}" for t in composed.tags] if composed.tags else []
    qparts = [p for p in [query, *tag_parts] if p]
    if qparts:
        fil["query"] = " ".join(qparts)
    body = {
        "filter": fil,
        "page": {"limit": limit},
        "sort": "-@timestamp",
    }

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/error_events"
            resp = await hc.post(url, headers=get_headers(), json=body)
            if resp.status_code == 404:
                logger.warning(
                    "Datadog Error Tracking endpoint returned 404 (unavailable on %s)",
                    get_datadog_url(),
                )
                return {"data": []}
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
