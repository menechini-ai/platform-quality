"""
Incident analysis agent.

Correlates Datadog monitors + events + logs + error tracking + APM
to enrich incidents. Produces: severity assessment, service impact,
timeline correlation, multi-source evidence.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import select

from app.core.models.analysis import AnalysisResult
from app.core.models.incident import Incident, IncidentTimeline
from app.datadog.client import DatadogClient
from app.datadog.write_guard import get_datadog_url, get_headers

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _time_window(incident: Incident) -> tuple[int, int]:
    """Return (from_ts, to_ts) centered on started_at +30min/-15min."""
    center = incident.started_at
    from_ts = int((center - timedelta(minutes=30)).timestamp())
    to_ts = int((center + timedelta(minutes=15)).timestamp())
    return from_ts, to_ts


def _service_filter(incident: Incident) -> str:
    """Build tag/query suffix for service if present."""
    return f" service:{incident.service}" if incident.service else ""


async def analyze_incident(
    incident_id: str,
    db: AsyncSession,
    tags: str | None = None,
) -> AnalysisResult:
    """Analyze an incident: enrich with Datadog context, detect patterns, assess severity."""
    from uuid import UUID

    uid = UUID(incident_id)
    result = await db.execute(select(Incident).where(Incident.id == uid))
    incident = result.scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []

    # 1. Check timeline for coverage
    tl_result = await db.execute(
        select(IncidentTimeline).where(IncidentTimeline.incident_id == uid)
    )
    timeline = tl_result.scalars().all()
    if len(timeline) < 2:
        recommendations.append(
            "Add more timeline events — at minimum detection, response, and resolution"
        )

    client = DatadogClient()
    from_ts, to_ts = _time_window(incident)
    sw_start = datetime.fromtimestamp(from_ts, tz=UTC)
    sw_end = datetime.fromtimestamp(to_ts, tz=UTC)

    # 2. Query Datadog events
    dd_events = []
    try:
        events = client.events.list_events(
            start=from_ts,
            end=to_ts,
            tags=incident.service or "",
        )
        dd_events = events.to_dict().get("events", [])
        findings.append(
            {
                "type": "datadog_events",
                "count": len(dd_events),
                "severity": "info",
                "detail": f"{len(dd_events)} events in window [-30m,+15m]",
            }
        )
    except Exception as e:
        logger.warning("Datadog events query failed: %s", e)

    # 3. Query ERROR/WARN/ALERT logs
    try:
        log_query = f"status:(error OR warn) {_service_filter(incident)}".strip()
        logs = client.search_logs(
            query=log_query,
            filter_from=sw_start,
            filter_to=sw_end,
        )
        logs_data = logs.get("data", [])
        findings.append(
            {
                "type": "logs",
                "count": len(logs_data),
                "query": log_query,
                "severity": "warning" if len(logs_data) > 10 else "info",
                "detail": f"{len(logs_data)} error/warn logs in window",
            }
        )
        if len(logs_data) > 10:
            recommendations.append(f"{len(logs_data)} error/warn logs found — review top sources")
    except Exception as e:
        logger.warning("Logs query failed: %s", e)

    # 4. Query ERROR/WARN/ALERT APM spans
    try:
        span_query = f"status:(error OR warn) {_service_filter(incident)}".strip()
        spans = client.list_spans(
            query=span_query,
            filter_from=sw_start,
            filter_to=sw_end,
        )
        spans_data = spans.get("data", [])
        findings.append(
            {
                "type": "apm_spans",
                "count": len(spans_data),
                "query": span_query,
                "severity": "warning" if len(spans_data) > 10 else "info",
                "detail": f"{len(spans_data)} error/warn APM spans in window",
            }
        )
        if len(spans_data) > 10:
            recommendations.append(f"{len(spans_data)} error/warn APM spans — check root span")
    except Exception as e:
        logger.warning("APM spans query failed: %s", e)

    # 5. Query Error Tracking via HTTP
    try:
        base = get_datadog_url()
        headers = get_headers()
        svc = _service_filter(incident)
        et_resp = httpx.get(
            f"{base}/api/v2/error_tracking/trackers",
            headers=headers,
            params={
                "filter[query]": f"status:active {svc}".strip(),
                "filter[from]": sw_start.isoformat(),
                "filter[to]": sw_end.isoformat(),
            },
            timeout=10,
        )
        if et_resp.status_code == 200:
            et_data = et_resp.json().get("data", [])
            findings.append(
                {
                    "type": "error_tracking",
                    "count": len(et_data),
                    "severity": "warning" if len(et_data) > 0 else "info",
                    "detail": f"{len(et_data)} active error trackers in window",
                }
            )
            if et_data:
                recommendations.append(
                    f"{len(et_data)} active error trackers — investigate root cause"
                )
        else:
            findings.append(
                {
                    "type": "error_tracking",
                    "count": 0,
                    "severity": "info",
                    "detail": f"Error Tracking API returned {et_resp.status_code}",
                }
            )
    except Exception as e:
        logger.warning("Error Tracking query failed: %s", e)

    # 5b. Multi-Metric SRE Analysis (Datadog metrics correlation)
    try:
        from app.analysis.sre_metrics import SREMetricsAnalyzer

        sre_analyzer = SREMetricsAnalyzer(
            service=incident.service,
            tags=tags,  # overrides service when set
            window_min=60,
        )
        sre_result = sre_analyzer.analyze_all_sync()
        findings.append(
            {
                "type": "sre_analysis",
                "health_score": sre_result.score,
                "narrative": sre_result.narrative,
                "metrics": [
                    {
                        "metric_id": m.metric_id,
                        "name": m.name,
                        "value": m.value,
                        "unit": m.unit,
                        "status": m.status,
                    }
                    for m in sre_result.metrics
                ],
                "correlations": [
                    {"rule_id": c.rule_id, "label": c.label, "severity": c.severity}
                    for c in sre_result.correlations
                ],
            }
        )
        sre_critical = [m for m in sre_result.metrics if m.status == "critical"]
        if sre_critical:
            recommendations.append(
                f"SRE: {len(sre_critical)} critical metric(s) during incident window — "
                f"{', '.join(m.name for m in sre_critical)}"
            )
    except Exception as e:
        logger.warning("SRE metrics analysis failed: %s", e)

    # 6. Assess severity correctness
    severity_mismatch = _assess_severity(incident, dd_events)
    if severity_mismatch:
        findings.append(severity_mismatch)
        recommendations.append(f"Review severity: {severity_mismatch['detail']}")

    # 7. MTTR heuristic
    if incident.resolved_at and incident.started_at:
        mttr_min = (incident.resolved_at - incident.started_at).total_seconds() / 60
        findings.append(
            {
                "type": "mttr",
                "value": round(mttr_min, 1),
                "unit": "minutes",
                "severity": "info",
            }
        )
        if mttr_min > 120:
            recommendations.append(
                f"MTTR is {mttr_min:.0f} min — consider automation to reduce resolution time"
            )
    else:
        findings.append(
            {
                "type": "mttr",
                "detail": "No resolution timestamp — incident may still be active",
            }
        )

    # 8. Service impact
    if incident.service:
        findings.append(
            {
                "type": "service_impact",
                "service": incident.service,
                "severity": incident.severity,
            }
        )

    severity_parts = incident.severity.removeprefix("SEV-")
    score = max(10, 100 - int(severity_parts) * 20) if severity_parts.isdigit() else 50
    if incident.status == "resolved":
        score = min(score + 20, 100)

    analysis = AnalysisResult(
        domain="incident",
        action="analyze",
        target_id=uid,
        title=f"Incident Analysis: {incident.title}",
        summary=_build_summary(incident, len(timeline), len(dd_events)),
        findings=findings,
        recommendations=recommendations,
        score=score,
        severity="critical" if incident.severity in ("SEV-1", "SEV-2") else "info",
        raw_data={"timeline_count": len(timeline), "dd_events_found": len(dd_events)},
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis


def _assess_severity(incident: Incident, dd_events: list) -> dict | None:
    """Check if Datadog event severity matches incident severity."""
    if not dd_events:
        return None
    dd_sevs = {e.get("alert_type", "") for e in dd_events if e.get("alert_type")}
    if incident.severity == "SEV-1" and "error" not in dd_sevs:
        return {
            "type": "severity_mismatch",
            "incident_severity": incident.severity,
            "datadog_alert_types": list(dd_sevs),
            "severity": "warning",
            "detail": "SEV-1 incident but no 'error' alerts found in related Datadog events",
        }
    return None


def _build_summary(incident: Incident, timeline_count: int, dd_count: int) -> str:
    return (
        f"Incident '{incident.title}' ({incident.severity}, {incident.status}). "
        f"{timeline_count} timeline events. "
        f"{dd_count} related Datadog events found."
    )
