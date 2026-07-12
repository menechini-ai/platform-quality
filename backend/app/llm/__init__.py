"""LiteLLM client — multi-provider LLM gateway.

Exposes ``LiteLLMClient`` for completion/streaming calls configured via
environment variables (LITELLM_API_KEY, LITELLM_BASE_URL, LITELLM_DEFAULT_MODEL).
"""

from __future__ import annotations

import os
from typing import Any

from litellm import completion

# Wire Langfuse callback when credentials are available.
if os.getenv("LANGFUSE_SECRET_KEY"):
    import litellm  # noqa: F811

    litellm.success_callback = ["langfuse"]  # type: ignore[assignment]

DEFAULT_MODEL: str = os.getenv("LITELLM_DEFAULT_MODEL", "gpt-4o")


class LiteLLMClient:
    """LiteLLM client that reads configuration from environment variables.

    Env vars:
        LITELLM_API_KEY       — API key passed to litellm
        LITELLM_BASE_URL      — Custom base URL for the provider
        LITELLM_DEFAULT_MODEL — Default model name (default: gpt-4o)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("LITELLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LITELLM_BASE_URL")
        self.default_model = default_model or os.getenv("LITELLM_DEFAULT_MODEL", "gpt-4o")
        self._vector_store: Any = None

    def attach_vector_store(self, vector_store: Any) -> None:
        """Attach a ``VectorStore`` for semantic KB search."""
        self._vector_store = vector_store

    def _build_kwargs(self, **overrides: Any) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url
        kwargs.update(overrides)
        return kwargs

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        kb_context: bool = False,
        **kwargs: Any,
    ) -> str:
        """Send a prompt and return the text response.

        Args:
            prompt: User message / question.
            system_prompt: Optional system-level instruction.
            model: Override the default model.
            kb_context: If True and a VectorStore is attached, injects
                        the top-3 most relevant KB entries as context.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if kb_context and self._vector_store is not None:
            kb_results = self._vector_store.search(prompt, k=3)
            if kb_results:
                kb_text = "\n\n".join(f"[KB:{r['id']}] {r['text']}" for r in kb_results)
                messages.append(
                    {
                        "role": "system",
                        "content": f"Relevant knowledge base context:\n{kb_text}",
                    }
                )

        messages.append({"role": "user", "content": prompt})
        model_name = model or self.default_model
        resp = completion(model=model_name, messages=messages, **self._build_kwargs(**kwargs))
        return resp.choices[0].message.content or ""

    def complete_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a prompt and stream the response chunks."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        model_name = model or self.default_model
        return completion(
            model=model_name,
            messages=messages,
            stream=True,
            **self._build_kwargs(**kwargs),
        )


# Wire Langfuse tracing when credentials are available.
if os.getenv("LANGFUSE_SECRET_KEY"):
    import litellm  # noqa: F811

    litellm.success_callback = ["langfuse"]  # type: ignore[assignment]
