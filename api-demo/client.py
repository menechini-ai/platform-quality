"""Datadog API client — thin httpx wrapper for test/lab use.

Multiple named APIs with distinct tags for identification in Datadog.
"""

from __future__ import annotations

import random
import time
from typing import Any

import httpx

# ── Registry of named APIs with distinct tags ────────────────
# Each entry: name → {service, env, tier, extra_tags}
APIS: dict[str, dict[str, str]] = {
    "api-gateway": {"service": "api-gateway", "env": "prod", "tier": "infra", "team": "observai"},
    "user-service": {
        "service": "user-service",
        "env": "prod",
        "tier": "backend",
        "team": "observai",
    },
    "payment-service": {
        "service": "payment-service",
        "env": "prod",
        "tier": "backend",
        "team": "observai",
    },
    "order-service": {
        "service": "order-service",
        "env": "staging",
        "tier": "backend",
        "team": "observai",
    },
    "notification-service": {
        "service": "notification-service",
        "env": "dev",
        "tier": "backend",
        "team": "observai",
    },
    "observai-frontend": {
        "service": "observai-frontend",
        "env": "prod",
        "tier": "frontend",
        "project": "observai",
        "team": "observai",
    },
    "observai-backend": {
        "service": "observai-backend",
        "env": "prod",
        "tier": "backend",
        "project": "observai",
        "team": "observai",
    },
    "observai-worker": {
        "service": "observai-worker",
        "env": "staging",
        "tier": "worker",
        "project": "observai",
        "team": "observai",
    },
}

API_NAMES = list(APIS.keys())

ENVS = ["prod", "staging", "dev"]
STATUSES = ["error", "warn", "info", "debug"]
ENDPOINTS = ["/api/users", "/api/orders", "/api/payments", "/api/notifications", "/health"]
ERROR_MSGS = [
    "Connection timeout after 30s",
    "Database connection pool exhausted",
    "Rate limit exceeded for API key",
    "Invalid authentication token",
    "Memory usage exceeded threshold",
]


def _tags(api_name: str) -> str:
    """Build comma-separated tag string from API config."""
    cfg = APIS.get(api_name, {"service": api_name, "env": "dev", "team": "observai"})
    return ",".join(f"{k}:{v}" for k, v in cfg.items())


def _tag_list(api_name: str) -> list[str]:
    """Build list of 'key:value' tags from API config."""
    cfg = APIS.get(api_name, {"service": api_name, "env": "dev", "team": "observai"})
    return [f"{k}:{v}" for k, v in cfg.items()]


