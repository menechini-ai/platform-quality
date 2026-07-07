"""Fleet Automation router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.formatters import fmt_fleet, maybe_human
from app.datadog.write_guard import get_datadog_url, get_headers, sanitize_error_message

router = APIRouter()


@router.get("/datadog/fleet/agents")
async def list_fleet_agents(
    filter: str | None = None,
    page_size: int = Query(50, le=200),
    human: bool = Query(False, alias="human"),
):
    """List fleet agents managed by Datadog Fleet Automation."""
    import httpx

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v2/fleet-agents"
            params: dict = {"page[size]": page_size}
            if filter:
                params["filter"] = filter
            resp = await hc.get(url, headers=get_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            return maybe_human(data, fmt_fleet, human, meta={"total": len(data.get("data", []))})
    except Exception as e:
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e


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
        raise HTTPException(status_code=502, detail=sanitize_error_message(str(e))) from e
