"""Embedding service for incident vector similarity search."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import async_session_factory
from app.core.models.incident import Incident
from app.core.models.incident_embedding import IncidentEmbedding

if TYPE_CHECKING:
    from app.core.models.rca import RcaReport
    from app.datadog_kit.models import RcaDiagnosis

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding via OpenAI-compatible API."""
    if not settings.OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY, cannot generate embedding")
        return []

    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.OPENAI_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={"model": settings.EMBEDDING_MODEL, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


def build_source_text(
    incident: Incident,
    diagnosis: RcaDiagnosis | None = None,
    rca_report: RcaReport | None = None,
) -> str:
    """Build source text for embedding from incident + diagnosis."""
    parts = []

    parts.append(f"Incident: {incident.title}")
    if incident.description:
        parts.append(f"Description: {incident.description}")

    parts.append(f"Service: {incident.service or 'unknown'}")
    parts.append(f"Environment: {incident.environment or 'unknown'}")
    parts.append(f"Severity: {incident.severity}")
    parts.append(f"Failure pattern: {incident.failure_pattern or 'unknown'}")

    if diagnosis:
        parts.append(f"Root cause: {diagnosis.root_cause}")
        parts.append(f"Root cause category: {diagnosis.root_cause_category}")
        parts.append(f"Causal chain: {' -> '.join(diagnosis.causal_chain)}")
        parts.append(f"Remediation: {'; '.join(diagnosis.remediation_steps)}")

    if rca_report and rca_report.timeline:
        timeline = rca_report.timeline
        if isinstance(timeline, dict) and "causal_chain" in timeline:
            parts.append(f"Causal chain: {timeline['causal_chain']}")

    return "\n".join(parts)


async def upsert_incident_embedding(
    incident: Incident,
    diagnosis: RcaDiagnosis | None = None,
    rca_report: RcaReport | None = None,
) -> IncidentEmbedding | None:
    """Generate and store embedding for an incident."""
    source_text = build_source_text(incident, diagnosis, rca_report)
    embedding = await generate_embedding(source_text)

    if not embedding:
        return None

    async with async_session_factory() as session:
        # Get or create embedding
        result = await session.execute(
            select(IncidentEmbedding).where(IncidentEmbedding.incident_id == incident.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.embedding = embedding
            existing.source_text = source_text
            existing.root_cause_category = diagnosis.root_cause_category if diagnosis else None
            existing.severity = diagnosis.severity if diagnosis else incident.severity
            existing.service = incident.service
            existing.environment = incident.environment
        else:
            existing = IncidentEmbedding(
                incident_id=incident.id,
                embedding=embedding,
                source_text=source_text,
                root_cause_category=diagnosis.root_cause_category if diagnosis else None,
                severity=diagnosis.severity if diagnosis else incident.severity,
                service=incident.service,
                environment=incident.environment,
            )
            session.add(existing)

        await session.commit()
        await session.refresh(existing)
        return existing


async def search_similar_incidents(
    query_text: str,
    limit: int = 5,
    threshold: float = 0.75,
    root_cause_category: str | None = None,
    severity: str | None = None,
    service: str | None = None,
) -> list[tuple[IncidentEmbedding, float]]:
    """Search for similar incidents using cosine similarity."""
    embedding = await generate_embedding(query_text)
    if not embedding:
        return []

    async with async_session_factory() as session:
        # Build query with filters
        query = select(
            IncidentEmbedding,
            IncidentEmbedding.embedding.cosine_distance(embedding).label("distance"),
        )

        if root_cause_category:
            query = query.where(IncidentEmbedding.root_cause_category == root_cause_category)
        if severity:
            query = query.where(IncidentEmbedding.severity == severity)
        if service:
            query = query.where(IncidentEmbedding.service == service)

        query = query.order_by("distance").limit(limit)

        result = await session.execute(query)
        rows = result.all()

        similar = []
        for row in rows:
            similarity = 1.0 - row.distance
            if similarity >= threshold:
                similar.append((row.IncidentEmbedding, similarity))

        return similar


async def get_incident_with_embedding(
    incident_id: str,
) -> tuple[Incident, IncidentEmbedding] | None:
    """Get incident with its embedding."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Incident)
            .options(selectinload(Incident.embedding))
            .where(Incident.id == incident_id)
        )
        incident = result.scalar_one_or_none()
        if incident and incident.embedding:
            return incident, incident.embedding
    return None


async def get_similar_incidents_context(
    query: str,
    limit: int = 3,
) -> str:
    """Get formatted similar incidents context for ReAct prompt."""
    similar = await search_similar_incidents(
        query_text=query,
        limit=limit,
        threshold=settings.SIMILARITY_THRESHOLD,
    )

    if not similar:
        return "No similar historical incidents found."

    lines = ["Similar historical incidents:"]
    for embedding, score in similar:
        incident = embedding.incident
        lines.append(
            f"  - {incident.title} (service: {incident.service}, "
            f"pattern: {incident.failure_pattern}, similarity: {score:.2f})"
        )
        if incident.description:
            lines.append(f"    Description: {incident.description[:200]}...")
        if embedding.source_text:
            lines.append(f"    Context: {embedding.source_text[:200]}...")
    return "\n".join(lines)
