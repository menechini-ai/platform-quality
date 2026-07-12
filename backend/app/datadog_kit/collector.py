"""Parallel signal collector — fetches logs, events, monitors, metrics concurrently."""

from __future__ import annotations

import asyncio
import logging
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
)

logger = logging.getLogger(__name__)


def _time_range(request: InvestigationRequest) -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(minutes=request.time_range_minutes)
    return start, end


async def _search_logs(
    client: DatadogClient,
    request: InvestigationRequest,
    config: DatadogKitConfig,
) -> LogsResult:
    t0 = time.monotonic()
    try:
        start, end = _time_range(request)
        raw = await client.call(
            client.search_logs,
            query=request.query,
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
) -> EventsResult:
    t0 = time.monotonic()
    try:
        start_dt, end_dt = _time_range(request)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        tags_str = ",".join(f"{k}:{v}" for k, v in request.tags.items())
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
) -> MonitorsResult:
    _ = config
    t0 = time.monotonic()
    try:
        tags_str = ",".join(f"{k}:{v}" for k, v in request.tags.items())
        raw = await client.call(client.list_monitors, tags=tags_str)
        duration = int((time.monotonic() - t0) * 1000)
        monitors_raw = raw if isinstance(raw, list) else []
        monitors = []
        for m in monitors_raw:
            if not isinstance(m, dict):
                continue
            monitors.append(
                MonitorEntry(
                    id=m.get("id"),
                    name=m.get("name", ""),
                    type=m.get("type", ""),
                    query=m.get("query", ""),
                    overall_state=m.get("overall_state", ""),
                    tags=m.get("tags", []),
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
) -> MetricsResult:
    _ = config
    t0 = time.monotonic()
    try:
        start_dt, end_dt = _time_range(request)
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        metric_queries = [
            f"avg:system.cpu.user{{{','.join(f'{k}:{v}' for k, v in request.tags.items())}}}",
            f"avg:system.mem.pct{{{','.join(f'{k}:{v}' for k, v in request.tags.items())}}}",
        ]
        series = []
        for mq in metric_queries:
            raw = await client.call(client.query_metrics, query=mq, from_ts=start_ts, to_ts=end_ts)
            data = raw if isinstance(raw, dict) else {}
            points = []
            for s in (data.get("series") or []):
                if isinstance(s, dict):
                    pts = s.get("pointlist") or []
                    for p in pts:
                        if isinstance(p, (list, tuple)) and len(p) >= 2 and p[1] is not None:
                            points.append(p)
            if points:
                series.append(
                    MetricSeries(
                        name=mq,
                        timestamps=[str(p[0]) for p in points],
                        values=[float(p[1]) for p in points],
                    )
                )
        duration = int((time.monotonic() - t0) * 1000)
        return MetricsResult(series=series, total=len(series), duration_ms=duration)
    except Exception as exc:
        duration = int((time.monotonic() - t0) * 1000)
        logger.warning("[datadog_kit] query_metrics failed: %s", exc)
        return MetricsResult(success=False, error=str(exc), duration_ms=duration)


async def fetch_all(
    request: InvestigationRequest,
    config: DatadogKitConfig | None = None,
) -> InvestigationResult:
    """Fetch 4 Datadog signals in parallel.

    Error isolation: each signal runs independently. A single failure
    populates that signal's result with ``success=False`` and an error message,
    without affecting the other three.
    """
    cfg = config or DatadogKitConfig()
    client = DatadogClient()

    t0 = time.monotonic()

    logs_task = _search_logs(client, request, cfg)
    events_task = _get_events(client, request, cfg)
    monitors_task = _list_monitors(client, request, cfg)
    metrics_task = _query_metrics(client, request, cfg)

    logs_result, events_result, monitors_result, metrics_result = await asyncio.gather(
        logs_task,
        events_task,
        monitors_task,
        metrics_task,
        return_exceptions=False,
    )

    total_duration = int((time.monotonic() - t0) * 1000)

    return InvestigationResult(
        query=request.query,
        time_range_minutes=request.time_range_minutes,
        logs=logs_result,
        events=events_result,
        monitors=monitors_result,
        metrics=metrics_result,
        total_duration_ms=total_duration,
    )
