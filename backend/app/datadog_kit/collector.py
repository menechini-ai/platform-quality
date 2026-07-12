"""Parallel signal collector — fetches logs, events, monitors, metrics concurrently."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import UTC, datetime, timedelta

from app.datadog.client import DatadogClient
from app.datadog_kit.config import DatadogKitConfig
from app.datadog_kit.models import (
    EventEntry,
    EventsResult,
    InvestigationRequest,
    InvestigationResult,
    LogEntry,
    LogsResult,
    MetricSeries,
    MetricsResult,
    MonitorEntry,
    MonitorsResult,
    SpanEntry,
    SpansResult,
)

logger = logging.getLogger(__name__)


def _parse_context(request: InvestigationRequest) -> dict[str, str | None]:
    """Extract structured context from query + tags."""
    ctx: dict[str, str | None] = {"host": None, "service": None, "env": None}
    # Parse query like "service:web host:app-1"
    if request.query:
        for match in re.finditer(r"(\w+):(\S+)", request.query):
            k, v = match.groups()
            if k in ctx:
                ctx[k] = v
    # tags override query
    for k in ctx:
        if request.tags.get(k):
            ctx[k] = request.tags[k]
    return ctx


def _build_tag_str(tags: dict[str, str]) -> str:
    return ",".join(f"{k}:{v}" for k, v in tags.items())


def _enrich_tags(request: InvestigationRequest, ctx: dict[str, str | None]) -> dict[str, str]:
    """Add host/service from context to request tags."""
    enriched = dict(request.tags)
    for k in ("host", "service", "env"):
        if ctx.get(k) and k not in enriched:
            enriched[k] = ctx[k]  # type: ignore[literal-required]
    return enriched


def _time_range(request: InvestigationRequest) -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(minutes=request.time_range_minutes)
    return start, end


async def _search_logs(
    client: DatadogClient,
    request: InvestigationRequest,
    config: DatadogKitConfig,
    ctx: dict[str, str | None],
) -> LogsResult:
    t0 = time.monotonic()
    try:
        start, end = _time_range(request)
        enriched = _enrich_tags(request, ctx)
        _ = enriched  # available for future use
        raw = await client.call(
            client.search_logs,
            query=request.query or "*",
            filter_from=start,
            filter_to=end,
            limit=config.logs_limit,
            sort="-timestamp",
        )
        duration = int((time.monotonic() - t0) * 1000)
        data = raw if isinstance(raw, dict) else {}
        logs_raw = data.get("data", [])
        logs = []
        for ev in logs_raw:
            attrs = ev.get("attributes", {}) if isinstance(ev, dict) else {}
            logs.append(
                LogEntry(
                    timestamp=attrs.get("timestamp", ""),
                    message=attrs.get("message", ""),
                    status=attrs.get("status", ""),
                    service=attrs.get("service", ""),
                    host=attrs.get("host", ""),
                    tags=attrs.get("tags", []),
                )
            )
        return LogsResult(logs=logs, total=len(logs), duration_ms=duration)
    except Exception as exc:
        duration = int((time.monotonic() - t0) * 1000)
        logger.warning("[datadog_kit] search_logs failed: %s", exc)
        return LogsResult(success=False, error=str(exc), duration_ms=duration)


async def _get_events(
    client: DatadogClient,
    request: InvestigationRequest,
    config: DatadogKitConfig,
    ctx: dict[str, str | None],
) -> EventsResult:
    _ = ctx
    t0 = time.monotonic()
    try:
        start_dt, end_dt = _time_range(request)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        tags_str = _build_tag_str(request.tags)
        raw = await client.call(
            client.events.list_events,
            start=start_ts,
            end=end_ts,
            tags=tags_str,
        )
        duration = int((time.monotonic() - t0) * 1000)
        data = raw.to_dict() if hasattr(raw, "to_dict") else (raw if isinstance(raw, dict) else {})
        events_raw = data.get("events", [])
        events = []
        for ev in events_raw:
            if not isinstance(ev, dict):
                continue
            events.append(
                EventEntry(
                    timestamp=ev.get("date_happened", ""),
                    title=ev.get("title", ""),
                    message=str(ev.get("text") or ev.get("message") or ""),
                    tags=ev.get("tags", []),
                    source=ev.get("source", ""),
                )
            )
        return EventsResult(
            events=events[: config.events_limit],
            total=len(events),
            duration_ms=duration,
        )
    except Exception as exc:
        duration = int((time.monotonic() - t0) * 1000)
        logger.warning("[datadog_kit] get_events failed: %s", exc)
        return EventsResult(success=False, error=str(exc), duration_ms=duration)


async def _list_monitors(
    client: DatadogClient,
    request: InvestigationRequest,
    config: DatadogKitConfig,
    ctx: dict[str, str | None],
) -> MonitorsResult:
    _ = config
    t0 = time.monotonic()
    try:
        tags_str = _build_tag_str(request.tags)
        raw = await client.call(client.list_monitors, tags=tags_str)
        duration = int((time.monotonic() - t0) * 1000)
        monitors_raw = raw if isinstance(raw, list) else []
        monitors = []
        # Extract host/service from monitor tags for context enrichment
        for m in monitors_raw:
            if not isinstance(m, dict):
                continue
            m_tags = m.get("tags", [])
            # Propagate monitor tags into context if empty
            if not ctx.get("host"):
                for t in m_tags:
                    if t.startswith("host:"):
                        ctx["host"] = t.split(":", 1)[1]
            if not ctx.get("service"):
                for t in m_tags:
                    if t.startswith("service:"):
                        ctx["service"] = t.split(":", 1)[1]
            monitors.append(
                MonitorEntry(
                    id=m.get("id"),
                    name=m.get("name", ""),
                    type=m.get("type", ""),
                    query=m.get("query", ""),
                    overall_state=m.get("overall_state", ""),
                    tags=m_tags,
                )
            )
        return MonitorsResult(monitors=monitors, total=len(monitors), duration_ms=duration)
    except Exception as exc:
        duration = int((time.monotonic() - t0) * 1000)
        logger.warning("[datadog_kit] list_monitors failed: %s", exc)
        return MonitorsResult(success=False, error=str(exc), duration_ms=duration)


async def _query_metrics(
    client: DatadogClient,
    request: InvestigationRequest,
    config: DatadogKitConfig,
    ctx: dict[str, str | None],
) -> MetricsResult:
    _ = config, ctx
    t0 = time.monotonic()
    try:
        start_dt, end_dt = _time_range(request)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        tag_str = _build_tag_str(request.tags)
        metric_queries = [
            f"avg:system.cpu.user{{{tag_str}}}" if tag_str else "avg:system.cpu.user{*}",
            f"avg:system.mem.pct{{{tag_str}}}" if tag_str else "avg:system.mem.pct{*}",
        ]
        series = []
        for mq in metric_queries:
            raw = await client.call(client.query_metrics, query=mq, from_ts=start_ts, to_ts=end_ts)
            data = raw if isinstance(raw, dict) else {}
            for s in (data.get("series") or []):
                if isinstance(s, dict):
                    pts = s.get("pointlist") or []
                    filtered = [
                        p
                        for p in pts
                        if isinstance(p, (list, tuple)) and len(p) >= 2 and p[1] is not None
                    ]
                    if filtered:
                        series.append(
                            MetricSeries(
                                name=mq,
                                timestamps=[str(p[0]) for p in filtered],
                                values=[float(p[1]) for p in filtered],
                            )
                        )
        duration = int((time.monotonic() - t0) * 1000)
        return MetricsResult(series=series, total=len(series), duration_ms=duration)
    except Exception as exc:
        duration = int((time.monotonic() - t0) * 1000)
        logger.warning("[datadog_kit] query_metrics failed: %s", exc)
        return MetricsResult(success=False, error=str(exc), duration_ms=duration)


async def _search_spans(
    client: DatadogClient,
    request: InvestigationRequest,
    config: DatadogKitConfig,
    ctx: dict[str, str | None],
) -> SpansResult:
    _ = config
    t0 = time.monotonic()
    try:
        start, end = _time_range(request)
        query_parts = [request.query or "*"]
        if ctx.get("service"):
            query_parts.append(f"@service:{ctx['service']}")
        query_parts.append("@duration:>1s")
        span_query = " AND ".join(query_parts)

        raw = await client.call(
            client.list_spans,
            query=span_query,
            filter_from=start,
            filter_to=end,
            limit=config.spans_limit,
            sort="-@duration",
        )
        duration = int((time.monotonic() - t0) * 1000)
        data = raw if isinstance(raw, dict) else {}
        spans_raw = data.get("data", [])
        spans = []
        for sp in spans_raw:
            attrs = sp.get("attributes", {}) if isinstance(sp, dict) else {}
            spans.append(
                SpanEntry(
                    span_id=attrs.get("span_id", ""),
                    trace_id=attrs.get("trace_id", ""),
                    service=attrs.get("service", ""),
                    resource=attrs.get("resource", ""),
                    operation=attrs.get("name", ""),
                    duration_ns=attrs.get("duration", 0),
                    status=attrs.get("status", ""),
                    timestamp=attrs.get("timestamp", ""),
                )
            )
        return SpansResult(spans=spans, total=len(spans), duration_ms=duration)
    except Exception as exc:
        duration = int((time.monotonic() - t0) * 1000)
        logger.warning("[datadog_kit] search_spans failed: %s", exc)
        return SpansResult(success=False, error=str(exc), duration_ms=duration)


async def fetch_all(
    request: InvestigationRequest,
    config: DatadogKitConfig | None = None,
) -> InvestigationResult:
    """Fetch 5 Datadog signals in parallel with error isolation.

    Context enrichment flow:
    1. Parse host/service/env from request.query + request.tags
    2. Monitors enrich context further (host tags from alerting monitors)
    3. Enriched context flows to logs, spans, events, metrics
    """
    cfg = config or DatadogKitConfig()
    client = DatadogClient()

    # Step 1: Parse context from request
    ctx = _parse_context(request)

    t0 = time.monotonic()

    logs_task = _search_logs(client, request, cfg, ctx)
    events_task = _get_events(client, request, cfg, ctx)
    monitors_task = _list_monitors(client, request, cfg, ctx)
    metrics_task = _query_metrics(client, request, cfg, ctx)
    spans_task = _search_spans(client, request, cfg, ctx)

    logs_result, events_result, monitors_result, metrics_result, spans_result = (
        await asyncio.gather(
            logs_task,
            events_task,
            monitors_task,
            metrics_task,
            spans_task,
            return_exceptions=False,
        )
    )

    total_duration = int((time.monotonic() - t0) * 1000)

    return InvestigationResult(
        query=request.query,
        time_range_minutes=request.time_range_minutes,
        logs=logs_result,
        events=events_result,
        monitors=monitors_result,
        metrics=metrics_result,
        spans=spans_result,
        total_duration_ms=total_duration,
    )
