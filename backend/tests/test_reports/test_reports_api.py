"""Tests for reports API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_reports_empty(client: AsyncClient):
    resp = await client.get("/api/v1/reports")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_executive_report(client: AsyncClient):
    resp = await client.post(
        "/api/v1/reports",
        json={
            "report_type": "executive",
            "title": "Q3 Executive Summary",
            "tags": ["quarterly", "summary"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_type"] == "executive"
    assert data["title"] == "Q3 Executive Summary"
    assert "Executive Summary" in data["content"]


@pytest.mark.asyncio
async def test_generate_postmortem_from_incident(client: AsyncClient):
    # First create an incident
    inc_resp = await client.post(
        "/api/v1/incidents",
        json={"title": "DB outage", "severity": "SEV-1", "service": "database"},
    )
    assert inc_resp.status_code == 201
    incident = inc_resp.json()
    inc_id = incident["id"]

    # Generate postmortem
    resp = await client.post(f"/api/v1/reports/postmortem/{inc_id}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_type"] == "postmortem"
    assert "DB outage" in data["content"]
    assert "Pending investigation" in data["content"]


@pytest.mark.asyncio
async def test_postmortem_nonexistent_incident(client: AsyncClient):
    resp = await client.post("/api/v1/reports/postmortem/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_by_id(client: AsyncClient):
    # Create
    create_resp = await client.post(
        "/api/v1/reports",
        json={"report_type": "monthly", "title": "June Report"},
    )
    report_id = create_resp.json()["id"]

    # Fetch
    resp = await client.get(f"/api/v1/reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "June Report"
