"""Real User Monitoring (RUM) router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient
from app.datadog.filters import compose_filters, to_domain_kwargs
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import friendly_datadog_error

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
        from datadog_api_client.v2.model.rum_query_filter import RUMQueryFilter
        from datadog_api_client.v2.model.rum_query_page_options import RUMQueryPageOptions
        from datadog_api_client.v2.model.rum_search_events_request import RUMSearchEventsRequest
        from datadog_api_client.v2.model.rum_sort import RUMSort

        api = RUMApi(client._api_client)
        sort_enum = (
            RUMSort.TIMESTAMP_DESCENDING if sort == "-@timestamp" else RUMSort.TIMESTAMP_ASCENDING
        )
        body = RUMSearchEventsRequest(
            filter=RUMQueryFilter(query=combined, _from=str(from_ts), to=str(now)),
            page=RUMQueryPageOptions(limit=limit),
            sort=sort_enum,
        )
        r = api.search_rum_events(body=body)
        return r.to_dict()
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e
