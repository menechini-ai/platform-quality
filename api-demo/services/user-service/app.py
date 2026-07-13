"""User Service API Demo — FastAPI with SQLite storage.
Generates Datadog telemetry (logs, metrics, events) on each request.
"""

from __future__ import annotations

import asyncio
import os
import random
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# ── OpenTelemetry tracing → otel-collector → Datadog (bypasses the Datadog Agent) ──
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _init_tracing() -> None:
    """Export spans over OTLP to the collector, which forwards them directly to Datadog."""
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": SERVICE,
                "deployment.environment": ENV,
                "team": "observai",
                "purpose": "demo",
            }
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces"))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


# ── Datadog config (from env or defaults) ─────────────────────
DD_API_KEY = os.environ.get("DATADOG_API_KEY", "")
DD_SITE = os.environ.get("DATADOG_SITE", "datadoghq.com")
SERVICE = os.environ.get("SERVICE", "user-service")
ENV = os.environ.get("ENV", "demo")
DD_API_BASE = f"https://api.{DD_SITE}"
DD_LOGS_INTAKE = f"https://http-intake.logs.{DD_SITE}"

# Global state for simulated downtime
_down_until: float = 0.0

# ── SQLite setup ──────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "/data/users.db")


def _init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


_init_db()


# ── Helpers ───────────────────────────────────────────────────


def _dd_headers() -> dict[str, str]:
    return {
        "DD-API-KEY": DD_API_KEY,
        "Content-Type": "application/json",
    }


def _tags() -> str:
    return f"service:{SERVICE},env:{ENV},team:observai,purpose:demo"


def _tag_list() -> list[str]:
    return [f"service:{SERVICE}", f"env:{ENV}", "team:observai", "purpose:demo"]


async def _send_log(message: str, status: str = "info") -> None:
    """Send a log entry to Datadog (best-effort, no raise)."""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(
                f"{DD_LOGS_INTAKE}/api/v2/logs",
                headers=_dd_headers(),
                json=[
                    {
                        "ddsource": "python",
                        "ddtags": _tags(),
                        "hostname": SERVICE,
                        "service": SERVICE,
                        "message": message,
                        "status": status,
                        "timestamp": int(time.time() * 1000),
                    }
                ],
            )
    except Exception:
        pass  # best-effort


async def _send_metric(name: str, value: float, mtype: str = "gauge") -> None:
    """Send a metric to Datadog (async, best-effort)."""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(
                f"{DD_API_BASE}/api/v2/series",
                headers=_dd_headers(),
                json={
                    "series": [
                        {
                            "metric": f"{SERVICE}.{name}",
                            "type": 1 if mtype == "count" else 0,
                            "points": [{"timestamp": int(time.time()), "value": value}],
                            "tags": _tag_list(),
                        }
                    ],
                },
            )
    except Exception:
        pass


async def _send_event(title: str, text: str, alert_type: str = "info") -> None:
    """Send an event to Datadog (async, best-effort)."""
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(
                f"{DD_API_BASE}/api/v1/events",
                headers=_dd_headers(),
                json={
                    "title": title,
                    "text": text,
                    "alert_type": alert_type,
                    "tags": _tags(),
                    "host": SERVICE,
                    "date_happened": int(time.time()),
                },
            )
    except Exception:
        pass


