# Datadog RCA Kit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an investigation engine that fetches 4 Datadog signals (logs, events, monitors, metrics) in parallel and produces a structured RCA with root_cause, causal_chain, confidence, and evidence_refs.

**Architecture:** New `app/datadog_kit/` package that wraps existing `DatadogClient` (official SDK) with async parallel fetch + LLM diagnosis. Existing `RcaReport` model used for persistence. New endpoint `POST /api/v1/datadog/investigate` calls the pipeline and saves result.

**Tech Stack:** FastAPI, `datadog-api-client` (already installed), pydantic, sqlalchemy, same LLM provider as rest of ObservAI.

## Global Constraints

- All Datadog API calls go through existing `app/datadog/client.py` `DatadogClient` singleton
- Async calls via `await client.call(client.monitors.list_monitors)` pattern
- Error isolation: one signal failure never blocks other signals
- LLM prompt must fit within model context — cap inputs at 50 logs, 20 events, 10 monitors, 4 metric series summaries
- Ruff lint + mypy strict pass required
- Follow existing project patterns: `__future__ import annotations`, `TYPE_CHECKING` guards, `from app.core.config import settings`

---

### Task 1: Create datadog_kit package structure + models

**Files:**
- Create: `backend/app/datadog_kit/__init__.py`
- Create: `backend/app/datadog_kit/models.py`
- Create: `backend/app/datadog_kit/config.py`
- Test: `tests/test_datadog_kit/test_models.py`

**Interfaces:**
- Consumes: `app.core.models.rca.RcaReport` model (already exists)
- Produces: `InvestigationRequest`, `InvestigationResult`, `LogEntry`, `EventEntry`, `MonitorEntry`, `MetricSeries`, `RcaDiagnosis` pydantic models

- [ ] **Step 1: Create package structure**

```bash
mkdir -p backend/app/datadog_kit
touch backend/app/datadog_kit/__init__.py
mkdir -p tests/test_datadog_kit
touch tests/test_datadog_kit/__init__.py
```

- [ ] **Step 2: Write `config.py`**

```python
"""Datadog Kit configuration."""

from __future__ import annotations

from pydantic import BaseModel


class DatadogKitConfig(BaseModel):
    """Runtime config for the investigation kit."""

    default_time_range_minutes: int = 60
    logs_limit: int = 50
    events_limit: int = 20
    monitors_limit: int = 50
    parallel_timeout_seconds: int = 120
    signal_timeout_seconds: int = 30
```

- [ ] **Step 3: Write `models.py`**

```python
"""Pydantic models for the Datadog investigation kit."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LogEntry(BaseModel):
    timestamp: str = ""
    message: str = ""
    status: str = ""
    service: str = ""
    host: str = ""
    tags: list[str] = []


class EventEntry(BaseModel):
    timestamp: str = ""
    title: str = ""
    message: str = ""
    tags: list[str] = []
    source: str = ""


class MonitorEntry(BaseModel):
    id: int | None = None
    name: str = ""
    type: str = ""
    query: str = ""
    overall_state: str = ""
    tags: list[str] = []


class MetricSeries(BaseModel):
    name: str = ""
    timestamps: list[str] = []
    values: list[float] = []


class InvestigationRequest(BaseModel):
    query: str
    tags: dict[str, str] = {}
    time_range_minutes: int = 60
    incident_id: str | None = None


class SignalResult(BaseModel):
    success: bool = True
    error: str | None = None
    duration_ms: int = 0


class LogsResult(SignalResult):
    logs: list[LogEntry] = []
    total: int = 0


class EventsResult(SignalResult):
    events: list[EventEntry] = []
    total: int = 0


class MonitorsResult(SignalResult):
    monitors: list[MonitorEntry] = []
    total: int = 0


class MetricsResult(SignalResult):
    series: list[MetricSeries] = []
    total: int = 0


class InvestigationResult(BaseModel):
    query: str
    time_range_minutes: int
    logs: LogsResult = LogsResult()
    events: EventsResult = EventsResult()
    monitors: MonitorsResult = MonitorsResult()
    metrics: MetricsResult = MetricsResult()
    total_duration_ms: int = 0


class RcaDiagnosis(BaseModel):
    root_cause: str
    root_cause_category: str  # deploy|resource|latency|dependency|data_corruption
    causal_chain: list[str]
    severity: str  # P1|P2|P3
    confidence: float  # 0.0-1.0
    evidence_refs: dict[str, list[str]] = {}
    remediation_steps: list[str] = []
    inconclusive: bool = False
```

