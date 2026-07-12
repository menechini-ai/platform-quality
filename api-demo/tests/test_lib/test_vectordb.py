"""Tests for lib.vectordb — VectorStore."""

from __future__ import annotations

import json
import tempfile
from unittest.mock import patch

import pytest

from lib.vectordb import VectorStore


class TestVectorStoreAddEntry:
    def test_add_entry_computes_embedding(self) -> None:
        mock_emb = [0.1, 0.2, 0.3]
        with patch("lib.vectordb.embed_text", return_value=mock_emb):
            vs = VectorStore()
            vs.add_entry("test-1", "hello world")
        assert vs.count() == 1

    def test_add_entry_stores_metadata(self) -> None:
        with patch("lib.vectordb.embed_text", return_value=[0.1, 0.2]):
            vs = VectorStore()
            vs.add_entry("test-1", "hello", metadata={"source": "test"})
        entry = vs._entries[0]
        assert entry["id"] == "test-1"
        assert entry["metadata"]["source"] == "test"

    def test_add_entry_accepts_precomputed_embedding(self) -> None:
        vs = VectorStore()
        vs.add_entry("test-1", "hello", embedding=[0.5, 0.5])
        assert vs.count() == 1


class TestVectorStoreSearch:
    def test_search_returns_top_k_similar(self) -> None:
        vs = VectorStore()
        vs.add_entry("a", "alpha", embedding=[1.0, 0.0])
        vs.add_entry("b", "beta", embedding=[0.0, 1.0])
        vs.add_entry("c", "gamma", embedding=[0.9, 0.1])

        with patch("lib.vectordb.embed_text", return_value=[1.0, 0.0]):
            results = vs.search("alpha-like", k=2)

        assert len(results) == 2
        assert results[0]["id"] == "a"  # most similar to [1,0]

    def test_search_empty_store_returns_empty_list(self) -> None:
        vs = VectorStore()
        with patch("lib.vectordb.embed_text", return_value=[0.1, 0.2]):
            results = vs.search("anything")
        assert results == []

    def test_search_returns_scores(self) -> None:
        vs = VectorStore()
        vs.add_entry("a", "alpha", embedding=[1.0, 0.0])
        with patch("lib.vectordb.embed_text", return_value=[1.0, 0.0]):
            results = vs.search("alpha")
        assert "score" in results[0]
        assert isinstance(results[0]["score"], float)

    def test_search_k_greater_than_count(self) -> None:
        vs = VectorStore()
        vs.add_entry("a", "alpha", embedding=[1.0, 0.0])
        with patch("lib.vectordb.embed_text", return_value=[1.0, 0.0]):
            results = vs.search("alpha", k=10)
        assert len(results) == 1


class TestVectorStoreLoadJson:
    def test_load_json_adds_entries(self) -> None:
        data = [
            {"id": "kb-001", "summary": "Deploy rollback", "tags": ["deploy"]},
            {"id": "kb-002", "summary": "DB tuning", "tags": ["database"]},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            vs = VectorStore()
            with patch("lib.vectordb.embed_text", return_value=[0.1, 0.2]):
                count = vs.load_json(f.name)
        assert count == 2

    def test_load_json_uses_text_field(self) -> None:
        data = [
            {"id": "kb-001", "title": "Rollback Guide", "summary": "How to rollback"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            vs = VectorStore()
            with patch("lib.vectordb.embed_text", return_value=[0.1, 0.2]) as mock_emb:
                vs.load_json(f.name, text_field="title")
        mock_emb.assert_called_with("Rollback Guide")


class TestVectorStoreClear:
    def test_clear_removes_all_entries(self) -> None:
        vs = VectorStore()
        vs.add_entry("a", "alpha", embedding=[1.0, 0.0])
        vs.clear()
        assert vs.count() == 0
