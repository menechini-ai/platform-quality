"""Notification dispatcher for Slack, Telegram, PagerDuty."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationChannel(StrEnum):
    SLACK = "slack"
    TELEGRAM = "telegram"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"


class NotificationPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationPayload:
    """Structured notification payload."""

    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    fields: dict[str, str] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    incident_id: str | None = None
    runbook_url: str | None = None
    playbook_execution_id: str | None = None


@dataclass
class NotificationResult:
    """Result of sending a notification."""

    channel: NotificationChannel
    success: bool
    message: str = ""
    external_id: str | None = None
    error: str | None = None


class NotificationChannelBase(ABC):
    """Base class for notification channels."""

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> NotificationResult:
        """Send notification and return result."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Channel identifier."""


class SlackNotifier(NotificationChannelBase):
    """Slack webhook/bot notifier."""

    def __init__(
        self,
        webhook_url: str | None = None,
        bot_token: str | None = None,
        default_channel: str | None = None,
    ):
        self.webhook_url = webhook_url or settings.SLACK_WEBHOOK_URL
        self.bot_token = bot_token or settings.SLACK_BOT_TOKEN
        self.default_channel = default_channel or settings.SLACK_DEFAULT_CHANNEL

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SLACK

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.webhook_url and not self.bot_token:
            return NotificationResult(
                channel=self.channel,
                success=False,
                error="No Slack webhook URL or bot token configured",
            )

        try:
            color_map = {
                NotificationPriority.LOW: "#36a64f",
                NotificationPriority.NORMAL: "#2196f3",
                NotificationPriority.HIGH: "#ff9800",
                NotificationPriority.CRITICAL: "#f44336",
            }
            color = color_map.get(payload.priority, "#2196f3")

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {payload.title}"
                        if payload.priority
                        in (NotificationPriority.HIGH, NotificationPriority.CRITICAL)
                        else f"ℹ️ {payload.title}",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": payload.message},
                },
            ]

            if payload.fields:
                fields = [
                    {"type": "mrkdwn", "text": f"*{k}*:\n{v}"} for k, v in payload.fields.items()
                ]
                blocks.append({"type": "section", "fields": fields})

            if payload.links:
                link_text = " | ".join(f"<{url}|{name}>" for name, url in payload.links.items())
                blocks.append(
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": link_text}]}
                )

            if payload.tags:
                blocks.append(
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": " ".join(f"`{t}`" for t in payload.tags)}
                        ],
                    }
                )

            msg = {
                "blocks": blocks,
                "attachments": [{"color": color}] if self.bot_token else [],
            }

            if self.bot_token and self.default_channel:
                msg["channel"] = self.default_channel

            async with httpx.AsyncClient(timeout=10) as client:
                if self.bot_token:
                    resp = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={
                            "Authorization": f"Bearer {self.bot_token}",
                            "Content-Type": "application/json",
                        },
                        json=msg,
                    )
                    data = resp.json()
                    if not data.get("ok"):
                        raise RuntimeError(f"Slack API error: {data.get('error')}")
                    return NotificationResult(
                        channel=self.channel,
                        success=True,
                        external_id=data.get("ts"),
                    )
                else:
                    resp = await client.post(self.webhook_url or "", json=msg)
                    resp.raise_for_status()
                    return NotificationResult(channel=self.channel, success=True)

        except Exception as exc:
            logger.error("Slack notification failed: %s", exc)
            return NotificationResult(channel=self.channel, success=False, error=str(exc))


