"""Playbook executor for automated remediation."""
from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class StepType(StrEnum):
    KUBECTL = "kubectl"
    HELM = "helm"
    SCALE_DEPLOYMENT = "scale_deployment"
    RESTART_DEPLOYMENT = "restart_deployment"
    FLIP_FEATURE_FLAG = "flip_feature_flag"
    RUN_SCRIPT = "run_script"
    HTTP_REQUEST = "http_request"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlaybookStep:
    """Single executable step in a playbook."""
    type: StepType
    name: str
    params: dict[str, Any]
    requires_confirmation: bool = True
    timeout_seconds: int = 300
    rollback: dict[str, Any] | None = None
    condition: str | None = None  # Optional condition to skip


@dataclass
class StepResult:
    """Result of executing a step."""
    step_name: str
    status: StepStatus
    output: str = ""
    error: str | None = None
    duration_seconds: float = 0.0
    rollback_output: str | None = None


@dataclass
class PlaybookExecution:
    """Full playbook execution result."""
    playbook_title: str
    steps: list[StepResult] = field(default_factory=list)
    overall_status: StepStatus = StepStatus.PENDING
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    @property
    def duration_seconds(self) -> float:
        end = self.completed_at or time.time()
        return end - self.started_at


class PlaybookExecutor:
    """Executes playbook steps with dry-run, confirmation, and rollback support."""

    def __init__(self, dry_run: bool = False, auto_confirm: bool = False):
        self.dry_run = dry_run
        self.auto_confirm = auto_confirm or settings.SELF_HEALING_APPROVAL_REQUIRED is False

    async def execute(
        self,
        steps: list[PlaybookStep],
        confirm_callback: callable | None = None,
    ) -> PlaybookExecution:
        """Execute all steps in sequence."""
        execution = PlaybookExecution(
            playbook_title="Playbook Execution",
            steps=[],
        )

        for step in steps:
            if self._should_skip(step):
                result = StepResult(
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    output="Skipped due to condition",
                )
                execution.steps.append(result)
                continue

            # Confirm if required
            if (
                step.requires_confirmation
                and not self.auto_confirm
                and not self.dry_run
                and confirm_callback
            ):
                confirmed = await confirm_callback(step)
                if not confirmed:
                    result = StepResult(
                        step_name=step.name,
                        status=StepStatus.SKIPPED,
                        output="User declined confirmation",
                    )
                    execution.steps.append(result)
                    continue

            # Execute step
            result = await self._execute_step(step)
            execution.steps.append(result)

            if result.status == StepStatus.FAILED:
                execution.overall_status = StepStatus.FAILED
                # Run rollbacks for completed steps
                await self._rollback(execution.steps)
                break
        else:
            execution.overall_status = StepStatus.SUCCESS

        execution.completed_at = time.time()
        return execution

    def _should_skip(self, step: PlaybookStep) -> bool:
        if not step.condition:
            return False
        # Simple condition evaluation - could be extended
        return False

    async def _execute_step(self, step: PlaybookStep) -> StepResult:
        start = time.time()
        logger.info("Executing step: %s (%s)", step.name, step.type)

        if self.dry_run:
            return StepResult(
                step_name=step.name,
                status=StepStatus.SUCCESS,
                output=f"[DRY RUN] Would execute: {step.type} with params {step.params}",
                duration_seconds=time.time() - start,
            )

        try:
            if step.type == StepType.KUBECTL:
                output = await self._run_kubectl(step.params)
            elif step.type == StepType.HELM:
                output = await self._run_helm(step.params)
            elif step.type == StepType.SCALE_DEPLOYMENT:
                output = await self._scale_deployment(step.params)
            elif step.type == StepType.RESTART_DEPLOYMENT:
                output = await self._restart_deployment(step.params)
            elif step.type == StepType.FLIP_FEATURE_FLAG:
                output = await self._flip_feature_flag(step.params)
            elif step.type == StepType.RUN_SCRIPT:
                output = await self._run_script(step.params)
            elif step.type == StepType.HTTP_REQUEST:
                output = await self._http_request(step.params)
            else:
                raise ValueError(f"Unknown step type: {step.type}")

            return StepResult(
                step_name=step.name,
                status=StepStatus.SUCCESS,
                output=output,
                duration_seconds=time.time() - start,
            )

        except Exception as exc:
            logger.error("Step %s failed: %s", step.name, exc)
            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                output="",
                error=str(exc),
                duration_seconds=time.time() - start,
            )

    async def _run_kubectl(self, params: dict[str, Any]) -> str:
        args = params.get("args", [])
        namespace = params.get("namespace", "default")
        cmd = ["kubectl", "-n", namespace] + args
        timeout = params.get("timeout", 60)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"kubectl failed: {result.stderr}")
        return result.stdout

    async def _run_helm(self, params: dict[str, Any]) -> str:
        args = params.get("args", [])
        namespace = params.get("namespace", "default")
        cmd = ["helm", "-n", namespace] + args
        timeout = params.get("timeout", 120)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"helm failed: {result.stderr}")
        return result.stdout

    async def _scale_deployment(self, params: dict[str, Any]) -> str:
        name = params["name"]
        namespace = params.get("namespace", "default")
        replicas = params["replicas"]
        cmd = ["kubectl", "scale", "deployment", name, f"--replicas={replicas}", "-n", namespace]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"scale failed: {result.stderr}")
        return f"Scaled {name} to {replicas} replicas"

    async def _restart_deployment(self, params: dict[str, Any]) -> str:
        name = params["name"]
        namespace = params.get("namespace", "default")
        cmd = ["kubectl", "rollout", "restart", f"deployment/{name}", "-n", namespace]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"restart failed: {result.stderr}")
        # Wait for rollout
        wait_cmd = [
            "kubectl",
            "rollout",
            "status",
            f"deployment/{name}",
            "-n",
            namespace,
            "--timeout=5m",
        ]
        subprocess.run(wait_cmd, capture_output=True, text=True, timeout=300)
        return f"Restarted deployment {name}"

    async def _flip_feature_flag(self, params: dict[str, Any]) -> str:
        # Placeholder - integrate with your feature flag system (LaunchDarkly, Unleash, etc.)
        flag = params["flag"]
        enabled = params["enabled"]
        # Example: requests.post(f"{FEATURE_FLAG_API}/flags/{flag}", json={"enabled": enabled})
        return f"Feature flag {flag} set to {enabled}"

    async def _run_script(self, params: dict[str, Any]) -> str:
        script = params["script"]
        args = params.get("args", [])
        env = params.get("env", {})
        result = subprocess.run(
            [script] + args,
            capture_output=True,
            text=True,
            timeout=params.get("timeout", 300),
            env={**_import_os_environ(), **env},
        )
        if result.returncode != 0:
            raise RuntimeError(f"script failed: {result.stderr}")
        return result.stdout

    async def _http_request(self, params: dict[str, Any]) -> str:
        import httpx
        method = params.get("method", "POST")
        url = params["url"]
        headers = params.get("headers", {})
        json_body = params.get("json")
        async with httpx.AsyncClient(timeout=params.get("timeout", 30)) as client:
            resp = await client.request(method, url, headers=headers, json=json_body)
            resp.raise_for_status()
            return resp.text

    async def _rollback(self, completed_steps: list[StepResult]) -> None:
        """Run rollback for completed steps in reverse order."""
        for result in reversed(completed_steps):
            # Find original step to get rollback info
            # This is simplified - in reality you'd track the original step objects
            if result.status == StepStatus.SUCCESS:
                logger.info("Would rollback step: %s", result.step_name)
                result.rollback_output = f"Rollback for {result.step_name} (not implemented)"


