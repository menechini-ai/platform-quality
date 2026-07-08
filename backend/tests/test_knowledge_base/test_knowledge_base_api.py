"""Tests for knowledge base API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_kb_empty(client: AsyncClient):
    resp = await client.get("/api/v1/kb")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_kb_entry(client: AsyncClient):
    resp = await client.post(
        "/api/v1/kb",
        json={
            "title": "DB Restart Procedure",
            "root_cause": "Unresponsive database",
            "resolution_steps": ["1. Check locks", "2. Restart service"],
            "tags": ["database", "runbook"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "DB Restart Procedure"
    assert data["root_cause"] == "Unresponsive database"
    assert "tags" in data


@pytest.mark.asyncio
async def test_seed_knowledge_base(client: AsyncClient):
    resp = await client.post("/api/v1/kb/seed")
    assert resp.status_code == 201
    data = resp.json()
    assert data["seeded"] >= 6  # 8 entries
    assert "message" in data

    # Verify they're now listable
    list_resp = await client.get("/api/v1/kb")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == data["seeded"]


@pytest.mark.asyncio
async def test_filter_by_tag(client: AsyncClient):
    # Seed first
    await client.post("/api/v1/kb/seed")
    resp = await client.get("/api/v1/kb?tag=postmortem")
    assert resp.status_code == 200
    entries = resp.json()
    assert all("postmortem" in e["tags"] for e in entries)


@pytest.mark.asyncio
async def test_get_nonexistent_kb(client: AsyncClient):
    resp = await client.get("/api/v1/kb/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_kb_by_id(client: AsyncClient):
    # Create
    create_resp = await client.post(
        "/api/v1/kb", json={"title": "Specific Entry", "tags": ["test"]}
    )
    kb_id = create_resp.json()["id"]

    # Get
    resp = await client.get(f"/api/v1/kb/{kb_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Specific Entry"
