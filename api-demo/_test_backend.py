"""Test backend Datadog connectivity."""
import asyncio
import os

import httpx

KEY = os.environ.get("DATADOG_API_KEY", "")
APP = os.environ.get("DATADOG_APP_KEY", "")
SITE = "us5.datadoghq.com"


async def main():
    h = {"DD-API-KEY": KEY, "DD-APPLICATION-KEY": APP}
    async with httpx.AsyncClient() as c:
        # Monitors
        r = await c.get(f"https://api.{SITE}/api/v1/monitor", headers=h)
        print(f"Monitors: {r.status_code} ({len(r.json())} total)")

        # SLOs
        r = await c.get(f"https://api.{SITE}/api/v1/slo", headers=h)
        print(f"SLOs: {r.status_code} ({len(r.json().get('data', []))} total)")

        # Synthetics
        r = await c.get(f"https://api.{SITE}/api/v1/synthetics/tests", headers=h)
        print(f"Synthetics: {r.status_code}")

        # Logs search
        r = await c.post(
            f"https://api.{SITE}/api/v2/logs/events/search",
            headers={**h, "Content-Type": "application/json"},
            json={"filter": {"from": "now-2h", "to": "now"}, "limit": 5},
        )
        data = r.json()
        print(f"Logs search: {r.status_code} hits={len(data.get('data', []))}")
        for hit in data.get("data", [])[:3]:
            attrs = hit.get("attributes", {})
            print(f"  - {attrs.get('service','?')} | {attrs.get('status','?')} | {attrs.get('message','')[:80]}")

        # Metrics
        r = await c.get(f"https://api.{SITE}/api/v1/metrics", headers=h)
        print(f"Metrics list: {r.status_code} ({len(r.json().get('metrics', []))} names)")


asyncio.run(main())
