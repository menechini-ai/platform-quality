"""APM / Distributed Tracing router — queries Datadog spans."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.filters import compose_filters, to_domain_kwargs
from app.datadog.formatters import fmt_spans, maybe_human
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import friendly_datadog_error

router = APIRouter()


@router.get("/datadog/apm/services")
async def list_services(
    env: str = "prod",
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    human: bool = Query(False, alias="human"),
):
    """List APM services.

    Note: Datadog's Spans API doesn't have a direct 'list services' endpoint.
    This wraps span aggregation by service for recent data.
    """
    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("apm", composed)
    client = DatadogClient()
    from datetime import datetime

    now = int(datetime.now(UTC).timestamp())
    from_ts = fkw.get("from", now - 3600 * 24 * 7)
    to_ts = fkw.get("to", now)
    query = " ".join(p for p in [f"env:{env}", fkw.get("query")] if p)

    try:
        r = client.aggregate_spans(
            filter_query=query,
            compute={"aggregation": "count"},
            group_by=[{"facet": "service"}, {"facet": "resource"}],
            filter_from=from_ts,
            filter_to=to_ts,
        )
        return maybe_human(r, fmt_spans, human, meta={"query": query})
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e


@router.get("/datadog/apm/spans")
async def list_spans(
    query: str | None = Query(default=None),
    service: str | None = None,
    env: str | None = None,
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    limit: int = Query(default=50, le=200),
    from_ts: int | None = None,
    to_ts: int | None = None,
    human: bool = Query(False, alias="human"),
):
    """Search APM traces/spans."""
    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("apm", composed)
    client = DatadogClient()
    filters: list[str] = []
    if query:
        filters.append(query)
    if service:
        filters.append(f"service:{service}")
    if env:
        filters.append(f"env:{env}")
    if "query" in fkw:
        filters.append(fkw["query"])
    combined = " ".join(filters)

    try:
        r = client.list_spans(
            combined,
            limit=limit,
            sort="-timestamp",
            filter_from=fkw.get("from", from_ts),
            filter_to=fkw.get("to", to_ts),
        )
        return maybe_human(r, fmt_spans, human, meta={"query": combined})
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e


@router.get("/datadog/apm/resources")
async def list_resources(
    service: str | None = None,
    env: str = "prod",
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    limit: int = Query(default=50, le=200),  # noqa: ARG001
    human: bool = Query(False, alias="human"),
):
    """List APM resources grouped by service.

    Returns top resources by span count for each service.
    """
    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("apm", composed)
    client = DatadogClient()
    from datetime import datetime

    now = int(datetime.now(UTC).timestamp())
    from_ts = fkw.get("from", now - 3600 * 24 * 7)
    to_ts = fkw.get("to", now)

    service_filter = f"service:{service}" if service else ""
    base = f"env:{env} {service_filter}".strip() if service_filter else f"env:{env}"
    query = " ".join(p for p in [base, fkw.get("query")] if p)
    try:
        r = client.aggregate_spans(
            filter_query=query,
            compute={"aggregation": "count"},
            group_by=[{"facet": "service"}, {"facet": "resource"}, {"facet": "operation_name"}],
            filter_from=from_ts,
            filter_to=to_ts,
        )
        return maybe_human(r, fmt_spans, human, meta={"query": query})
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e


@router.get("/datadog/apm/services/{service_name}/definition")
async def get_service_definition(service_name: str):
    """Get service definition (schema, team, contacts)."""
    import httpx

    from app.datadog.write_guard import friendly_datadog_error, get_datadog_url, get_headers

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/services/definitions/{service_name}"
            resp = await hc.get(url, headers=get_headers(), params={"schema_version": "v2.2"})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e


@router.get("/datadog/apm/services/{service_name}/dependencies")
async def get_service_dependencies(service_name: str, days: int = Query(7, ge=1, le=30)):
    """Get upstream/downstream dependencies for a service."""
    from datetime import UTC, datetime

    import httpx

    from app.datadog.write_guard import friendly_datadog_error, get_datadog_url, get_headers

    now = int(datetime.now(UTC).timestamp())
    from_ts = now - 3600 * 24 * days
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/services/{service_name}/dependencies"
            resp = await hc.get(url, headers=get_headers(), params={"from": from_ts, "to": now})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e


@router.get("/datadog/apm/dependencies")
async def list_all_dependencies(days: int = Query(7, ge=1, le=30)):
    """Get all service dependencies map."""
    from datetime import UTC, datetime

    import httpx

    from app.datadog.write_guard import friendly_datadog_error, get_datadog_url, get_headers

    now = int(datetime.now(UTC).timestamp())
    from_ts = now - 3600 * 24 * days
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/services/dependencies"
            resp = await hc.get(url, headers=get_headers(), params={"from": from_ts, "to": now})
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e
