"""Datadog metrics exploration — list metrics, discover tag keys/values."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.write_guard import sanitize_error_message

router = APIRouter()


@router.get("/datadog/metrics/list")
async def list_available_metrics(
    filter_tags: str = Query("*", description="Tag filter, e.g. 'env:prod', 'aws:*'"),
    limit: int = Query(50, le=200),
    cursor: str | None = None,
):
    """List Datadog metrics matching a tag filter.

    Uses v2 Metrics API with filter[tags] param.
    Example: /api/v1/datadog/metrics/list?filter_tags=env:prod,service:api
    """
    client = DatadogClient()
    try:
        r = client.metrics.list_metrics(
            filter_tags=filter_tags,
            page_size=limit,
            page_cursor=cursor or "",
        )
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/metrics/{metric_name}/fields")
async def get_metric_tag_fields(metric_name: str):
    """List available tag keys (field names) for a metric.

    Example: /api/v1/datadog/metrics/system.cpu.user/fields
    Returns unique tag keys like ['env', 'host', 'service', 'team']
    """
    client = DatadogClient()
    try:
        r = client.metrics.list_tags_by_metric_name(metric_name=metric_name)
        data = r.to_dict()
        tags = data.get("data", {}).get("tags", [])
        # tags format: ["env:prod", "service:api", "host:i-123"]
        fields = sorted(set(t.split(":", 1)[0] for t in tags if ":" in t))
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
    client = DatadogClient()
    try:
        r = client.metrics.list_tags_by_metric_name(metric_name=metric_name)
        data = r.to_dict()
        tags = data.get("data", {}).get("tags", [])
        prefix = f"{field_name}:"
        values = sorted(set(t[len(prefix):] for t in tags if t.startswith(prefix)))
        return {"metric": metric_name, "field": field_name, "values": values}
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
