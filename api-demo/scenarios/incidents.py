"""Scenario: Incidents + Events + Monitors — lifecycle simulation."""

from __future__ import annotations

import random
import time
from datetime import UTC, datetime, timedelta

from client import DdClient


def run_incident_lifecycle(client: DdClient) -> dict[str, str | int | None]:
    """Create an incident, annotate timeline, then resolve."""
    if not client.app_key:
        return {"error": "APP_KEY required for incidents"}

    results: dict[str, str | int | None] = {}
    svc = random.choice(["api-gateway", "payment-service", "user-service"])
    severity = random.choice(["SEV-3", "SEV-4", "SEV-5"])

    # 1. Create incident
    inc = client.create_incident(
        f"High latency on {svc} — p95 > 2s",
        severity,
        svc,
    )
    if not inc:
        return {"error": "incident create failed"}
    inc_id = inc.get("data", {}).get("id", "unknown")
    results["incident_id"] = inc_id
    results["severity"] = severity

    # 2. Send correlated error logs
    for _ in range(5):
        client.send_log(f"Timeout connecting to {svc}:5432", "error", svc)
        client.send_log(f"Retry attempt #{_ + 1} for {svc}", "warn", svc)
    results["logs_sent"] = 5

    # 3. Send metric spike
    for _ in range(3):
        client.send_metric(f"{svc}.latency_ms", random.gauss(2500, 500), svc)
    results["metrics_sent"] = 3

    # 4. Send event
    code = client.send_event(
        f"Incident {inc_id}: {severity} — {svc} p95 breach",
        f"Latency spiked to >2s on {svc}",
        "warning",
        svc,
    )
    results["event_status"] = code

    return results


def run_monitor_alert(client: DdClient) -> dict[str, str | int | None]:
    """Create a monitor and trigger a threshold breach via metric."""
    if not client.app_key:
        return {"error": "APP_KEY required for monitors"}

    svc = "api-gateway"
    mon = client.create_monitor(
        f"[{svc}] High error rate",
        f"avg(last_5m):avg:{svc}.error_rate{{*}} > 0.1",
        f"Error rate on {svc} exceeded 10%",
    )
    if not mon:
        return {"error": "monitor create failed"}
    mon_id = mon.get("id", "unknown")
    results: dict[str, str | int | None] = {"monitor_id": str(mon_id)}

    # Send metric points that breach threshold
    for _ in range(5):
        client.send_metric(f"{svc}.error_rate", random.uniform(0.15, 0.35), svc)
    results["error_metrics_sent"] = 5

    return results