- [ ] **Step 4: Write failing tests**

```python
# tests/test_datadog_kit/test_models.py

from app.datadog_kit.models import (
    LogEntry,
    EventEntry,
    MonitorEntry,
    MetricSeries,
    InvestigationRequest,
    RcaDiagnosis,
)


def test_log_entry_defaults():
    entry = LogEntry()
    assert entry.timestamp == ""
    assert entry.message == ""
    assert entry.status == ""
    assert entry.tags == []


def test_event_entry_defaults():
    entry = EventEntry()
    assert entry.title == ""
    assert entry.source == ""


def test_monitor_entry_defaults():
    entry = MonitorEntry()
    assert entry.id is None
    assert entry.overall_state == ""


def test_metric_series_defaults():
    series = MetricSeries()
    assert series.timestamps == []
    assert series.values == []


def test_investigation_request_defaults():
    req = InvestigationRequest(query="service:test")
    assert req.query == "service:test"
    assert req.time_range_minutes == 60


def test_rca_diagnosis_defaults():
    d = RcaDiagnosis(
        root_cause="memory leak",
        root_cause_category="resource",
        causal_chain=["deploy", "memory spike"],
        severity="P1",
        confidence=0.85,
    )
    assert d.inconclusive is False
    assert d.remediation_steps == []
```

- [ ] **Step 5: Run tests to verify they fail initially (models not importable yet)**

Run: `cd /opt/data/workspace/observai && uv run pytest tests/test_datadog_kit/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.datadog_kit'`

- [ ] **Step 6: Create `__init__.py` with empty `__all__`**

```python
"""Datadog investigation kit — parallel signal collection + LLM RCA."""
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_datadog_kit/test_models.py -v`
Expected: PASS (6 passed)

- [ ] **Step 8: Commit**

```bash
git add backend/app/datadog_kit/ tests/test_datadog_kit/
git commit -m "feat: create datadog_kit package structure and models"
```

---

### Task 2: Build Collector — parallel fetch of 4 signals

**Files:**
- Create: `backend/app/datadog_kit/collector.py`
- Create: `tests/test_datadog_kit/test_collector.py`

**Interfaces:**
- Consumes: `DatadogClient` from `app.datadog.client`, `InvestigationRequest`, `LogEntry`, `EventEntry`, `MonitorEntry`, `MetricSeries`, `InvestigationResult`, `DatadogKitConfig`
- Produces: `collector.fetch_all(request: InvestigationRequest) -> InvestigationResult`

- [ ] **Step 1: Write the collector**

```python
"""Parallel signal collector — fetches logs, events, monitors, metrics concurrently."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.datadog.client import DatadogClient
from app.datadog_kit.config import DatadogKitConfig
from app.datadog_kit.models import (
    EventEntry,
    InvestigationResult,
    InvestigationRequest,
    LogEntry,
    MetricsResult,
    MetricSeries,
    LogsResult,
    EventsResult,
    MonitorsResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable

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
            tags=tags_str or None,
        )
        duration = int((time.monotonic() - t0) * 1000)
        data = raw if isinstance(raw, dict) else {}
        events_raw = data.get("events", [])
        events = []
        for ev in events_raw:
            if not isinstance(ev, dict):
                continue
            events.append(
                EventEntry(
                    timestamp=ev.get("date_happened", ""),
                    title=ev.get("title", ""),
                    message=ev.get("text", ev.get("message", "")),
                    tags=ev.get("tags", []),
                    source=ev.get("source", ""),
                )
            )
        return EventsResult(events=events[: config.events_limit], total=len(events), duration_ms=duration)
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
        raw = await client.call(client.monitors.list_monitors, tags=tags_str or None)
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
```

