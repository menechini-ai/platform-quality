"""SSE streaming handler for LangGraph pipeline outputs.

Yields per-node results as Server-Sent Events so they can be consumed
by an HTTP endpoint (e.g. FastAPI ``StreamingResponse``).
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from langgraph.graph.state import CompiledStateGraph


def format_sse(event: str, data: dict[str, Any]) -> str:
    """Format a dict as an SSE ``data:`` line."""
    payload = {"event": event, **data}
    return f"data: {json.dumps(payload)}\n\n"


async def stream_pipeline(
    state: dict[str, Any],
    pipeline: CompiledStateGraph,
) -> AsyncGenerator[str, None]:
    """Run the pipeline and yield SSE-formatted per-step output.

    Yields one ``data:`` event per node invocation (or a single
    ``complete`` event if the pipeline runs atomically).

    Example event::

        data: {"event": "complete", "node": "__end__", "analysis": "…", "recommendation": "…"}
    """
    result = await pipeline.ainvoke(state)
    yield format_sse("complete", {"node": "__end__", **result})
