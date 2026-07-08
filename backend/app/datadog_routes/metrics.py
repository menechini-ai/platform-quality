"""Datadog metrics router — query timeseries with tag filters."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.formatters import fmt_metrics, maybe_human
from app.datadog.write_guard import sanitize_error_message

router = APIRouter()


@router.get("/datadog/metrics")
async def query_metrics(
    metric: str = Query(..., description="Metric name, e.g. 'system.cpu.user'"),
    agg: str = Query("avg", description="Aggregation: avg, sum, max, min, count"),
    tags: str = Query("*", description="Tag filter, e.g. 'service:api,env:prod'"),
    scope: str | None = Query(
        None, description="Full scope override, e.g. 'service:api AND env:prod'"
    ),
    from_ts: int | None = None,
    to_ts: int | None = None,
    days: int = Query(1, ge=1, le=30),
    human: bool = Query(False, alias="human"),
):
    """Query Datadog metrics timeseries with tag filtering.

    Tags follow Unified Service Tagging (UST) standard:
      env:prod/staging/dev, service:<name>, team:<team>

    Examples:
      /api/v1/datadog/metrics?metric=system.cpu.user&tags=service:api,env:prod
      /api/v1/datadog/metrics?metric=trace.servlet.request.hits&agg=sum&tags=*&days=7
      /api/v1/datadog/metrics?metric=jvm.heap_memory&tags=service:worker,env:staging
    """
    from datetime import UTC, datetime

    now = int(datetime.now(UTC).timestamp())
    from_val = from_ts or (now - 3600 * 24 * days)
    to_val = to_ts or now

    # Build scope: if tags != "*", convert to Datadog scope syntax
    if scope:
        scope_query = scope
    elif tags != "*":
        tag_pairs = [t.strip() for t in tags.split(",") if t.strip()]
        scope_query = ",".join(tag_pairs)
    else:
        scope_query = "*"

    dd_query = f"{agg}:{metric}{{{scope_query}}}"

    client = DatadogClient()
    try:
        r = client.query_metrics(query=dd_query, from_ts=from_val, to_ts=to_val)
        return maybe_human(r, fmt_metrics, human, meta={"query": dd_query})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/metrics/metadata")
async def get_metric_metadata(
    metric_name: str = Query(..., description="Full metric name, e.g. 'system.cpu.user'"),
):
    """Get metadata about a metric (unit, type, description)."""
    client = DatadogClient()
    try:
        r = client.metrics.get_metric_metadata(metric_name=metric_name)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
