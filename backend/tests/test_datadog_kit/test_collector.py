from __future__ import annotations

import pytest

from app.datadog_kit.collector import fetch_all
from app.datadog_kit.models import InvestigationRequest


@pytest.mark.asyncio
async def test_fetch_all_returns_investigation_result() -> None:
    """Smoke test — returns InvestigationResult with all 5 signals."""
    req = InvestigationRequest(query="service:test")
    result = await fetch_all(req)
    assert result.query == "service:test"
    # Each signal is a SignalResult subclass with fields
    assert hasattr(result.logs, "success")
    assert hasattr(result.events, "success")
    assert hasattr(result.monitors, "success")
    assert hasattr(result.metrics, "success")
    assert hasattr(result.spans, "success")
    assert result.total_duration_ms >= 0
