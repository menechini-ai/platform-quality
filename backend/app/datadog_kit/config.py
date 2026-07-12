"""Datadog Kit configuration."""

from __future__ import annotations

from pydantic import BaseModel


class DatadogKitConfig(BaseModel):
    """Runtime config for the investigation kit."""

    default_time_range_minutes: int = 60
    logs_limit: int = 50
    events_limit: int = 20
    monitors_limit: int = 50
    spans_limit: int = 20
    parallel_timeout_seconds: int = 120
    signal_timeout_seconds: int = 30
