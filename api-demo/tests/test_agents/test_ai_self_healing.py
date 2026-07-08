"""Tests for agents.ai_self_healing — LLM-driven remediation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agents.ai_self_healing import AISelfHealing


class TestAISelfHealing:
    @pytest.mark.asyncio
    async def test_analyze_returns_remediation_plan(self) -> None:
        healing = AISelfHealing(auto_approve=True)
        mock_reasoning = AsyncMock()
        mock_reasoning.ainvoke.return_value = type("", (), {"content": "High CPU"})()
        mock_tool = AsyncMock()
        mock_tool.ainvoke.return_value = type("", (), {"content": "Scale up"})()
        patches = (
            patch("agents.ai_self_healing.run_pipeline"),
            patch("agents.langgraph_pipeline.get_reasoning_model", return_value=mock_reasoning),
            patch("agents.langgraph_pipeline.get_tool_model", return_value=mock_tool),
        )
        with patches[0] as mock_run, patches[1], patches[2]:
            mock_run.return_value = {
                "analysis": "High CPU",
                "recommendation": "Scale up EC2",
            }
            result = await healing.analyze("inc-1", "CPU spike")
        assert result["analysis"] == "High CPU"
        assert result["recommendation"] == "Scale up EC2"
        assert result["approved"] is True
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_execute_applies_remediation_when_approved(self) -> None:
        healing = AISelfHealing(auto_approve=True)
        mock_reasoning = AsyncMock()
        mock_reasoning.ainvoke.return_value = type("", (), {"content": "Memory leak"})()
        mock_tool = AsyncMock()
        mock_tool.ainvoke.return_value = type("", (), {"content": "Restart service"})()
        patches = (
            patch("agents.ai_self_healing.run_pipeline"),
            patch("agents.langgraph_pipeline.get_reasoning_model", return_value=mock_reasoning),
            patch("agents.langgraph_pipeline.get_tool_model", return_value=mock_tool),
        )
        with patches[0] as mock_run, patches[1], patches[2]:
            mock_run.return_value = {
                "analysis": "Memory leak",
                "recommendation": "Restart service",
            }
            result = await healing.execute("inc-2", "OOM")
        assert result["executed"] is True
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_status_failed_when_no_analysis(self) -> None:
        healing = AISelfHealing()
        mock_reasoning = AsyncMock()
        mock_reasoning.ainvoke.return_value = type("", (), {"content": ""})()
        mock_tool = AsyncMock()
        mock_tool.ainvoke.return_value = type("", (), {"content": ""})()
        patches = (
            patch("agents.ai_self_healing.run_pipeline"),
            patch("agents.langgraph_pipeline.get_reasoning_model", return_value=mock_reasoning),
            patch("agents.langgraph_pipeline.get_tool_model", return_value=mock_tool),
        )
        with patches[0] as mock_run, patches[1], patches[2]:
            mock_run.return_value = {"analysis": None, "recommendation": None}
            result = await healing.analyze("inc-3", "unknown issue")
        assert result["status"] == "failed"
        assert result["executed"] is False
