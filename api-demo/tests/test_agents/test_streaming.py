"""Tests for agents.streaming_handler — SSE event formatting."""

from __future__ import annotations

import json

import pytest

from agents.streaming_handler import format_sse, stream_pipeline


class TestFormatSse:
    def test_includes_event_and_data(self) -> None:
        result = format_sse("test_event", {"key": "value"})
        data = json.loads(result.removeprefix("data: ").removesuffix("\n\n"))
        assert data["event"] == "test_event"
        assert data["key"] == "value"

    def test_ends_with_double_newline(self) -> None:
        result = format_sse("e", {})
        assert result.endswith("\n\n")


class TestStreamPipeline:
    @pytest.mark.asyncio
    async def test_yields_sse_event(self) -> None:
        async def fake_ainvoke(state):
            return {"analysis": "test", "recommendation": "test"}

        mock_pipeline = type("MockPipeline", (), {})()
        mock_pipeline.ainvoke = fake_ainvoke

        state = {
            "messages": [{"role": "user", "content": "test"}],
            "incident_id": "inc-1",
            "analysis": None,
            "recommendation": None,
        }

        events = [e async for e in stream_pipeline(state, mock_pipeline)]
        assert len(events) == 1
        data = json.loads(events[0].removeprefix("data: ").removesuffix("\n\n"))
        assert data["event"] == "complete"
        assert data["analysis"] == "test"
