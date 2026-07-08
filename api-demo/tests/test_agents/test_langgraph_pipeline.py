"""Tests for agents.langgraph_pipeline — pipeline construction and logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agents.langgraph_pipeline import (
    AgentState,
    build_pipeline,
    run_pipeline,
    should_continue,
)


class TestShouldContinue:
    def test_returns_generate_recommendation_when_analysis_present(self) -> None:
        state: AgentState = {
            "messages": [],
            "incident_id": "inc-1",
            "analysis": "CPU spike",
            "recommendation": None,
        }
        assert should_continue(state) == "generate_recommendation"

    def test_returns_end_when_analysis_is_none(self) -> None:
        state: AgentState = {
            "messages": [],
            "incident_id": "inc-1",
            "analysis": None,
            "recommendation": None,
        }
        assert should_continue(state) == "__end__"

    def test_returns_end_when_analysis_is_empty(self) -> None:
        state: AgentState = {
            "messages": [],
            "incident_id": "inc-1",
            "analysis": "",
            "recommendation": None,
        }
        assert should_continue(state) == "__end__"


class TestBuildPipeline:
    def test_returns_compiled_graph(self) -> None:
        graph = build_pipeline()
        assert graph is not None
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")

    def test_graph_has_expected_nodes(self) -> None:
        graph = build_pipeline()
        nodes = set(graph.nodes)  # graph.nodes is a dict/OrderedDict
        assert "triage_incident" in nodes
        assert "generate_recommendation" in nodes


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_run_pipeline_returns_complete_state(self) -> None:
        mock_reasoning = AsyncMock()
        mock_reasoning.ainvoke.return_value = type("", (), {"content": "Triage analysis"})()
        mock_tool = AsyncMock()
        mock_tool.ainvoke.return_value = type("", (), {"content": "Use runbook ABC"})()

        with (
            patch("agents.langgraph_pipeline.get_reasoning_model", return_value=mock_reasoning),
            patch("agents.langgraph_pipeline.get_tool_model", return_value=mock_tool),
        ):
            result = await run_pipeline("inc-1", "Latency spike detected")

        assert result["incident_id"] == "inc-1"
        assert result["analysis"] == "Triage analysis"
        assert result["recommendation"] == "Use runbook ABC"
        mock_reasoning.ainvoke.assert_awaited_once()
        mock_tool.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_pipeline_with_empty_description(self) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = type("", (), {"content": "Empty analysis"})()

        with (
            patch("agents.langgraph_pipeline.get_reasoning_model", return_value=mock_llm),
            patch("agents.langgraph_pipeline.get_tool_model", return_value=mock_llm),
        ):
            result = await run_pipeline("inc-2", "")

        assert result["analysis"] == "Empty analysis"
        assert result["recommendation"] is not None
