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


def friendly_datadog_error(exc: Exception) -> tuple[int, str]:
    """Convert a Datadog API exception to a user-friendly (status_code, detail) pair.

    Handles SDK ApiException subclasses, httpx.HTTPStatusError, and generic errors.
    Never leaks raw exception messages to the user except as a last resort.
    """
    status: int | None = getattr(exc, "status", None)  # datadog SDK ApiException
    if status is None:
        resp = getattr(exc, "response", None)  # httpx.HTTPStatusError
        if resp is not None:
            status = getattr(resp, "status_code", None)

    if status == 401:
        return (
            401,
            "Datadog API key lacks permission for this feature. "
            "Verify the API/Application key has the required scope "
            "in your Datadog organization settings.",
        )
    if status == 403:
        return (
            403,
            "Access denied by Datadog. The API key does not have permission for this feature.",
        )
    if status == 404:
        return (
            404,
            "This Datadog feature is not enabled for your account. "
            "Check your Datadog plan or contact support.",
        )

    return (502, sanitize_error_message(str(exc)))
