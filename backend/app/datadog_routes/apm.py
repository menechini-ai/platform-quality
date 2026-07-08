"""APM / Distributed Tracing router — queries Datadog spans."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.formatters import fmt_spans, maybe_human
from app.datadog.write_guard import sanitize_error_message

router = APIRouter()


@router.get("/datadog/apm/services")
async def list_services(
    env: str = "prod",
    human: bool = Query(False, alias="human"),
):
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
        return maybe_human(r, fmt_spans, human, meta={"query": f"env:{env}"})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/apm/spans")
async def list_spans(
    query: str | None = Query(default=None),
    service: str | None = None,
    env: str | None = None,
    limit: int = Query(default=50, le=200),
    from_ts: int | None = None,
    to_ts: int | None = None,
    human: bool = Query(False, alias="human"),
):
    """Search APM traces/spans."""
    client = DatadogClient()
    filters: list[str] = []
    if query:
        filters.append(query)
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
        return maybe_human(r, fmt_spans, human, meta={"query": combined})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/apm/resources")
async def list_resources(
    service: str | None = None,
    env: str = "prod",
    limit: int = Query(default=50, le=200),  # noqa: ARG001
    human: bool = Query(False, alias="human"),
):
    """List APM resources grouped by service.

    Returns top resources by span count for each service.
    """
    client = DatadogClient()
    from datetime import datetime

    now = int(datetime.now(UTC).timestamp())

    service_filter = f"service:{service}" if service else ""
    try:
        r = client.aggregate_spans(
            filter_query=f"env:{env} {service_filter}".strip() if service_filter else f"env:{env}",
            compute={"aggregation": "count"},
            group_by=[{"facet": "service"}, {"facet": "resource"}, {"facet": "operation_name"}],
            filter_from=now - 3600 * 24 * 7,
            filter_to=now,
        )
        return maybe_human(r, fmt_spans, human, meta={"query": f"env:{env} {service_filter}"})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/apm/services/{service_name}/definition")
async def get_service_definition(service_name: str):
    """Get service definition (schema, team, contacts)."""
    import httpx

    from app.datadog.write_guard import get_datadog_url, get_headers

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/services/definitions/{service_name}"
            resp = await hc.get(url, headers=get_headers(), params={"schema_version": "v2.2"})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/apm/services/{service_name}/dependencies")
async def get_service_dependencies(service_name: str, days: int = Query(7, ge=1, le=30)):
    """Get upstream/downstream dependencies for a service."""
    from datetime import UTC, datetime

    import httpx

    from app.datadog.write_guard import get_datadog_url, get_headers

    now = int(datetime.now(UTC).timestamp())
    from_ts = now - 3600 * 24 * days
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/services/{service_name}/dependencies"
            resp = await hc.get(url, headers=get_headers(), params={"from": from_ts, "to": now})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


@router.get("/datadog/apm/dependencies")
async def list_all_dependencies(days: int = Query(7, ge=1, le=30)):
    """Get all service dependencies map."""
    from datetime import UTC, datetime

    import httpx

    from app.datadog.write_guard import get_datadog_url, get_headers

    now = int(datetime.now(UTC).timestamp())
    from_ts = now - 3600 * 24 * days
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/services/dependencies"
            resp = await hc.get(url, headers=get_headers(), params={"from": from_ts, "to": now})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
