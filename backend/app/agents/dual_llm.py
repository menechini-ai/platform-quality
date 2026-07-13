"""Dual-LLM pattern — separate reasoning and tool-call models.

Reads ``OPENAI_API_KEY`` first, falls back to ``LITELLM_API_KEY``,
then ``app.core.config.settings.OPENAI_API_KEY``.
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from app.core.config import settings


def _pick_api_key() -> str:
    """Return the first available API key: OPENAI_API_KEY > LITELLM_API_KEY > settings.OPENAI_API_KEY."""
    return (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("LITELLM_API_KEY")
        or getattr(settings, "OPENAI_API_KEY", None)
        or ""
    )


def get_reasoning_model() -> ChatOpenAI:
    """Return ChatOpenAI for reasoning (gpt-4o, temperature=0)."""
    api_key = _pick_api_key()
    base_url = os.getenv("OPENAI_BASE_URL") or getattr(settings, "LITELLM_BASE_URL", None)
    return ChatOpenAI(
        model=os.getenv("LITELLM_DEFAULT_MODEL", "gpt-4o"),
        temperature=0,
        api_key=api_key,
        base_url=base_url,
    )


def get_tool_model() -> ChatOpenAI:
    """Return ChatOpenAI for tool calls (gpt-4o-mini, temperature=0)."""
    api_key = _pick_api_key()
    base_url = os.getenv("OPENAI_BASE_URL") or getattr(settings, "LITELLM_BASE_URL", None)
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key,
        base_url=base_url,
    )
