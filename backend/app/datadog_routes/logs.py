"""Datadog logs router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.filters import compose_filters, to_domain_kwargs
from app.datadog.formatters import fmt_logs, maybe_human
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import sanitize_error_message

router = APIRouter()


@router.get("/datadog/logs")
async def list_logs(
    query: str | None = Query(default=None),
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    limit: int = Query(default=50, le=200),
    sort: str = "-timestamp",
    from_ts: int | None = None,
    to_ts: int | None = None,
    human: bool = Query(False, alias="human"),
):
    """Search Datadog logs filtered by tags and time window."""
    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("logs", composed)
    combined = " ".join(p for p in [query, fkw.get("query")] if p) or ""
    client = DatadogClient()
    try:
        r = client.search_logs(
            combined,
            limit=limit,
            sort=sort,
            filter_from=fkw.get("from", from_ts),
            filter_to=fkw.get("to", to_ts),
        )
        return maybe_human(r, fmt_logs, human, meta={"query": combined or None})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


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
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.post("/datadog/logs/aggregate")
async def aggregate_logs(
    query: str | None = Query(default=None),
    group_by_facets: list[str] = Query(default=["service"]),
    from_ts: int | None = None,
    to_ts: int | None = None,
    human: bool = Query(False, alias="human"),
):
    """Aggregate logs count by facets."""
    client = DatadogClient()
    try:
        r = client.aggregate_logs(
            filter_query=query or "",
            compute={"aggregation": "count"},
            group_by=[{"facet": f} for f in group_by_facets],
            filter_from=from_ts,
            filter_to=to_ts,
        )
        return maybe_human(r, fmt_logs, human, meta={"query": query})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
