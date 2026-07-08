"""
SRE Metrics Engine — multi-metric Datadog analysis for senior SRE-level insights.

Queries multiple metric categories (CPU, memory, latency, errors, disk, network)
and correlates them to produce structured findings with severity assessment.

Usage:
    analyzer = SREMetricsAnalyzer(service="api-gateway")
    results = await analyzer.analyze_all()
    # results.findings  → list of dicts per metric
    # results.narrative → senior SRE analysis text
    # results.score     → 0-100 health score
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.datadog.client import DatadogClient

logger = logging.getLogger(__name__)


# ── Metric Definitions ──────────────────────────────────────────────

SRE_METRICS: list[dict[str, Any]] = [
    {
        "id": "cpu_user",
        "category": "cpu",
        "name": "CPU Utilization",
        "query": "avg:system.cpu.user{${TAGS}}",
        "agg": "avg",
        "unit": "%",
        "warning_gt": 70.0,
        "critical_gt": 90.0,
        "description": "Average CPU utilization across hosts. >70% indicates bottleneck.",
    },
    {
        "id": "cpu_iowait",
        "category": "cpu",
        "name": "CPU I/O Wait",
        "query": "avg:system.cpu.iowait{${TAGS}}",
        "agg": "avg",
        "unit": "%",
        "warning_gt": 10.0,
        "critical_gt": 25.0,
        "description": "CPU time waiting for I/O. High I/O wait suggests disk bottleneck.",
    },
    {
        "id": "memory_used",
        "category": "memory",
        "name": "Memory Usage",
        "query": "avg:system.mem.used_percent{${TAGS}}",
        "agg": "avg",
        "unit": "%",
        "warning_gt": 75.0,
        "critical_gt": 90.0,
        "description": "Physical memory in use. High usage may trigger OOM or swapping.",
    },
    {
        "id": "memory_swap",
        "category": "memory",
        "name": "Swap Usage",
        "query": "avg:system.swap.used_percent{${TAGS}}",
        "agg": "avg",
        "unit": "%",
        "warning_gt": 10.0,
        "critical_gt": 30.0,
        "description": "Swap space in use. Non-zero swap indicates memory pressure.",
    },
    {
        "id": "latency_p50",
        "category": "latency",
        "name": "Latency p50",
        "query": "avg:trace.servlet.request.duration{${TAGS}}",
        "agg": "avg",
        "unit": "ms",
        "warning_gt": 500.0,
        "critical_gt": 2000.0,
        "description": "Median request latency. Detects early-stage perf regression.",
    },
    {
        "id": "latency_p99",
        "category": "latency",
        "name": "Latency p99",
        "query": "p99:trace.servlet.request.duration{${TAGS}}",
        "agg": "p99",
        "unit": "ms",
        "warning_gt": 2000.0,
        "critical_gt": 5000.0,
        "description": "p99 request latency. High p99 indicates tail-latency problems.",
    },
    {
        "id": "error_rate",
        "category": "errors",
        "name": "Error Rate",
        "query": "sum:trace.servlet.request.errors{${TAGS}}.as_rate()",
        "agg": "rate",
        "unit": "errors/s",
        "warning_gt": 1.0,
        "critical_gt": 5.0,
        "description": "Request error rate per second. Spikes indicate app failures.",
    },
    {
        "id": "disk_used",
        "category": "disk",
        "name": "Disk Usage",
        "query": "avg:system.disk.used_percent{${TAGS}}",
        "agg": "avg",
        "unit": "%",
        "warning_gt": 75.0,
        "critical_gt": 90.0,
        "description": "Disk space utilization. Near-capacity disks risk write failures.",
    },
    {
        "id": "disk_io",
        "category": "disk",
        "name": "Disk I/O",
        "query": "avg:system.disk.r_await{${TAGS}}",
        "agg": "avg",
        "unit": "ms",
        "warning_gt": 20.0,
        "critical_gt": 50.0,
        "description": "Average disk read latency. High values indicate storage contention.",
    },
    {
        "id": "network_in",
        "category": "network",
        "name": "Network Inbound",
        "query": "avg:system.net.bytes_rcvd{${TAGS}}",
        "agg": "avg",
        "unit": "bytes/s",
        "warning_gt": 1_000_000_000,  # 1 Gbps
        "critical_gt": 5_000_000_000,  # 5 Gbps
        "description": "Inbound network throughput. High bandwidth may indicate DDoS.",
    },
    {
        "id": "network_out",
        "category": "network",
        "name": "Network Outbound",
        "query": "avg:system.net.bytes_sent{${TAGS}}",
        "agg": "avg",
        "unit": "bytes/s",
        "warning_gt": 1_000_000_000,
        "critical_gt": 5_000_000_000,
        "description": "Outbound network throughput.",
    },
]

# Correlation rules — cross-metric patterns that senior SREs recognize
CORRELATION_RULES: list[dict[str, Any]] = [
    {
        "id": "resource_contention",
        "label": "Resource Contention",
        "description": "High CPU + High Latency suggests resource contention or noisy neighbor",
        "conditions": {"cpu_user": "critical", "latency_p50": "warning"},
    },
    {
        "id": "memory_pressure_oom",
        "label": "Memory Pressure",
        "description": "High Memory + Swap usage indicates memory pressure, potential OOM risk",
        "conditions": {"memory_used": "critical", "memory_swap": "warning"},
    },
    {
        "id": "disk_bottleneck",
        "label": "Disk Bottleneck",
        "description": "High I/O Wait + High Disk Latency = storage subsystem bottleneck",
        "conditions": {"cpu_iowait": "warning", "disk_io": "warning"},
    },
    {
        "id": "capacity_exhaustion",
        "label": "Capacity Exhaustion",
        "description": "Multiple resources near limits — scale consideration needed",
        "conditions": {"cpu_user": "warning", "memory_used": "warning", "disk_used": "warning"},
    },
    {
        "id": "error_burst",
        "label": "Error Burst with Impact",
        "description": "High error rate + latency degradation suggests application-level failure",
        "conditions": {"error_rate": "critical", "latency_p99": "warning"},
    },
]


# ── Data Classes ────────────────────────────────────────────────────


@dataclass
class MetricResult:
    """Result of a single metric query."""

    metric_id: str
    category: str
    name: str
    value: float | None
    unit: str
    status: str  # ok, warning, critical, nodata, error
    threshold_warning: float
    threshold_critical: float
    description: str
    detail: str = ""


@dataclass
class CorrelationFinding:
    """A cross-metric correlation finding."""

    rule_id: str
    label: str
    description: str
    severity: str  # info, warning, critical
    involved_metrics: list[str]


@dataclass
class SREAnalysisResult:
    """Complete SRE analysis result."""

    service: str | None
    metrics: list[MetricResult]
    correlations: list[CorrelationFinding]
    score: float  # 0-100
    narrative: str  # Senior SRE analysis text
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: int = 0


# ── Analyzer ─────────────────────────────────────────────────────────


class SREMetricsAnalyzer:
    """Query and analyze multiple Datadog metrics for SRE-level insights.

    Args:
        service: Optional service name to filter metrics (e.g. "api-gateway").
            Only used when ``tags`` is not provided — builds ``service:<name>``.
        tags: Full Datadog tag filter string (e.g. ``"service:api-gateway,env:prod"``).
            Takes precedence over ``service`` when provided.
        window_min: Time window in minutes for metric queries (default: 60).
        client: Optional DatadogClient instance. Creates one if not provided.
    """

    def __init__(
        self,
        service: str | None = None,
        tags: str | None = None,
        window_min: int = 60,
        client: DatadogClient | None = None,
    ) -> None:
        self.service = service
        self.tags = tags
        self.window_min = window_min

        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            from app.datadog.client import DatadogClient

            self._client = DatadogClient()
            self._owns_client = True

    # ── Public API ──────────────────────────────────────────────────

    def analyze_all_sync(self) -> SREAnalysisResult:
        """Run all metric queries and produce a comprehensive SRE analysis (sync)."""
        now = int(datetime.now(UTC).timestamp())
        from_ts = now - self.window_min * 60

        metric_results = self._query_all_metrics(from_ts, now)
        correlations = self._find_correlations(metric_results)
        recommendations = self._build_recommendations(metric_results, correlations)
        score = self._compute_health_score(metric_results, correlations)
        narrative = self._build_narrative(metric_results, correlations, score)

        findings: list[dict[str, Any]] = []
        for m in metric_results:
            findings.append(
                {
                    "type": "sre_metric",
                    "metric_id": m.metric_id,
                    "category": m.category,
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "status": m.status,
                    "detail": m.detail,
                }
            )

        for c in correlations:
            findings.append(
                {
                    "type": "sre_correlation",
                    "rule_id": c.rule_id,
                    "label": c.label,
                    "description": c.description,
                    "severity": c.severity,
                    "involved_metrics": c.involved_metrics,
                }
            )

        return SREAnalysisResult(
            service=self.service,
            metrics=metric_results,
            correlations=correlations,
            score=score,
            narrative=narrative,
            findings=findings,
            recommendations=recommendations,
            timestamp=now,
        )

    # ── Metric Queries ──────────────────────────────────────────────

    def _query_all_metrics(self, from_ts: int, to_ts: int) -> list[MetricResult]:
        """Query every SRE metric against Datadog."""
        results: list[MetricResult] = []

        for metric_def in SRE_METRICS:
            result = self._query_single(metric_def, from_ts, to_ts)
            results.append(result)

        return results

    def _query_single(self, metric_def: dict[str, Any], from_ts: int, to_ts: int) -> MetricResult:
        """Query one metric and return a MetricResult."""
        mid = metric_def["id"]
        tags = self._build_tags()

        query = metric_def["query"].replace("${TAGS}", tags)

        try:
            raw = self._client.query_metrics(query=query, from_ts=from_ts, to=to_ts)

            series = raw.get("series", [])
            if not series:
                return MetricResult(
                    metric_id=mid,
                    category=metric_def["category"],
                    name=metric_def["name"],
                    value=None,
                    unit=metric_def["unit"],
                    status="nodata",
                    threshold_warning=metric_def["warning_gt"],
                    threshold_critical=metric_def["critical_gt"],
                    description=metric_def["description"],
                    detail="No data returned for the time window",
                )

            # Extract the average/point value from the first series
            points = series[0].get("pointlist", [])
            if not points:
                return MetricResult(
                    metric_id=mid,
                    category=metric_def["category"],
                    name=metric_def["name"],
                    value=None,
                    unit=metric_def["unit"],
                    status="nodata",
                    threshold_warning=metric_def["warning_gt"],
                    threshold_critical=metric_def["critical_gt"],
                    description=metric_def["description"],
                    detail="No data points in series",
                )

            # Use the most recent data point
            values = [p[1] for p in points if p[1] is not None]
            if not values:
                return MetricResult(
                    metric_id=mid,
                    category=metric_def["category"],
                    name=metric_def["name"],
                    value=None,
                    unit=metric_def["unit"],
                    status="nodata",
                    threshold_warning=metric_def["warning_gt"],
                    threshold_critical=metric_def["critical_gt"],
                    description=metric_def["description"],
                    detail="All data points are null",
                )

            value = sum(values) / len(values)
            status = self._classify(value, metric_def)
            detail = f"{metric_def['name']}: {value:.1f}{metric_def['unit']}"

            return MetricResult(
                metric_id=mid,
                category=metric_def["category"],
                name=metric_def["name"],
                value=round(value, 2),
                unit=metric_def["unit"],
                status=status,
                threshold_warning=metric_def["warning_gt"],
                threshold_critical=metric_def["critical_gt"],
                description=metric_def["description"],
                detail=detail,
            )

        except Exception as exc:
            logger.warning("Metric %s query failed: %s", mid, exc)
            return MetricResult(
                metric_id=mid,
                category=metric_def["category"],
                name=metric_def["name"],
                value=None,
                unit=metric_def["unit"],
                status="error",
                threshold_warning=metric_def["warning_gt"],
                threshold_critical=metric_def["critical_gt"],
                description=metric_def["description"],
                detail=f"Query failed: {exc}",
            )

    # ── Correlation Engine ──────────────────────────────────────────

    def _find_correlations(self, metrics: list[MetricResult]) -> list[CorrelationFinding]:
        """Detect cross-metric correlation patterns."""
        by_id = {m.metric_id: m for m in metrics}
        correlations: list[CorrelationFinding] = []

        for rule in CORRELATION_RULES:
            involved: list[str] = []
            all_match = True
            worst_severity = "info"

            for metric_id, required_status in rule["conditions"].items():
                m = by_id.get(metric_id)
                if m is None:
                    all_match = False
                    break
                involved.append(metric_id)

                # Check if metric meets or exceeds the required status
                if m.status == "critical":
                    if required_status in ("warning", "critical"):
                        worst_severity = "critical"
                    else:
                        all_match = False
                        break
                elif m.status == "warning":
                    if required_status == "critical":
                        all_match = False
                        break
                    if required_status == "warning":
                        worst_severity = max(worst_severity, "warning", key=self._severity_order)
                elif m.status == "ok" or m.status == "nodata":
                    all_match = False
                    break

            if all_match and involved:
                correlations.append(
                    CorrelationFinding(
                        rule_id=rule["id"],
                        label=rule["label"],
                        description=rule["description"],
                        severity=worst_severity,
                        involved_metrics=involved,
                    )
                )

        return correlations

    @staticmethod
    def _severity_order(s: str) -> int:
        return {"info": 0, "warning": 1, "critical": 2}.get(s, 0)

    # ── Health Score ────────────────────────────────────────────────

    def _compute_health_score(
        self,
        metrics: list[MetricResult],
        correlations: list[CorrelationFinding],
    ) -> float:
        """Calculate 0-100 health score from metrics and correlations."""
        score = 100.0

        # Each critical metric: -15 points
        critical_count = sum(1 for m in metrics if m.status == "critical")
        score -= critical_count * 15

        # Each warning metric: -5 points
        warning_count = sum(1 for m in metrics if m.status == "warning")
        score -= warning_count * 5

        # Each correlation finding: -10 for critical, -5 for warning
        for c in correlations:
            if c.severity == "critical":
                score -= 10
            elif c.severity == "warning":
                score -= 5

        # No data = not penalized (might be expected for some metrics)
        # Error on a metric: -3
        error_count = sum(1 for m in metrics if m.status == "error")
        score -= error_count * 3

        return max(0.0, round(score, 1))

    # ── Recommendations ─────────────────────────────────────────────

    def _build_recommendations(
        self,
        metrics: list[MetricResult],
        correlations: list[CorrelationFinding],
    ) -> list[str]:
        """Build prioritized SRE recommendations."""
        recs: list[str] = []

        # 1. Critical metrics first
        for m in metrics:
            if m.status == "critical":
                recs.append(
                    f"CRITICAL: {m.name} at {m.value}{m.unit} "
                    f"(threshold: {m.threshold_critical}{m.unit}). "
                    f"{m.description}"
                )

        # 2. Correlation-based
        for c in correlations:
            if c.severity == "critical":
                recs.append(f"CORRELATION: {c.label} — {c.description}")

        # 3. Warning metrics
        for m in metrics:
            if m.status == "warning" and m.metric_id not in {
                mid for c in correlations for mid in c.involved_metrics
            }:
                recs.append(
                    f"WARNING: {m.name} at {m.value}{m.unit} "
                    f"(threshold: {m.threshold_warning}{m.unit})"
                )

        # 4. Cross-cutting SRE recommendations
        critical_metrics = [m for m in metrics if m.status == "critical"]
        warning_metrics = [m for m in metrics if m.status == "warning"]

        if critical_metrics:
            categories_critical = {m.category for m in critical_metrics}
            if "cpu" in categories_critical and "memory" in categories_critical:
                recs.append(
                    "SCALE: Both CPU and memory critical — consider vertical or horizontal scaling"
                )
            if "disk" in categories_critical:
                recs.append("CAPACITY: Disk usage critical — review retention policies")
            if "latency" in categories_critical:
                recs.append(
                    "PERFORMANCE: Latency critical — review recent deploys,"
                    " DB queries, and downstream deps"
                )

        if len(critical_metrics) + len(warning_metrics) >= 5:
            recs.append(
                "MULTI-METRIC: Multiple dimensions degraded — consider incident declaration"
            )

        return recs

    # ── Narrative ───────────────────────────────────────────────────

    def _build_narrative(
        self,
        metrics: list[MetricResult],
        correlations: list[CorrelationFinding],
        score: float,
    ) -> str:
        """Generate a senior SRE narrative summary."""
        [m for m in metrics if m.status == "ok"]
        warning = [m for m in metrics if m.status == "warning"]
        critical = [m for m in metrics if m.status == "critical"]
        nodata = [m for m in metrics if m.status == "nodata"]

        parts: list[str] = []
        svc_str = f"service '{self.service}'" if self.service else "all services"

        # Opening
        parts.append(f"SRE Analysis for {svc_str} — Health Score: {score}/100.")

        # Critical section
        if critical:
            crit_names = [f"{m.name} ({m.value}{m.unit})" for m in critical]
            parts.append(f"CRITICAL: {'; '.join(crit_names)}. Immediate investigation required.")
        else:
            parts.append("No critical-level metric anomalies detected.")

        # Correlations
        if correlations:
            for c in correlations:
                parts.append(f"Correlation detected — {c.label}: {c.description}.")
        else:
            parts.append("No cross-metric correlation patterns detected.")

        # Warning section
        if warning:
            warn_names = [f"{m.name} ({m.value}{m.unit})" for m in warning]
            parts.append(f"Warning-level: {'; '.join(warn_names)}. Monitor closely.")

        # Summary by category
        cat_status: dict[str, list[str]] = {}
        for m in metrics:
            cat_status.setdefault(m.category, []).append(m.status)

        category_lines = []
        for cat, statuses in sorted(cat_status.items()):
            if "critical" in statuses:
                category_lines.append(f"{cat}: ⚠ CRITICAL")
            elif "warning" in statuses:
                category_lines.append(f"{cat}: ⚡ warning")
            elif "error" in statuses:
                category_lines.append(f"{cat}: ❓ error (check config/connectivity)")
            else:
                category_lines.append(f"{cat}: ✓ ok")

        parts.append("Category summary: " + " | ".join(category_lines))

        # Metadata
        if nodata:
            nodata_names = [m.name for m in nodata]
            parts.append(
                f"No data for: {', '.join(nodata_names)}"
                " (expected if service is new or metrics not configured)."
            )

        return " ".join(parts)

    # ── Helpers ─────────────────────────────────────────────────────

    def _build_tags(self) -> str:
        """Build Datadog tag filter string.

        Priority order:
          1. Explicit ``tags`` string (passed at construction) — used as-is.
          2. ``service`` name only — builds ``service:<name>``.
          3. Neither — returns ``"*"`` (all infrastructure).
        """
        if self.tags:
            return self.tags
        if self.service:
            return f"service:{self.service}"
        return "*"

    @staticmethod
    def _classify(value: float, metric_def: dict[str, Any]) -> str:
        """Classify a metric value as ok/warning/critical."""
        critical_gt = metric_def["critical_gt"]
        warning_gt = metric_def["warning_gt"]

        if value >= critical_gt:
            return "critical"
        if value >= warning_gt:
            return "warning"
        return "ok"
