"""ReAct Agent for iterative Datadog investigation."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.datadog.client import DatadogClient
from app.datadog_kit.collector import fetch_all
from app.datadog_kit.config import DatadogKitConfig
from app.datadog_kit.diagnosis import _call_openai, _parse_rca_response
from app.datadog_kit.models import (
    InvestigationRequest,
    InvestigationRequestV3,
    InvestigationResult,
    MttrBreakdown,
    ReActTurn,
    Runbook,
)

logger = logging.getLogger(__name__)


def _build_tools_prompt() -> str:
    lines = ["Available tools:"]
    tools = {
        "fetch_logs": "Search logs (query, time_range_minutes, limit)",
        "fetch_spans": "Search APM spans (query, time_range_minutes, limit)",
        "fetch_metrics": "Query metrics (query, time_range_minutes)",
        "fetch_monitors": "List monitors (state, tags)",
        "fetch_events": "Search events (query, time_range_minutes)",
        "search_incidents": "Search incidents (query)",
        "get_incident": "Get incident details (incident_id)",
    }
    for name, desc in tools.items():
        lines.append(f"  {name}: {desc}")
    return "\n".join(lines)


_REACT_SYSTEM_PROMPT = (
    "You are an SRE ReAct agent investigating production incidents using Datadog.\n"
    + _build_tools_prompt()
    + """

At each turn, respond with JSON:
{
  "thought": "reasoning about next step",
  "action": "tool_name",
  "action_input": {"param": "value"},
  "final_answer": false
}

