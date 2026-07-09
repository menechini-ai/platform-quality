"""Semantic KB search service using embeddings."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import select

from app.core.db import get_db
from app.core.models.knowledge_base import KnowledgeBase
from app.llm.service import cosine_similarity, embed_text


async def search_kb(query: str, k: int = 3) -> list[dict[str, Any]]:
    """Search the knowledge base semantically using embedding similarity.

    Embeds the query, retrieves all KB entries, ranks by cosine similarity,
    and returns the top-K results.

    Args:
        query: Natural language search query.
        k: Number of results to return (default 3).

    Returns:
        List of dicts with keys: id, title, symptom_pattern, root_cause,
        resolution_steps, tags, score.
    """

    query_emb = embed_text(query)

    async for db in get_db():
        result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
        entries = result.scalars().all()

    scored: list[tuple[float, KnowledgeBase]] = []
    for entry in entries:
        if entry.embedding is None:
            continue
        emb = _parse_embedding(entry.embedding)
        if emb is None:
            continue
        try:
            score = cosine_similarity(query_emb, emb)
            # Normalize NaN to 0
            if math.isnan(score):
                score = 0.0
            scored.append((score, entry))
        except ValueError:
            continue

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "id": str(entry.id),
            "title": entry.title,
            "symptom_pattern": entry.symptom_pattern,
            "root_cause": entry.root_cause,
            "resolution_steps": entry.resolution_steps,
            "tags": entry.tags,
            "score": round(score, 4),
        }
        for score, entry in scored[:k]
    ]


def _parse_embedding(embedding: Any) -> list[float] | None:
    """Parse an embedding from various storage formats (pgvector, JSON, etc.)."""
    if embedding is None:
        return None
    if isinstance(embedding, (list, tuple)):
        return [float(v) for v in embedding]
    if hasattr(embedding, "__iter__"):
        return [float(v) for v in embedding]
    return None
