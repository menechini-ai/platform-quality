"""Fleet Automation router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.filters import compose_filters, to_domain_kwargs
from app.datadog.formatters import fmt_fleet, maybe_human
from app.datadog.schemas import DatadogFilter, Period
from app.datadog.write_guard import (
    friendly_datadog_error,
    get_datadog_url,
    get_headers,
)

router = APIRouter()


@router.get("/datadog/fleet/agents")
async def list_fleet_agents(
    filter: str | None = None,
    tags: list[str] | None = Query(default=None, description="Tag filter (env:prod, service:api)"),
    period: Period | None = Query(default=None, description="Time window: 1d, 7d, 15d, 30d"),
    page_size: int = Query(50, le=200),
    human: bool = Query(False, alias="human"),
):
    """List fleet agents managed by Datadog Fleet Automation."""
    import httpx

    composed = compose_filters(DatadogFilter(tags=tags, period=period))
    fkw = to_domain_kwargs("fleet", composed)
    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/fleet-agents"
            params: dict = {"page[size]": page_size}
            fleet_filter = " ".join(p for p in [filter, fkw.get("filter")] if p)
            if fleet_filter:
                params["filter"] = fleet_filter
            resp = await hc.get(url, headers=get_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            return maybe_human(data, fmt_fleet, human, meta={"total": len(data.get("data", []))})
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e


@router.get("/datadog/fleet/agents/{agent_id}")
async def get_fleet_agent_info(agent_id: str):
    """Get detailed info for a specific fleet agent."""
    import httpx

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/fleet-agents/{agent_id}"
            resp = await hc.get(url, headers=get_headers())
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        status, detail = friendly_datadog_error(e)
        raise HTTPException(status_code=status, detail=detail) from e
