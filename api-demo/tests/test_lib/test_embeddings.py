"""Tests for lib.embeddings — cosine_similarity and embed_text."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from lib.embeddings import cosine_similarity, embed_text


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_same_direction_different_magnitude(self) -> None:
        a = [3.0, 4.0]
        b = [6.0, 8.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_angle_between_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [1.0, 1.0]
        expected = 1.0 / np.sqrt(2)
        assert cosine_similarity(a, b) == pytest.approx(expected)

    def test_zero_vector_returns_nan(self) -> None:
        result = cosine_similarity([0.0, 0.0], [1.0, 0.0])
        assert math.isnan(result)

    def test_different_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="mismatch"):
            cosine_similarity([1.0, 0.0], [1.0])

    def test_empty_lists_returns_nan(self) -> None:
        result = cosine_similarity([], [])
        assert math.isnan(result)

    def test_real_values_feel_correct(self) -> None:
        close_a = [0.95, 0.30, 0.10]
        close_b = [0.94, 0.31, 0.11]
        far = [0.10, 0.90, 0.40]
        assert cosine_similarity(close_a, close_b) > cosine_similarity(close_a, far)


class TestEmbedText:
    @pytest.fixture(autouse=True)
    def _reset_client(self) -> None:
        """Clear the cached _client before each test so patching works."""
        import lib.embeddings

        lib.embeddings._client = None
        yield

    def test_embed_text_returns_float_list(self) -> None:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        )
        with patch("lib.embeddings.OpenAI", return_value=mock_client):
            result = embed_text("hello")
        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)
        assert len(result) == 3

    def test_embed_text_calls_openai_with_correct_args(self) -> None:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.5, 0.5])]
        )
        with patch("lib.embeddings.OpenAI", return_value=mock_client):
            embed_text("test input", model="text-embedding-3-small")
        mock_client.embeddings.create.assert_called_once_with(
            input=["test input"], model="text-embedding-3-small"
        )

    def test_embed_text_empty_string(self) -> None:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[])]
        )
        with patch("lib.embeddings.OpenAI", return_value=mock_client):
            result = embed_text("")
        assert isinstance(result, list)