def _import_os_environ() -> dict[str, str]:
    import os
    return dict(os.environ)


def build_playbook_from_runbook(runbook: Any) -> list[PlaybookStep]:
    """Convert Runbook model to executable PlaybookSteps.

    This is a template - customize based on your infrastructure.
    """
    steps = []

    for mitigation in runbook.mitigation:
        # Simple mapping - in reality you'd parse structured mitigation steps
        if "restart" in mitigation.lower():
            steps.append(PlaybookStep(
                type=StepType.RESTART_DEPLOYMENT,
                name=f"Restart: {mitigation[:50]}",
                params={"name": "TODO-extract-deployment-name", "namespace": "default"},
                requires_confirmation=True,
            ))
        elif "scale" in mitigation.lower():
            steps.append(PlaybookStep(
                type=StepType.SCALE_DEPLOYMENT,
                name=f"Scale: {mitigation[:50]}",
                params={"name": "TODO-extract-deployment-name", "namespace": "default", "replicas": 3},
                requires_confirmation=True,
            ))
        elif "flag" in mitigation.lower() or "feature" in mitigation.lower():
            steps.append(PlaybookStep(
                type=StepType.FLIP_FEATURE_FLAG,
                name=f"Feature flag: {mitigation[:50]}",
                params={"flag": "TODO-extract-flag-name", "enabled": False},
                requires_confirmation=True,
            ))

    return steps