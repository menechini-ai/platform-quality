"""Tests for embedding service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.llm.service import cosine_similarity, embed_text


@pytest.fixture(autouse=True)
def _reset_embed_client() -> None:
    import app.llm.service as svc

    svc._client = None


class TestEmbedText:
    """embed_text() behaviour."""

    @patch("app.llm.service.OpenAI")
    def test_embed_text_basic(self, mock_openai: MagicMock) -> None:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value.data[0].embedding = [0.1, 0.2, 0.3]

        result = embed_text("hello world")
        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once_with(
            input=["hello world"], model="text-embedding-3-small"
        )

    @patch("app.llm.service.OpenAI")
    def test_embed_text_dimension(self, mock_openai: MagicMock) -> None:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value.data[0].embedding = [0.0] * 1536

        result = embed_text("test")
        assert len(result) == 1536

    @patch("app.llm.service.OpenAI")
    def test_embed_text_custom_model(self, mock_openai: MagicMock) -> None:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.embeddings.create.return_value.data[0].embedding = [0.5]

        result = embed_text("test", model="text-embedding-ada-002")
        assert result == [0.5]
        assert mock_client.embeddings.create.call_args[1]["model"] == "text-embedding-ada-002"


class TestCosineSimilarity:
    """cosine_similarity() behaviour."""

    def test_identical_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-10)

    def test_partial_similarity(self) -> None:
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_dimension_mismatch(self) -> None:
        a = [1.0, 0.0]
        b = [1.0, 0.0, 0.0]
        with pytest.raises(ValueError, match="dimension mismatch: 2 != 3"):
            cosine_similarity(a, b)

    def test_zero_vector(self) -> None:
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_large_vectors(self) -> None:
        a = np.random.rand(1536).tolist()
        b = np.random.rand(1536).tolist()
        result = cosine_similarity(a, b)
        assert -1.0 <= result <= 1.0