class DdClient:
    """Thin httpx client for Datadog API V1/V2 endpoints.

    Accepts an api_name to auto-tag all data sent.
    """

    def __init__(
        self,
        api_key: str,
        app_key: str = "",
        site: str = "datadoghq.com",
        api_name: str = "api-gateway",
    ):
        self.api_key = api_key
        self.app_key = app_key
        self.site = site
        self.api_name = api_name
        self.api_base = f"https://api.{site}"
        self.log_intake = f"https://http-intake.logs.{site}"
        h = {"DD-API-KEY": api_key, "Content-Type": "application/json"}
        if app_key:
            h["DD-APPLICATION-KEY"] = app_key
        self.headers = h
        self._api = httpx.Client(base_url=self.api_base, headers=h, timeout=15)
        self._logs = httpx.Client(base_url=self.log_intake, headers=h, timeout=15)

    def close(self) -> None:
        self._api.close()
        self._logs.close()

    def __enter__(self) -> DdClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _svc(self) -> str:
        return APIS.get(self.api_name, {}).get("service", self.api_name)

    def _env(self) -> str:
        return APIS.get(self.api_name, {}).get("env", "dev")

    # ── Logs V2 ────────────────────────────────────────────────

    def send_log(self, message: str, status: str = "info") -> int:
        r = self._logs.post(
            "/api/v2/logs",
            json=[
                {
                    "ddsource": "python",
                    "ddtags": _tags(self.api_name),
                    "hostname": f"test-{self._svc()}",
                    "service": self._svc(),
                    "message": message,
                    "status": status,
                    "timestamp": int(time.time() * 1000),
                }
            ],
        )
        return r.status_code

    def send_logs(self, count: int = 3) -> list[int]:
        return [
            self.send_log(
                random.choice(ERROR_MSGS) if random.random() < 0.3 else "Request processed",
                random.choice(STATUSES) if random.random() > 0.7 else "info",
            )
            for _ in range(count)
        ]

    # ── Metrics V2 ─────────────────────────────────────────────

    def send_metric(self, name: str, value: float, mtype: str = "gauge") -> int:
        r = self._api.post(
            "/api/v2/series",
            json={
                "series": [
                    {
                        "metric": name,
                        "type": 1 if mtype == "count" else 0,
                        "points": [{"timestamp": int(time.time()), "value": value}],
                        "tags": _tag_list(self.api_name),
                    }
                ]
            },
        )
        return r.status_code

    def send_metrics(self) -> list[int]:
        svc = self._svc()
        return [
            self.send_metric(f"{svc}.request_count", random.randint(10, 500), mtype="count"),
            self.send_metric(f"{svc}.latency_ms", round(random.gauss(120, 40), 1)),
            self.send_metric(f"{svc}.error_rate", round(random.uniform(0, 0.05), 4)),
            self.send_metric(f"{svc}.cpu_usage", round(random.uniform(10, 90), 1)),
        ]

    # ── Events V1 ──────────────────────────────────────────────

    def send_event(self, title: str, text: str, alert_type: str = "info") -> int:
        r = self._api.post(
            "/api/v1/events",
            json={
                "title": title,
                "text": text,
                "alert_type": alert_type,
                "tags": _tags(self.api_name),
                "host": f"test-{self._svc()}",
                "date_happened": int(time.time()),
            },
        )
        return r.status_code

    # ── Incidents V2 ───────────────────────────────────────────

    def create_incident(
        self, title: str, severity: str = "SEV-3", customer_impacted: bool = False
    ) -> dict[str, Any] | None:
        if not self.app_key:
            return None
        r = self._api.post(
            "/api/v2/incidents",
            json={
                "data": {
                    "type": "incidents",
                    "attributes": {
                        "title": title,
                        "severity": severity,
                        "customer_impacted": customer_impacted,
                        "fields": {"services": {"type": "string", "value": self._svc()}},
                    },
                }
            },
        )
        return r.json() if r.status_code in (200, 201) else None

    # ── Monitors V1 ────────────────────────────────────────────

    def create_monitor(
        self,
        name: str,
        query: str = "avg(last_5m):avg:system.cpu.user{*} > 90",
        message: str = "CPU alert",
    ) -> dict[str, Any] | None:
        if not self.app_key:
            return None
        r = self._api.post(
            "/api/v1/monitor",
            json={
                "name": name,
                "type": "query alert",
                "query": query,
                "message": message,
                "tags": [f"service:{self._svc()}", "team:observai"],
            },
        )
        return r.json() if r.status_code == 200 else None

    # ── SLOs V1 ────────────────────────────────────────────────

    def create_slo(
        self,
        name: str,
        monitor_ids: list[int],
        target: float = 99.9,
        warning: float = 99.0,
        timeframe: str = "30d",
    ) -> dict[str, Any] | None:
        """Create a monitor-based SLO. Warning must be < target."""
        if not self.app_key:
            return None
        if warning >= target:
            warning = target - 0.5
        r = self._api.post(
            "/api/v1/slo",
            json={
                "type": "monitor",
                "name": name,
                "thresholds": [{"target": target, "timeframe": timeframe, "warning": warning}],
                "monitor_ids": monitor_ids,
                "tags": [f"service:{self._svc()}", "team:observai"],
            },
        )
        return r.json() if r.status_code in (200, 201) else None

    # ── Synthetics V1 ──────────────────────────────────────────

    def create_synthetics_test(
        self, name: str, url: str = "https://example.com", frequency: int = 900
    ) -> dict[str, Any] | None:
        if not self.app_key:
            return None
        r = self._api.post(
            "/api/v1/synthetics/tests/api",
            json={
                "config": {
                    "assertions": [{"type": "statusCode", "target": 200, "operator": "is"}],
                    "request": {"method": "GET", "url": url},
                },
                "locations": ["aws:us-east-1"],
                "message": "Synthetic test",
                "name": name,
                "options": {"monitor_name": name, "tick_every": frequency},
                "subtype": "http",
                "tags": [f"service:{self._svc()}", "team:observai"],
                "type": "api",
            },
        )
        return r.json() if r.status_code == 200 else None

    # ── Error Tracking ─────────────────────────────────────────

    def send_error_tracking_event(self, message: str, kind: str = "ValueError") -> int:
        return self.send_log(f"[{kind}] {message}", "error")

    # ── Raw request helper ─────────────────────────────────────

    def request(self, method: str, path: str, json_body: Any = None) -> httpx.Response:
        return self._api.request(method, path, json=json_body)