When complete, set final_answer: true and include diagnosis:
{
  "thought": "investigation complete",
  "action": "analyze",
  "action_input": {},
  "final_answer": true,
  "diagnosis": {
    "root_cause": "...",
    "root_cause_category": "deploy|resource|latency|dependency|data_corruption",
    "causal_chain": [...],
    "severity": "P1|P2|P3",
    "confidence": 0.0-1.0,
    "evidence_refs": {"logs": [...], "spans": [...], "monitors": [...],
      "metrics": [...], "events": [...]},
    "remediation_steps": [...],
    "inconclusive": false
  }
}"""
)


async def _execute_tool(name: str, params: dict[str, Any]) -> str:
    """Execute a tool and return observation summary."""
    client = DatadogClient()

    try:
        if name == "fetch_logs":
            now = datetime.now(UTC)
            start = now - timedelta(minutes=params.get("time_range_minutes", 60))
            raw = await client.call(
                client.search_logs,
                query=params.get("query", "*"),
                filter_from=start,
                filter_to=now,
                limit=params.get("limit", 50),
                sort="-timestamp",
            )
            data = raw if isinstance(raw, dict) else {}
            logs = data.get("data", [])
            count = len(logs)
            errors = [
                lg for lg in logs
                if lg.get("attributes", {}).get("status", "").lower()
                in ("error", "critical", "fatal")
            ]
            sample = errors[:3] if errors else logs[:3]
            return f"Found {count} logs, {len(errors)} errors. Sample: {sample}"

        if name == "fetch_spans":
            now = datetime.now(UTC)
            start = now - timedelta(minutes=params.get("time_range_minutes", 60))
            raw = await client.call(
                client.list_spans,
                query=params.get("query", "*"),
                filter_from=start,
                filter_to=now,
                limit=params.get("limit", 20),
                sort="-@duration",
            )
            data = raw if isinstance(raw, dict) else {}
            spans = data.get("data", [])
            count = len(spans)
            slow = sorted(
                spans,
                key=lambda s: s.get("attributes", {}).get("duration", 0),
                reverse=True,
            )[:3]
            slow_info = [
                {
                    "service": s.get("attributes", {}).get("service"),
                    "duration_ms": s.get("attributes", {}).get("duration", 0) / 1e6,
                }
                for s in slow
            ]
            return f"Found {count} spans. Slowest: {slow_info}"

        if name == "fetch_metrics":
            now_ts = int(datetime.now(UTC).timestamp())
            start_ts = int(
                (datetime.now(UTC) - timedelta(
                    minutes=params.get("time_range_minutes", 60)
                )).timestamp()
            )
            raw = await client.call(
                client.query_metrics,
                query=params.get("query", ""),
                from_ts=start_ts,
                to_ts=now_ts,
            )
            data = raw if isinstance(raw, dict) else {}
            series = data.get("series", [])
            metrics_list = [s.get("metric") for s in series[:5]]
            return f"Found {len(series)} metric series: {metrics_list}"

        if name == "fetch_monitors":
            state = params.get("state")
            tags = params.get("tags", "")
            query_parts = []
            if state:
                query_parts.append(f"state:{state.lower()}")
            if tags:
                query_parts.append(tags)
            query = " ".join(query_parts) if query_parts else ""
            raw = await client.call(client.list_monitors, tags=query)
            monitors = raw if isinstance(raw, list) else []
            alerting = [m for m in monitors if m.get("overall_state") in ("Alert", "Warn")]
            names = [m.get("name") for m in alerting[:5]]
            return f"Found {len(monitors)} monitors, {len(alerting)} alerting: {names}"

        if name == "fetch_events":
            start = int(
                (datetime.now(UTC) - timedelta(
                    minutes=params.get("time_range_minutes", 60)
                )).timestamp()
            )
            end = int(datetime.now(UTC).timestamp())
            raw = await client.call(
                client.events.list_events,
                start=start,
                end=end,
                tags=params.get("query", ""),
            )
            data = raw.to_dict() if hasattr(raw, "to_dict") else (
                raw if isinstance(raw, dict) else {}
            )
            events = data.get("events", [])
            titles = [e.get("title") for e in events[:5]]
            return f"Found {len(events)} events: {titles}"

        if name == "search_incidents":
            raw = await client.call(
                client.incidents.list_incidents,
                filter_query=params.get("query", "")
            )
            data = raw if isinstance(raw, dict) else {}
            incidents = data.get("data", [])
            titles = [i.get("attributes", {}).get("title") for i in incidents[:5]]
            return f"Found {len(incidents)} incidents: {titles}"

        if name == "get_incident":
            raw = await client.call(
                client.incidents.get_incident,
                incident_id=params["incident_id"]
            )
            data = raw if isinstance(raw, dict) else {}
            inc = data.get("data", {})
            title = inc.get("attributes", {}).get("title", "N/A")
            return f"Incident {params['incident_id']}: {title}"

        return f"Unknown tool: {name}"
    except Exception as exc:
        logger.warning("[datadog_kit] Tool %s failed: %s", name, exc)
        return f"Tool {name} failed: {exc}"


def _build_context_summary(result: InvestigationResult) -> str:
    """Build compact context summary."""
    error_count = len([
        lg for lg in result.logs.logs
        if lg.status.lower() in ("error", "critical", "fatal")
    ])
    alert_count = len([
        m for m in result.monitors.monitors
        if m.overall_state in ("Alert", "Warn")
    ])
    return "\n".join([
        f"Query: {result.query}",
        f"Time range: {result.time_range_minutes}min",
        f"Logs: {result.logs.total} ({error_count} errors)",
        f"Monitors: {result.monitors.total} ({alert_count} alerting)",
        f"Spans: {result.spans.total}",
        f"Metrics series: {result.metrics.total}",
        f"Events: {result.events.total}",
    ])


async def _build_runbook(diagnosis: Any, incident_ids: list[str]) -> Runbook:
    """Generate runbook from diagnosis."""
    return Runbook(
        title=f"Runbook: {diagnosis.root_cause[:80]}",
        detection=["Monitor alerts for similar patterns", "Check log error rates"],
        diagnosis=diagnosis.causal_chain,
        mitigation=diagnosis.remediation_steps,
        prevention=["Add synthetic monitoring", "Improve log correlation"],
        references=incident_ids,
    )


async def _build_mttr_breakdown(incident_id: str | None) -> MttrBreakdown | None:
    """Fetch incident and build MTTR breakdown."""
    if not incident_id:
        return None
    client = DatadogClient()
    try:
        raw = await client.call(client.incidents.get_incident, incident_id=incident_id)
        data = raw if isinstance(raw, dict) else {}
        inc = data.get("data", {})
        attrs = inc.get("attributes", {})

        def parse_ts(ts: str | None) -> datetime | None:
            if not ts:
                return None
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                return None

        mttr = MttrBreakdown(
            detected_at=parse_ts(attrs.get("detected")) or datetime.now(UTC),
            triaged_at=parse_ts(attrs.get("triaged")),
            diagnosed_at=parse_ts(attrs.get("diagnosed")),
            mitigated_at=parse_ts(attrs.get("mitigated")),
            resolved_at=parse_ts(attrs.get("resolved")),
        )
        return mttr.compute()
    except Exception as exc:
        logger.warning("[datadog_kit] MTTR build failed: %s", exc)
        return None


async def investigate_react(request: InvestigationRequestV3) -> InvestigationResult:
    """Run ReAct investigation loop."""
    config = DatadogKitConfig(default_time_range_minutes=request.time_range_minutes)

    # Initial fetch
    base_request = InvestigationRequest(
        query=request.query,
        tags=request.tags,
        time_range_minutes=request.time_range_minutes,
        incident_id=request.incident_id,
    )
    context = await fetch_all(base_request, config)

    trace: list[ReActTurn] = []

    for _turn in range(1, request.max_turns + 1):
        context_summary = _build_context_summary(context)
        msg = f"Investigation: {request.query}\nData:\n{context_summary}"
        messages = [
            {"role": "system", "content": _REACT_SYSTEM_PROMPT},
            {"role": "user", "content": msg},
        ]

        for t in trace:
            messages.append({"role": "assistant", "content": json.dumps({
                "thought": t.thought,
                "action": t.action,
                "action_input": t.action_input,
                "final_answer": False,
            })})
            messages.append({"role": "user", "content": t.observation})

        if not settings.OPENAI_API_KEY:
            break

        # Call LLM for next action
        try:
            prompt_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
            raw = await _call_openai(prompt_text)
            action_data = json.loads(raw)
        except Exception as exc:
            logger.warning("[datadog_kit] ReAct LLM call failed: %s", exc)
            break

        thought = action_data.get("thought", "")
        action = action_data.get("action", "")
        action_input = action_data.get("action_input", {})
        final_answer = action_data.get("final_answer", False)

        if final_answer or action == "conclude":
            # Parse diagnosis from action_input
            diag_data = action_data.get("diagnosis", action_input)
            diagnosis = _parse_rca_response(json.dumps(diag_data))
            break

        # Execute tool
        observation = await _execute_tool(action, action_input)

        trace.append(ReActTurn(
            turn=_turn,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
        ))
    else:
        # Max turns reached without conclusion
        diagnosis = _parse_rca_response(json.dumps({
            "root_cause": "Max turns reached without conclusion",
            "root_cause_category": "dependency",
            "causal_chain": [t.thought for t in trace],
            "severity": "P3",
            "confidence": 0.3,
            "evidence_refs": {},
            "remediation_steps": ["Re-run with more turns or manual investigation"],
            "inconclusive": True,
        }))

    # Build enhanced result
    runbook = None
    if request.generate_runbook and not diagnosis.inconclusive:
        incident_ids = [request.incident_id] if request.incident_id else []
        runbook = await _build_runbook(diagnosis, incident_ids)

    mttr = await _build_mttr_breakdown(request.incident_id)

    return InvestigationResult(
        query=request.query,
        time_range_minutes=request.time_range_minutes,
        logs=context.logs,
        events=context.events,
        monitors=context.monitors,
        metrics=context.metrics,
        spans=context.spans,
        total_duration_ms=context.total_duration_ms,
        react_trace=trace,
        runbook=runbook,
        mttr_breakdown=mttr,
        diagnosis=diagnosis,
    )