class TelegramNotifier(NotificationChannelBase):
    """Telegram bot notifier."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.TELEGRAM

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.bot_token or not self.chat_id:
            return NotificationResult(
                channel=self.channel,
                success=False,
                error="Telegram bot token or chat ID not configured",
            )

        try:
            priority_emoji = {
                NotificationPriority.LOW: "🟢",
                NotificationPriority.NORMAL: "🔵",
                NotificationPriority.HIGH: "🟠",
                NotificationPriority.CRITICAL: "🔴",
            }
            emoji = priority_emoji.get(payload.priority, "🔵")

            text = f"{emoji} *{payload.title}*\n\n{payload.message}"

            if payload.fields:
                text += "\n\n"
                for k, v in payload.fields.items():
                    text += f"*{k}:* `{v}`\n"

            if payload.links:
                text += "\n"
                for name, url in payload.links.items():
                    text += f"[{name}]({url})  "

            if payload.tags:
                text += f"\n\nTags: {', '.join(f'`{t}`' for t in payload.tags)}"

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return NotificationResult(
                    channel=self.channel,
                    success=True,
                    external_id=str(data.get("result", {}).get("message_id")),
                )

        except Exception as exc:
            logger.error("Telegram notification failed: %s", exc)
            return NotificationResult(channel=self.channel, success=False, error=str(exc))


class PagerDutyNotifier(NotificationChannelBase):
    """PagerDuty Events API v2 notifier."""

    def __init__(self, integration_key: str | None = None):
        self.integration_key = integration_key or settings.PAGERDUTY_INTEGRATION_KEY
        self.api_url = "https://events.pagerduty.com/v2/enqueue"

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.PAGERDUTY

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.integration_key:
            return NotificationResult(
                channel=self.channel,
                success=False,
                error="PagerDuty integration key not configured",
            )

        try:
            severity_map = {
                NotificationPriority.LOW: "info",
                NotificationPriority.NORMAL: "warning",
                NotificationPriority.HIGH: "error",
                NotificationPriority.CRITICAL: "critical",
            }
            severity = severity_map.get(payload.priority, "warning")

            details = {
                "message": payload.message,
                "fields": payload.fields,
                "links": payload.links,
                "tags": payload.tags,
            }

            if payload.incident_id:
                details["incident_id"] = payload.incident_id
            if payload.runbook_url:
                details["runbook_url"] = payload.runbook_url

            event = {
                "routing_key": self.integration_key,
                "event_action": "trigger",
                "payload": {
                    "summary": payload.title,
                    "source": "ObservAI",
                    "severity": severity,
                    "custom_details": details,
                },
            }

            if payload.incident_id:
                event["dedup_key"] = payload.incident_id

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(self.api_url, json=event)
                resp.raise_for_status()
                data = resp.json()
                return NotificationResult(
                    channel=self.channel,
                    success=True,
                    external_id=data.get("dedup_key"),
                )

        except Exception as exc:
            logger.error("PagerDuty notification failed: %s", exc)
            return NotificationResult(channel=self.channel, success=False, error=str(exc))


class NotificationDispatcher:
    """Dispatches notifications to multiple channels."""

    def __init__(self):
        self.channels: dict[NotificationChannel, NotificationChannelBase] = {}
        self._init_channels()

    def _init_channels(self):
        if settings.SLACK_WEBHOOK_URL or settings.SLACK_BOT_TOKEN:
            self.channels[NotificationChannel.SLACK] = SlackNotifier()
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            self.channels[NotificationChannel.TELEGRAM] = TelegramNotifier()
        if settings.PAGERDUTY_INTEGRATION_KEY:
            self.channels[NotificationChannel.PAGERDUTY] = PagerDutyNotifier()

    async def send(
        self,
        payload: NotificationPayload,
        channels: list[NotificationChannel] | None = None,
    ) -> list[NotificationResult]:
        """Send payload to specified channels (or all configured)."""
        target_channels = channels or list(self.channels.keys())
        results = []

        for ch in target_channels:
            notifier = self.channels.get(ch)
            if not notifier:
                results.append(
                    NotificationResult(
                        channel=ch,
                        success=False,
                        error=f"Channel {ch.value} not configured",
                    )
                )
                continue
            result = await notifier.send(payload)
            results.append(result)

        return results


def build_incident_notification(
    incident_title: str,
    diagnosis: dict[str, Any],
    incident_id: str | None = None,
    runbook_url: str | None = None,
    investigation_url: str | None = None,
) -> NotificationPayload:
    """Build notification from investigation diagnosis."""
    root_cause = diagnosis.get("root_cause", "Unknown")
    severity = diagnosis.get("severity", "P3")
    confidence = diagnosis.get("confidence", 0.0)
    causal_chain = diagnosis.get("causal_chain", [])
    remediation = diagnosis.get("remediation_steps", [])

    priority_map = {
        "P1": NotificationPriority.CRITICAL,
        "P2": NotificationPriority.HIGH,
        "P3": NotificationPriority.NORMAL,
        "P4": NotificationPriority.LOW,
    }
    priority = priority_map.get(severity, NotificationPriority.NORMAL)

    fields = {
        "Root Cause": root_cause,
        "Severity": severity,
        "Confidence": f"{confidence:.0%}",
    }
    if incident_id:
        fields["Incident ID"] = incident_id

    links = {}
    if runbook_url:
        links["Runbook"] = runbook_url
    if investigation_url:
        links["Investigation"] = investigation_url

    tags = ["rca", "datadog", severity.lower()]
    if causal_chain:
        tags.append("causal-chain")

    message = f"Root cause identified: {root_cause}"
    if causal_chain:
        message += "\n\nCausal chain:\n" + "\n".join(f"  → {c}" for c in causal_chain)
    if remediation:
        message += "\n\nRemediation:\n" + "\n".join(f"  • {r}" for r in remediation[:5])

    return NotificationPayload(
        title=f"Incident RCA: {incident_title}",
        message=message,
        priority=priority,
        fields=fields,
        links=links,
        tags=tags,
        incident_id=incident_id,
        runbook_url=runbook_url,
    )


def build_playbook_notification(
    playbook_title: str,
    execution: dict[str, Any],
    investigation_url: str | None = None,
) -> NotificationPayload:
    """Build notification from playbook execution result."""
    overall = execution.get("overall_status", "unknown")
    steps = execution.get("steps", [])
    duration = execution.get("duration_seconds", 0)

    success_count = sum(1 for s in steps if s.get("status") == "success")
    failed_count = sum(1 for s in steps if s.get("status") == "failed")
    skipped_count = sum(1 for s in steps if s.get("status") == "skipped")

    priority = NotificationPriority.CRITICAL if failed_count > 0 else NotificationPriority.NORMAL

    fields = {
        "Overall Status": overall.upper(),
        "Steps": f"{success_count} ok, {failed_count} failed, {skipped_count} skipped",
        "Duration": f"{duration:.1f}s",
    }

    links = {}
    if investigation_url:
        links["Investigation"] = investigation_url

    def _step_icon(status: str) -> str:
        if status == "success":
            return "✅"
        if status == "failed":
            return "❌"
        return "⏭️"

    step_details = "\n".join(
        f"  {_step_icon(s.get('status', ''))} {s.get('step_name', 'unknown')}: "
        f"{s.get('output', s.get('error', ''))[:100]}"
        for s in steps[:10]
    )

    message = f"Playbook execution completed.\n\nSteps:\n{step_details}"

    return NotificationPayload(
        title=f"Playbook: {playbook_title}",
        message=message,
        priority=priority,
        fields=fields,
        links=links,
        tags=["playbook", "remediation", overall.lower()],
    )
