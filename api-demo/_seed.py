"""Seed ObservAI DB with demo data using hex UUIDs (SQLAlchemy-compatible)."""
import sqlite3, uuid, json
from datetime import UTC, datetime, timedelta

DB = "/opt/data/workspace/observai/backend/observai.db"
h = lambda: uuid.uuid4().hex  # hex UUID — no hyphens!
now = datetime.now(UTC)

conn = sqlite3.connect(DB)

# Clean
tables = ["auto_heal_actions", "incident_timeline", "analysis_results",
          "incidents", "rca_reports", "reports", "health_snapshots",
          "slos", "maturity_assessments", "runbooks"]
for t in tables:
    conn.execute(f"DELETE FROM {t}")

# Incidents
iid1 = h()
iid2 = h()
conn.executemany(
    "INSERT INTO incidents (id, title, description, severity, status, service, started_at, created_at, updated_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [
        (iid1, "Payment Service — 5xx Error Spike", "Error rate exceeded 5% threshold",
         "SEV-2", "investigating", "payment-service", now.isoformat(), now.isoformat(), now.isoformat()),
        (iid2, "API Gateway — P50 Latency Breach", "P50 latency exceeded 500ms SLO threshold",
         "SEV-3", "resolved", "api-gateway",
         (now - timedelta(hours=2)).isoformat(), (now - timedelta(hours=2)).isoformat(), now.isoformat()),
    ]
)

# Incident timeline
conn.executemany(
    "INSERT INTO incident_timeline (id, incident_id, event_type, content, author, created_at) VALUES (?, ?, ?, ?, ?, ?)",
    [
        (h(), iid1, "detected", "Monitor triggered: 5xx error rate > 5%", "datadog", now.isoformat()),
        (h(), iid1, "investigation", "Checking recent deploys and DB query performance", "sre-bot", now.isoformat()),
        (h(), iid2, "detected", "Monitor triggered: P50 latency > 500ms", "datadog", (now - timedelta(hours=2)).isoformat()),
    ]
)

# Auto-heal action
aid = h()
conn.execute(
    "INSERT INTO auto_heal_actions (id, incident_id, action_type, action_config, triggered_by, status, requested_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)",
    (aid, iid1, "rollback", json.dumps({"service": "payment-service", "version": "v2.1.4"}), "monitor", "pending", now.isoformat())
)

# RCA reports
conn.executemany(
    "INSERT INTO rca_reports (id, incident_id, summary, root_cause, timeline, changes, recommendations, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    [
        (h(), iid1, "5xx spike caused by N+1 query in payment processing",
         "Missing database index on payment_transactions.user_id",
         json.dumps([{"time":"T-5m","event":"deploy v2.1.5"},{"time":"T-2m","event":"error rate spikes"}]),
         json.dumps([{"type":"deploy","service":"payment-service","version":"v2.1.5"}]),
         json.dumps(["Add composite index on payment_transactions(status, created_at)",
                     "Add circuit breaker on payment gateway calls"]), now.isoformat()),
        (h(), iid2, "Latency breach caused by increased traffic from campaign",
         "Autoscaling threshold too high for traffic spike",
         json.dumps([{"time":"T-1h","event":"campaign launch"},{"time":"T-30m","event":"latency increases"}]),
         json.dumps([{"type":"config","service":"api-gateway","change":"autoscaling threshold: 70% -> 50%"}]),
         json.dumps(["Reduce autoscaling CPU threshold", "Add predictive scaling based on campaign schedule"]),
         now.isoformat()),
    ]
)

# Reports (postmortems) — incident_id in metadata
conn.executemany(
    "INSERT INTO reports (id, report_type, title, content, tags, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
    [
        (h(), "postmortem", "Postmortem: Payment Service — 5xx Error Spike",
         "## Summary\n5xx error spike on payment-service.\n## Root Cause\nN+1 query from v2.1.5 deploy.\n## Action Items\n1. Add composite index\n2. Add circuit breaker",
         json.dumps(["payment","5xx","N+1"]),
         json.dumps({"incident_id": iid1, "service": "payment-service", "severity": "SEV-2"}), now.isoformat()),
        (h(), "postmortem", "Postmortem: API Gateway — P50 Latency Breach",
         "## Summary\nLatency breach during campaign launch hour.\n## Root Cause\nAutoscaling threshold too high.",
         json.dumps(["api-gateway","latency","campaign"]),
         json.dumps({"incident_id": iid2, "service": "api-gateway", "severity": "SEV-3"}), now.isoformat()),
    ]
)

# Health snapshots
services_slis = [
    ("api-gateway", "latency_p50", 99.5, 120, 0.5, 85.0, "healthy"),
    ("api-gateway", "error_rate", 99.9, 0.5, 0.1, 95.0, "healthy"),
    ("payment-service", "latency_p50", 99.0, 250, 1.2, 60.0, "warning"),
    ("payment-service", "error_rate", 99.5, 2.1, 2.0, 40.0, "warning"),
    ("order-service", "latency_p50", 99.5, 180, 0.3, 90.0, "healthy"),
    ("order-service", "throughput", 99.0, 1500, 0.0, 100.0, "healthy"),
    ("notification-service", "delivery_rate", 99.5, 98.5, 0.2, 95.0, "healthy"),
    ("notification-service", "latency_p50", 99.0, 80, 0.1, 97.0, "healthy"),
    ("user-service", "latency_p50", 99.5, 60, 0.1, 98.0, "healthy"),
    ("user-service", "error_rate", 99.9, 0.1, 0.0, 100.0, "healthy"),
]
conn.executemany(
    "INSERT INTO health_snapshots (id, service, sli_name, slo_target, current_value, burn_rate, error_budget_remaining, status, snapshot_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [(h(), svc, sli, target, val, burn, ebr, status, now.isoformat()) for svc, sli, target, val, burn, ebr, status in services_slis]
)

# SLOs
conn.executemany(
    "INSERT INTO slos (id, dd_id, name, description, target, time_window, service, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    [
        (h(), None, "API Gateway Latency P50", "P50 latency below 200ms", 99.5, "30d", "api-gateway", now.isoformat()),
        (h(), None, "Payment Service Availability", "Payment success rate above 99.9%", 99.9, "30d", "payment-service", now.isoformat()),
        (h(), None, "Order Processing Time", "Orders processed within 5 seconds", 99.0, "7d", "order-service", now.isoformat()),
    ]
)

# Runbooks
conn.executemany(
    "INSERT INTO runbooks (id, name, description, triggers, steps, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
    [
        (h(), "Latency Spike Response", "Auto-remediation for latency spikes",
         json.dumps([{"type": "monitor", "tags": ["severity:SEV-3", "metric:latency"]}]),
         json.dumps([{"action": "investigate", "target": "check recent deploys"},
                     {"action": "rollback", "target": "last stable version"}]),
         1, now.isoformat()),
        (h(), "Auto-Rollback", "Automatic rollback on critical error rate",
         json.dumps([{"type": "monitor", "tags": ["metric:error_rate", "threshold:5%"]}]),
         json.dumps([{"action": "rollback", "target": "payment-service", "version": "prev"}]),
         1, now.isoformat()),
    ]
)

conn.commit()
conn.close()
print(f"Seeded OK — {iid1[:12]} {iid2[:12]} action={aid[:12]}")
