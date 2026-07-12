"""Pydantic models for the Datadog investigation kit."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 -- runtime need: Pydantic field type
from typing import Any, Literal

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


class SpanEntry(BaseModel):
    span_id: str = ""
    trace_id: str = ""
    service: str = ""
    resource: str = ""
    operation: str = ""
    duration_ns: int = 0
    status: str = ""
    tags: list[str] = []
    timestamp: str = ""


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


class SpansResult(SignalResult):
    spans: list[SpanEntry] = []
    total: int = 0


class InvestigationResult(BaseModel):
    query: str
    time_range_minutes: int
    logs: LogsResult = LogsResult()
    events: EventsResult = EventsResult()
    monitors: MonitorsResult = MonitorsResult()
    metrics: MetricsResult = MetricsResult()
    spans: SpansResult = SpansResult()
    total_duration_ms: int = 0
    diagnosis: RcaDiagnosis | None = None
    react_trace: list[ReActTurn] = []
    runbook: Runbook | None = None
    mttr_breakdown: MttrBreakdown | None = None


class RcaDiagnosis(BaseModel):
    root_cause: str
    root_cause_category: str  # deploy|resource|latency|dependency|data_corruption
    causal_chain: list[str]
    severity: str  # P1|P2|P3
    confidence: float  # 0.0-1.0
    evidence_refs: dict[str, list[str]] = {}
    remediation_steps: list[str] = []
    inconclusive: bool = False


# V3: ReAct Agent models
class ReActTurn(BaseModel):
    turn: int
    thought: str
    action: str
    action_input: dict[str, Any]
    observation: str


class Runbook(BaseModel):
    title: str
    detection: list[str] = []
    diagnosis: list[str] = []
    mitigation: list[str] = []
    prevention: list[str] = []
    references: list[str] = []


class MttrBreakdown(BaseModel):
    detected_at: datetime
    triaged_at: datetime | None = None
    diagnosed_at: datetime | None = None
    mitigated_at: datetime | None = None
    resolved_at: datetime | None = None
    mttd_seconds: float | None = None
    mtti_seconds: float | None = None
    mttk_seconds: float | None = None
    mtta_seconds: float | None = None
    mttr_seconds: float | None = None

    def compute(self) -> MttrBreakdown:
        """Compute derived fields from timestamps."""
        if self.triaged_at:
            self.mttd_seconds = (self.triaged_at - self.detected_at).total_seconds()
        if self.diagnosed_at and self.triaged_at:
            self.mtti_seconds = (self.diagnosed_at - self.triaged_at).total_seconds()
        if self.mitigated_at and self.diagnosed_at:
            self.mttk_seconds = (self.mitigated_at - self.diagnosed_at).total_seconds()
        if self.resolved_at and self.mitigated_at:
            self.mtta_seconds = (self.resolved_at - self.mitigated_at).total_seconds()
        if self.resolved_at:
            self.mttr_seconds = (self.resolved_at - self.detected_at).total_seconds()
        return self


class InvestigationRequestV3(InvestigationRequest):
    mode: Literal["single", "react"] = "single"
    max_turns: int = 5
    generate_runbook: bool = False


class InvestigationResponseV3(InvestigationResult):
    react_trace: list[ReActTurn] | None = None
    runbook: Runbook | None = None
    mttr_breakdown: MttrBreakdown | None = None
    diagnosis: RcaDiagnosis | None = None
