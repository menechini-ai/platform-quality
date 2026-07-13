"""Tests for agents.litellm_client — LiteLLMClient class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.litellm_client import LiteLLMClient, llm_complete


class TestLiteLLMClientInit:
    def test_default_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LITELLM_DEFAULT_MODEL", "gpt-4o-mini")
        client = LiteLLMClient()
        assert client.default_model == "gpt-4o-mini"

    def test_default_model_fallback(self) -> None:
        client = LiteLLMClient()
        assert client.default_model == "gpt-4o"

    def test_explicit_constructor_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LITELLM_DEFAULT_MODEL", "gpt-4o")
        client = LiteLLMClient(default_model="anthropic/claude-3-opus")
        assert client.default_model == "anthropic/claude-3-opus"

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
        client = LiteLLMClient()
        assert client.api_key == "sk-test"

    def test_base_url_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:4000")
        client = LiteLLMClient()
        assert client.base_url == "http://localhost:4000"


class TestLiteLLMClientComplete:
    def test_complete_returns_text(self) -> None:
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="Hello world"))]
        with patch("agents.litellm_client.completion", return_value=mock_resp):
            client = LiteLLMClient()
            result = client.complete("say hello")
        assert result == "Hello world"

    def test_complete_with_system_prompt(self) -> None:
        with patch("agents.litellm_client.completion") as mock_comp:
            mock_comp.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))])
            client = LiteLLMClient()
            client.complete("hello", system_prompt="Be concise")
        messages = mock_comp.call_args[1]["messages"]
        assert messages[0] == {"role": "system", "content": "Be concise"}
        assert messages[1] == {"role": "user", "content": "hello"}

    def test_complete_custom_model(self) -> None:
        with patch("agents.litellm_client.completion") as mock_comp:
            mock_comp.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))])
            client = LiteLLMClient()
            client.complete("hello", model="anthropic/claude-3-opus")
        assert mock_comp.call_args[1]["model"] == "anthropic/claude-3-opus"

    def test_complete_passes_api_key_from_client(self) -> None:
        with patch("agents.litellm_client.completion") as mock_comp:
            mock_comp.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))])
            client = LiteLLMClient(api_key="sk-test-key")
            client.complete("hello")
        assert mock_comp.call_args[1]["api_key"] == "sk-test-key"


class TestLiteLLMClientStream:
    def test_complete_stream_passes_stream_flag(self) -> None:
        with patch("agents.litellm_client.completion") as mock_comp:
            mock_comp.return_value = iter(["chunk1", "chunk2"])
            client = LiteLLMClient()
            list(client.complete_stream("hello"))
        assert mock_comp.call_args[1]["stream"] is True


class TestLiteLLMClientKbSearch:
    def test_kb_search_without_vector_store_returns_empty(self) -> None:
        client = LiteLLMClient()
        results = client.kb_search("deploy", k=2)
        assert results == []

    def test_kb_search_with_vector_store(self) -> None:
        from lib.vectordb import VectorStore

        vs = VectorStore()
        vs.add_entry("kb-001", "Deploy rollback procedure", embedding=[1.0, 0.0])
        vs.add_entry("kb-002", "Database tuning", embedding=[0.0, 1.0])
        client = LiteLLMClient()
        client.attach_vector_store(vs)

        with patch("lib.vectordb.embed_text", return_value=[1.0, 0.0]):
            results = client.kb_search("deploy", k=2)
        assert len(results) >= 1
        assert results[0]["id"] == "kb-001"

    def test_complete_inject_kb_adds_context(self) -> None:
        from lib.vectordb import VectorStore

        vs = VectorStore()
        vs.add_entry("kb-001", "Deploy rollback procedure", embedding=[1.0, 0.0])
        client = LiteLLMClient()
        client.attach_vector_store(vs)

        with patch("lib.vectordb.embed_text", return_value=[1.0, 0.0]):
            with patch("agents.litellm_client.completion") as mock_comp:
                mock_comp.return_value = MagicMock(
                    choices=[MagicMock(message=MagicMock(content="ok"))]
                )
                client.complete("how to rollback", inject_kb=True)
        messages = mock_comp.call_args[1]["messages"]
        system_msgs = [m for m in messages if m["role"] == "system"]
        kb_msg = system_msgs[-1]
        assert "Deploy" in kb_msg["content"]


# ── Existing llm_complete tests still pass ──────────────────────────


class TestLegacyLlmComplete:
    def test_returns_response_text(self) -> None:
        with patch("agents.litellm_client.completion") as mock_comp:
            mock_comp.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="Mocked"))]
            )
            result = llm_complete("hello")
        assert result == "Mocked"
        mock_comp.assert_called_once()

    def test_includes_system_prompt(self) -> None:
        with patch("agents.litellm_client.completion") as mock_comp:
            mock_comp.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))])
            llm_complete("hello", system_prompt="Be concise")
        messages = mock_comp.call_args[1]["messages"]
        assert messages[0] == {"role": "system", "content": "Be concise"}
        assert messages[1] == {"role": "user", "content": "hello"}
