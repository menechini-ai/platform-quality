"""Tests for dual-LLM pattern."""

from __future__ import annotations

import os
from unittest.mock import patch

from app.agents.dual_llm import get_reasoning_model, get_tool_model


class TestDualLlm:
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_reasoning_model_config(self) -> None:
        model = get_reasoning_model()
        assert model.model_name == "gpt-4o"
        assert model.temperature == 0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_tool_model_config(self) -> None:
        model = get_tool_model()
        assert model.model_name == "gpt-4o-mini"
        assert model.temperature == 0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_models_are_different(self) -> None:
        reasoning = get_reasoning_model()
        tool = get_tool_model()
        assert reasoning.model_name != tool.model_name
