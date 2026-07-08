"""Tests for semantic KB search service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.llm.kb_service import search_kb


def _make_mock_db(entries: list) -> MagicMock:
    """Create a mock get_db generator that yields a session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.execute.return_value = MagicMock()  # sync Result mock
    session.execute.return_value.scalars.return_value.all.return_value = entries
    gen = MagicMock()
    gen.__aiter__.return_value = [session]
    return gen


@pytest.fixture
def mock_kb_entries() -> list[MagicMock]:
    entries = []
    for title, emb in [
        ("Deploy rollback", [1.0, 0.0, 0.0]),
        ("Database failover", [0.0, 1.0, 0.0]),
        ("Rate limiting", [0.0, 0.0, 1.0]),
    ]:
        entry = MagicMock()
        entry.id = uuid4()
        entry.title = title
        entry.symptom_pattern = f"symptom_{title}"
        entry.root_cause = f"cause_{title}"
        entry.resolution_steps = [f"step1_{title}"]
        entry.tags = ["sre"]
        entry.embedding = emb
        entries.append(entry)
    return entries


class TestSearchKb:
    """search_kb() behaviour."""

    @patch("app.llm.kb_service.get_db")
    @patch("app.llm.kb_service.embed_text")
    async def test_search_returns_top_k(
        self, mock_embed: MagicMock, mock_get_db: MagicMock, mock_kb_entries: list
    ) -> None:
        mock_get_db.return_value = _make_mock_db(mock_kb_entries)
        mock_embed.return_value = [1.0, 0.0, 0.0]

        results = await search_kb("deploy", k=2)
        assert len(results) == 2
        assert results[0]["title"] == "Deploy rollback"
        assert "score" in results[0]

    @patch("app.llm.kb_service.get_db")
    @patch("app.llm.kb_service.embed_text")
    async def test_search_all_results(
        self, mock_embed: MagicMock, mock_get_db: MagicMock, mock_kb_entries: list
    ) -> None:
        mock_get_db.return_value = _make_mock_db(mock_kb_entries)
        mock_embed.return_value = [1.0, 0.0, 0.0]

        results = await search_kb("deploy", k=5)
        assert len(results) == 3

    @patch("app.llm.kb_service.get_db")
    @patch("app.llm.kb_service.embed_text")
    async def test_search_empty(self, mock_embed: MagicMock, mock_get_db: MagicMock) -> None:
        mock_get_db.return_value = _make_mock_db([])
        mock_embed.return_value = [0.5, 0.5, 0.5]

        results = await search_kb("anything")
        assert results == []

    @patch("app.llm.kb_service.get_db")
    @patch("app.llm.kb_service.embed_text")
    async def test_search_skips_null_embeddings(
        self, mock_embed: MagicMock, mock_get_db: MagicMock
    ) -> None:
        entry_with_emb = MagicMock()
        entry_with_emb.id = uuid4()
        entry_with_emb.title = "Has embedding"
        entry_with_emb.symptom_pattern = "pat"
        entry_with_emb.root_cause = "cause"
        entry_with_emb.resolution_steps = ["step"]
        entry_with_emb.tags = ["sre"]
        entry_with_emb.embedding = [1.0, 0.0]

        entry_no_emb = MagicMock()
        entry_no_emb.id = uuid4()
        entry_no_emb.title = "No embedding"
        entry_no_emb.symptom_pattern = "pat2"
        entry_no_emb.root_cause = "cause2"
        entry_no_emb.resolution_steps = ["step2"]
        entry_no_emb.tags = ["sre"]
        entry_no_emb.embedding = None

        mock_get_db.return_value = _make_mock_db([entry_with_emb, entry_no_emb])
        mock_embed.return_value = [1.0, 0.0]
        results = await search_kb("test")
        assert len(results) == 1
        assert results[0]["title"] == "Has embedding"
