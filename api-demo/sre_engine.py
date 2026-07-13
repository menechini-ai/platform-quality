"""SRE Scenario Engine — realistic failure simulation for ObservAI.

Simulates 5 failure patterns (Deploy, Resource, Latency, Dependency, Data),
sends real Datadog telemetry, creates local DB records (incident, RCA, runbook,
auto-heal action), and returns MTTR breakdown + maturity impact.

Usage:
  uv run python api-demo/sre_engine.py --scenario deploy
  uv run python api-demo/sre_engine.py --list
  uv run python api-demo/sre_engine.py --scenario latency --api-key ... --app-key ...
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta
from typing import Any

# ── MTTR Breakdown ────────────────────────────────────────────────────
# MTTR = MTTD (detect) + MTTI (identify) + MTTK (know) + MTTA (act) + MTTR (resolve)


@dataclass
class MttrBreakdown:
    """Realistic MTTR breakdown in minutes for a failure pattern."""
    pattern: str
    mttd_min: float
    mtti_min: float
    mttk_min: float
    mtta_min: float
    mttr_min: float
    total_min: float = 0

    def __post_init__(self):
        self.total_min = self.mttd_min + self.mtti_min + self.mttk_min + self.mtta_min + self.mttr_min

    def breakdown(self) -> dict[str, float]:
        return asdict(self)


DB_PATH = "/opt/data/workspace/observai/backend/observai.db"

# ── 5 Failure Pattern Definitions ────────────────────────────────────

SCENARIOS: dict[str, dict[str, Any]] = {
    "deploy": {
        "title": "Deploy Failure — v2.1.5 regression",
        "severity": "SEV-2",
        "service": "api-gateway",
        "description": "Release v2.1.5 introduced N+1 query on /api/users endpoint. "
                       "p50 latency jumped from 120ms to 1200ms, error rate 0.1%→8.5%.",
        "rca_summary": "Missing database index on `transactions.user_id` introduced by v2.1.5",
        "root_cause": "Code change: ORM query lacked JOIN fetch, causing N+1 per user row. "
                      "Index was present in staging but missing in prod migration.",
        "recommendations": [
            "Rollback to v2.1.4 immediately",
            "Add composite index on (user_id, created_at) to transactions table",
            "Add performance regression test for all read endpoints in CI",
            "Implement canary deployments with traffic mirroring",
        ],
        "changes": [{"type": "deploy", "service": "api-gateway", "version": "v2.1.5", "rollback": "v2.1.4"}],
        "runbook_name": "Latency Spike Response — Post-Deploy",
        "runbook_steps": [
            {"order": 1, "action": "Check recent deploys", "command": "kubectl rollout history deployment/api-gateway"},
            {"order": 2, "action": "Check p50/p99 latency graphs", "command": "datadog dashboard latency-spike"},
            {"order": 3, "action": "Rollback to previous version", "command": "kubectl rollout undo deployment/api-gateway"},
            {"order": 4, "action": "Verify recovery", "command": "check error_rate < 1% for 5min"},
            {"order": 5, "action": "File postmortem", "command": "add index + perf test"},
        ],
        "self_heal_action": {"type": "rollback", "config": {"target_version": "v2.1.4", "service": "api-gateway"}},
        "monitor_query": "avg(last_5m):avg:system.cpu.user{service:api-gateway} > 80",
        "slo_target": 99.0,
        "mttr": MttrBreakdown("deploy", mttd_min=2, mtti_min=8, mttk_min=3, mtta_min=2, mttr_min=5),
    },
    "resource": {
        "title": "Resource Starvation — payment-service CPU 95%",
        "severity": "SEV-3",
        "service": "payment-service",
        "description": "Payment worker CPU sustained at 95% for 15min. "
                       "Auto-scale kicked in but HPA max replicas reached. "
                       "Payment queue backlog grew 50k messages.",
        "rca_summary": "Unexpected traffic 3x normal baseline after Black Friday campaign",
        "root_cause": "Capacity: HPA max replicas set too low (3) for promotional traffic. "
                      "CPU request misconfigured at 500m instead of 1.5 core per pod. "
                      "No vertical pod autoscaling configured.",
        "recommendations": [
            "Increase HPA max replicas from 3→10",
            "Adjust CPU requests to 1.5 cores per pod (match actual usage)",
            "Enable VPA in auto mode for burst traffic",
            "Set up queue-depth monitor on payment-worker queue",
            "Pre-scale before known promotional events",
        ],
        "changes": [{"type": "config", "service": "payment-service", "change": "hpa_max_replicas 3→10"}],
        "runbook_name": "CPU Saturation Response",
        "runbook_steps": [
            {"order": 1, "action": "Check current CPU and HPA status", "command": "kubectl top pods -l app=payment"},
            {"order": 2, "action": "Increase HPA max replicas", "command": "kubectl patch hpa payment-service -p '{\"spec\":{\"maxReplicas\":10}}'"},
            {"order": 3, "action": "Check queue backlog depth", "command": "kubectl exec payment-worker -- rabbitmqctl list_queues"},
            {"order": 4, "action": "Monitor recovery", "command": "check cpu < 80% for 5min"},
        ],
        "self_heal_action": {"type": "scale", "config": {"replicas": 10, "service": "payment-service"}},
        "monitor_query": "avg(last_5m):avg:system.cpu.user{service:payment-service} > 85",
        "slo_target": 99.5,
        "mttr": MttrBreakdown("resource", mttd_min=5, mtti_min=10, mttk_min=5, mtta_min=3, mttr_min=10),
    },
    "latency": {
        "title": "Latency Cascade — user-service DB pool exhausted",
        "severity": "SEV-2",
        "service": "user-service",
        "description": "Connection pool to Postgres exhausted. All 50 connections "
                       "held by long-running queries from a bad index hint. "
                       "p99 latency 50ms→8s. Downstream services timing out.",
        "rca_summary": "Postgres connection pool starvation from seq scan on users table",
        "root_cause": "Missing index on `users.organization_id` — recent schema change "
                      "dropped the index. Queries fell back to sequential scan holding "
                      "connections for 30s+ instead of 2ms index lookup.",
        "recommendations": [
            "Recreate index on users.organization_id",
            "Set statement_timeout=10s on Postgres to kill runaway queries",
            "Implement connection pool with max_wait queue in app",
            "Add PgBouncer between app and database",
            "Monitor pool utilization with Datadog PG integration",
        ],
        "changes": [{"type": "schema", "service": "user-service", "change": "index dropped during migration v3.2.0"}],
        "runbook_name": "DB Connection Pool Exhaustion",
        "runbook_steps": [
            {"order": 1, "action": "Check active connections", "command": "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"},
            {"order": 2, "action": "Kill long-running queries", "command": "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE now() - query_start > interval '30s'"},
            {"order": 3, "action": "Recreate missing index", "command": "CREATE INDEX CONCURRENTLY idx_users_org ON users(organization_id)"},
            {"order": 4, "action": "Verify recovery", "command": "check p99 < 200ms for 5min"},
        ],
        "self_heal_action": {"type": "script", "config": {"script": "pg_recreate_index_users_org.sh", "service": "user-service"}},
        "monitor_query": "avg(last_5m):avg:system.cpu.user{service:user-service} > 85",
        "slo_target": 99.0,
        "mttr": MttrBreakdown("latency", mttd_min=3, mtti_min=15, mttk_min=5, mtta_min=2, mttr_min=8),
    },
    "dependency": {
        "title": "Dependency Failure — Redis cluster degraded",
        "severity": "SEV-1",
        "service": "api-gateway",
        "description": "Redis primary node OOM. Cluster fell back to replica with stale data. "
                       "Session cache misses 100%. All authenticated requests fail. "
                       "Affects 60% of traffic (logged-in users).",
        "rca_summary": "Redis maxmemory exceeded — no eviction policy set",
        "root_cause": "Configuration: Redis instance provisioned with 1GB maxmemory "
                      "but no 'maxmemory-policy allkeys-lru'. New user sessions grew "
                      "until OOM killer terminated the primary. Replica had 30min old data.",
        "recommendations": [
            "Set maxmemory-policy allkeys-lru on Redis config",
            "Increase Redis instance memory from 1GB→4GB",
            "Add Redis cluster with automatic failover (3 nodes)",
            "Implement local session cache fallback in app",
            "Alert on Redis memory usage > 75%",
        ],
        "changes": [{"type": "config", "service": "redis", "change": "maxmemory-policy unset → allkeys-lru"}],
        "runbook_name": "Redis Degraded/Failover Response",
        "runbook_steps": [
            {"order": 1, "action": "Check Redis node roles", "command": "redis-cli -h redis-cluster info replication"},
            {"order": 2, "action": "Force failover to replica", "command": "redis-cli -h redis-replica cluster failover"},
            {"order": 3, "action": "Set eviction policy on primary", "command": "redis-cli config set maxmemory-policy allkeys-lru"},
            {"order": 4, "action": "Verify session recovery", "command": "check /api/auth endpoint"},
        ],
        "self_heal_action": {"type": "script", "config": {"script": "redis_failover.sh", "service": "redis"}},
        "monitor_query": "avg(last_5m):avg:system.cpu.user{service:api-gateway} > 85",
        "slo_target": 99.9,
        "mttr": MttrBreakdown("dependency", mttd_min=1, mtti_min=12, mttk_min=4, mtta_min=3, mttr_min=15),
    },
    "data_corruption": {
        "title": "Data Corruption — order-service schema migration v4.0 failed",
        "severity": "SEV-2",
        "service": "order-service",
        "description": "Schema migration v4.0 added NOT NULL constraint on `orders.discount_pct` "
                       "without backfilling existing NULL rows. 25% of order reads crash. "
                       "No rollback plan in migration script.",
        "rca_summary": "Rollback-incompatible schema change applied without data migration",
        "root_cause": "Process: Migration tested only on empty staging DB. "
                      "Production had 50k orders with NULL discount_pct. "
                      "No pre-migration validation step. No canary migration strategy.",
        "recommendations": [
            "Run backfill: UPDATE orders SET discount_pct=0 WHERE discount_pct IS NULL",
            "Remove NOT NULL constraint and add app-level validation instead",
            "Implement migration testing on production-sized clone",
            "Add pre-migration data quality checks",
            "Write rollback script for every future migration",
        ],
        "changes": [{"type": "migration", "service": "order-service", "change": "migration v4.0 adding NOT NULL without backfill"}],
        "runbook_name": "Schema Migration Recovery",
        "runbook_steps": [
            {"order": 1, "action": "Run backfill query", "command": "UPDATE orders SET discount_pct=0 WHERE discount_pct IS NULL"},
            {"order": 2, "action": "Drop NOT NULL constraint", "command": "ALTER TABLE orders ALTER COLUMN discount_pct DROP NOT NULL"},
            {"order": 3, "action": "Fix migration script", "command": "add backfill step BEFORE constraint"},
            {"order": 4, "action": "Verify data integrity", "command": "SELECT count(*) FROM orders WHERE discount_pct IS NULL"},
        ],
        "self_heal_action": {"type": "script", "config": {"script": "rollback_migration_v4.sh", "service": "order-service"}},
        "monitor_query": "avg(last_5m):avg:system.cpu.user{service:order-service} > 85",
        "slo_target": 99.5,
        "mttr": MttrBreakdown("data_corruption", mttd_min=4, mtti_min=20, mttk_min=8, mtta_min=5, mttr_min=25),
    },
}


# ── Datadog Client ────────────────────────────────────────────────────

class DdClient:
    """Direct Datadog HTTP client for lab simulation."""
    def __init__(self, api_key: str, app_key: str, site: str = "us5.datadoghq.com"):
        self.api_key = api_key
        self.app_key = app_key
        self.site = site
        self.api_base = f"https://api.{site}"
        self.log_intake = f"https://http-intake.logs.{site}"
        self.headers = {"DD-API-KEY": api_key, "Content-Type": "application/json"}
        if app_key:
            self.headers["DD-APPLICATION-KEY"] = app_key

    def _req(self, method: str, url: str, json_body: Any = None) -> dict[str, Any] | None:
        if not self.api_key:
            return {"id": 99999, "data": {"id": "dry-run-fake-id"}}
        import httpx
        try:
            r = httpx.request(method, url, headers=self.headers, json=json_body, timeout=15)
            if r.status_code in (200, 201, 202):
                return r.json() if r.text else {"status": r.status_code}
            print(f"  ⚠ {method} {url} → {r.status_code}: {r.text[:100]}")
            return None
        except Exception as e:
            print(f"  ⚠ {method} {url} → {e}")
            return None

    def send_metric(self, name: str, value: float, mtype: str = "gauge", tags: list[str] | None = None) -> bool:
        body = {"series": [{
            "metric": name, "type": 1 if mtype == "count" else 0,
            "points": [{"timestamp": int(time.time()), "value": value}],
            "tags": tags or [],
        }]}
        return self._req("POST", f"{self.api_base}/api/v2/series", body) is not None

    def send_log(self, msg: str, status: str = "info", svc: str = "", tags: list[str] | None = None) -> bool:
        body = [{"ddsource": "sre-engine", "ddtags": ",".join(tags or []), "service": svc, "message": msg, "status": status}]
        return self._req("POST", f"{self.log_intake}/api/v2/logs", body) is not None

    def send_event(self, title: str, text: str, alert_type: str = "info", tags: list[str] | None = None) -> bool:
        body = {"title": title, "text": text, "alert_type": alert_type, "tags": tags or [], "date_happened": int(time.time())}
        return self._req("POST", f"{self.api_base}/api/v1/events", body) is not None

    def create_monitor(self, name: str, query: str, msg: str, tags: list[str] | None = None) -> dict[str, Any] | None:
        if not self.app_key:
            return None
        body = {"name": name, "type": "query alert", "query": query, "message": msg, "tags": tags or []}
        return self._req("POST", f"{self.api_base}/api/v1/monitor", body)

    def create_incident(self, title: str, severity: str = "SEV-3", svc: str = "") -> dict[str, Any] | None:
        if not self.app_key:
            return None
        body = {
            "data": {
                "type": "incidents",
                "attributes": {
                    "title": title, "severity": severity, "customer_impacted": severity in ("SEV-1", "SEV-2"),
                    "description": f"Incident: {title}",
                },
                "relationships": {
                    "services": {
                        "data": [{"type": "services", "id": s.strip()} for s in svc.split(",") if s.strip()]
                    }
                }
            }
        }
        if severity in ("SEV-1", "SEV-2"):
            body["data"]["attributes"]["customer_impact_start"] = datetime.now(UTC).isoformat()
            body["data"]["attributes"]["customer_impact_scope"] = "60% of authenticated users affected"
        return self._req("POST", f"{self.api_base}/api/v2/incidents", body)


# ── Local DB Helpers ──────────────────────────────────────────────────

def _to_hex(u: uuid.UUID) -> str:
    return u.hex


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _time_ago(minutes: int) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()


def db_ensure_tables():
    """Create tables via ORM if they don't exist."""
    import subprocess, sys
    p = subprocess.run(
        [sys.executable, "-c", "from app.core.db import engine, Base; Base.metadata.create_all(bind=engine); print('tables ok')"],
        cwd="/opt/data/workspace/observai/backend", capture_output=True, text=True, timeout=10,
    )
    if p.returncode != 0:
        print(f"  ⚠ DB init cwd backend/: {p.stderr[:200]}")