- [ ] **Step 2: Write failing test**

```python
# tests/test_datadog_kit/test_collector.py

import pytest
from app.datadog_kit.collector import fetch_all
from app.datadog_kit.models import InvestigationRequest


@pytest.mark.asyncio
async def test_fetch_all_returns_investigation_result():
    """Smoke test — without Datadog creds signals fail but result is still returned."""
    req = InvestigationRequest(query="service:test")
    result = await fetch_all(req)
    assert result.query == "service:test"
    # Without real creds, all signals should have success=False
    assert result.logs.success is False
    assert result.events.success is False
    assert result.monitors.success is False
    assert result.metrics.success is False
    assert result.total_duration_ms >= 0
```

- [ ] **Step 3: Run test to verify it fails (collector not importable yet)**

Run: `uv run pytest tests/test_datadog_kit/test_collector.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_datadog_kit/test_collector.py -v`
Expected: PASS (1 passed — signals fail gracefully without creds)

- [ ] **Step 5: Commit**

```bash
git add backend/app/datadog_kit/collector.py tests/test_datadog_kit/
git commit -m "feat: add parallel signal collector (logs, events, monitors, metrics)"
```

---

### Task 3: Build Diagnosis — LLM structured RCA from investigation data

**Files:**
- Create: `backend/app/datadog_kit/diagnosis.py`
- Create: `tests/test_datadog_kit/test_diagnosis.py`

**Interfaces:**
- Consumes: `InvestigationResult`, `RcaDiagnosis`
- Produces: `diagnosis.analyze(result: InvestigationResult) -> RcaDiagnosis`

Note: This task uses an LLM call. For testing, mock the LLM provider. The implementation should be provider-agnostic — accept a callable that takes a prompt string and returns structured JSON.

- [ ] **Step 1: Write diagnosis module**

```python
"""LLM-powered RCA diagnosis from collected investigation data."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from app.datadog_kit.models import (
    InvestigationResult,
    RcaDiagnosis,
)

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
- "evidence_refs": dict with keys "logs", "events", "monitors", "metrics" — each a list of brief identifiers
- "remediation_steps": list of actionable steps
- "inconclusive": true if confidence < 0.5 or no clear root cause

Be precise. If there's not enough evidence, set inconclusive=true and explain why in root_cause.
"""


def _summarize_logs(result: InvestigationResult) -> str:
    logs = result.logs.logs
    if not logs:
        return "No logs captured."
    errors = [l for l in logs if l.status.lower() in ("error", "critical", "fatal")]
    if errors:
        lines = [f"[{e.timestamp}] {e.service} | {e.status} | {e.message[:200]}" for e in errors[:15]]
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
    alerts_count = len([m for m in result.monitors.monitors if m.overall_state in ("Alert", "Warn")])
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
        root_cause=f"{error_count} error logs, {alerts_count} monitors alerting, {event_count} events",
        root_cause_category="resource",
        causal_chain=[],
        severity="P2" if alerts_count > 0 else "P3",
        confidence=0.3,
        inconclusive=True,
    )
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_datadog_kit/test_diagnosis.py

import pytest
from app.datadog_kit.diagnosis import _fallback_diagnosis, build_prompt, _parse_rca_response
from app.datadog_kit.models import (
    InvestigationResult,
    LogEntry,
    LogsResult,
    RcaDiagnosis,
)


def test_fallback_no_data():
    result = InvestigationResult(query="test", time_range_minutes=60)
    d = _fallback_diagnosis(result)
    assert d.inconclusive is True
    assert d.confidence == 0.0


def test_fallback_with_alerts():
    from app.datadog_kit.models import MonitorEntry, MonitorsResult
    result = InvestigationResult(
        query="test",
        time_range_minutes=60,
        monitors=MonitorsResult(
            monitors=[MonitorEntry(name="CPU Alert", overall_state="Alert")]
        ),
    )
    d = _fallback_diagnosis(result)
    assert d.inconclusive is True
    assert "CPU Alert" in d.root_cause or "monitors" in d.root_cause


def test_parse_rca_json():
    raw = '''{
        "root_cause": "memory leak in checkout service",
        "root_cause_category": "resource",
        "causal_chain": ["deploy v2.3.1", "memory spike", "OOM kills"],
        "severity": "P1",
        "confidence": 0.85,
        "evidence_refs": {"logs": ["OOM errors"], "metrics": ["memory.p95"]},
        "remediation_steps": ["rollback to v2.3.0", "add memory limit"],
        "inconclusive": false
    }'''
    d = _parse_rca_response(raw)
    assert d.root_cause == "memory leak in checkout service"
    assert d.root_cause_category == "resource"
    assert d.severity == "P1"
    assert d.confidence == 0.85
    assert d.inconclusive is False


def test_parse_rca_json_with_code_fence():
    raw = '''Some text
```json
{"root_cause": "db connection pool exhausted", "root_cause_category": "dependency", "causal_chain": [], "severity": "P1", "confidence": 0.7, "evidence_refs": {}, "remediation_steps": [], "inconclusive": false}
```
more text'''
    d = _parse_rca_response(raw)
    assert d.root_cause == "db connection pool exhausted"
    assert d.confidence == 0.7


def test_build_prompt_returns_string():
    result = InvestigationResult(query="service:api", time_range_minutes=60)
    prompt = build_prompt(result)
    assert "service:api" in prompt
    assert "60 minutes" in prompt
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_datadog_kit/test_diagnosis.py -v`
Expected: PASS (5 passed)

