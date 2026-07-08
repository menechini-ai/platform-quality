"""Shared Datadog filter schema: tag filtering + time period.

Imported by routers, the client wrapper, and filter composition logic.
No `from __future__ import annotations` — keeps Pydantic v2 boundary models explicit.
"""

from typing import Literal

from pydantic import BaseModel

Period = Literal["1d", "7d", "15d", "30d"]


class DatadogFilter(BaseModel):
    """Uniform filter applied individually per path or globally via settings.

    - `tags`: Datadog `key:value` tags, AND-combined when multiple.
    - `period`: rolling time window mapped to `from`/`to` timestamps.
    """

    tags: list[str] | None = None
    period: Period | None = None
