"""Error Tracking router — queries Datadog logs + spans for error events."""

from __future__ import annotations


from fastapi import APIRouter, Query

from app.datadog.client import DatadogClient

router = APIRouter()


@router.get("/datadog/errors")
async def list_errors(
    query: str = "status:error OR status:critical",
    service: str | None = None,
    env: str | None = None,
    limit: int = Query(default=50, le=200),
    from_ts: int | None = None,
    to_ts: int | None = None,
):
    """Search error events across logs + APM.

    Combines log errors and APM error spans in a single view.
    Uses `@error.*` facets for structured error data.
    """
    client = DatadogClient()

    filters = [query]
    if service:
        filters.append(f"service:{service}")
    if env:
        filters.append(f"env:{env}")

    combined_query = " ".join(filters)

    logs_result = {}
    spans_result = {}

    # Query logs for errors
    try:
        logs_result = client.search_logs(
            combined_query,
            limit=limit,
            sort="-timestamp",
            filter_from=from_ts,
            filter_to=to_ts,
        )
    except Exception as e:
        logs_result = {"error": str(e), "data": []}

    # Query APM error spans
    try:
        spans_result = client.list_spans(
            combined_query,
            limit=limit,
            sort="-timestamp",
            filter_from=from_ts,
            filter_to=to_ts,
        )
    except Exception as e:
        spans_result = {"error": str(e), "data": []}

    return {
        "query": combined_query,
        "logs": logs_result.get("data", []),
        "spans": spans_result.get("data", []),
        "total_logs": len(logs_result.get("data", [])),
        "total_spans": len(spans_result.get("data", [])),
    }


@router.get("/datadog/errors/summary")
async def error_summary(
    query: str = "status:error",
    from_ts: int | None = None,
    to_ts: int | None = None,
):
    """Aggregated error summary by service and type."""
    client = DatadogClient()

    # Aggregate logs
    log_aggregation = {}
    try:
        log_aggregation = client.aggregate_logs(
            filter_query=query,
            compute={"aggregation": "count"},
            group_by=[{"facet": "service"}, {"facet": "@error.kind"}],
            filter_from=from_ts,
            filter_to=to_ts,
        )
    except Exception as e:
        log_aggregation = {"error": str(e)}

    # Aggregate APM error spans
    span_aggregation = {}
    try:
        span_aggregation = client.aggregate_spans(
            filter_query=query,
            compute={"aggregation": "count"},
            group_by=[{"facet": "service"}, {"facet": "resource"}],
            filter_from=from_ts,
            filter_to=to_ts,
        )
    except Exception as e:
        span_aggregation = {"error": str(e)}

    return {
        "logs": log_aggregation,
        "spans": span_aggregation,
    }
