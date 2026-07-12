"""Tests for LiteLLMClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.llm import LiteLLMClient


class TestLiteLLMClientInit:
    """Client construction."""

    def test_default_model(self) -> None:
        client = LiteLLMClient()
        assert client.default_model == "gpt-4o"

    def test_custom_model(self) -> None:
        client = LiteLLMClient(default_model="gpt-4o-mini")
        assert client.default_model == "gpt-4o-mini"

    def test_attach_vector_store(self) -> None:
        client = LiteLLMClient()
        vs = MagicMock()
        client.attach_vector_store(vs)
        assert client._vector_store is vs


class TestLiteLLMClientComplete:
    """completion() behaviour."""

    @patch("app.llm.completion")
    def test_complete_basic(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value.choices[0].message.content = "Hello world"
        client = LiteLLMClient(api_key="test-key")
        result = client.complete("say hello")
        assert result == "Hello world"
        mock_completion.assert_called_once()

    @patch("app.llm.completion")
    def test_complete_with_system_prompt(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value.choices[0].message.content = "Analysis result"
        client = LiteLLMClient()
        result = client.complete("analyze", system_prompt="You are an SRE")
        assert result == "Analysis result"
        call_kwargs = mock_completion.call_args[1]
        assert {"role": "system", "content": "You are an SRE"} in call_kwargs["messages"]

    @patch("app.llm.completion")
    def test_complete_empty_response(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value.choices[0].message.content = None
        client = LiteLLMClient()
        result = client.complete("test")
        assert result == ""

    @patch("app.llm.completion")
    def test_complete_with_kb_context(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value.choices[0].message.content = "With KB"
        client = LiteLLMClient()
        vs = MagicMock()
        vs.search.return_value = [{"id": "kb-1", "text": "Restart nginx"}]
        client.attach_vector_store(vs)

        result = client.complete("fix it", kb_context=True)
        assert result == "With KB"
        vs.search.assert_called_once_with("fix it", k=3)
        call_kwargs = mock_completion.call_args[1]
        assert any("Restart nginx" in m["content"] for m in call_kwargs["messages"])

    @patch("app.llm.completion")
    def test_complete_stream(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value = MagicMock()
        client = LiteLLMClient(api_key="test-key", base_url="https://api.example.com")
        result = client.complete_stream("stream test")
        assert result is not None
        mock_completion.assert_called_once_with(
            model="gpt-4o",
            messages=[{"role": "user", "content": "stream test"}],
            stream=True,
            api_key="test-key",
            base_url="https://api.example.com",
        )


class TestLiteLLMClientModelOverride:
    """Model override behaviour."""

    @patch("app.llm.completion")
    def test_complete_custom_model(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value.choices[0].message.content = "custom"
        client = LiteLLMClient(default_model="gpt-4o")
        result = client.complete("test", model="gpt-4o-mini")
        assert result == "custom"
        assert mock_completion.call_args[1]["model"] == "gpt-4o-mini"
