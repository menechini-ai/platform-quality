"""Tests for agents.mcp_server — JSON-RPC tool dispatch."""

from __future__ import annotations

import json

from agents.mcp_server import call_tool, configure_budget, handle_request, list_tools


class TestListTools:
    def test_returns_three_tools(self) -> None:
        tools = list_tools()
        names = {t["name"] for t in tools}
        assert names == {"search_kb", "get_incident", "suggest_runbook"}

    def test_each_tool_has_description_and_parameters(self) -> None:
        for tool in list_tools():
            assert "description" in tool
            assert "parameters" in tool


class TestCallTool:
    def test_search_kb_returns_matches(self) -> None:
        result = call_tool("search_kb", {"query": "deploy"})
        assert "result" in result
        assert any("deploy" in str(r).lower() for r in result["result"])

    def test_get_incident_returns_details(self) -> None:
        result = call_tool("get_incident", {"id": "inc-001"})
        assert result["result"]["title"] == "API Latency Spike"

    def test_get_incident_unknown_returns_none(self) -> None:
        result = call_tool("get_incident", {"id": "unknown"})
        assert result["result"] is None

    def test_suggest_runbook_returns_runbook(self) -> None:
        result = call_tool("suggest_runbook", {"pattern": "latency"})
        assert "runbook" in result["result"]

    def test_unknown_tool_returns_error(self) -> None:
        result = call_tool("nonexistent", {})
        assert "error" in result
        assert result["error"]["code"] == -32601

    def test_budget_exceeded_returns_error(self) -> None:
        configure_budget(max_calls=0, window_seconds=60)
        try:
            result = call_tool("search_kb", {"query": "deploy"})
            assert "error" in result
            assert result["error"]["code"] == -32000
        finally:
            configure_budget(max_calls=10, window_seconds=60)


class TestHandleRequest:
    def test_list_tools_request(self) -> None:
        resp = json.loads(handle_request('{"method": "list_tools", "params": {}}'))
        assert "result" in resp
        assert len(resp["result"]) == 3

    def test_call_tool_request(self) -> None:
        resp = json.loads(handle_request('{"method": "search_kb", "params": {"query": "deploy"}}'))
        assert "result" in resp

    def test_invalid_json_returns_error(self) -> None:
        resp = json.loads(handle_request("not json"))
        assert "error" in resp
