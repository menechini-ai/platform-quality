"""Datadog API Demo — laboratory runner.

Send test data for multiple tagged APIs, create monitors, SLOs,
synthetics, incidents, and error tracking samples.

Usage:
  uv run python api-demo/run.py                              # iter over all APIs, send data
  uv run python api-demo/run.py --all                        # send data + create monitors/SLOs/etc
  uv run python api-demo/run.py --create monitors            # create monitors only
  uv run python api-demo/run.py --iter 5 --api api-gateway   # single API
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from typing import Any

from client import API_NAMES, APIS, DdClient


def send_data(client: DdClient, iterations: int = 5, delay: float = 1.0) -> dict[str, int]:
    """Send logs + metrics + events for one API."""
    ok = errors = 0
    for i in range(1, iterations + 1):
        res: list[int] = []
        res += client.send_logs(random.randint(1, 5))
        res += client.send_metrics()
        res.append(
            client.send_event(
                f"[{client.api_name}] Demo #{i}",
                f"Iteration {i} for {client.api_name}",
                random.choice(["info", "warning", "error"]),
            )
        )
        for c in res:
            if str(c).startswith("2"):
                ok += 1
            else:
                errors += 1
        if i < iterations:
            time.sleep(delay)
    return {"ok": ok, "errors": errors}


def create_monitors(client: DdClient) -> dict[str, Any]:
    """Create monitors for current API."""
    svc = client._svc()
    monitors = []
    m = client.create_monitor(
        f"ObservAI — {svc} CPU > 80%",
        f"avg(last_5m):avg:{svc}.cpu_usage{{*}} > 80",
        f"CPU high on {svc}",
    )
    if m:
        monitors.append(m)
        print(f"  ✓ Monitor CPU: id={m.get('id')}")

    m = client.create_monitor(
        f"ObservAI — {svc} Latency > 500ms",
        f"avg(last_5m):avg:{svc}.latency_ms{{*}} > 500",
        f"Latency spike on {svc}",
    )
    if m:
        monitors.append(m)
        print(f"  ✓ Monitor Latency: id={m.get('id')}")

    m = client.create_monitor(
        f"ObservAI — {svc} Error Rate > 5%",
        f"avg(last_5m):avg:{svc}.error_rate{{*}} > 0.05",
        f"Error rate breach on {svc}",
    )
    if m:
        monitors.append(m)
        print(f"  ✓ Monitor Error Rate: id={m.get('id')}")

    return {"monitors": [m.get("id") for m in monitors if m]}


def create_slos(client: DdClient, monitor_ids: list[int]) -> dict[str, Any]:
    """Create SLOs for current API linked to its monitors."""
    if not monitor_ids:
        return {}
    svc = client._svc()
    env = client._env()
    slos = []

    s = client.create_slo(
        f"ObservAI — {svc} Uptime SLO (99.5%)",
        monitor_ids,
        target=99.5,
        warning=99.0,
    )
    if s:
        slos.append(s)
        print("  ✓ SLO Uptime: created")

    s = client.create_slo(
        f"ObservAI — {svc} Performance SLO (99%)",
        monitor_ids,
        target=99.0,
        warning=98.5,
    )
    if s:
        slos.append(s)
        print("  ✓ SLO Performance: created")

    return {"slos": len(slos)}


def create_synthetics(client: DdClient) -> dict[str, Any]:
    """Create a synthetic test for current API."""
    svc = client._svc()
    t = client.create_synthetics_test(
        f"ObservAI — {svc} Health Check",
        "https://httpbin.org/status/200",
    )
    if t:
        print(f"  ✓ Synthetic: public_id={t.get('public_id')}")
        return {"synthetic": t.get("public_id")}
    return {}


def create_incident(client: DdClient) -> dict[str, Any]:
    """Create a demo incident for current API."""
    svc = client._svc()
    inc = client.create_incident(
        f"ObservAI — High latency on {svc}",
        "SEV-4",
    )
    if inc:
        pid = inc.get("data", {}).get("attributes", {}).get("public_id")
        print(f"  ✓ Incident: public_id={pid}")
        return {"incident": pid}
    return {}


def send_error_tracking(client: DdClient) -> dict[str, int]:
    """Send error tracking events."""
    import random as rnd

    kinds = ["ValueError", "TimeoutError", "KeyError", "PermissionError", "ConnectionError"]
    ok = 0
    for _ in range(5):
        code = client.send_error_tracking_event(
            f"Error in {client._svc()}: {rnd.choice(['timeout', 'invalid input', 'access denied'])}",
            rnd.choice(kinds),
        )
        if str(code).startswith("2"):
            ok += 1
    return {"errors_sent": ok}


# ── Main ───────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="ObservAI — Datadog API Demo Lab")
    parser.add_argument("--api-key", default=os.environ.get("DATADOG_API_KEY", ""))
    parser.add_argument("--app-key", default=os.environ.get("DATADOG_APP_KEY", ""))
    parser.add_argument("--site", default=os.environ.get("DATADOG_SITE", "datadoghq.com"))
    parser.add_argument("--iter", type=int, default=5, help="Iterations per API")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between iterations")
    parser.add_argument("--api", "-a", choices=API_NAMES, help="Single API (default: all)")
    parser.add_argument(
        "--create",
        "-c",
        choices=["monitors", "slos", "synthetics", "incidents", "all"],
        help="Create resources",
    )
    parser.add_argument(
        "--send", action="store_true", default=True, help="Send test data (default: on)"
    )
    args = parser.parse_args()

    if not args.api_key:
        print("❌ DATADOG_API_KEY required")
        sys.exit(1)

    apis = [args.api] if args.api else API_NAMES

    for name in apis:
        print(f"\n{'=' * 50}")
        print(f"  {name}  ({APIS[name]})")
        print(f"{'=' * 50}")

        with DdClient(args.api_key, args.app_key, args.site, api_name=name) as client:
            # Send data
            if args.send:
                print(f"  Sending data ({args.iter} iter)...")
                r = send_data(client, args.iter, args.delay)
                print(f"  → {r['ok']} OK, {r['errors']} errors")

            # Create resources
            if args.create in ("monitors", "all"):
                print("  Creating monitors...")
                mon_result = create_monitors(client)
                monitor_ids = mon_result.get("monitors", [])

                if args.create == "all" and monitor_ids:
                    print("  Creating SLOs...")
                    create_slos(client, monitor_ids)

            if args.create in ("synthetics", "all"):
                print("  Creating synthetics...")
                create_synthetics(client)

            if args.create in ("incidents", "all"):
                print("  Creating incident...")
                create_incident(client)

            # Error tracking always
            if args.send:
                print("  Error tracking...")
                send_error_tracking(client)

    print(f"\n✅ Done — {len(apis)} API(s) processed")


if __name__ == "__main__":
    main()
