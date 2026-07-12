"""In-memory vector store with optional pgvector persistence.

Stores entries with pre-computed embeddings and returns the top-K most
similar entries for a given query using cosine similarity.
"""

from __future__ import annotations

import json
from typing import Any

from app.llm.service import cosine_similarity, embed_text


class VectorStore:
    """Simple in-memory vector store.

    Usage::

        vs = VectorStore()
        vs.add_entry("kb-001", "Deploy rollback procedure", {"pattern": "deploy"})
        results = vs.search("how to rollback a deploy", k=3)
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def add_entry(
        self,
        entry_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
    ) -> None:
        """Add an entry, computing its embedding if not provided."""
        if embedding is None:
            embedding = embed_text(text)
        self._entries.append(
            {
                "id": entry_id,
                "text": text,
                "metadata": metadata or {},
                "embedding": embedding,
            }
        )

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Return top-K entries most similar to the query."""
        if not self._entries:
            return []

        query_emb = embed_text(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in self._entries:
            try:
                score = cosine_similarity(query_emb, entry["embedding"])
                scored.append((score, entry))
            except ValueError:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": e["id"],
                "text": e["text"],
                "metadata": e["metadata"],
                "score": s,
            }
            for s, e in scored[:k]
        ]

    def load_json(self, path: str, text_field: str = "summary") -> int:
        """Load entries from a JSON file. Returns count of entries added.

        Each JSON object should have an ``id`` field. The ``text_field``
        (default ``summary``) is used as the embedding text.
        """
        with open(path) as f:
            items = json.load(f)
        for item in items:
            text = item.get(text_field, item.get("title", ""))
            self.add_entry(
                entry_id=item["id"],
                text=text,
                metadata=item,
            )
        return len(items)
