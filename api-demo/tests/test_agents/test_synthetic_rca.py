"""Tests for agents.synthetic_rca — pipeline evaluation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agents.synthetic_rca import evaluate_pipeline, load_incidents


class TestLoadIncidents:
    def test_loads_json_file(self, tmp_path) -> None:
        f = tmp_path / "incidents.json"
        f.write_text('[{"id": "inc-1", "title": "Test"}]')
        incidents = load_incidents(str(f))
        assert len(incidents) == 1
        assert incidents[0]["id"] == "inc-1"


class TestEvaluatePipeline:
    @pytest.mark.asyncio
    async def test_returns_report_with_accuracy(self) -> None:
        mock_reasoning = AsyncMock()
        mock_reasoning.ainvoke.return_value = type(
            "", (), {"content": "Database connection pool exhausted"}
        )()
        mock_tool = AsyncMock()
        mock_tool.ainvoke.return_value = type("", (), {"content": "Restore database"})()
        patches = (
            patch("agents.synthetic_rca.run_pipeline"),
            patch("agents.langgraph_pipeline.get_reasoning_model", return_value=mock_reasoning),
            patch("agents.langgraph_pipeline.get_tool_model", return_value=mock_tool),
        )
        with patches[0] as mock_run, patches[1], patches[2]:
            mock_run.return_value = {
                "analysis": "Database connection pool exhausted",
                "recommendation": "Restore database",
            }
            incidents = [
                {
                    "id": "inc-1",
                    "title": "DB down",
                    "description": "db connection issue",
                    "expected_root_cause": "Database connection pool",
                },
            ]
            report = await evaluate_pipeline(incidents)

        assert report["total"] == 1
        assert report["correct_rca"] == 1
        assert report["accuracy"] == 1.0
        assert report["results"][0]["rca_match"] is True
        assert report["results"][0]["has_runbook"] is True
