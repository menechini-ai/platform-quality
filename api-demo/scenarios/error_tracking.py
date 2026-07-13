"""Scenario: Error Tracking — simulate errors with various exception types."""

from __future__ import annotations

import random

from client import DdClient

ERROR_TYPES = [
    ("ValueError", "Invalid input: field 'email' does not match pattern"),
    ("TimeoutError", "Connection to database timed out after 30s"),
    ("KeyError", "Missing required field 'transaction_id' in payload"),
    ("PermissionError", "Access denied for API key on resource /api/v2/orders"),
    ("ConnectionError", "Failed to establish connection to upstream:443"),
    ("JSONDecodeError", "Expecting value: line 1 column 1 (char 0)"),
    ("OSError", "[Errno 24] Too many open files"),
    ("ZeroDivisionError", "division by zero in pricing calculation"),
]


def run_random_errors(
    client: DdClient, count: int = 20, service: str | None = None
) -> dict[str, int]:
    """Send a batch of random error types to populate Error Tracking."""
    svc = service or random.choice(["api-gateway", "payment-service", "user-service"])
    results = {}
    for _ in range(count):
        kind, msg = random.choice(ERROR_TYPES)
        code = client.send_error_tracking_event(f"[{kind}] {msg}", svc, kind)
        key = f"et_{code}"
        results[key] = results.get(key, 0) + 1
    return results


def run_error_burst(client: DdClient) -> dict[str, int]:
    """One error type fires repeatedly — simulates a real bug."""
    svc = "payment-service"
    kind, msg = ERROR_TYPES[1]  # TimeoutError
    results = {}
    for _ in range(10):
        client.send_error_tracking_event(msg, svc, kind)
        client.send_log("Retry attempt failed — circuit breaker opened", "error", svc)
    results["error_type"] = kind
    return results
