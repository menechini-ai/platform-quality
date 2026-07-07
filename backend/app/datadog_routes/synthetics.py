"""Synthetics router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.datadog.write_guard import get_headers, get_datadog_url
from app.datadog.client import DatadogClient

router = APIRouter()


@router.get("/datadog/synthetics")
async def list_synthetics(limit: int = Query(50, le=200)):
    """List synthetic tests."""
    import httpx

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v1/synthetics/tests"
            resp = await hc.get(url, headers=get_headers(), params={"limit": limit})
            resp.raise_for_status()
            return resp.json().get("tests", [])
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/datadog/synthetics/{public_id}/results")
async def get_synthetics_result(public_id: str):
    """Get results for a synthetic test."""
    import httpx

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v1/synthetics/tests/{public_id}/results"
            resp = await hc.get(url, headers=get_headers())
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/datadog/synthetics/browser/{public_id}/results")
async def get_browser_synthetics_result(public_id: str):
    """Get browser test results with screenshot paths."""
    import httpx

    try:
        async with httpx.AsyncClient() as hc:
            url = f"{get_datadog_url()}/api/v1/synthetics/tests/browser/{public_id}/results"
            resp = await hc.get(url, headers=get_headers())
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
