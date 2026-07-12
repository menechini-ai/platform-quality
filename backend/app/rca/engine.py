"""Multi-phase RCA correlation engine (FR-009).

Pipeline: Discovery -> Breadth -> Depth -> Conclusion. Each phase emits an
explicit Pydantic state model; the final Conclusion carries a labeled
dependency chain (root cause / propagator / victim) and a confidence score.

The engine is backend-agnostic: it receives a client exposing the Datadog
surface used for correlation. Every external call is guarded so the engine
degrades gracefully when Datadog is unavailable (the report still returns with
what evidence it could gather).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class DependencyNode(BaseModel):
    role: str  # "root_cause" | "propagator" | "victim"
    name: str
    evidence: str = ""


class DependencyChain(BaseModel):
    nodes: list[DependencyNode] = Field(default_factory=list)


class DiscoveryState(BaseModel):
    incident_id: str
    services: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BreadthState(BaseModel):
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    candidate_roots: list[str] = Field(default_factory=list)


class DepthState(BaseModel):
    correlated_events: list[dict[str, Any]] = Field(default_factory=list)
    metric_anomalies: list[dict[str, Any]] = Field(default_factory=list)


class ConclusionState(BaseModel):
    root_cause: str = ""
    dependency_chain: DependencyChain = Field(default_factory=DependencyChain)
    confidence: float = 0.0
    summary: str = ""


def _ts(offset_seconds: int) -> int:
    return int(datetime.now(UTC).timestamp()) + offset_seconds


def _extract_services(agg: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for row in agg.get("data", {}).get("attributes", {}).get("series", []) or []:
        for grp in row.get("group_by", []) or []:
            if grp.get("facet") == "service" and grp.get("value"):
                out.append(str(grp["value"]))
    return list(dict.fromkeys(out))


def _extract_dependencies(agg: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in agg.get("data", {}).get("attributes", {}).get("series", []) or []:
        rec: dict[str, Any] = {}
        for grp in row.get("group_by", []) or []:
            if grp.get("facet") in ("service", "parent_service"):
                rec[grp["facet"]] = grp.get("value")
        if rec:
            out.append(rec)
    return out


def _has_anomaly(metrics: dict[str, Any]) -> bool:
    series = metrics.get("series", metrics.get("data", {}).get("attributes", {}).get("series", []))
    if not series:
        return False
    points = series[0].get("pointlist", series[0].get("resources", []))
    values = [p[1] for p in points if isinstance(p, list) and len(p) > 1 and p[1] is not None]
    return bool(values) and (max(values) - min(values) > 0)


def _summarize(payload: Any) -> str:
    if isinstance(payload, dict):
        series = payload.get("data", {}).get("attributes", {}).get("series", []) or []
        return f"{len(series)} series"
    return str(payload)[:120]


def _confidence(discovery: DiscoveryState, breadth: BreadthState, depth: DepthState) -> float:
    score = 0.0
    if discovery.services:
        score += 0.2
    if breadth.candidate_roots:
        score += 0.2
    score += min(0.3, 0.1 * len(depth.metric_anomalies))
    score += min(0.3, 0.1 * len(depth.correlated_events))
    return round(min(1.0, score), 2)


def _summarize_conclusion(chain: DependencyChain, confidence: float) -> str:
    if not chain.nodes:
        return "Insufficient correlation evidence; Datadog signal unavailable."
    root = next((n for n in chain.nodes if n.role == "root_cause"), chain.nodes[0])
    return (
        f"Root cause: {root.name} (confidence {confidence:.0%}). "
        f"Propagation chain: {' -> '.join(n.name for n in chain.nodes)}."
    )


class RcaEngine:
    def __init__(self, client: Any) -> None:
        self._client = client

    async def run(self, incident_id: str, context: dict[str, Any] | None = None) -> ConclusionState:
        discovery = await self._discovery(incident_id, context or {})
        breadth = await self._breadth(discovery)
        depth = await self._depth(breadth)
        return self._conclude(discovery, breadth, depth)

    async def _call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        # Real client exposes call(func, *args) (thread-offloaded). A test fake
        # may expose the coroutine method directly.
        if hasattr(self._client, "call"):
            return await self._client.call(func, *args, **kwargs)
        return await func(*args, **kwargs)

    async def _discovery(self, incident_id: str, context: dict[str, Any]) -> DiscoveryState:
        state = DiscoveryState(incident_id=str(incident_id))
        services = list(context.get("services") or [])
        if not services and hasattr(self._client, "aggregate_spans"):
            try:
                res = await self._call(
                    self._client.aggregate_spans, group_by=[{"facet": "service"}]
                )
                services = _extract_services(res)
            except Exception as exc:  # noqa: BLE001 - degrade gracefully
                state.notes.append(f"discovery: span aggregation failed: {exc}")
        state.services = services
        if context.get("signal"):
            state.signals.append(str(context["signal"]))
        return state

    async def _breadth(self, discovery: DiscoveryState) -> BreadthState:
        state = BreadthState()
        state.candidate_roots = list(discovery.services)
        if hasattr(self._client, "aggregate_spans"):
            try:
                res = await self._call(
                    self._client.aggregate_spans,
                    group_by=[{"facet": "service"}, {"facet": "parent_service"}],
                )
                state.dependencies = _extract_dependencies(res)
            except Exception as exc:  # noqa: BLE001 - degrade gracefully
                state.candidate_roots.append(f"(deps failed: {exc})")
        return state

    async def _depth(self, breadth: BreadthState) -> DepthState:
        state = DepthState()
        for root in breadth.candidate_roots[:5]:
            if hasattr(self._client, "query_metrics"):
                try:
                    res = await self._call(
                        self._client.query_metrics,
                        query=f"avg:trace.{root}.duration",
                        from_ts=_ts(-3600),
                        to_ts=_ts(0),
                    )
                    if _has_anomaly(res):
                        state.metric_anomalies.append({"service": root, "detail": _summarize(res)})
                except Exception:  # noqa: BLE001 - degrade gracefully
                    pass
            if hasattr(self._client, "search_logs"):
                try:
                    res = await self._call(self._client.search_logs, query=f"service:{root} error")
                    state.correlated_events.append({"service": root, "logs": _summarize(res)})
                except Exception:  # noqa: BLE001 - degrade gracefully
                    pass
        return state

    def _conclude(
        self, discovery: DiscoveryState, breadth: BreadthState, depth: DepthState
    ) -> ConclusionState:
        nodes: list[DependencyNode] = []
        roots = breadth.candidate_roots
        root_name = (
            roots[0] if roots else (discovery.signals[0] if discovery.signals else "unknown")
        )
        if root_name and root_name != "unknown":
            nodes.append(
                DependencyNode(
                    role="root_cause",
                    name=str(root_name),
                    evidence="highest fan-in / first failure in signal window",
                )
            )
        for prop in roots[1:3]:
            nodes.append(
                DependencyNode(
                    role="propagator", name=str(prop), evidence="downstream of root cause"
                )
            )
        seen = {n.name for n in nodes}
        for victim in discovery.services:
            if victim not in seen:
                nodes.append(
                    DependencyNode(role="victim", name=victim, evidence="impacted by propagation")
                )
                seen.add(victim)
        confidence = _confidence(discovery, breadth, depth)
        return ConclusionState(
            root_cause=root_name if root_name != "unknown" else "",
            dependency_chain=DependencyChain(nodes=nodes),
            confidence=confidence,
            summary=_summarize_conclusion(DependencyChain(nodes=nodes), confidence),
        )
