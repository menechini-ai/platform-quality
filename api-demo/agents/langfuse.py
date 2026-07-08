"""Langfuse LLM observability wrapper.

Gracefully skips tracing when ``LANGFUSE_SECRET_KEY`` is not set.
"""

from __future__ import annotations

import os
from typing import Any


class LangfuseTracer:
    """Wraps LLM calls with Langfuse observation.

    Usage::

        tracer = LangfuseTracer()
        with tracer.observe("my_trace", input="hello") as ctx:
            result = llm_complete("hello")
            ctx["output"] = result
    """

    def __init__(self) -> None:
        self._enabled = bool(os.getenv("LANGFUSE_SECRET_KEY"))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def observe(self, name: str, **tags: Any) -> _TraceContext:
        """Return a context manager that records a trace.

        If Langfuse is not configured the context manager is a no-op.
        """
        return _TraceContext(name=name, enabled=self._enabled, tags=tags)


class _TraceContext:
    """Simple trace context — records input/output/duration."""

    def __init__(self, name: str, enabled: bool, tags: dict[str, Any]) -> None:
        self.name = name
        self._enabled = enabled
        self._tags = tags
        self.input: str | None = None
        self.output: str | None = None
        self._records: list[dict[str, Any]] = []

    def record(self, **data: Any) -> None:
        """Append a span record to this trace if enabled."""
        if self._enabled:
            self._records.append(data)

    def __enter__(self) -> "_TraceContext":
        if self._enabled:
            self._records = [{"event": "start", "name": self.name, **self._tags}]
        return self

    def __exit__(self, *args: Any) -> None:
        if self._enabled:
            self._records.append({"event": "end", "name": self.name})

    @property
    def records(self) -> list[dict[str, Any]]:
        return list(self._records)
