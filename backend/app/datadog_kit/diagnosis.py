"""LLM-powered RCA diagnosis from collected investigation data."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.datadog_kit.models import (
    InvestigationResult,
    RcaDiagnosis,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_DEFAULT_PROMPT_TEMPLATE = """You are an SRE root cause analysis engine.

Analyze the following Datadog investigation data and produce a structured RCA.

## Investigation Query
{query}
Time range: {time_range_minutes} minutes

## Error Logs
{logs_summary}

## Events (deployments, changes, alerts)
{events_summary}

## Monitors in Alert
{monitors_summary}

## Metrics (anomalies)
{metrics_summary}

Respond ONLY with a JSON object using these exact keys:
- "root_cause": short description of the root cause
- "root_cause_category": one of "deploy", "resource", "latency", "dependency", "data_corruption"
- "causal_chain": list of events leading to the incident (oldest first)
- "severity": "P1", "P2", or "P3"
- "confidence": float 0.0-1.0
- "evidence_refs": dict with keys "logs", "events", "monitors", "metrics"
- "remediation_steps": list of actionable steps
- "inconclusive": true if confidence < 0.5 or no clear root cause

Be precise. If there's not enough evidence, set inconclusive=true and explain why in root_cause.
"""


def _summarize_logs(result: InvestigationResult) -> str:
    logs = result.logs.logs
    if not logs:
        return "No logs captured."
    errors = [log for log in logs if log.status.lower() in ("error", "critical", "fatal")]
    if errors:
        lines = [
            f"[{e.timestamp}] {e.service} | {e.status} | {e.message[:200]}"
            for e in errors[:15]
        ]
        return f"{len(errors)} error logs (showing {len(lines)}):\n" + "\n".join(lines)
    return f"{len(logs)} logs captured, no errors detected."


def _summarize_events(result: InvestigationResult) -> str:
    events = result.events.events
    if not events:
        return "No events captured."
    lines = [f"[{e.timestamp}] {e.title} ({e.source})" for e in events[:10]]
    return "\n".join(lines)


def _summarize_monitors(result: InvestigationResult) -> str:
    monitors = result.monitors.monitors
    if not monitors:
        return "No monitors captured."
    alerting = [m for m in monitors if m.overall_state in ("Alert", "Warn")]
    if alerting:
        lines = [f"  {m.name} ({m.overall_state})" for m in alerting[:10]]
        return f"{len(alerting)} monitors in alert/warning state:\n" + "\n".join(lines)
    return f"{len(monitors)} monitors checked, all OK."


def _summarize_metrics(result: InvestigationResult) -> str:
    series_list = result.metrics.series
    if not series_list:
        return "No metric data captured."
    lines = []
    for s in series_list:
        if s.values:
            avg = sum(s.values) / len(s.values)
            peak = max(s.values)
            lines.append(f"  {s.name}: avg={avg:.2f}, peak={peak:.2f}")
    return "\n".join(lines) if lines else "No metric anomalies detected."


def build_prompt(result: InvestigationResult) -> str:
    """Build the LLM prompt from investigation data."""
    return _DEFAULT_PROMPT_TEMPLATE.format(
        query=result.query,
        time_range_minutes=result.time_range_minutes,
        logs_summary=_summarize_logs(result),
        events_summary=_summarize_events(result),
        monitors_summary=_summarize_monitors(result),
        metrics_summary=_summarize_metrics(result),
    )


def _parse_rca_response(raw: str) -> RcaDiagnosis:
    """Parse LLM JSON response into RcaDiagnosis."""
    # Try to extract JSON block
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    data: dict[str, Any] = json.loads(text)

    return RcaDiagnosis(
        root_cause=data.get("root_cause", "unknown"),
        root_cause_category=data.get("root_cause_category", "resource"),
        causal_chain=data.get("causal_chain", []),
        severity=data.get("severity", "P3"),
        confidence=float(data.get("confidence", 0.0)),
        evidence_refs=data.get("evidence_refs", {}),
        remediation_steps=data.get("remediation_steps", []),
        inconclusive=bool(data.get("inconclusive", False)),
    )


async def analyze(
    result: InvestigationResult,
    llm_call: Callable[..., Any] | None = None,
) -> RcaDiagnosis:
    """Run RCA diagnosis on investigation data.

    Args:
        result: The investigation data from ``fetch_all``.
        llm_call: Optional async callable that accepts a prompt string
            and returns a JSON string. If omitted, returns a basic
            diagnosis from summary heuristics.

    Returns:
        A structured RCA diagnosis.
    """
    if llm_call is None:
        return _fallback_diagnosis(result)

    prompt = build_prompt(result)
    try:
        raw = await llm_call(prompt)
        return _parse_rca_response(raw)
    except Exception as exc:
        logger.warning("[datadog_kit] LLM diagnosis failed: %s", exc)
        return _fallback_diagnosis(result)


def _fallback_diagnosis(result: InvestigationResult) -> RcaDiagnosis:
    """Heuristic fallback when LLM is unavailable."""
    error_count = len(result.logs.logs)
    alerts_count = len(
        [m for m in result.monitors.monitors if m.overall_state in ("Alert", "Warn")]
    )
    event_count = len(result.events.events)

    if error_count == 0 and alerts_count == 0:
        return RcaDiagnosis(
            root_cause="No anomalies detected in collected signals",
            root_cause_category="resource",
            causal_chain=[],
            severity="P3",
            confidence=0.0,
            inconclusive=True,
        )

    return RcaDiagnosis(
        root_cause=(
            f"{error_count} error logs, {alerts_count} monitors alerting,"
            f" {event_count} events"
        ),
        root_cause_category="resource",
        causal_chain=[],
        severity="P2" if alerts_count > 0 else "P3",
        confidence=0.3,
        inconclusive=True,
    )
