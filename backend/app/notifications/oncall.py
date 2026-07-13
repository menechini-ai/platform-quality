"""On-call integration (PagerDuty, AWS Incident Manager) - Versus parity."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.models.incident import Incident

logger = logging.getLogger(__name__)


@dataclass
class OnCallConfig:
    """On-call configuration."""
    initialized_only: bool = True
    enable: bool = False
    wait_minutes: int = 3
    provider: str = "pagerduty"  # pagerduty | aws_incident_manager
    pagerduty: dict | None = None
    aws_incident_manager: dict | None = None


class OnCallProvider(ABC):
    """Abstract on-call provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def trigger_oncall(self, incident: Incident, wait_minutes: int = 0) -> bool:
        """Trigger on-call escalation. Returns success."""
        pass

    @abstractmethod
    async def acknowledge(self, incident_id: str) -> bool:
        """Acknowledge on-call alert."""
        pass


class PagerDutyOnCall(OnCallProvider):
    """PagerDuty on-call integration."""

    def __init__(self, routing_key: str, other_keys: dict[str, str] | None = None):
        self.routing_key = routing_key
        self.other_keys = other_keys or {}
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "pagerduty"

    async def trigger_oncall(self, incident: Incident, wait_minutes: int = 0) -> bool:
        severity_map = {"SEV-1": "critical", "SEV-2": "error", "SEV-3": "warning", "SEV-4": "info"}

        event = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": f"oncall-{incident.id}",
            "payload": {
                "summary": f"[ON-CALL] {incident.title}",
                "source": incident.service or "observai",
                "severity": severity_map.get(incident.severity, "error"),
                "component": incident.service,
                "group": "ObservAI On-Call",
                "class": incident.failure_pattern,
                "custom_details": {
                    "incident_id": str(incident.id),
                    "description": incident.description,
                    "tags": incident.tags,
                    "wait_minutes": wait_minutes,
                },
            },
        }

        try:
            resp = await self._client.post("https://events.pagerduty.com/v2/enqueue", json=event)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"PagerDuty on-call triggered: {data}")
            return True
        except Exception as e:
            logger.error(f"PagerDuty on-call trigger failed: {e}")
            return False

    async def trigger_with_override(self, incident: Incident, env: str) -> bool:
        """Trigger on-call with environment-specific routing key."""
        routing_key = self.other_keys.get(env, self.routing_key)
        event = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "dedup_key": f"oncall-{incident.id}-{env}",
            "payload": {
                "summary": f"[ON-CALL-{env.upper()}] {incident.title}",
                "source": incident.service or "observai",
                "severity": "critical",
                "component": incident.service,
                "group": "ObservAI On-Call",
                "class": incident.failure_pattern,
                "custom_details": {"incident_id": str(incident.id), "environment": env},
            },
        }
        try:
            resp = await self._client.post("https://events.pagerduty.com/v2/enqueue", json=event)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"PagerDuty override trigger failed: {e}")
            return False

    async def acknowledge(self, incident_id: str) -> bool:
        # PagerDuty uses Events API for ack via resolve
        event = {
            "routing_key": self.routing_key,
            "event_action": "acknowledge",
            "dedup_key": f"oncall-{incident_id}",
        }
        try:
            resp = await self._client.post("https://events.pagerduty.com/v2/enqueue", json=event)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"PagerDuty ack failed: {e}")
            return False


