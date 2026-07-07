"""Utility: write guard, headers, datadog URL, error sanitization."""

from __future__ import annotations

import re

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


_SANITIZE_PATTERNS = [
    (re.compile(r"DD_API_KEY[=:\s]*[^\s,\]\}]+"), "DD_API_KEY=[REDACTED]"),
    (re.compile(r"DD_APP_KEY[=:\s]*[^\s,\]\}]+"), "DD_APP_KEY=[REDACTED]"),
    (re.compile(r"api_key[=:\s]*[^\s,\]\}]+"), "api_key=[REDACTED]"),
    (re.compile(r"Bearer\s+[^\s]+"), "Bearer [REDACTED]"),
    (re.compile(r"DD-API-KEY[=:\s]*[^\s,\]\}]+"), "DD-API-KEY=[REDACTED]"),
    (re.compile(r"DD-APPLICATION-KEY[=:\s]*[^\s,\]\}]+"), "DD-APPLICATION-KEY=[REDACTED]"),
]


def sanitize_error_message(message: str) -> str:
    """Sanitize sensitive patterns from error messages."""
    for pattern, replacement in _SANITIZE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message
