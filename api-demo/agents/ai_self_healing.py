"""AI-augmented self-healing — uses LLM to select and recommend runbook actions.

Extends the rule-based self-healing pattern by leveraging the LangGraph
pipeline to analyze incidents and suggest remediation steps.
"""

from __future__ import annotations

from typing import Any

from agents.langgraph_pipeline import run_pipeline


class AISelfHealing:
    """LLM-driven runbook selection and remediation recommendation.

    Args:
        auto_approve: If True, skips the approval gate (default: False).
    """

    def __init__(self, auto_approve: bool = False) -> None:
        self.auto_approve = auto_approve

    async def analyze(
        self,
        incident_id: str,
        description: str,
    ) -> dict[str, Any]:
        """Analyze an incident and return a remediation plan.

        Returns:
            Dict with ``incident_id``, ``analysis``, ``recommendation``,
            ``approved``, ``status``, ``executed``.
        """
        state = await run_pipeline(incident_id=incident_id, description=description)

        result: dict[str, Any] = {
            "incident_id": incident_id,
            "analysis": state.get("analysis"),
            "recommendation": state.get("recommendation"),
            "approved": self.auto_approve,
            "status": "approved" if self.auto_approve else "pending",
            "executed": False,
        }

        if not result["analysis"]:
            result["status"] = "failed"
            return result

        if not result["recommendation"]:
            result["status"] = "no_recommendation"
            return result

        return result

    async def execute(self, incident_id: str, description: str) -> dict[str, Any]:
        """Analyze and (if approved) mark the remediation as applied."""
        result = await self.analyze(incident_id, description)
        if result["status"] == "approved":
            result["executed"] = True
        else:
            result["executed"] = False
        return result
