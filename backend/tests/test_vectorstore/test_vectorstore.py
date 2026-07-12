"""Tests for VectorStore."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.vectorstore.service import VectorStore


class TestVectorStoreAdd:
    """add_entry() behaviour."""

    @patch("app.vectorstore.service.embed_text")
    def test_add_entry_auto_embed(self, mock_embed: MagicMock) -> None:
        mock_embed.return_value = [0.1, 0.2, 0.3]
        vs = VectorStore()
        vs.add_entry("id-1", "some text")
        assert len(vs._entries) == 1
        assert vs._entries[0]["id"] == "id-1"
        mock_embed.assert_called_once_with("some text")

    def test_add_entry_with_embedding(self) -> None:
        vs = VectorStore()
        vs.add_entry("id-1", "text", embedding=[1.0, 0.0])
        assert vs._entries[0]["embedding"] == [1.0, 0.0]

    def test_add_entry_with_metadata(self) -> None:
        vs = VectorStore()
        vs.add_entry("id-1", "text", metadata={"key": "val"}, embedding=[0.1, 0.2])
        assert vs._entries[0]["metadata"] == {"key": "val"}


class TestVectorStoreSearch:
    """search() behaviour."""

    @patch("app.vectorstore.service.embed_text")
    def test_search_returns_top_k(self, mock_embed: MagicMock) -> None:
        mock_embed.return_value = [0.5, 0.5]
        vs = VectorStore()
        vs.add_entry("a", "first", embedding=[1.0, 0.0])
        vs.add_entry("b", "second", embedding=[0.0, 1.0])
        vs.add_entry("c", "third", embedding=[0.7, 0.3])

        mock_embed.return_value = [1.0, 0.0]
        results = vs.search("query", k=2)
        assert len(results) == 2

    @patch("app.vectorstore.service.embed_text")
    def test_search_empty_store(self, _mock_embed: MagicMock) -> None:
        vs = VectorStore()
        results = vs.search("anything")
        assert results == []

    @patch("app.vectorstore.service.embed_text")
    def test_search_score_in_range(self, mock_embed: MagicMock) -> None:
        mock_embed.return_value = [0.5, 0.5]
        vs = VectorStore()
        vs.add_entry("a", "first", embedding=[1.0, 0.0])
        vs.add_entry("b", "second", embedding=[0.0, 1.0])

        mock_embed.return_value = [0.5, 0.5]
        results = vs.search("test", k=5)
        for r in results:
            assert -1.0 <= r["score"] <= 1.0

    @patch("app.vectorstore.service.embed_text")
    def test_search_sorted_by_score(self, mock_embed: MagicMock) -> None:
        mock_embed.side_effect = [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 0.5],
            [0.5, 0.0],
        ]
        vs = VectorStore()
        vs.add_entry("a", "first", embedding=[1.0, 0.0])

        mock_embed.return_value = [1.0, 0.5]
        results = vs.search("similar to a", k=5)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


class TestVectorStoreLoadJson:
    """load_json() behaviour."""

    @patch("app.vectorstore.service.embed_text")
    @patch("builtins.open")
    def test_load_json_from_file(self, mock_open: MagicMock, mock_embed: MagicMock) -> None:
        import json

        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            [{"id": "1", "summary": "first entry"}, {"id": "2", "summary": "second entry"}]
        )
        mock_embed.return_value = [0.1, 0.2]

        vs = VectorStore()
        count = vs.load_json("/fake/path.json")
        assert count == 2
        assert len(vs._entries) == 2
