"""Tests for SSE streaming handler."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.agents.streaming_handler import stream_pipeline


def _mock_pipeline(events: list[dict]) -> MagicMock:
    """Create a mock pipeline whose astream returns an async generator."""

    async def _agen():
        for e in events:
            yield e

    pipeline = MagicMock()
    pipeline.astream = MagicMock(return_value=_agen())
    return pipeline


class TestStreamPipeline:
    @pytest.mark.asyncio
    async def test_stream_yields_events(self) -> None:
        pipeline = _mock_pipeline(
            [
                {"triage_incident": {"analysis": "CPU spike detected"}},
                {"generate_recommendation": {"recommendation": "Restart nginx"}},
            ]
        )

        initial = {
            "messages": [{"role": "user", "content": "test"}],
            "incident_id": "1",
            "analysis": None,
            "recommendation": None,
        }

        events = []
        async for event in stream_pipeline(initial, pipeline):
            events.append(event)

        assert len(events) == 3
        assert events[0].startswith("data: ")
        assert events[1].startswith("data: ")
        assert events[2] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_stream_event_format(self) -> None:
        pipeline = _mock_pipeline(
            [
                {"triage_incident": {"analysis": "test analysis"}},
            ]
        )

        initial = {
            "messages": [],
            "incident_id": "1",
            "analysis": None,
            "recommendation": None,
        }

        async for event in stream_pipeline(initial, pipeline):
            if event == "data: [DONE]\n\n":
                continue
            prefix = "data: "
            assert event.startswith(prefix)
            payload = json.loads(event[len(prefix) :].strip())
            assert "node" in payload
            assert "output" in payload
