"""SSE streaming handler for LangGraph pipelines.

Yields Server-Sent Events as the pipeline executes each node.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langgraph.graph.state import CompiledStateGraph


async def stream_pipeline(
    initial_state: dict[str, Any],
    pipeline: CompiledStateGraph,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events for each node execution.

    Each event is a JSON line: ``data: {"node": "...", "output": "..."}\n\n``

    Yields:
        SSE-formatted strings with node execution output.
    """
    async for event in pipeline.astream(initial_state):
        for node_name, output in event.items():
            text = str(output.get("analysis", output.get("recommendation", "")))
            yield f"data: {json.dumps({'node': node_name, 'output': text})}\n\n"

    yield "data: [DONE]\n\n"
