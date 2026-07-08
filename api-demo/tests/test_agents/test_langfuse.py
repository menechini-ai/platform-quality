"""Tests for agents.langfuse — observability tracer."""

from __future__ import annotations

import os
from unittest.mock import patch

from agents.langfuse import LangfuseTracer


class TestLangfuseTracer:
    def test_disabled_when_key_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            tracer = LangfuseTracer()
        assert tracer.enabled is False

    def test_enabled_when_key_present(self) -> None:
        with patch.dict(os.environ, {"LANGFUSE_SECRET_KEY": "sk-123"}):
            tracer = LangfuseTracer()
        assert tracer.enabled is True

    def test_observe_noop_when_disabled(self) -> None:
        tracer = LangfuseTracer()
        with tracer.observe("test") as ctx:
            ctx.record(key="value")
        assert ctx.records == []

    def test_observe_records_when_enabled(self) -> None:
        with patch.dict(os.environ, {"LANGFUSE_SECRET_KEY": "sk-123"}):
            tracer = LangfuseTracer()
        with tracer.observe("test", env="prod") as ctx:
            ctx.record(step="llm_call")
        assert len(ctx.records) >= 2
        assert ctx.records[0]["event"] == "start"
        assert ctx.records[-1]["event"] == "end"
