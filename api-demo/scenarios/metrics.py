"""Scenario: Metrics — custom metrics, load simulation, anomaly patterns."""

from __future__ import annotations

import math
import random
import time

from client import DdClient


def run_load_simulation(client: DdClient, service: str = "api-gateway") -> dict[str, int]:
    """Simulate load: ramp-up → peak → plateau → cool-down."""
    results = {}
    phases = [
        ("ramp-up", 0, 100, 20, 0.3),
        ("peak", 80, 120, 15, 0.2),
        ("plateau", 100, 110, 10, 0.5),
        ("cool-down", 100, 10, 20, 0.3),
    ]
    for phase, vmin, vmax, steps, delay in phases:
        for step in range(steps):
            t = step / steps
            rps = vmin + (vmax - vmin) * (
                1 - math.cos(t * math.pi / 2) if phase in ("ramp-up",) else t
            )
            latency = random.gauss(100 + (100 - rps) * 0.5, 20)
            errors = max(0, random.gauss(0.02 * rps, 0.5))

            results[f"metric_{client.send_metric(f'{service}.rps', rps, service)}"] = (
                results.get(f"metric_{client.send_metric(f'{service}.rps', rps, service)}", 0) + 1
            )
            client.send_metric(f"{service}.latency", max(1, latency), service)
            client.send_metric(f"{service}.errors", int(errors), service, mtype="count")
            time.sleep(delay)
    return results


def run_spike_test(client: DdClient) -> dict[str, int]:
    """Simulate a traffic spike on random service."""
    svc = random.choice(["api-gateway", "payment-service"])
    results = {}
    for i in range(30):
        spike = 1500 if 10 <= i <= 14 else random.randint(50, 200)
        code = client.send_metric(f"{svc}.rps", spike, svc)
        results[f"metric_{code}"] = results.get(f"metric_{code}", 0) + 1
        time.sleep(0.3)
    return results
