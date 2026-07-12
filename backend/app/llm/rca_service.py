"""LLM-powered RCA report generation service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

if TYPE_CHECKING:
    from uuid import UUID

from app.core.db import get_db
from app.core.models.incident import Incident
from app.llm import LiteLLMClient


async def generate_rca(incident_id: UUID, description: str | None = None) -> str:
    """Generate an LLM-powered RCA report for an incident.

    Fetches the incident from DB, calls LiteLLM with incident context,
    stores the result in ``incident.llm_rca``, and returns the text.

    Args:
        incident_id: UUID of the incident to analyze.
        description: Optional override description — uses incident's own
                     description if not provided.

    Returns:
        The generated RCA text.

    Raises:
        ValueError: If the incident is not found.
    """

    async for db in get_db():
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        text = description or incident.description or "No description available"

        prompt = (
            f"Perform a root cause analysis for the following incident:\n\n"
            f"Title: {incident.title}\n"
            f"Severity: {incident.severity}\n"
            f"Service: {incident.service or 'unknown'}\n"
            f"Failure Pattern: {incident.failure_pattern or 'unknown'}\n"
            f"Description: {text}\n\n"
            f"Provide: 1) Root cause 2) Contributing factors 3) Recommended actions"
        )

        client = LiteLLMClient()
        rca_text = client.complete(
            prompt=prompt,
            system_prompt="You are an expert SRE performing root cause analysis.",
        )

        incident.llm_rca = rca_text
        await db.flush()
        await db.refresh(incident)
        return rca_text


def generate_rca_sync(incident_id: UUID, description: str | None = None) -> str:
    """Synchronous wrapper for generate_rca (for use in non-async contexts)."""
    import asyncio  # noqa: PLC0415

    return asyncio.run(generate_rca(incident_id, description))
