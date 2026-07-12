"""Pydantic models for the Datadog investigation kit."""

from __future__ import annotations

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