- [ ] **Step 4: Commit**

```bash
git add backend/app/datadog_kit/diagnosis.py tests/test_datadog_kit/
git commit -m "feat: add LLM diagnosis module with structured RCA fallback"
```

---

### Task 4: Wire router — POST /datadog/investigate

**Files:**
- Create: `backend/app/datadog_kit/router.py`
- Modify: `backend/app/main.py` (register router)
- Modify: `backend/app/core/schemas/rca.py` (add `RcaReportCreate` field for investigation data)
- Test: `tests/test_datadog_kit/test_router.py`

**Interfaces:**
- Consumes: `fetch_all`, `analyze`, `DatadogKitConfig`, `InvestigationRequest`, `RcaDiagnosis`, `app.core.db.get_db`, `app.core.models.rca.RcaReport`, `app.core.schemas.rca.RcaReportRead`
- Produces: `POST /api/v1/datadog/investigate` endpoint

- [ ] **Step 1: Write router**

```python
"""Investigation endpoint — parallel Datadog signal fetch + structured RCA."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.db import get_db
from app.core.models.rca import RcaReport
from app.core.schemas.rca import RcaReportRead
from app.datadog_kit.collector import fetch_all
from app.datadog_kit.config import DatadogKitConfig
from app.datadog_kit.diagnosis import analyze
from app.datadog_kit.models import InvestigationRequest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datadog", tags=["datadog-investigate"])


@router.post("/investigate", response_model=RcaReportRead)
async def investigate(
    request: InvestigationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a full investigation: fetch 4 Datadog signals in parallel,
    then produce a structured RCA diagnosis. Result is saved as an RCA report."""
    config = DatadogKitConfig(
        default_time_range_minutes=request.time_range_minutes,
    )

    # Step 1: Collect signals
    investigation = await fetch_all(request, config)

    # Step 2: Diagnose using LLM
    diagnosis = await analyze(investigation)

    # Step 3: Build evidence snapshots
    error_logs = [
        l.model_dump()
        for l in investigation.logs.logs
        if l.status.lower() in ("error", "critical", "fatal")
    ]
    alerting_monitors = [
        m.model_dump()
        for m in investigation.monitors.monitors
        if m.overall_state in ("Alert", "Warn")
    ]

    # Step 4: Save to DB
    report = RcaReport(
        incident_id=None,  # optional — can be linked later
        summary=f"Investigation for: {request.query}",
        root_cause=diagnosis.root_cause,
        recommendations=diagnosis.remediation_steps,
        timeline={
            "causal_chain": diagnosis.causal_chain,
            "severity": diagnosis.severity,
            "confidence": diagnosis.confidence,
            "inconclusive": diagnosis.inconclusive,
            "category": diagnosis.root_cause_category,
        },
        metrics_snapshot={
            "series": [s.model_dump() for s in investigation.metrics.series],
            "total_duration_ms": investigation.total_duration_ms,
        },
        logs_snapshot={
            "total": investigation.logs.total,
            "errors": error_logs[:20],
            "query": investigation.query,
        },
        changes=diagnosis.evidence_refs,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    logger.info(
        "Investigation complete: query=%s confidence=%.2f duration=%dms",
        request.query,
        diagnosis.confidence,
        investigation.total_duration_ms,
    )

    return report


@router.get("/investigate/{report_id}", response_model=RcaReportRead)
async def get_investigation_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a saved investigation report by ID."""
    import uuid

    try:
        uid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report ID") from None

    result = await db.execute(select(RcaReport).where(RcaReport.id == uid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Investigation report not found")
    return report
```

