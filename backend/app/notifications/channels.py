"""Notification channels (Versus parity: Slack, Teams, Telegram, Email, PagerDuty, Opsgenie)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from datetime import datetime

    from app.core.models.incident import Incident

logger = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    """Standard notification payload."""

    incident: Incident
    title: str
    message: str
    severity: str
    timestamp: datetime
    source: str = "webhook"
    tags: list[str] | None = None
    actions: list[dict] | None = None  # For Slack/Teams buttons


class NotificationChannel(ABC):
    """Abstract notification channel."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Send notification. Returns success."""
        pass


class SlackChannel(NotificationChannel):
    """Slack webhook notification."""

    def __init__(self, webhook_url: str, channel: str | None = None):
        self.webhook_url = webhook_url
        self.channel = channel
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "slack"

    async def send(self, payload: NotificationPayload) -> bool:
        severity_colors = {
            "SEV-1": "#FF0000",
            "SEV-2": "#FF8C00",
            "SEV-3": "#FFD700",
            "SEV-4": "#32CD32",
        }
        color = severity_colors.get(payload.severity, "#808080")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🚨 {payload.title}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{payload.severity}"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{payload.source}"},
                    {"type": "mrkdwn", "text": f"*Service:*\n{payload.incident.service or 'N/A'}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Description:*\n{payload.message[:1500]}"},
            },
        ]

        if payload.tags:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": " ".join(f"`{t}`" for t in payload.tags[:10])}
                    ],
                }
            )

        if payload.actions:
            blocks.append({"type": "actions", "elements": payload.actions})

        data = {"attachments": [{"color": color, "blocks": blocks}]}
        if self.channel:
            data["channel"] = self.channel

        try:
            resp = await self._client.post(self.webhook_url, json=data)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Slack notification failed: %s", e)
            return False


class TeamsChannel(NotificationChannel):
    """Microsoft Teams webhook notification."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "teams"

    async def send(self, payload: NotificationPayload) -> bool:
        severity_colors = {
            "SEV-1": "FF0000",
            "SEV-2": "FF8C00",
            "SEV-3": "FFD700",
            "SEV-4": "32CD32",
        }
        color = severity_colors.get(payload.severity, "808080")

        facts = [
            {"name": "Severity", "value": payload.severity},
            {"name": "Source", "value": payload.source},
            {"name": "Service", "value": payload.incident.service or "N/A"},
            {"name": "Time", "value": payload.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")},
        ]

        if payload.tags:
            facts.append({"name": "Tags", "value": ", ".join(payload.tags[:10])})

        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": payload.title,
            "sections": [
                {
                    "activityTitle": f"🚨 {payload.title}",
                    "activitySubtitle": f"Incident from {payload.source}",
                    "facts": facts,
                    "text": payload.message[:2000],
                }
            ],
        }

        if payload.actions:
            card["potentialAction"] = payload.actions

        try:
            resp = await self._client.post(self.webhook_url, json=card)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Teams notification failed: %s", e)
            return False


class TelegramChannel(NotificationChannel):
    """Telegram bot notification."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "telegram"

    async def send(self, payload: NotificationPayload) -> bool:
        severity_emoji = {"SEV-1": "🔴", "SEV-2": "🟠", "SEV-3": "🟡", "SEV-4": "🟢"}
        emoji = severity_emoji.get(payload.severity, "⚪")

        text = (
            f"{emoji} *{payload.title}*\n\n"
            f"*Severity:* {payload.severity}\n"
            f"*Source:* {payload.source}\n"
            f"*Service:* {payload.incident.service or 'N/A'}\n"
            f"*Time:* {payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            f"{payload.message[:2000]}"
        )

        if payload.tags:
            text += f"\n\nTags: {', '.join(f'`{t}`' for t in payload.tags[:10])}"

        try:
            resp = await self._client.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)
            return False


class PagerDutyChannel(NotificationChannel):
    """PagerDuty Events API v2 notification."""

    def __init__(self, routing_key: str):
        self.routing_key = routing_key
        self._client = httpx.AsyncClient(timeout=10.0)
        self._base_url = "https://events.pagerduty.com/v2/enqueue"

    @property
    def name(self) -> str:
        return "pagerduty"

    async def send(self, payload: NotificationPayload) -> bool:
        severity_map = {"SEV-1": "critical", "SEV-2": "error", "SEV-3": "warning", "SEV-4": "info"}

        event = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": str(payload.incident.id),
            "payload": {
                "summary": payload.title,
                "source": payload.source,
                "severity": severity_map.get(payload.severity, "error"),
                "component": payload.incident.service,
                "group": "ObservAI",
                "class": payload.incident.failure_pattern,
                "custom_details": {
                    "description": payload.message,
                    "tags": payload.tags,
                    "incident_id": str(payload.incident.id),
                },
            },
        }

        try:
            resp = await self._client.post(self._base_url, json=event)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("PagerDuty notification failed: %s", e)
            return False


