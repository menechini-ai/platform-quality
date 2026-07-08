"""Tests for agents.dual_llm — reasoning/tool-model configuration."""

from __future__ import annotations

from unittest.mock import patch

from agents.dual_llm import get_reasoning_model, get_tool_model


class TestGetReasoningModel:
    def test_returns_chat_openai_with_gpt_4o(self) -> None:
        with patch("agents.dual_llm.ChatOpenAI") as mock:
            get_reasoning_model()
        mock.assert_called_once_with(
            model="gpt-4o",
            temperature=0,
            api_key="",
            base_url=None,
        )


class TestGetToolModel:
    def test_returns_chat_openai_with_gpt_4o_mini(self) -> None:
        with patch("agents.dual_llm.ChatOpenAI") as mock:
            get_tool_model()
        mock.assert_called_once_with(
            model="gpt-4o-mini",
            temperature=0,
            api_key="",
            base_url=None,
        )
