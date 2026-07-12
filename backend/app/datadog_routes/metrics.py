"""Datadog metrics router — query timeseries with tag filters."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

from app.datadog.client import DatadogClient
from app.datadog.filters import compose_filters, period_to_range
from app.datadog.formatters import fmt_metrics
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import sanitize_error_message

router = APIRouter()


def _shape_metrics(raw: dict[str, Any], query: str) -> dict[str, Any]:
    """Reshape a Datadog v1 metrics response into the shape the frontend expects.

    Datadog returns ``series[].pointlist`` as ``[[ts, value], ...]`` at the top
    level; the frontend expects ``resp.series[].points`` as ``[{timestamp, value}]``.
    """
    series: list[dict[str, Any]] = []
    for s in raw.get("series", []):
        points = [
            {"timestamp": int(p[0]), "value": p[1]}
            for p in s.get("pointlist", [])
            if p and len(p) == 2
        ]
        series.append(
            {
                "metric": s.get("metric") or s.get("expression") or s.get("display_name"),
                "points": points,
                "tag_set": s.get("tag_set") or s.get("scope"),
            }
        )
    return {
        "status": "ok",
        "resp": {
            "series": series,
            "from_date": raw.get("from_date"),
            "to_date": raw.get("to_date"),
            "query": query,
        },
    }


@router.get("/datadog/metrics")
async def query_metrics(
    metric: str = Query(..., description="Metric name, e.g. 'system.cpu.user'"),
    agg: str = Query("avg", description="Aggregation: avg, sum, max, min, count"),
    tags: str = Query("*", description="Tag scope filter, e.g. 'service:api,env:prod'"),
    scope: str | None = Query(
        None, description="Full scope override, e.g. 'service:api AND env:prod'"
    ),
    filter_tags: list[str] | None = Query(
        default=None, description="UST tags, AND-combined with global default"
    ),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    from_ts: int | None = None,
    to_ts: int | None = None,
    days: int = Query(1, ge=1, le=30),
    human: bool = Query(False, alias="human"),
):
    """Query Datadog metrics timeseries with tag filtering.

    Tags follow Unified Service Tagging (UST) standard:
      env:prod/staging/dev, service:<name>, team:<team>

    `filter_tags` (and the global default from settings) are AND-combined into the
    query scope; `period` sets the time window.
    """
    from datetime import UTC, datetime

    composed = compose_filters(DatadogFilter(tags=filter_tags, period=period))
    rng = period_to_range(composed.period)

    now = int(datetime.now(UTC).timestamp())
    from_val = from_ts or (rng[0] if rng else now - 3600 * 24 * days)
    to_val = to_ts or (rng[1] if rng else now)

    # Build scope: explicit scope wins; else combined UST tags (global + request);
    # else the existing string `tags` scope; else all.
    if scope:
        scope_query = scope
    elif composed.tags:
        scope_query = ",".join(composed.tags)
    elif tags != "*":
        tag_pairs = [t.strip() for t in tags.split(",") if t.strip()]
        scope_query = ",".join(tag_pairs)
    else:
        scope_query = "*"

    dd_query = f"{agg}:{metric}{{{scope_query}}}"

    client = DatadogClient()
    try:
        r = await client.query_metrics(query=dd_query, from_ts=from_val, to_ts=to_val)
        payload = _shape_metrics(r.to_dict(), dd_query)
        if human:
            return Response(
                content=fmt_metrics(payload["resp"]["series"], {"query": dd_query}),
                media_type="text/plain",
            )
        return payload
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
