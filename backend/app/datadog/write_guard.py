"""Utility: write guard, headers, datadog URL."""

from __future__ import annotations

import os

from app.core.config import settings


def assert_write_allowed() -> None:
    """Raise if write operations are not allowed (no real DD keys)."""
    if not settings.DATADOG_API_KEY or not settings.DATADOG_APP_KEY:
        raise PermissionError(
            "Write operation blocked: DATADOG_API_KEY and DATADOG_APP_KEY must be configured"
        )


def get_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "DD-API-KEY": settings.DATADOG_API_KEY or "",
        "DD-APPLICATION-KEY": settings.DATADOG_APP_KEY or "",
    }


def get_datadog_url() -> str:
    return f"https://api.{settings.DATADOG_SITE or 'datadoghq.com'}"
