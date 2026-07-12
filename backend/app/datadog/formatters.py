"""Human-readable formatters for Datadog API responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import Response

if TYPE_CHECKING:
    from collections.abc import Callable


def maybe_human(
    data: Any,
    fmt_func: Callable[[list[dict[str, Any]], dict[str, Any] | None], str],
    format: bool = False,
    meta: dict[str, Any] | None = None,
) -> Any:
    """Return human-readable text if format=True, else pass-through for JSON."""
    if format:
        items = _to_list(data)
        return Response(content=fmt_func(items, meta), media_type="text/plain")
    return data


def _to_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        inner = data.get("data", data)
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict):
            return [inner]
    return []


def fmt_items(data: Any) -> list[dict[str, Any]]:
    """Normalize response data to a list of items."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        inner = data.get("data", data)
        if isinstance(inner, list):
            return inner
        return [inner]
    return []


def fmt_monitors(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== Monitors ==="]
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, mon in enumerate(data[:25]):
        name = mon.get("name", "Unnamed")
        mid = mon.get("id", "?")
        state = mon.get("overall_state", "unknown")
        lines.append(f"[{i + 1}] [{mid}] [{state.upper()}] {name}")
        if tags := ", ".join(mon.get("tags", [])):
            lines.append(f"     Tags: {tags}")
    if len(data) > 25:
        lines.append(f"... +{len(data) - 25} more")
    return "\n".join(lines)


def fmt_logs(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== Logs ==="]
    lines.append(f"Query: {m.get('query', '?')}")
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, log in enumerate(data[:50]):
        attr = log.get("attributes", log.get("_source", log))
        ts = attr.get("@timestamp", attr.get("timestamp", "?"))
        svc = attr.get("service", "?")
        host = attr.get("host", "")
        msg = str(attr.get("message", attr.get("msg", "")))[:200]
        lines.append(f"[{i + 1}] [{ts}] [{svc}] {host}: {msg}")
    if len(data) > 50:
        lines.append(f"... +{len(data) - 50} more")
    return "\n".join(lines)


def fmt_incidents(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== Incidents ==="]
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, inc in enumerate(data[:25]):
        attr = inc.get("attributes", inc)
        title = attr.get("title", "Untitled")
        iid = inc.get("id", inc.get("incident_id", "?"))
        sev = attr.get("severity", "unknown")
        state = attr.get("state", "open")
        lines.append(f"[{i + 1}] [{iid}] [{sev}] [{state}] {title}")
    if len(data) > 25:
        lines.append(f"... +{len(data) - 25} more")
    return "\n".join(lines)


def fmt_metrics(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== Metrics ==="]
    if query := m.get("query"):
        lines.append(f"Query: {query}")
    points = data.get("series", []) if isinstance(data, dict) else data
    for i, ser in enumerate(points[:20]):
        metric = ser.get("metric", "?")
        scope = ser.get("scope", ser.get("tag_set", ""))
        plen = len(ser.get("pointlist", ser.get("points", [])))
        lines.append(f"[{i + 1}] {metric}")
        lines.append(f"     Scope: {scope}  |  Points: {plen}")
    if len(points) > 20:
        lines.append(f"... +{len(points) - 20} more")
    return "\n".join(lines)


def fmt_spans(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== APM Spans ==="]
    lines.append(f"Query: {m.get('query', '?')}")
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, span in enumerate(data[:25]):
        attr = span.get("attributes", span.get("_source", span))
        svc = attr.get("service", "?")
        op = attr.get("name", attr.get("resource", "?"))
        dur = attr.get("duration", attr.get("duration_nano", 0))
        if isinstance(dur, (int, float)) and dur > 1e6:
            dur = f"{dur / 1e6:.2f}ms"
        else:
            dur = f"{dur}ns"
        lines.append(f"[{i + 1}] [{svc}] {op} ({dur})")
    if len(data) > 25:
        lines.append(f"... +{len(data) - 25} more")
    return "\n".join(lines)


def fmt_synthetics(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== Synthetics Tests ==="]
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, test in enumerate(data[:25]):
        name = test.get("name", "Unnamed")
        pid = test.get("public_id", test.get("id", "?"))
        status = test.get("status", "?")
        ttype = test.get("type", "?")
        lines.append(f"[{i + 1}] [{pid}] [{status}] {name}")
        lines.append(f"     Type: {ttype}")
    if len(data) > 25:
        lines.append(f"... +{len(data) - 25} more")
    return "\n".join(lines)


def fmt_fleet(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== Fleet Agents ==="]
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, agent in enumerate(data[:25]):
        a = agent.get("attributes", agent)
        host = a.get("hostname", a.get("name", "?"))
        aid = agent.get("id", "?")
        status = a.get("status", "?")
        ver = a.get("agent_version", "?")
        lines.append(f"[{i + 1}] [{aid}] [{status}] {host}  v{ver}")
    if len(data) > 25:
        lines.append(f"... +{len(data) - 25} more")
    return "\n".join(lines)


def fmt_slos(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== SLOs ==="]
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, slo in enumerate(data[:25]):
        attr = slo.get("attributes", slo)
        name = attr.get("name", "Unnamed")
        sid = slo.get("id", "?")
        target = attr.get("target", attr.get("sli_target", "?"))
        lines.append(f"[{i + 1}] [{sid}] {name}  (target: {target})")
    if len(data) > 25:
        lines.append(f"... +{len(data) - 25} more")
    return "\n".join(lines)


def fmt_events(data: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    m = meta or {}
    lines = ["=== Events ==="]
    lines.append(f"Total: {m.get('total', len(data))}")
    for i, ev in enumerate(data[:25]):
        title = ev.get("title", ev.get("text", ""))
        eid = ev.get("id", "?")
        at = ev.get("alert_type", "?")
        ev.get("date_happened", ev.get("timestamp", "?"))
        lines.append(f"[{i + 1}] [{eid}] [{at}] {title}")
    if len(data) > 25:
        lines.append(f"... +{len(data) - 25} more")
    return "\n".join(lines)
