"""Embedding utilities — pgvector integration for semantic search.

Provides helpers to generate embeddings via OpenAI-compatible APIs
and run cosine-similarity queries against pgvector.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
from openai import OpenAI

DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL")
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        _client = OpenAI(**kwargs)
    return _client


def embed_text(text: str, model: str = DEFAULT_EMBED_MODEL) -> list[float]:
    """Generate an embedding vector for the given text."""
    client = _get_client()
    resp = client.embeddings.create(input=[text], model=model)
    return resp.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} != {len(b)}")
    arr_a, arr_b = np.array(a), np.array(b)
    return float(np.dot(arr_a, arr_b) / (np.linalg.norm(arr_a) * np.linalg.norm(arr_b)))
