from __future__ import annotations

import pytest

from app.datadog_kit.collector import fetch_all
from app.datadog_kit.models import InvestigationRequest


@pytest.mark.asyncio
async def test_fetch_all_returns_investigation_result() -> None:
    """Smoke test — without Datadog creds signals fail but result is still returned."""
    req = InvestigationRequest(query="service:test")
    result = await fetch_all(req)
    assert result.query == "service:test"
    # Without real creds, all signals should have success=False
    assert result.logs.success is False
    assert result.events.success is False
    assert result.monitors.success is False
    assert result.metrics.success is False
    assert result.total_duration_ms >= 0
