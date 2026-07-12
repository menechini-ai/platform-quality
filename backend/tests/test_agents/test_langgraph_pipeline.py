"""Tests for LangGraph agent pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.langgraph_pipeline import build_pipeline, should_continue


class TestShouldContinue:
    def test_continue_with_analysis(self) -> None:
        state = {
            "analysis": "CPU spike detected",
            "recommendation": None,
            "messages": [],
            "incident_id": "1",
        }
        result = should_continue(state)
        assert result == "generate_recommendation"

    def test_stop_without_analysis(self) -> None:
        state = {"analysis": None, "recommendation": None, "messages": [], "incident_id": "1"}
        result = should_continue(state)
        assert result == "__end__"

    def test_stop_with_empty_analysis(self) -> None:
        state = {"analysis": "", "recommendation": None, "messages": [], "incident_id": "1"}
        result = should_continue(state)
        assert result == "__end__"


class TestBuildPipeline:
    def test_pipeline_compiles(self) -> None:
        pipeline = build_pipeline()
        assert pipeline is not None
        assert "triage_incident" in pipeline.nodes
        assert "generate_recommendation" in pipeline.nodes

    @patch("app.agents.langgraph_pipeline.get_reasoning_model")
    @patch("app.agents.langgraph_pipeline.get_tool_model")
    @pytest.mark.asyncio
    async def test_pipeline_full_run(self, mock_tool: MagicMock, mock_reasoning: MagicMock) -> None:
        mock_reasoning_instance = AsyncMock()
        mock_reasoning_instance.ainvoke.return_value.content = "Memory leak detected"
        mock_reasoning.return_value = mock_reasoning_instance

        mock_tool_instance = AsyncMock()
        mock_tool_instance.ainvoke.return_value.content = "Restart the service"
        mock_tool.return_value = mock_tool_instance

        from app.agents.langgraph_pipeline import run_pipeline

        result = await run_pipeline("inc-1", "High memory usage")
        assert result["analysis"] == "Memory leak detected"
        assert result["recommendation"] == "Restart the service"

    @patch("app.agents.langgraph_pipeline.get_reasoning_model")
    @patch("app.agents.langgraph_pipeline.get_tool_model")
    @pytest.mark.asyncio
    async def test_pipeline_empty_analysis_stops(
        self, mock_tool: MagicMock, mock_reasoning: MagicMock
    ) -> None:
        mock_reasoning_instance = AsyncMock()
        mock_reasoning_instance.ainvoke.return_value.content = ""
        mock_reasoning.return_value = mock_reasoning_instance

        mock_tool_instance = AsyncMock()
        mock_tool.return_value = mock_tool_instance

        from app.agents.langgraph_pipeline import run_pipeline

        result = await run_pipeline("inc-2", "Everything looks fine")
        assert result["analysis"] == ""
        # Recommendation should NOT be generated (empty analysis stops pipeline)
        # In LangGraph, when should_continue returns "__end__", the recommendation node
        # is never called, so it stays None
        assert result["recommendation"] is None
