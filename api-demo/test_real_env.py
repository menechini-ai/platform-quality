#!/usr/bin/env python3
"""Real-environment test data seeder and runner for ObservAI.

Seeds Datadog with test telemetry (metrics, logs, events, incidents)
using api-demo services with distinct tags for each service/env.

Usage:
  uv run python api-demo/test_real_env.py --api-key xxx --app-key yyy --seed-only
  uv run python api-demo/test_real_env.py --api-key xxx --app-key yyy --run-scenario deploy
"""

from __future__ import annotations

import sys
import time

# Add backend to path
sys.path.insert(0, "/opt/data/workspace/observai/backend")

from client import DdClient, APIS, API_NAMES


def seed_all_services(dd: DdClient) -> dict[str, int]:
    """Seed all API services with test telemetry."""
    results = {"metrics": 0, "logs": 0, "events": 0, "monitors": 0, "incidents": 0}

    print("\n📡 Seeding all services with test telemetry...")
    for api_name in API_NAMES:
        cfg = APIS[api_name]
        svc = cfg.get("service", api_name)
        env = cfg.get("env", "dev")
        tier = cfg.get("tier", "backend")
        team = cfg.get("team", "observai")

        tags = [f"service:{svc}", f"env:{env}", f"tier:{tier}", f"team:{team}"]
        if "project" in cfg:
            tags.append(f"project:{cfg['project']}")

        print(f"  → {svc} ({env}/{tier})", end="", flush=True)

        # Create a client for this specific service
        svc_client = DdClient(
            api_key=dd.api_key,
            app_key=dd.app_key,
            site=dd.site,
            api_name=api_name,
        )

        # Send metrics
        for _ in range(5):
            svc_client.send_metric(f"{svc}.request_count", 100, "count")
            svc_client.send_metric(f"{svc}.latency_ms", 120, "gauge")
            svc_client.send_metric(f"{svc}.error_rate", 0.01, "gauge")
            svc_client.send_metric(f"{svc}.cpu_usage", 45, "gauge")
            results["metrics"] += 4

        # Send logs
        for msg, lvl in [
            (f"Request processed OK", "info"),
            (f"Slow query detected on /api/users", "warn"),
            (f"Connection timeout to downstream", "error"),
        ]:
            svc_client.send_log(msg, lvl)
            results["logs"] += 1

        # Send event
        svc_client.send_event(
            f"Test deployment of {svc}",
            f"Deployed {svc} v2.1.0 to {env}",
            "info",
        )
        results["events"] += 1

        # Create monitor (if app_key available)
        if dd.app_key:
            mon = svc_client.create_monitor(
                f"High latency: {svc} ({env})",
                f"avg(last_5m):avg:{svc}.latency_ms{{{','.join(tags)}}} > 500",
                f"Latency spike on {svc} in {env}",
                tags,
            )
            if mon:
                results["monitors"] += 1
                # Create incident
                inc = svc_client.create_incident(
                    f"Latency alert: {svc} ({env})",
                    "SEV-3",
                    False,  # customer_impacted
                )
                if inc:
                    results["incidents"] += 1

        print(" ✓")

    return results


def run_scenario(dd: DdClient, scenario: str) -> dict:
    """Run a specific SRE scenario from sre_engine.py."""
    # Import sre_engine's DdClient and scenario runner
    from sre_engine import SCENARIOS, run_scenario as run_sre_scenario, DdClient as SreDdClient

    if scenario not in SCENARIOS:
        print(f"❌ Unknown scenario: {scenario}")
        print(f"   Available: {list(SCENARIOS.keys())}")
        return {}

    print(f"\n🚀 Running scenario: {scenario}")

    # Convert to sre_engine's DdClient
    sre_dd = SreDdClient(dd.api_key, dd.app_key, dd.site)

    return run_sre_scenario(scenario, sre_dd)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ObservAI Real-Environment Test Runner")
    parser.add_argument("--api-key", help="Datadog API Key")
    parser.add_argument("--app-key", help="Datadog Application Key")
    parser.add_argument("--site", default="us5.datadoghq.com", help="Datadog site")
    parser.add_argument("--seed-only", action="store_true", help="Only seed test data, don't run scenarios")
    parser.add_argument("--scenario", choices=["deploy", "resource", "latency", "dependency", "data_corruption", "all"],
                        default="deploy", help="SRE scenario to run")
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios and exit")

    args = parser.parse_args()

    if args.list_scenarios:
        from sre_engine import SCENARIOS
        print("\nAvailable SRE Scenarios:")
        for name, cfg in SCENARIOS.items():
            print(f"  {name:20} {cfg['title']} ({cfg['severity']})")
        return 0

    if not args.api_key or not args.app_key:
        parser.error("--api-key and --app-key are required (except for --list-scenarios)")

    # Create Datadog client
    dd = DdClient(args.api_key, args.app_key, args.site)

    if args.seed_only:
        print("\n🌱 Seeding Datadog with test data...")
        results = seed_all_services(dd)
        print(f"\n✅ Seeding complete: {results}")
        return 0

    # Run scenario
    if args.scenario == "all":
        from sre_engine import SCENARIOS
        for name in SCENARIOS.keys():
            run_scenario(dd, name)
            time.sleep(2)  # Brief pause between scenarios
    else:
        run_scenario(dd, args.scenario)

    return 0


if __name__ == "__main__":
    sys.exit(main())