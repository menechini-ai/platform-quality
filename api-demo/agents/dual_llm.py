"""Dual-LLM pattern — separate reasoning and tool-call models.

Uses ``ChatOpenAI`` configured to route through LiteLLM (or directly to
OpenAI via env vars).  Both models read:

- ``OPENAI_API_KEY``   (fallback: empty string)
- ``OPENAI_BASE_URL``  (fallback: None → OpenAI default)
"""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


def get_reasoning_model() -> ChatOpenAI:
    """Return a ``ChatOpenAI`` instance configured for reasoning tasks.

    - model = ``gpt-4o``
    - temperature = 0 (deterministic analysis)
    """
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )


def get_tool_model() -> ChatOpenAI:
    """Return a ``ChatOpenAI`` instance configured for tool-call tasks.

    - model = ``gpt-4o-mini`` (faster, cheaper)
    - temperature = 0
    """
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
