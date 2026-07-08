"""Seed demo data for ObservAI local DB."""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from app.core.db import engine, Base
from app.core.models.health import HealthSnapshot, Slo
from app.core.models.incident import Incident
from app.core.models.rca import RcaReport
from app.core.models.self_healing import Runbook, AutoHealAction
from app.core.models.maturity import MaturityAssessment
from app.core.models.report import Report
from app.maturity.service import run_assessment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def seed():
    async with session_factory() as sess:
        # Check if data exists
        r = await sess.execute(select(Slo))
        if len(r.scalars().all()) > 0:
            print("Data already seeded, skipping")
            return

        now = datetime.now(UTC)

        # --- Health Snapshots ---
        services = ["api-gateway", "user-service", "payment-service", "order-service", "notification-service"]
        for svc in services:
            for sli_name, target, current in [
                ("availability", 99.9, 99.95),
                ("latency_p99", 500, 320),
                ("error_rate", 1.0, 0.3),
            ]:
                bps = [HealthSnapshot(
                    id=uuid.uuid4(), service=svc, sli_name=sli_name,
                    slo_target=target, current_value=current if current > target else current,
                    burn_rate=0.0, error_budget_remaining=80.0,
                    status="healthy", snapshot_at=now - timedelta(hours=h),
                ) for h in range(24, 0, -1)]  # 24h history
                for bp in bps:
                    sess.add(bp)

        # --- SLOs (local) ---
        for svc in services:
            sess.add(Slo(id=uuid.uuid4(), name=f"{svc} — Availability", target=99.9, time_window="30d", service=svc))

        # --- Incidents ---
        inc1 = Incident(
            id=uuid.uuid4(), title="API Gateway — P50 Latency Breach",
            severity="SEV-3", status="resolved", service="api-gateway",
            started_at=now - timedelta(hours=6), resolved_at=now - timedelta(hours=5),
            description="Latency spiked to 1.2s after code deployment",
        )
        inc2 = Incident(
            id=uuid.uuid4(), title="Payment Service — 5xx Error Spike",
            severity="SEV-2", status="investigating", service="payment-service",
            started_at=now - timedelta(hours=2),
            description="Payment processing errors increased 300%",
        )
        sess.add_all([inc1, inc2])
        await sess.flush()

        # --- RCA Reports ---
        sess.add(RcaReport(
            id=uuid.uuid4(), incident_id=inc1.id,
            summary="Latency spike caused by N+1 query introduced in v2.1.5",
            root_cause="Missing index on `transactions.user_id`",
            timeline=[{"time": str(now - timedelta(hours=6)), "event": "deploy v2.1.5"},
                      {"time": str(now - timedelta(hours=6, minutes=10)), "event": "p50 latency breach alert"}],
            metrics_snapshot={"p50_latency_ms": 1200, "p99_latency_ms": 3500},
            changes=[{"type": "deploy", "service": "api-gateway", "version": "v2.1.5"}],
            recommendations=["Add index on transactions.user_id", "Rollback to v2.1.4"],
        ))

        # --- Runbooks ---
        sess.add(Runbook(
            id=uuid.uuid4(), name="Latency Spike Response",
            description="Steps to diagnose and mitigate latency spikes",
            triggers=[{"metric": "p50_latency", "threshold": 800}],
            steps=[{"order": 1, "action": "Check recent deploys", "command": "kubectl rollout history"},
                   {"order": 2, "action": "Rollback if recent deploy", "command": "kubectl rollout undo"}],
            is_active=True,
        ))

        # --- Maturity Assessment ---
        assessment = await run_assessment(sess)
        print(f"Assessment: level={assessment.overall_level} score={assessment.overall_score:.1f}")

        # --- Maturity/Reports: Postmortem style ---
        sess.add(Report(
            id=uuid.uuid4(), report_type="postmortem",
            title=f"Postmortem: API Gateway Latency Breach ({inc1.title})",
            content="## Summary\nLatency spike caused by N+1 query after deploy v2.1.5...",
            tags=["incident", "postmortem", "api-gateway"],
            metadata={"incident_id": str(inc1.id), "severity": "SEV-3"},
        ))

        await sess.commit()

    print("✅ Seed complete")


asyncio.run(seed())
