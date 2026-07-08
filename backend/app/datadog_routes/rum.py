"""Real User Monitoring (RUM) router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.filters import compose_filters, to_domain_kwargs
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import sanitize_error_message

router = APIRouter()


@router.get("/datadog/rum")
async def search_rum_events(
    query: str = Query("*", description="RUM event query"),
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    limit: int = Query(50, le=200),
    sort: str = "-@timestamp",
):
    """Search RUM events (real user monitoring)."""
    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("rum", composed)
    client = DatadogClient()
    from datetime import UTC, datetime

    now = int(datetime.now(UTC).timestamp())
    from_ts = fkw.get("from", now - 3600)
    combined = " ".join(p for p in [query, fkw.get("query")] if p)
    try:
        from datadog_api_client.v2.api.rum_api import RUMApi
        from datadog_api_client.v2.model.rum_search_events_request import RUMSearchEventsRequest

        api = RUMApi(client._api_client)
        body = RUMSearchEventsRequest(
            filter={"query": combined, "from": from_ts, "to": now},
            page={"limit": limit},
            sort=sort,
        )
        r = api.search_rum_events(body=body)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
