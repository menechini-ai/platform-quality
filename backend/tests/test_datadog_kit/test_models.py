from app.datadog_kit.models import (
    EventEntry,
    InvestigationRequest,
    LogEntry,
    MetricSeries,
    MonitorEntry,
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
