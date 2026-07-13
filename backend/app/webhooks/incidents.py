"""Webhook incident ingestion (Versus parity: Alertmanager, Grafana, Sentry, CloudWatch, FluentBit)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.core.models.user import User
from app.core.db import async_session_factory
from app.core.models.incident import Incident, IncidentTimeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["webhook-incidents"])


# Source-specific payload models
class AlertmanagerAlert(BaseModel):
    status: str
    labels: dict[str, str]
    annotations: dict[str, str]
    startsAt: str
    endsAt: str | None = None
    generatorURL: str = ""


class AlertmanagerPayload(BaseModel):
    receiver: str
    status: str
    alerts: list[AlertmanagerAlert]
    groupLabels: dict[str, str] = {}
    commonLabels: dict[str, str] = {}
    commonAnnotations: dict[str, str] = {}
    externalURL: str = ""


class GrafanaAlert(BaseModel):
    status: str
    labels: dict[str, str]
    annotations: dict[str, str]
    startsAt: str
    endsAt: str | None = None
    generatorURL: str = ""


class GrafanaPayload(BaseModel):
    receiver: str
    status: str
    alerts: list[GrafanaAlert]
    groupLabels: dict[str, str] = {}
    commonLabels: dict[str, str] = {}
    commonAnnotations: dict[str, str] = {}
    externalURL: str = ""


class SentryIssue(BaseModel):
    id: str
    title: str
    culprit: str | None = None
    shortId: str
    project: dict
    metadata: dict
    status: str
    level: str
    firstSeen: str
    lastSeen: str
    count: int
    userCount: int


class SentryData(BaseModel):
    issue: SentryIssue


class SentryPayload(BaseModel):
    action: str
    data: SentryData
    installation: dict
    actor: dict


class CloudWatchRecord(BaseModel):
    EventSource: str
    EventName: str
    EventTime: str
    Message: str


class CloudWatchPayload(BaseModel):
    Type: str = "Notification"
    MessageId: str
    TopicArn: str
    Subject: str | None = None
    Message: str
    Timestamp: str
    SignatureVersion: str
    Signature: str
    SigningCertURL: str
    UnsubscribeURL: str


class FluentBitRecord(BaseModel):
    log: str
    time: int | str
    kubernetes: dict | None = None
    stream: str = "stdout"


class FluentBitPayload(BaseModel):
    records: list[FluentBitRecord]


@dataclass
class NormalizedIncident:
    """Normalized incident from any source."""
    title: str
    description: str
    severity: str
    source: str
    source_id: str
    labels: dict[str, str]
    annotations: dict[str, str]
    started_at: datetime
    service: str | None = None
    failure_pattern: str | None = None
    tags: list[str] | None = None


def normalize_alertmanager(payload: AlertmanagerPayload) -> list[NormalizedIncident]:
    """Convert Alertmanager alerts to normalized incidents."""
    incidents = []
    for alert in payload.alerts:
        severity = alert.labels.get("severity", "critical").upper()
        sev_map = {"CRITICAL": "SEV-1", "HIGH": "SEV-2", "WARNING": "SEV-3", "INFO": "SEV-4"}
        incidents.append(NormalizedIncident(
            title=alert.labels.get("alertname", "Unknown Alert"),
            description=alert.annotations.get("description", alert.annotations.get("summary", "")),
            severity=sev_map.get(severity, "SEV-3"),
            source="alertmanager",
            source_id=alert.labels.get("alertname", ""),
            labels=alert.labels,
            annotations=alert.annotations,
            started_at=datetime.fromisoformat(alert.startsAt.replace("Z", "+00:00")),
            service=alert.labels.get("service") or alert.labels.get("instance"),
            failure_pattern=alert.labels.get("alertname"),
            tags=["alertmanager", alert.status] + list(alert.labels.keys()),
        ))
    return incidents


def normalize_grafana(payload: GrafanaPayload) -> list[NormalizedIncident]:
    """Convert Grafana alerts to normalized incidents."""
    incidents = []
    for alert in payload.alerts:
        severity = alert.labels.get("severity", "critical").upper()
        sev_map = {"CRITICAL": "SEV-1", "HIGH": "SEV-2", "WARNING": "SEV-3", "INFO": "SEV-4"}
        incidents.append(NormalizedIncident(
            title=alert.labels.get("alertname", "Grafana Alert"),
            description=alert.annotations.get("description", alert.annotations.get("summary", "")),
            severity=sev_map.get(severity, "SEV-3"),
            source="grafana",
            source_id=alert.labels.get("alertname", ""),
            labels=alert.labels,
            annotations=alert.annotations,
            started_at=datetime.fromisoformat(alert.startsAt.replace("Z", "+00:00")),
            service=alert.labels.get("service") or alert.labels.get("instance"),
            failure_pattern=alert.labels.get("alertname"),
            tags=["grafana", alert.status] + list(alert.labels.keys()),
        ))
    return incidents


def normalize_sentry(payload: SentryPayload) -> list[NormalizedIncident]:
    """Convert Sentry issue to normalized incident."""
    issue = payload.data.issue
    level_map = {"error": "SEV-2", "fatal": "SEV-1", "warning": "SEV-3", "info": "SEV-4"}
    return [NormalizedIncident(
        title=issue.title,
        description=f"{issue.metadata.get('type', 'Error')}: {issue.metadata.get('value', '')}",
        severity=level_map.get(issue.level.lower(), "SEV-3"),
        source="sentry",
        source_id=issue.id,
        labels={"project": issue.project.get("name", ""), "culprit": issue.culprit or ""},
        annotations={"short_id": issue.shortId, "count": str(issue.count), "user_count": str(issue.userCount)},
        started_at=datetime.fromisoformat(issue.firstSeen.replace("Z", "+00:00")),
        service=issue.project.get("name"),
        failure_pattern=issue.metadata.get("type"),
        tags=["sentry", issue.level, payload.action],
    )]


def normalize_cloudwatch(payload: CloudWatchPayload) -> list[NormalizedIncident]:
    """Convert CloudWatch SNS message to normalized incident."""
    try:
        import json
        msg = json.loads(payload.Message)
        # Handle AlarmStateChange
        if "AlarmName" in msg:
            state = msg.get("NewStateValue", "ALARM")
            severity = "SEV-2" if state == "ALARM" else "SEV-4"
            return [NormalizedIncident(
                title=msg["AlarmName"],
                description=msg.get("AlarmDescription", ""),
                severity=severity,
                source="cloudwatch",
                source_id=msg["AlarmName"],
                labels={"region": msg.get("Region", ""), "state": state},
                annotations={"reason": msg.get("NewStateReason", "")},
                started_at=datetime.fromisoformat(payload.Timestamp.replace("Z", "+00:00")),
                service=msg.get("Trigger", {}).get("Dimensions", [{}])[0].get("value"),
                failure_pattern=msg.get("AlarmName"),
                tags=["cloudwatch", state],
            )]
    except Exception as e:
        logger.warning(f"Failed to parse CloudWatch message: {e}")

    return [NormalizedIncident(
        title=payload.Subject or "CloudWatch Notification",
        description=payload.Message[:2000],
        severity="SEV-3",
        source="cloudwatch",
        source_id=payload.MessageId,
        labels={},
        annotations={},
        started_at=datetime.fromisoformat(payload.Timestamp.replace("Z", "+00:00")),
        tags=["cloudwatch"],
    )]


def normalize_fluentbit(payload: FluentBitPayload) -> list[NormalizedIncident]:
    """Convert FluentBit records to normalized incidents (error-level only)."""
    incidents = []
    for record in payload.records:
        log_line = record.log
        # Simple heuristic: only process error/fatal/critical logs
        if not any(kw in log_line.lower() for kw in ["error", "fatal", "critical", "exception", "panic"]):
            continue

        k8s = record.kubernetes or {}
        incidents.append(NormalizedIncident(
            title=f"K8s Error: {k8s.get('container_name', 'unknown')}",
            description=log_line[:2000],
            severity="SEV-3",
            source="fluentbit",
            source_id=str(record.time),
            labels={
                "namespace": k8s.get("namespace_name", ""),
                "pod": k8s.get("pod_name", ""),
                "container": k8s.get("container_name", ""),
                "host": k8s.get("host", ""),
            },
            annotations={"stream": record.stream},
            started_at=datetime.fromtimestamp(int(record.time) / 1e9, UTC) if isinstance(record.time, (int, float)) else datetime.now(UTC),
            service=k8s.get("container_name"),
            failure_pattern="k8s-log-error",
            tags=["fluentbit", "k8s", k8s.get("namespace_name", "unknown")],
        ))
    return incidents


# Source detector
def detect_source(payload: dict) -> str:
    """Detect incident source from payload structure."""
    if "receiver" in payload and "alerts" in payload and "groupLabels" in payload:
        if "generatorURL" in payload.get("alerts", [{}])[0]:
            return "alertmanager"
        return "grafana"
    if "action" in payload and "data" in payload and "issue" in payload["data"]:
        return "sentry"
    if "Type" in payload and payload["Type"] == "Notification" and "Message" in payload:
        return "cloudwatch"
    if "records" in payload:
        return "fluentbit"
    return "unknown"


def normalize_payload(source: str, payload: dict) -> list[NormalizedIncident]:
    """Normalize payload based on detected source."""
    if source == "alertmanager":
        return normalize_alertmanager(AlertmanagerPayload(**payload))
    if source == "grafana":
        return normalize_grafana(GrafanaPayload(**payload))
    if source == "sentry":
        return normalize_sentry(SentryPayload(**payload))
    if source == "cloudwatch":
        return normalize_cloudwatch(CloudWatchPayload(**payload))
    if source == "fluentbit":
        return normalize_fluentbit(FluentBitPayload(**payload))
    # Generic fallback
    return [NormalizedIncident(
        title=payload.get("title", "Unknown Incident"),
        description=payload.get("description", ""),
        severity=payload.get("severity", "SEV-3"),
        source="generic",
        source_id=payload.get("id", "unknown"),
        labels=payload.get("labels", {}),
        annotations=payload.get("annotations", {}),
        started_at=datetime.now(UTC),
        service=payload.get("service"),
        failure_pattern=payload.get("pattern"),
        tags=payload.get("tags", ["generic"]),
    )]


@router.post("", status_code=201)
async def receive_incident(
    request: Request,
    oncall_enable: bool | None = None,
    oncall_wait_minutes: int | None = None,
    user: User = Depends(get_current_user),
):
    """
    Universal webhook endpoint for incident ingestion.

    Accepts payloads from: Alertmanager, Grafana, Sentry, CloudWatch SNS, FluentBit.
    Auto-detects source and normalizes to internal incident model.

    Query params (Versus parity):
    - oncall_enable: override on-call for this request
    - oncall_wait_minutes: override wait time before on-call triggers
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")

    source = detect_source(payload)
    logger.info(f"Received incident from {source}")

    normalized = normalize_payload(source, payload)

    created = []
    async with async_session_factory() as session:
        for inc in normalized:
            incident = Incident(
                title=inc.title,
                description=inc.description,
                severity=inc.severity,
                status="active",
                service=inc.service,
                failure_pattern=inc.failure_pattern,
                tags=inc.tags,
                llm_rca=None,
            )
            session.add(incident)
            await session.flush()

            timeline = IncidentTimeline(
                incident_id=incident.id,
                event_type="created",
                content=f"Received from {inc.source} (source_id: {inc.source_id}). Labels: {inc.labels}",
                author=f"webhook-{inc.source}",
            )
            session.add(timeline)

            created.append({
                "id": str(incident.id),
                "title": incident.title,
                "severity": incident.severity,
            })

        await session.commit()

    logger.info(f"Created {len(created)} incidents from {source}")
    return {"status": "created", "count": len(created), "incidents": created}


@router.post("/test")
async def test_webhook(request: Request):
    """Test endpoint - echoes back detected source and normalized count."""
    payload = await request.json()
    source = detect_source(payload)
    normalized = normalize_payload(source, payload)
    return {
        "detected_source": source,
        "normalized_count": len(normalized),
        "sample": normalized[0].model_dump() if normalized else None,
    }