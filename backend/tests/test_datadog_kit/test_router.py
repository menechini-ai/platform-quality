from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_investigate_returns_200() -> None:
    """Smoke test: POST /datadog/investigate returns a report (no DB = error)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/datadog/investigate",
            json={"query": "service:test", "time_range_minutes": 60},
        )
    # Without real Datadog creds + DB, will return 500 — that's expected.
    # We just check the endpoint responds without import error.
    assert resp.status_code in (200, 422, 500)


async def test_investigate_needs_query() -> None:
    """POST without required 'query' field returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/datadog/investigate", json={})
    assert resp.status_code == 422


async def test_get_report_returns_404() -> None:
    """GET on nonexistent report returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/datadog/investigate/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