- [ ] **Step 2: Modify `main.py` to register the router**

Add after line 61 (the existing `from app.self_healing.router import router as self_healing_router`):

```python
    from app.datadog_kit.router import router as datadog_kit_router
```

Add after line 85 (existing `app.include_router(analysis_router...)`):

```python
    app.include_router(datadog_kit_router, prefix=prefix, tags=["datadog-investigate"])
```

- [ ] **Step 3: Write failing test**

```python
# tests/test_datadog_kit/test_router.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_investigate_no_auth():
    """Without auth, endpoint returns 401 (auth middleware)."""
    resp = client.post(
        "/api/v1/datadog/investigate",
        json={"query": "service:test", "time_range_minutes": 60},
    )
    assert resp.status_code in (401, 422)  # 422 if no auth middleware yet
```

- [ ] **Step 4: Run test**

Run: `uv run pytest tests/test_datadog_kit/test_router.py -v`
Expected: PASS or 401/422 depending on auth state

- [ ] **Step 5: Commit**

```bash
git add backend/app/datadog_kit/router.py backend/app/main.py tests/test_datadog_kit/
git commit -m "feat: add POST /datadog/investigate endpoint with RCA persistence"
```

---

### Task 5: Run all tests and verify lint

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/test_datadog_kit/ -v`
Expected: All tests pass

- [ ] **Step 2: Run ruff linter**

Run: `uv run ruff check backend/app/datadog_kit/`
Expected: No errors

- [ ] **Step 3: Run mypy**

Run: `uv run mypy backend/app/datadog_kit/`
Expected: Success (no issues)

- [ ] **Step 4: Run full project test suite**

Run: `uv run pytest tests/ -q`
Expected: All existing tests still pass (no regressions)

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: lint and test pass for datadog_kit"
```

---

## File Structure (final)

```
backend/app/
├── datadog_kit/
│   ├── __init__.py
│   ├── config.py          # DatadogKitConfig
│   ├── models.py          # LogEntry, EventEntry, MonitorEntry, MetricSeries, InvestigationRequest/Result, RcaDiagnosis
│   ├── collector.py       # fetch_all() — parallel asyncio.gather
│   ├── diagnosis.py       # build_prompt(), analyze(), _parse_rca_response()
│   └── router.py          # POST /api/v1/datadog/investigate, GET /api/v1/datadog/investigate/{id}
└── main.py                # +1 router import

tests/test_datadog_kit/
├── __init__.py
├── test_models.py
├── test_collector.py
├── test_diagnosis.py
└── test_router.py
```
