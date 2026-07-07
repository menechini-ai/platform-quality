"""Datadog logs router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient

router = APIRouter()


@router.get("/datadog/logs")
async def list_logs(
    query: str = "*",
    limit: int = Query(default=50, le=200),
    sort: str = "-timestamp",
    from_ts: int | None = None,
    to_ts: int | None = None,
):
    """Search Datadog logs."""
    client = DatadogClient()
    try:
        r = client.search_logs(
            query,
            limit=limit,
            sort=sort,
            filter_from=from_ts,
            filter_to=to_ts,
        )
        return r
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/datadog/logs")
async def submit_log(
    ddsource: str = "observai",
    ddtags: str = "env:dev,service:observai",
    hostname: str = "observai",
    message: str = "",
    service: str = "observai",
):
    """Submit a log entry to Datadog."""
    client = DatadogClient()
    from datadog_api_client.v2.model.http_log import HTTPLog
    from datadog_api_client.v2.model.http_log_item import HTTPLogItem

    item = HTTPLogItem(
        ddsource=ddsource,
        ddtags=ddtags,
        hostname=hostname,
        message=message,
        service=service,
    )
    body = HTTPLog([item])
    try:
        r = client.logs.submit_log(body=body)
        return {"status": "ok", "response": r.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/datadog/logs/aggregate")
async def aggregate_logs(
    query: str = "*",
    group_by_facets: list[str] = Query(default=["service"]),
    from_ts: int | None = None,
    to_ts: int | None = None,
):
    """Aggregate logs count by facets."""
    client = DatadogClient()
    try:
        r = client.aggregate_logs(
            filter_query=query,
            compute={"aggregation": "count"},
            group_by=[{"facet": f} for f in group_by_facets],
            filter_from=from_ts,
            filter_to=to_ts,
        )
        return r
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
