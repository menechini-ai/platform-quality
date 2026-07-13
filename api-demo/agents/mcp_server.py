"""MCP protocol server for ObservAI tool dispatch.

Implements JSON-RPC style request/response with three demo tools:

- ``search_kb(query)``       — quick keyword KB lookup
- ``get_incident(id)``        — fetch incident details from fixture data
- ``suggest_runbook(pattern)`` — mock runbook recommendation

Tool calls pass through ``ToolBudget`` for rate enforcement.
"""

from __future__ import annotations

import json
from typing import Any

from agents.tool_budget import ToolBudget

# ── Internal Data ──────────────────────────────────────────────────────

_KB_ENTRIES: list[dict[str, str]] = [
    {"id": "kb-001", "title": "Deploy rollback", "summary": "kubectl rollout undo deployment/app"},
    {
        "id": "kb-002",
        "title": "Database recovery",
        "summary": "Restore from latest pg_dump snapshot",
    },
    {"id": "kb-003", "title": "Certificate renewal", "summary": "certbot renew --force-renewal"},
]

_INCIDENTS: list[dict[str, str]] = [
    {"id": "inc-001", "title": "API Latency Spike", "severity": "critical"},
    {"id": "inc-002", "title": "Database Connection Pool Exhausted", "severity": "high"},
    {"id": "inc-003", "title": "TLS Certificate Expiry", "severity": "medium"},
]


# ── Internal Tool Handlers ─────────────────────────────────────────────


def _search_kb(query: str) -> list[dict[str, str]]:
    q = query.lower()
    return [e for e in _KB_ENTRIES if q in e["title"].lower() or q in e["summary"].lower()]


def _get_incident(id: str) -> dict[str, str] | None:
    return next((i for i in _INCIDENTS if i["id"] == id), None)


def _suggest_runbook(pattern: str) -> dict[str, str]:
    return {"pattern": pattern, "runbook": f"Runbook for '{pattern}' — verify, isolate, remediate"}


# ── Tool Registry ──────────────────────────────────────────────────────

_TOOLS: dict[str, dict[str, Any]] = {
    "search_kb": {
        "description": "Search knowledge base entries by keyword",
        "parameters": {"query": {"type": "string", "description": "Search keyword"}},
        "handler": _search_kb,
    },
    "get_incident": {
        "description": "Get incident details by ID",
        "parameters": {"id": {"type": "string", "description": "Incident identifier"}},
        "handler": _get_incident,
    },
    "suggest_runbook": {
        "description": "Suggest a runbook for a given failure pattern",
        "parameters": {"pattern": {"type": "string", "description": "Failure pattern to match"}},
        "handler": _suggest_runbook,
    },
}

_budget: ToolBudget | None = None


def configure_budget(max_calls: int = 10, window_seconds: int = 60) -> None:
    """Attach a ``ToolBudget`` to the MCP server."""
    global _budget
    _budget = ToolBudget(max_calls=max_calls, window_seconds=window_seconds)


# ── Public API ─────────────────────────────────────────────────────────


def list_tools() -> list[dict[str, Any]]:
    """Return tool metadata (name + description + parameters)."""
    return [
        {"name": name, "description": meta["description"], "parameters": meta["parameters"]}
        for name, meta in _TOOLS.items()
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a tool call.

    Returns a JSON-RPC-like result dict: ``{"result": ...}`` or ``{"error": ...}``.

    Raises:
        No exception — always returns a dict with either ``result`` or ``error``.
    """
    if _budget is not None and not _budget.allow_call():
        return {"error": {"code": -32000, "message": "Tool budget exceeded"}}

    tool = _TOOLS.get(name)
    if tool is None:
        return {"error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    try:
        result = tool["handler"](**arguments)
        return {"result": result}
    except Exception as exc:
        return {"error": {"code": -32603, "message": str(exc)}}


def handle_request(raw: str) -> str:
    """Accept a JSON-RPC-like request string and return a JSON response.

    Expected format::

        {"method": "search_kb", "params": {"query": "deploy"}}
        {"method": "list_tools", "params": {}}
    """
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": {"code": -32700, "message": str(exc)}})

    method = request.get("method", "")
    params = request.get("params", {})

    if method == "list_tools":
        return json.dumps({"result": list_tools()})

    return json.dumps(call_tool(method, params))


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="MCP demo server")
    parser.add_argument("--port", type=int, default=8100, help="Port to listen on")
    parser.add_argument("--max-calls", type=int, default=10, help="Tool budget max calls")
    parser.add_argument("--window", type=int, default=60, help="Tool budget window (seconds)")
    args = parser.parse_args()

    configure_budget(max_calls=args.max_calls, window_seconds=args.window)
    print(
        f"MCP demo server configured on port {args.port} with budget ({args.max_calls}/{args.window}s)"
    )
    print("Available tools:", [t["name"] for t in list_tools()])
    print()

    if sys.stdin.isatty():
        print("Enter JSON-RPC requests (Ctrl+D to exit):")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        print(handle_request(line))
