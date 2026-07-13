"""API Gateway Demo — FastAPI proxy that routes to user-service.
Generates Datadog telemetry with additional trace-like correlation IDs.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
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


# ── Config ────────────────────────────────────────────────────
DD_API_KEY = os.environ.get("DATADOG_API_KEY", "")
DD_SITE = os.environ.get("DATADOG_SITE", "datadoghq.com")
SERVICE = os.environ.get("SERVICE", "api-gateway")
ENV = os.environ.get("ENV", "demo")
USER_SVC_URL = os.environ.get("USER_SVC_URL", "http://user-service:8001")

DD_API_BASE = f"https://api.{DD_SITE}"
DD_LOGS_INTAKE = f"https://http-intake.logs.{DD_SITE}"

# Global state for simulated downtime
_down_until: float = 0.0

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


async def _send_log(message: str, status: str = "info", correlation_id: str = "") -> None:
    try:
        tags = _tags()
        if correlation_id:
            tags += f",correlation_id:{correlation_id}"
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(
                f"{DD_LOGS_INTAKE}/api/v2/logs",
                headers=_dd_headers(),
                json=[
                    {
                        "ddsource": "python",
                        "ddtags": tags,
                        "hostname": SERVICE,
                        "service": SERVICE,
                        "message": message,
                        "status": status,
                        "timestamp": int(time.time() * 1000),
                    }
                ],
            )
    except Exception:
        pass


async def _send_metric(name: str, value: float, mtype: str = "gauge") -> None:
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


async def _generate_traffic() -> None:
    while True:
        await asyncio.sleep(random.randint(20, 60))
        is_down = time.time() < _down_until
        cid = uuid.uuid4().hex[:12]
        if is_down:
            await _send_metric("health", 0.0, "count")
            await _send_metric("error_rate", 1.0)
            await _send_metric("latency_ms", round(random.gauss(2000, 500), 1))
            await _send_log(
                f"[{SERVICE}] SERVICE DOWN — requests failing (503)",
                "error",
                correlation_id=cid,
            )
            continue
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                resp = await c.get(f"{USER_SVC_URL}/health")
                status = resp.status_code
                await _send_log(
                    f"[{SERVICE}] Health check via user-service: {status}",
                    "info" if status == 200 else "error",
                    correlation_id=cid,
                )
        except Exception as e:
            await _send_log(
                f"[{SERVICE}] Health check failed: {e}",
                "error",
                correlation_id=cid,
            )
        await _send_metric("health", 1.0, "count")
        await _send_metric("latency_ms", round(random.gauss(45, 20), 1))
        await _send_metric("request_count", random.randint(3, 30), "count")
        if random.random() < 0.1:
            await _send_log(
                f"[{SERVICE}] Rate limit approaching — {random.randint(70, 95)}% capacity",
                "warn",
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_generate_traffic())
    yield


app = FastAPI(title=SERVICE, lifespan=lifespan)

_init_tracing()

UPSTREAMS: dict[str, str] = {
    "users": USER_SVC_URL,
}


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
    """Deep health check — tests upstream user-service connectivity."""
    import time

    try:
        async with httpx.AsyncClient(timeout=5) as c:
            start = time.monotonic()
            resp = await c.get(f"{USER_SVC_URL}/health")
            elapsed = (time.monotonic() - start) * 1000
            return {
                "service": SERVICE,
                "status": "ok" if resp.status_code == 200 else "degraded",
                "upstream": {
                    "service": "user-service",
                    "status": resp.status_code,
                    "latency_ms": round(elapsed, 1),
                },
            }
    except Exception as e:
        return {
            "service": SERVICE,
            "status": "unhealthy",
            "upstream": {"service": "user-service", "error": str(e)},
        }


@app.get("/api/v1/gateway/{upstream}")
async def gateway_list(upstream: str):
    base = UPSTREAMS.get(upstream)
    if not base:
        raise HTTPException(status_code=404, detail=f"Unknown upstream: {upstream}")
    cid = uuid.uuid4().hex[:12]
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(f"{base}/api/{upstream}")
            elapsed = (time.monotonic() - start) * 1000
            data = resp.json() if resp.status_code < 400 else {"error": resp.text}
            await _send_log(
                f"GET /api/v1/gateway/{upstream} → {resp.status_code} ({elapsed:.0f}ms)",
                "info" if resp.status_code < 400 else "error",
                correlation_id=cid,
            )
            await _send_metric("request_count", 1, "count")
            await _send_metric("latency_ms", round(elapsed, 1))
            if resp.status_code >= 400:
                await _send_metric("error_rate", 1.0)
            return {
                "upstream": upstream,
                "correlation_id": cid,
                "status": resp.status_code,
                "data": data,
            }
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        await _send_log(
            f"GET /api/v1/gateway/{upstream} → FAILED: {e}",
            "error",
            correlation_id=cid,
        )
        await _send_metric("error_rate", 1.0)
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/gateway/{upstream}/{entity_id}")
async def gateway_get(upstream: str, entity_id: str):
    base = UPSTREAMS.get(upstream)
    if not base:
        raise HTTPException(status_code=404, detail=f"Unknown upstream: {upstream}")
    cid = uuid.uuid4().hex[:12]
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            resp = await c.get(f"{base}/api/{upstream}/{entity_id}")
        await _send_log(
            f"GET /api/v1/gateway/{upstream}/{entity_id} → {resp.status_code}",
            "info" if resp.status_code < 400 else "error",
            correlation_id=cid,
        )
        await _send_metric("request_count", 1, "count")
        return {"upstream": upstream, "correlation_id": cid, "data": resp.json()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/v1/gateway/{upstream}")
async def gateway_create(upstream: str, body: dict[str, Any]):
    base = UPSTREAMS.get(upstream)
    if not base:
        raise HTTPException(status_code=404, detail=f"Unknown upstream: {upstream}")
    cid = uuid.uuid4().hex[:12]
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            resp = await c.post(f"{base}/api/{upstream}", json=body)
        await _send_log(
            f"POST /api/v1/gateway/{upstream} → {resp.status_code}",
            "info" if resp.status_code < 400 else "error",
            correlation_id=cid,
        )
        await _send_metric("request_count", 1, "count")
        return {"upstream": upstream, "correlation_id": cid, "data": resp.json()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