class OpsgenieChannel(NotificationChannel):
    """Opsgenie Alert API notification."""

    def __init__(self, api_key: str, api_url: str = "https://api.opsgenie.com/v2/alerts"):
        self.api_key = api_key
        self.api_url = api_url
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "opsgenie"

    async def send(self, payload: NotificationPayload) -> bool:
        severity_map = {"SEV-1": "P1", "SEV-2": "P2", "SEV-3": "P3", "SEV-4": "P4", "SEV-5": "P5"}

        alert = {
            "message": payload.title,
            "alias": str(payload.incident.id),
            "description": payload.message,
            "priority": severity_map.get(payload.severity, "P3"),
            "source": payload.source,
            "tags": payload.tags or [],
            "details": {
                "service": payload.incident.service,
                "failure_pattern": payload.incident.failure_pattern,
                "incident_id": str(payload.incident.id),
            },
        }

        try:
            resp = await self._client.post(
                self.api_url,
                json=alert,
                headers={
                    "Authorization": f"GenieKey {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Opsgenie notification failed: %s", e)
            return False


class EmailChannel(NotificationChannel):
    """Email notification via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: list[str],
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

    @property
    def name(self) -> str:
        return "email"

    async def send(self, payload: NotificationPayload) -> bool:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.to_emails)
        msg["Subject"] = f"[{payload.severity}] {payload.title}"

        body = f"""Incident Alert

Title: {payload.title}
Severity: {payload.severity}
Source: {payload.source}
Service: {payload.incident.service or "N/A"}
Time: {payload.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}

Description:
{payload.message}

Tags: {", ".join(payload.tags or [])}
Incident ID: {payload.incident.id}
"""
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error("Email notification failed: %s", e)
            return False


class NotificationManager:
    """Manages all notification channels."""

    def __init__(self):
        self.channels: list[NotificationChannel] = []

    def add_channel(self, channel: NotificationChannel) -> None:
        self.channels.append(channel)

    def get_channel(self, name: str) -> NotificationChannel | None:
        for ch in self.channels:
            if ch.name == name:
                return ch
        return None

    async def notify_all(self, payload: NotificationPayload) -> dict[str, bool]:
        """Send to all enabled channels."""
        results = {}
        for ch in self.channels:
            try:
                results[ch.name] = await ch.send(payload)
            except Exception as e:
                logger.error("Channel %s failed: %s", ch.name, e)
                results[ch.name] = False
        return results

    async def notify_channels(
        self, payload: NotificationPayload, channel_names: list[str]
    ) -> dict[str, bool]:
        """Send to specific channels."""
        results = {}
        for name in channel_names:
            ch = self.get_channel(name)
            if ch:
                try:
                    results[name] = await ch.send(payload)
                except Exception as e:
                    logger.error("Channel %s failed: %s", name, e)
                    results[name] = False
            else:
                results[name] = False
        return results


# Global notification manager
_notification_manager: NotificationManager | None = None


def get_notification_manager() -> NotificationManager:
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


async def init_notifications(config: dict) -> NotificationManager:
    """Initialize notification channels from config."""
    manager = get_notification_manager()

    # Slack
    slack = config.get("notifications", {}).get("slack", {})
    if slack.get("webhook_url"):
        manager.add_channel(SlackChannel(slack["webhook_url"], slack.get("channel")))

    # Teams
    teams = config.get("notifications", {}).get("teams", {})
    if teams.get("webhook_url"):
        manager.add_channel(TeamsChannel(teams["webhook_url"]))

    # Telegram
    tg = config.get("notifications", {}).get("telegram", {})
    if tg.get("bot_token") and tg.get("chat_id"):
        manager.add_channel(TelegramChannel(tg["bot_token"], tg["chat_id"]))

    # PagerDuty
    pd = config.get("notifications", {}).get("pagerduty", {})
    if pd.get("routing_key"):
        manager.add_channel(PagerDutyChannel(pd["routing_key"]))

    # Opsgenie
    og = config.get("notifications", {}).get("opsgenie", {})
    if og.get("api_key"):
        manager.add_channel(OpsgenieChannel(og["api_key"], og.get("api_url")))

    # Email
    email = config.get("notifications", {}).get("email", {})
    if email.get("smtp_host") and email.get("to_emails"):
        manager.add_channel(
            EmailChannel(
                smtp_host=email["smtp_host"],
                smtp_port=email.get("smtp_port", 587),
                username=email["username"],
                password=email["password"],
                from_email=email["from_email"],
                to_emails=email["to_emails"],
                use_tls=email.get("use_tls", True),
            )
        )

    return manager