async def _generate_traffic() -> None:
    while True:
        await asyncio.sleep(random.randint(30, 120))
        is_down = time.time() < _down_until
        if is_down:
            await _send_metric("health", 0.0, "count")
            await _send_metric("latency_ms", round(random.gauss(3000, 1000), 1))
            await _send_metric("error_rate", round(random.uniform(0.5, 1.0), 4))
            await _send_metric("cpu_usage", 100.0)
            await _send_log(f"[{SERVICE}] SERVICE DOWN — all requests failing", "error")
            await _send_event(
                f"[DOWN] {SERVICE} outage ({ENV})",
                "Service is down and returning 503 errors",
                "error",
            )
            continue
        await _send_metric("health", 1.0, "count")
        # Send some random latency
        await _send_metric("latency_ms", round(random.gauss(85, 30), 1))
        # Send error rate
        await _send_metric("error_rate", round(random.uniform(0, 0.03), 4))
        # Send request count
        await _send_metric("request_count", random.randint(5, 50), "count")
        await _send_metric("cpu_usage", round(random.uniform(15, 70), 1))
        # Send a periodic event
        await _send_event(
            f"[{SERVICE}] Background health check OK",
            f"Service {SERVICE} is running in {ENV}. Latency p50={round(random.gauss(85, 50), 0)}ms",
            "info",
        )
        # Send a log every cycle
        await _send_log(
            f"[{SERVICE}] Health check passed — {random.randint(10, 200)} active users",
            "info",
        )
        # Occasionally inject an error
        if random.random() < 0.15:
            await _send_log(
                f"[{SERVICE}] Connection pool nearly exhausted ({random.randint(80, 95)}% capacity)",
                "warn",
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_generate_traffic())
    yield


app = FastAPI(title=f"{SERVICE}", lifespan=lifespan)

_init_tracing()


# ── Routes ────────────────────────────────────────────────────


@app.get("/health")
async def health():
    if time.time() < _down_until:
        return JSONResponse(
            {
                "service": SERVICE,
                "status": "down",
                "env": ENV,
                "down_for": round(_down_until - time.time(), 1),
            },
            status_code=503,
        )
    return {"service": SERVICE, "status": "ok", "env": ENV}


@app.post("/down")
async def set_down(body: dict[str, Any] = {}):
    global _down_until
    duration = float(body.get("duration", 10))
    _down_until = time.time() + duration
    return {
        "service": SERVICE,
        "env": ENV,
        "status": "degraded",
        "down_for_seconds": duration,
        "expected_recovery": duration,
    }


@app.get("/health/check")
async def health_check():
    """Deep health check — tests DB connectivity."""
    try:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return {"service": SERVICE, "status": "ok", "users_count": count, "db": "connected"}
    except Exception as e:
        return {"service": SERVICE, "status": "unhealthy", "error": str(e)}


@app.get("/api/users")
async def list_users():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    users = [
        {
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "role": r[3],
            "created_at": r[4],
            "updated_at": r[5],
        }
        for r in rows
    ]
    await _send_log(f"GET /api/users — returned {len(users)} users", "info")
    await _send_metric("request_count", 1, "count")
    await _send_metric("latency_ms", round(random.gauss(25, 10), 1))
    return users


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        await _send_log(f"GET /api/users/{user_id} — user not found", "warn")
        await _send_metric("error_rate", 1.0)
        raise HTTPException(status_code=404, detail="User not found")
    user = {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "role": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }
    await _send_log(f"GET /api/users/{user_id} — user found", "info")
    await _send_metric("request_count", 1, "count")
    return user


@app.post("/api/users")
async def create_user(body: dict[str, Any]):
    user_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC).isoformat()
    name = body.get("name", f"user-{user_id}")
    email = body.get("email", f"{name.lower()}@example.com")
    role = body.get("role", "viewer")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO users (id, name, email, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, email, role, now, now),
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already exists")

    await _send_log(f"POST /api/users — created user {user_id} ({email})", "info")
    await _send_metric("request_count", 1, "count")
    await _send_event(
        f"[{SERVICE}] New user created",
        f"User {name} ({email}) created with role={role}",
        "info",
    )
    return {"id": user_id, "name": name, "email": email, "role": role, "created_at": now}


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    await _send_log(f"DELETE /api/users/{user_id} — deleted", "info")
    await _send_metric("request_count", 1, "count")
    return {"deleted": True}


@app.get("/api/health/check")
async def health_check():
    """Heavier health check that tests DB + sends telemetry."""
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    await _send_metric("db_connection_ok", 1.0)
    return {"service": SERVICE, "status": "ok", "users_count": count}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
