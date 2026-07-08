"""In-memory vector store for semantic KB search.

Uses ``lib.embeddings.embed_text`` + ``cosine_similarity`` to store
and retrieve entries by embedding similarity.

Usage:
    vs = VectorStore()
    vs.add_entry("kb-001", "Deploy rollback procedure", {"pattern": "deploy"})
    results = vs.search("how to rollback a deploy", k=3)
"""

from __future__ import annotations

import json
from typing import Any

from lib.embeddings import cosine_similarity, embed_text


class VectorStore:
    """Simple in-memory vector store.

    Stores entries with pre-computed embeddings and returns the top-K
    most similar entries for a given query.
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
        self._entries.append({
            "id": entry_id,
            "text": text,
            "metadata": metadata or {},
            "embedding": embedding,
        })

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
                metadata={k: v for k, v in item.items() if k not in ("id", text_field)},
            )
        return len(items)

    def count(self) -> int:
        """Return the number of stored entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Remove all entries."""
        self._entries.clear()
