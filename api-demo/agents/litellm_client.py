"""LiteLLM proxy client — multi-provider LLM gateway for ObservAI.

Provides both a lightweight `llm_complete()` function (backward compat)
and a `LiteLLMClient` class with env-var config, streaming, and KB search.

Usage:
    python -m api-demo.agents.litellm_client --prompt "analyze incident"
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from litellm import completion

DEFAULT_MODEL = os.getenv("LITELLM_DEFAULT_MODEL", "gpt-4o")

# Wire Langfuse callback when credentials are available.
if os.getenv("LANGFUSE_SECRET_KEY"):
    import litellm

    litellm.success_callback = ["langfuse"]  # type: ignore[assignment]


# ── Legacy functional API ──────────────────────────────────────────


def llm_complete(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: str | None = None,
    **kwargs: Any,
) -> str:
    """Send a prompt to the configured LLM and return the text response."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = completion(model=model, messages=messages, **kwargs)
    return resp.choices[0].message.content or ""


# ── Class-based API ────────────────────────────────────────────────


class LiteLLMClient:
    """LiteLLM client that reads config from environment variables.

    Env vars:
        LITELLM_API_KEY      — API key passed to litellm
        LITELLM_BASE_URL     — Custom base URL for the provider
        LITELLM_DEFAULT_MODEL — Default model name (default: gpt-4o)

    When a ``VectorStore`` (from ``lib.vectordb``) is attached, ``kb_search``
    performs semantic search and ``complete`` can inject KB context.
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
        model: str | None = None,
        system_prompt: str | None = None,
        inject_kb: bool = False,
        kb_k: int = 3,
        **kwargs: Any,
    ) -> str:
        """Send a prompt and return the text response.

        If ``inject_kb`` is True and a VectorStore is attached, the top-kb_k
        KB entries are prepended as context before the prompt.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if inject_kb and self._vector_store is not None:
            kb_results = self._vector_store.search(prompt, k=kb_k)
            if kb_results:
                kb_context = "\n".join(f"- {r['text']}" for r in kb_results)
                messages.append(
                    {
                        "role": "system",
                        "content": f"Relevant knowledge base entries:\n{kb_context}",
                    }
                )

        messages.append({"role": "user", "content": prompt})
        resp = completion(
            model=model or self.default_model,
            messages=messages,
            **self._build_kwargs(**kwargs),
        )
        return resp.choices[0].message.content or ""

    def complete_stream(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a prompt and return a streaming response iterator."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs["stream"] = True
        return completion(
            model=model or self.default_model,
            messages=messages,
            **self._build_kwargs(**kwargs),
        )

    def kb_search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Semantic KB search via attached VectorStore.

        Falls back to keyword matching if no VectorStore is attached.

        Args:
            query: Search query string.
            k: Maximum number of results (default 3).
        """
        if self._vector_store is not None:
            return self._vector_store.search(query, k=k)
        return []


# ── CLI ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="LiteLLM demo client")
    parser.add_argument("--prompt", required=True, help="Prompt text")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--system", help="System prompt")
    parser.add_argument("--kb", action="store_true", help="Inject KB context into prompt")
    args = parser.parse_args()

    client = LiteLLMClient()
    if args.kb:
        from lib.vectordb import VectorStore

        vs = VectorStore()
        vs.load_json("api-demo/data/kb_entries.json")
        client.attach_vector_store(vs)

    result = client.complete(
        args.prompt,
        model=args.model,
        system_prompt=args.system,
        inject_kb=args.kb,
    )
    print(result)


if __name__ == "__main__":
    main()