class AWSIncidentManagerOnCall(OnCallProvider):
    """AWS Incident Manager (SSM Incident Manager) on-call integration."""

    def __init__(
        self,
        response_plan_arn: str,
        other_plans: dict[str, str] | None = None,
        region: str = "us-east-1",
    ):
        self.response_plan_arn = response_plan_arn
        self.other_plans = other_plans or {}
        self.region = region
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def name(self) -> str:
        return "aws_incident_manager"

    async def trigger_oncall(self, incident: Incident, wait_minutes: int = 0) -> bool:
        # Use AWS CLI via subprocess since boto3 is heavy
        import subprocess
        import json

        title = f"[ON-CALL] {incident.title}"
        detail = {
            "incident_id": str(incident.id),
            "service": incident.service,
            "severity": incident.severity,
            "description": incident.description,
            "tags": incident.tags,
        }

        cmd = [
            "aws", "ssm-incidents", "start-incident",
            "--response-plan-arn", self.response_plan_arn,
            "--title", title,
            "--client-token", str(incident.id),
            "--related-items", json.dumps([{
                "identifier": {"type": "ARN", "value": f"arn:aws:events:{self.region}:*:rule/observai-incident"},
                "title": "ObservAI Incident",
            }]),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"AWS Incident Manager triggered: {result.stdout}")
                return True
            logger.error(f"AWS Incident Manager failed: {result.stderr}")
            return False
        except Exception as e:
            logger.error(f"AWS Incident Manager trigger failed: {e}")
            return False

    async def trigger_with_override(self, incident: Incident, env: str) -> bool:
        plan_arn = self.other_plans.get(env, self.response_plan_arn)
        title = f"[ON-CALL-{env.upper()}] {incident.title}"

        import subprocess
        import json

        cmd = [
            "aws", "ssm-incidents", "start-incident",
            "--response-plan-arn", plan_arn,
            "--title", title,
            "--client-token", f"{incident.id}-{env}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"AWS Incident Manager override failed: {e}")
            return False

    async def acknowledge(self, incident_id: str) -> bool:
        # AWS Incident Manager doesn't have direct ack via API easily
        # Would need to use update-incident or related-items
        logger.info(f"AWS Incident Manager ack for {incident_id} - manual in console")
        return True


class OnCallManager:
    """Manages on-call providers."""

    def __init__(self):
        self.provider: OnCallProvider | None = None
        self.config: OnCallConfig | None = None

    def initialize(self, config: OnCallConfig) -> None:
        self.config = config
        if not config.enable:
            return

        if config.provider == "pagerduty":
            pd_config = config.pagerduty or {}
            self.provider = PagerDutyOnCall(
                routing_key=pd_config.get("routing_key", ""),
                other_keys=pd_config.get("other_routing_keys"),
            )
        elif config.provider == "aws_incident_manager":
            aws_config = config.aws_incident_manager or {}
            self.provider = AWSIncidentManagerOnCall(
                response_plan_arn=aws_config.get("response_plan_arn", ""),
                other_plans=aws_config.get("other_response_plan_arns"),
                region=aws_config.get("region", "us-east-1"),
            )
        else:
            logger.warning(f"Unknown on-call provider: {config.provider}")

    async def maybe_trigger_oncall(self, incident: Incident, wait_minutes: int | None = None) -> bool:
        """Trigger on-call if conditions met."""
        if not self.config or not self.config.enable:
            return False

        # Check if initialized_only mode - only trigger if explicitly enabled
        if self.config.initialized_only:
            # In Versus, this means don't auto-trigger unless query param says so
            # Here we check if wait_minutes was explicitly provided (override)
            if wait_minutes is None:
                return False

        wait_time = wait_minutes if wait_minutes is not None else self.config.wait_minutes

        if self.provider:
            logger.info(f"Triggering on-call via {self.provider.name} for incident {incident.id}")
            return await self.provider.trigger_oncall(incident, wait_time)

        return False

    async def trigger_with_env_override(self, incident: Incident, env: str) -> bool:
        """Trigger on-call with environment-specific routing."""
        if not self.config or not self.config.enable or not self.provider:
            return False

        if isinstance(self.provider, PagerDutyOnCall):
            return await self.provider.trigger_with_override(incident, env)
        elif isinstance(self.provider, AWSIncidentManagerOnCall):
            return await self.provider.trigger_with_override(incident, env)

        return False

    async def acknowledge(self, incident_id: str) -> bool:
        """Acknowledge on-call alert."""
        if self.provider:
            return await self.provider.acknowledge(incident_id)
        return False


# Global on-call manager
_oncall_manager: OnCallManager | None = None


def get_oncall_manager() -> OnCallManager:
    global _oncall_manager
    if _oncall_manager is None:
        _oncall_manager = OnCallManager()
    return _oncall_manager


async def init_oncall(config: OnCallConfig) -> OnCallManager:
    """Initialize on-call manager from config."""
    manager = get_oncall_manager()
    manager.initialize(config)
    return manager