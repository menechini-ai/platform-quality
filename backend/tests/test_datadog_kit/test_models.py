from __future__ import annotations

from app.datadog_kit.models import (
    EventEntry,
    InvestigationRequest,
    InvestigationResult,
    LogEntry,
    MetricSeries,
    MonitorEntry,
    RcaDiagnosis,
)


def test_log_entry_defaults() -> None:
    entry = LogEntry()
    assert entry.timestamp == ""
    assert entry.message == ""
    assert entry.status == ""
    assert entry.tags == []


def test_log_entry_explicit() -> None:
    entry = LogEntry(
        timestamp="2026-07-12T00:00:00Z",
        message="OOM killed",
        status="error",
        service="checkout",
        host="pod-1",
        tags=["env:prod", "service:checkout"],
    )
    assert entry.message == "OOM killed"
    assert entry.service == "checkout"


def test_event_entry_defaults() -> None:
    entry = EventEntry()
    assert entry.title == ""
    assert entry.source == ""


def test_event_entry_explicit() -> None:
    entry = EventEntry(
        timestamp="2026-07-12T00:00:00Z",
        title="Deploy v2.3.1",
        message="Rolled out to 50%",
        tags=["env:prod"],
        source="datadog",
    )
    assert entry.title == "Deploy v2.3.1"
    assert entry.source == "datadog"


def test_monitor_entry_defaults() -> None:
    entry = MonitorEntry()
    assert entry.id is None
    assert entry.overall_state == ""


def test_monitor_entry_explicit() -> None:
    entry = MonitorEntry(
        id=12345,
        name="CPU Alert",
        type="query alert",
        query="avg:system.cpu.user{*} > 90",
        overall_state="Alert",
        tags=["env:prod"],
    )
    assert entry.name == "CPU Alert"
    assert entry.overall_state == "Alert"


def test_metric_series_defaults() -> None:
    series = MetricSeries()
    assert series.timestamps == []
    assert series.values == []


def test_metric_series_with_data() -> None:
    series = MetricSeries(
        name="avg:system.cpu.user{service:api}",
        timestamps=["1700000000", "1700000060"],
        values=[45.0, 92.0],
    )
    assert series.name == "avg:system.cpu.user{service:api}"
    assert len(series.values) == 2


def test_investigation_request_defaults() -> None:
    req = InvestigationRequest(query="service:test")
    assert req.query == "service:test"
    assert req.time_range_minutes == 60


def test_investigation_request_full() -> None:
    req = InvestigationRequest(
        query="service:checkout",
        tags={"env": "prod"},
        time_range_minutes=30,
        incident_id="abc-123",
    )
    assert req.query == "service:checkout"
    assert req.tags == {"env": "prod"}
    assert req.incident_id == "abc-123"


def test_rca_diagnosis_defaults() -> None:
    d = RcaDiagnosis(
        root_cause="memory leak",
        root_cause_category="resource",
        causal_chain=["deploy", "memory spike"],
        severity="P1",
        confidence=0.85,
    )
    assert d.inconclusive is False
    assert d.remediation_steps == []


def test_rca_diagnosis_inconclusive() -> None:
    d = RcaDiagnosis(
        root_cause="insufficient data",
        root_cause_category="resource",
        causal_chain=[],
        severity="P3",
        confidence=0.3,
        inconclusive=True,
    )
    assert d.inconclusive is True
    assert d.confidence == 0.3


def test_investigation_result_defaults() -> None:
    result = InvestigationResult(query="test", time_range_minutes=60)
    assert result.logs.total == 0
    assert result.monitors.success is True
    assert result.total_duration_ms == 0


def test_rca_diagnosis_full_fields() -> None:
    d = RcaDiagnosis(
        root_cause="db pool exhausted",
        root_cause_category="dependency",
        causal_chain=["deploy", "connection spike", "pool full"],
        severity="P1",
        confidence=0.92,
        evidence_refs={"logs": ["db timeout errors"], "metrics": ["db.connections"]},
        remediation_steps=["increase pool size", "rollback deploy"],
    )
    assert "db timeout errors" in d.evidence_refs.get("logs", [])
    assert d.remediation_steps == ["increase pool size", "rollback deploy"]
