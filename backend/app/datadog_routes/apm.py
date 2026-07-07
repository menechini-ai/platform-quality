"""APM / Distributed Tracing router — queries Datadog spans."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient

router = APIRouter()


@router.get("/datadog/apm/services")
async def list_services(env: str = "prod"):
    """List APM services.
    
    Note: Datadog's Spans API doesn't have a direct 'list services' endpoint.
    This wraps span aggregation by service for recent data.
    """
    client = DatadogClient()
    from datetime import datetime
    now = int(datetime.now(UTC).timestamp())

    try:
        r = client.aggregate_spans(
            filter_query=f"env:{env}",
            compute={"aggregation": "count"},
            group_by=[{"facet": "service"}, {"facet": "resource"}],
            filter_from=now - 3600 * 24 * 7,  # 7 days
            filter_to=now,
        )
        return r
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/datadog/apm/spans")
async def list_spans(
    query: str = "*",
    service: str | None = None,
    env: str | None = None,
    limit: int = Query(default=50, le=200),
    from_ts: int | None = None,
    to_ts: int | None = None,
):
    """Search APM traces/spans."""
    client = DatadogClient()
    filters = [query]
    if service:
        filters.append(f"service:{service}")
    if env:
        filters.append(f"env:{env}")
    combined = " ".join(filters)

    try:
        r = client.list_spans(
            combined,
            limit=limit,
            sort="-timestamp",
            filter_from=from_ts,
            filter_to=to_ts,
        )
        return r
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/datadog/apm/resources")
async def list_resources(
    service: str | None = None,
    env: str = "prod",
    limit: int = Query(default=50, le=200),
):
    """List APM resources grouped by service.
    
    Returns top resources by span count for each service.
    """
    client = DatadogClient()
    from datetime import datetime
    now = int(datetime.now(UTC).timestamp())

    service_filter = f"service:{service}" if service else "*"
    try:
        r = client.aggregate_spans(
            filter_query=f"env:{env} {service_filter}",
            compute={"aggregation": "count"},
            group_by=[{"facet": "service"}, {"facet": "resource"}, {"facet": "operation_name"}],
            filter_from=now - 3600 * 24 * 7,
            filter_to=now,
        )
        return r
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
