"""Datadog metrics exploration — list metrics, discover tag keys/values."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.filters import compose_filters, to_domain_kwargs
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import get_datadog_url, get_headers, sanitize_error_message

router = APIRouter()


@router.get("/datadog/metrics/list")
async def list_available_metrics(
    filter_tags: str = Query("*", description="Tag filter, e.g. 'env:prod', 'aws:*'"),
    tags: list[str] | None = Query(
        default=None, description="UST tags, AND-combined with global default"
    ),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
):
    """List Datadog metrics matching a tag filter.

    `tags` is AND-combined with the global default from settings into the comma-separated
    tag filter passed to the Metrics API.
    """
    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("metrics_explore", composed)
    effective_tags = fkw.get("filter_tags", filter_tags)
    client = DatadogClient()
    try:
        r = client.metrics.list_metrics(q=effective_tags)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/metrics/{metric_name}/fields")
async def get_metric_tag_fields(metric_name: str):
    """List available tag keys (field names) for a metric.

    Example: /api/v1/datadog/metrics/system.cpu.user/fields
    Returns unique tag keys like ['env', 'host', 'service', 'team']
    """
    try:
        import httpx

        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v1/metrics/{metric_name}/tags"
            resp = await hc.get(url, headers=get_headers())
            resp.raise_for_status()
            data = resp.json()
        tags = data.get("tags", [])
        # tags format: ["env:prod", "service:api", "host:i-123"]
        fields = sorted({t.split(":", 1)[0] for t in tags if ":" in t})
        return {"metric": metric_name, "fields": fields, "tag_count": len(tags)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/metrics/{metric_name}/values")
async def get_metric_tag_values(
    metric_name: str,
    field_name: str = Query(..., description="Tag key, e.g. 'service', 'env'"),
):
    """List all unique values for a specific tag key on a metric.

    Example: /api/v1/datadog/metrics/system.cpu.user/values?field_name=env
    Returns values like ['prod', 'staging', 'dev']
    """
    try:
        import httpx

        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v1/metrics/{metric_name}/tags"
            resp = await hc.get(url, headers=get_headers())
            resp.raise_for_status()
            data = resp.json()
        tags = data.get("tags", [])
        prefix = f"{field_name}:"
        values = sorted({t[len(prefix) :] for t in tags if t.startswith(prefix)})
        return {"metric": metric_name, "field": field_name, "values": values}
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
