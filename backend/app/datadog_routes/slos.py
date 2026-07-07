"""Datadog SLOs router — proxy to Datadog SLO API with tag filtering."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.client import DatadogClient

router = APIRouter()


@router.get("/datadog/slos")
async def list_datadog_slos(
    tags: str | None = Query(None, description="Tag filter, e.g. 'env:prod,service:api'"),
    query: str | None = Query(None, description="Substring match on SLO name/description"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """List Datadog SLOs with optional tag filtering.

    Tags follow Unified Service Tagging (UST):
      env:prod/staging/dev, service:<name>, team:<team>

    Example:
      /api/v1/datadog/slos?tags=env:prod,service:api&limit=25
    """
    client = DatadogClient()
    kwargs: dict = {"limit": limit, "offset": offset}
    if tags:
        kwargs["tags_query"] = tags
    if query:
        kwargs["query"] = query
    try:
        return client.list_slos(**kwargs)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


# Static paths BEFORE param paths
@router.get("/datadog/slos/corrections")
async def list_slo_corrections(
    slo_id: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """List SLO corrections (manual adjustments)."""
    client = DatadogClient()
    kwargs: dict = {"limit": limit, "offset": offset}
    if slo_id:
        kwargs["slo_id"] = slo_id
    try:
        r = client.slos.list_slo_corrections(**kwargs)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/datadog/slos/{slo_id}")
async def get_datadog_slo(slo_id: str):
    """Get a single Datadog SLO by ID."""
    client = DatadogClient()
    try:
        r = client.slos.get_slo(slo_id=slo_id)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/datadog/slos/{slo_id}/history")
async def get_slo_history(
    slo_id: str,
    days: int = Query(30, ge=1, le=90),
):
    """Get SLO history (burn-rate, status over time)."""
    from datetime import UTC, datetime

    client = DatadogClient()
    now = int(datetime.now(UTC).timestamp())
    from_ts = now - 3600 * 24 * days
    try:
        r = client.slos.get_slo_history(slo_id=slo_id, from_ts=from_ts, to_ts=now)
        return r.to_dict()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
