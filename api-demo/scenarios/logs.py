"""Scenario: Logs — send log entries with various statuses, patterns, error types."""

from __future__ import annotations

import random
import time

from client import ERROR_MSGS, DdClient

# Patterns for realistic log scenarios
SCENARIOS = {
    "normal": (
        "Request processed successfully in {:.0f}ms",
        ["info", "debug"],
        0.05,
    ),
    "p95": (
        "Request slow — completed in {:.0f}ms (p95 threshold: 500ms)",
        ["warn"],
        0.15,
    ),
    "error": (
        "{}",
        ["error"],
        0.30,
    ),
    "timeout": (
        "Request timed out after {}s — upstream unreachable",
        ["error"],
        0.40,
    ),
    "degraded": (
        "Circuit breaker opened for {} — {} requests blocked",
        ["warn", "error"],
        0.25,
    ),
}


def run_log_burst(client: DdClient, count: int = 50, service: str | None = None) -> dict[str, int]:
    """Send a burst of log entries mimicking real traffic patterns."""
    svc = service or random.choice(
        ["api-gateway", "user-service", "payment-service", "order-service"]
    )
    env = random.choice(["prod", "staging"])
    results = {}

    for i in range(count):
        scenario = random.choices(
            list(SCENARIOS.keys()),
            weights=[60, 15, 10, 8, 7],
            k=1,
        )[0]
        pattern, statuses, error_rate = SCENARIOS[scenario]
        is_error = random.random() < error_rate
        status = random.choice(statuses)

        if scenario == "normal":
            dur = random.gauss(120, 40)
            msg = pattern.format(max(0, dur))
        elif scenario == "p95":
            dur = random.gauss(1200, 300)
            msg = pattern.format(max(0, dur))
        elif scenario == "error":
            msg = random.choice(ERROR_MSGS)
        elif scenario == "timeout":
            msg = pattern.format(random.randint(10, 60))
        elif scenario == "degraded":
            msg = pattern.format(svc, random.randint(50, 500))
        else:
            msg = pattern

        code = client.send_log(msg, status, svc, env)
        results[f"log_{code}"] = results.get(f"log_{code}", 0) + 1

        if (i + 1) % 10 == 0:
            time.sleep(0.1)

    return results


def run_error_wave(client: DdClient, service: str = "payment-service") -> dict[str, int]:
    """Simulate an error wave — gradual increase then recovery."""
    results = {}
    for pct, delay in [(0.05, 0), (0.20, 1), (0.50, 2), (0.80, 3), (0.50, 4), (0.10, 5)]:
        err_count = int(pct * 20)
        ok_count = 20 - err_count
        for _ in range(ok_count):
            code = client.send_log("Request OK", "info", service)
            results[f"log_{code}"] = results.get(f"log_{code}", 0) + 1
        for _ in range(err_count):
            msg = random.choice(ERROR_MSGS)
            code = client.send_log(msg, "error", service)
            results[f"log_{code}"] = results.get(f"log_{code}", 0) + 1
        time.sleep(delay)
    return results