def db_insert(table: str, data: dict[str, Any]) -> None:
    if not os.path.exists(DB_PATH):
        print(f"  ⚠ DB not found: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    keys = list(data.keys())
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in data.values()]
    placeholders = ",".join("?" for _ in keys)
    sql = f"INSERT OR IGNORE INTO {table} ({','.join(keys)}) VALUES ({placeholders})"
    try:
        conn.execute(sql, vals)
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"  ⚠ DB insert failed: {e}")
    conn.close()


def get_runbook_id(name: str) -> str | None:
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id FROM runbooks WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row[0] if row else None


# ── Scenario Runner ───────────────────────────────────────────────────

def categorize_severity(s: str) -> int:
    try:
        return int(s.split("-")[1])
    except (IndexError, ValueError):
        return 3


def run_scenario(name: str, dd: DdClient) -> dict[str, Any]:
    """Execute a single failure scenario end-to-end."""

    cfg = SCENARIOS[name]
    mttr = cfg["mttr"]
    svc = cfg["service"]
    tags = [f"service:{svc}", "team:observai", f"scenario:{name}"]

    print(f"\n{'='*55}")
    print(f"  🔥 {cfg['title']}")
    print(f"  Severity: {cfg['severity']}  |  Service: {svc}")
    print(f"{'='*55}")

    results: dict[str, Any] = {"scenario": name, "service": svc, "severity": cfg['severity']}
    incident_id: uuid.UUID = uuid.uuid4()
    runbook_id: uuid.UUID = uuid.uuid4()
    action_id: uuid.UUID = uuid.uuid4()

    # ── Phase 1: Send telemetry ──────────────────────────────────
    print(f"\n  [1/6] Sending fault telemetry...")

    metric_templates = {
        "deploy": [
            (f"{svc}.latency_ms", lambda i: round(120 + (1100 * (1 - math.exp(-(i-2)*0.5))) if i >= 2 else 120 + random.gauss(10, 5), 1)),
            (f"{svc}.error_rate", lambda i: round(0.001 if i < 2 else 0.02 * (i-1), 4)),
            (f"{svc}.request_count", lambda i: random.randint(80, 120)),
        ],
        "resource": [
            (f"{svc}.cpu_usage", lambda i: round(min(40 + i*8 + random.gauss(0, 3), 98), 1)),
            (f"{svc}.memory_usage", lambda i: round(60 + i*4, 1)),
            (f"{svc}.queue_depth", lambda i: round(100 * (1 + i*0.4))),
        ],
        "latency": [
            (f"{svc}.latency_ms", lambda i: round(min(50*(1+i*0.8)+random.gauss(0,20), 8000), 1)),
            (f"{svc}.db_connections", lambda i: round(10 + i*5)),
            (f"{svc}.error_rate", lambda i: round(min(0.001*i*i, 0.15), 4)),
        ],
        "dependency": [
            ("redis.mem.used_pct", lambda i: round(60 + i*5, 1)),
            ("redis.cache_hit_pct", lambda i: round(max(100 - i*10, 0), 1)),
            (f"{svc}.auth_error_rate", lambda i: round(min(0.01*i*i, 0.60), 4)),
        ],
        "data_corruption": [
            (f"{svc}.error_rate", lambda i: round(min(0.005*i*i, 0.30), 4)),
            (f"{svc}.db_error_rate", lambda i: round(min(0.005*i*i*0.8, 0.24), 4)),
            (f"{svc}.request_count", lambda i: random.randint(50, 100)),
        ],
    }

    faults_sent = 0
    for i in range(8):
        for m_name, m_fn in metric_templates.get(name, []):
            dd.send_metric(m_name, m_fn(i), tags=tags)
            faults_sent += 1
        time.sleep(0.05)
    results["metrics_sent"] = faults_sent

    # Logs
    log_templates = {
        "deploy": [
            ("ERROR: N+1 query detected on /api/users (500ms per row)", "error"),
            ("WARN: connection pool 80% utilized", "warn"),
            ("ERROR: POST /api/users/ timeout after 30s", "error"),
            ("INFO: deploy v2.1.5 completed", "info"),
        ],
        "resource": [
            ("ERROR: CPU throttled at 95% for 300s", "error"),
            ("WARN: HPA max replicas reached (3/3)", "warn"),
            ("ERROR: payment queue depth 50000", "error"),
            ("INFO: auto-scale triggered", "info"),
        ],
        "latency": [
            ("ERROR: FATAL: remaining connection slots reserved for non-replication superuser", "error"),
            ("WARN: query seq scan on users (estimated 50k rows)", "warn"),
            ("ERROR: timeout reading from downstream user-service", "error"),
        ],
        "dependency": [
            ("ERROR: Redis connection refused (OOM killed)", "error"),
            ("WARN: session cache miss, falling back to DB", "warn"),
            ("ERROR: 401 auth failed for session token", "error"),
            ("CRITICAL: Redis cluster degraded (1/3 nodes up)", "error"),
        ],
        "data_corruption": [
            ("ERROR: null value in column discount_pct violates NOT NULL constraint", "error"),
            ("WARN: migration v4.0 applied with 50202 null values", "warn"),
            ("ERROR: 25% of orders failing on read", "error"),
        ],
    }
    log_count = 0
    for msg, lvl in log_templates.get(name, []):
        dd.send_log(f"{svc} — {msg}", lvl, svc, tags)
        log_count += 1
    results["logs_sent"] = log_count

    # Events
    event_texts = {
        "deploy": "🚀 Deploy v2.1.5 rolled out — p50 latency spike detected",
        "resource": "🔥 CPU 95% sustained — HPA at max replicas",
        "latency": "🐘 DB pool exhaustion — p99 8s",
        "dependency": "💀 Redis OOM — cluster degraded, 60% traffic affected",
        "data_corruption": "🗃️ Schema migration v4.0 — order read errors at 25%",
    }
    dd.send_event(f"[{cfg['severity']}] {cfg['title'][:80]}", event_texts.get(name, ""), "error", tags)
    results["events_sent"] = 1

    # ── Phase 2: Create monitor in Datadog ──────────────────────
    print(f"  [2/6] Creating monitor + incident...")
    time.sleep(3)  # wait for metrics to index
    mon = dd.create_monitor(
        f"SRE Demo — {cfg['title'][:60]}",
        cfg["monitor_query"],
        f"{cfg['title']} — check dashboard",
        tags,
    )
    results["dd_monitor_id"] = str(mon.get("id", "")) if mon else ""
    results["dd_monitor_created"] = bool(mon)

    dd_inc = dd.create_incident(cfg["title"], cfg["severity"], svc)
    results["dd_incident_id"] = dd_inc.get("data", {}).get("id", "") if dd_inc else ""

    # ── Phase 3: Create local DB records ─────────────────────────
    print(f"  [3/6] Creating local DB records...")

    # incident
    db_insert("incidents", {
        "id": _to_hex(incident_id),
        "title": cfg["title"],
        "description": cfg["description"],
        "severity": cfg["severity"],
        "status": "active",
        "service": svc,
        "dd_event_id": results["dd_incident_id"],
        "dd_monitor_id": results["dd_monitor_id"],
        "started_at": _time_ago(int(mttr.mttd_min + mttr.mtti_min + mttr.mttk_min + mttr.mtta_min + 5)),
        "created_at": _time_ago(int(mttr.total_min + 5)),
        "updated_at": _now(),
    })

    # timeline
    for etype, content in [
        ("detected", f"Monitor fired: {cfg['monitor_query']}"),
        ("identified", f"RCA: {cfg['root_cause'][:200]}"),
        ("runbook_matched", f"Runbook '{cfg['runbook_name']}' applied"),
        ("action_executed", f"Auto-heal: {cfg['self_heal_action']['type']}"),
        ("resolved", f"Incident resolved. MTTR: {mttr.total_min:.0f}min"),
    ]:
        db_insert("incident_timeline", {
            "id": _to_hex(uuid.uuid4()),
            "incident_id": _to_hex(incident_id),
            "event_type": etype,
            "content": content,
            "author": "sre-engine",
            "created_at": _now(),
        })

    # RCA
    db_insert("rca_reports", {
        "id": _to_hex(uuid.uuid4()),
        "incident_id": _to_hex(incident_id),
        "summary": cfg["rca_summary"],
        "root_cause": cfg["root_cause"],
        "created_at": _now(),
        "timeline": [
            {"time": _time_ago(int(mttr.mttd_min)), "event": "fault injected"},
            {"time": _time_ago(int(mttr.mttd_min + mttr.mtti_min)), "event": "RCA complete"},
            {"time": _now(), "event": "resolution applied"},
        ],
        "metrics_snapshot": {"service": svc, "scenario": name,
                            "mttd_min": mttr.mttd_min, "mtti_min": mttr.mtti_min,
                            "mttr_total_min": mttr.total_min},
        "changes": cfg["changes"],
        "recommendations": cfg["recommendations"],
    })

    # runbook
    existing_rb = get_runbook_id(cfg["runbook_name"])
    if not existing_rb:
        db_insert("runbooks", {
            "id": _to_hex(runbook_id),
            "name": cfg["runbook_name"],
            "description": cfg["description"],
            "triggers": [{"metric": cfg['monitor_query'], "pattern": name}],
            "steps": cfg["runbook_steps"],
            "is_active": 1,
            "created_at": _now(),
        })
        results["runbook_id"] = _to_hex(runbook_id)
    else:
        results["runbook_id"] = existing_rb

    # auto-heal action
    db_insert("auto_heal_actions", {
        "id": _to_hex(action_id),
        "incident_id": _to_hex(incident_id),
        "monitor_id": results["dd_monitor_id"],
        "action_type": cfg["self_heal_action"]["type"],
        "action_config": cfg["self_heal_action"]["config"],
        "triggered_by": "auto",
        "status": "pending",
        "requested_at": _now(),
    })
    results["action_id"] = _to_hex(action_id)

    # postmortem report
    content = (
        f"## Summary\n{cfg['description'][:200]}\n\n"
        f"### Root Cause\n{cfg['root_cause'][:300]}\n\n"
        f"### MTTR Breakdown\n"
        f"- MTTD (detect): {mttr.mttd_min}min\n- MTTI (identify): {mttr.mtti_min}min\n"
        f"- MTTK (know): {mttr.mttk_min}min\n- MTTA (act): {mttr.mtta_min}min\n"
        f"- MTTR (resolve): {mttr.mttr_min}min\n- **Total: {mttr.total_min}min**\n\n"
        f"### Recommendations\n" + "\n".join(f"- {r}" for r in cfg['recommendations'])
    )
    db_insert("reports", {
        "id": _to_hex(uuid.uuid4()),
        "report_type": "postmortem",
        "title": f"Postmortem: {cfg['title'][:80]}",
        "content": content,
        "tags": json.dumps(["incident", "postmortem", name, svc]),
        "metadata": json.dumps({"scenario": name, "incident_id": _to_hex(incident_id),
                               "severity": cfg["severity"], "mttr_total_min": mttr.total_min}),
        "created_at": _now(),
    })

    # ── Phase 4: MTTR Summary ───────────────────────────────────
    print(f"\n  [4/6] MTTR Breakdown:")
    print(f"    ├─ MTTD (detect):     {mttr.mttd_min:5.0f} min  — monitor fires")
    print(f"    ├─ MTTI (identify):   {mttr.mtti_min:5.0f} min  — RCA pinpoints cause")
    print(f"    ├─ MTTK (know):       {mttr.mttk_min:5.0f} min  — runbook matched")
    print(f"    ├─ MTTA (act):        {mttr.mtta_min:5.0f} min  — action approved/executed")
    print(f"    ├─ MTTR (resolve):    {mttr.mttr_min:5.0f} min  — incident closed")
    print(f"    └─ TOTAL:             {mttr.total_min:5.0f} min")
    results["mttr"] = mttr.breakdown()

    # ── Phase 5: SLO ────────────────────────────────────────────
    print(f"  [5/6] Creating SLO in Datadog...")
    if dd.app_key and mon:
        mid = mon.get("id")
        if mid:
            slo_body = {
                "type": "monitor",
                "name": f"SRE Demo — {cfg['title'][:50]} SLO ({cfg['slo_target']}%)",
                "thresholds": [{"target": cfg["slo_target"], "timeframe": "30d", "warning": min(cfg["slo_target"] + 0.5, 99.95)}],
                "monitor_ids": [mid],
                "tags": tags,
            }
            results["slo_created"] = bool(dd._req("POST", f"{dd.api_base}/api/v1/slo", slo_body))

    results["status"] = "completed"
    print(f"\n  ✅ Scenario '{name}' done — MTTR: {mttr.total_min:.0f}min")
    return results


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SRE Scenario Engine — ObservAI")
    parser.add_argument("--scenario", "-s", choices=list(SCENARIOS.keys()) + ["all"], default="deploy",
                       help="Failure scenario to run")
    parser.add_argument("--all", "-a", action="store_true", help="Run all scenarios")
    parser.add_argument("--list", "-l", action="store_true", help="List available scenarios")
    parser.add_argument("--api-key", default=os.environ.get("DATADOG_API_KEY", ""))
    parser.add_argument("--app-key", default=os.environ.get("DATADOG_APP_KEY", ""))
    parser.add_argument("--site", default=os.environ.get("DATADOG_SITE", "us5.datadoghq.com"))
    args = parser.parse_args()

    if args.list:
        print("\nAvailable SRE Scenarios:")
        print(f"{'Name':25s} {'Severity':10s} {'Service':20s} {'MTTR(min)':10s} {'Description'}")
        print("-" * 90)
        for n, c in SCENARIOS.items():
            m = c["mttr"]
            print(f"{n:25s} {c['severity']:10s} {c['service']:20s} {m.total_min:<10.0f} {c['title'][:55]}")
        return

    db_ensure_tables()
    dd = DdClient(args.api_key, args.app_key, args.site)
    if not args.api_key:
        print("  ⚠ No API key — dry-run (no Datadog data)")

    scenarios_to_run = list(SCENARIOS.keys()) if (args.scenario == "all" or args.all) else [args.scenario]
    for name in scenarios_to_run:
        run_scenario(name, dd)
        if len(scenarios_to_run) > 1:
            time.sleep(2)

    print(f"\n{'='*55}")
    print(f"  All scenarios complete.")
    print(f"  Run assessment: POST /api/v1/maturity/assess")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
