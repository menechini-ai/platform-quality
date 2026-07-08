"""Knowledge base router — stores RCA patterns, tagging strategy, postmortem templates."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.db import get_db
from app.core.models.knowledge_base import KnowledgeBase
from app.core.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/kb", response_model=list[KnowledgeBaseRead])
async def list_kb(
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List knowledge base entries, optionally filtered by tag."""
    query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
    if tag:
        query = query.where(KnowledgeBase.tags.contains([tag]))
    result = await db.execute(query.offset(offset).limit(limit))
    return result.scalars().all()


@router.get("/kb/{kb_id}", response_model=KnowledgeBaseRead)
async def get_kb(kb_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single KB entry."""
    try:
        uid = uuid.UUID(kb_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid KB ID") from err

    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == uid))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="KB entry not found")
    return entry


@router.post("/kb", response_model=KnowledgeBaseRead, status_code=201)
async def create_kb(data: KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)):
    """Create a KB entry."""
    entry = KnowledgeBase(
        title=data.title,
        symptom_pattern=data.symptom_pattern,
        root_cause=data.root_cause,
        resolution_steps=data.resolution_steps,
        tags=data.tags,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.post("/kb/seed", status_code=201)
async def seed_knowledge_base(db: AsyncSession = Depends(get_db)):
    """Seed KB with tagging strategy, postmortem templates, and common RCA patterns."""

    entries = [
        KnowledgeBase(
            title="Unified Service Tagging (UST) Standard",
            symptom_pattern=None,
            root_cause="Standard tagging taxonomy for Datadog: env, service, team, version, host",
            resolution_steps=[
                "Apply tags: env:prod/staging/dev, service:<name>, team:<team>, version:<semver>",
                "Use Datadog's unified_service_tagging() helper in agent config",
                "Add `env` and `service` tags to all monitors, dashboards, and logs",
                "Standard: env identifies deployment stage, service identifies code component",
                "Second-class tags: host, container_id, cluster_name, availability_zone",
            ],
            tags=["tagging", "standard", "ust", "datadog"],
        ),
        KnowledgeBase(
            title="Postmortem Template — Standard SRE",
            symptom_pattern=None,
            root_cause="Structured postmortem following SRE best practices",
            resolution_steps=[
                "# Postmortem: {incident_title}",
                "**Date:** {date}  **Severity:** {severity}  **Duration:** {duration}",
                "## Summary",
                "- What happened: Jira ticket, services affected, user impact",
                "- Detection: how was it found (monitor, alert, customer report?)",
                "- Response: who responded, timeline of actions taken",
                "## Root Cause",
                "- Direct cause, contributing factors, why it wasn't caught earlier",
                "## Timeline",
                "- {time}: {event} — structured chronological log",
                "## Action Items",
                "- [ ] {owner}: {action} — due {date}",
                "## Lessons Learned",
                "- What went well, what went wrong, what to improve",
                "## Blameless Postmortem Declaration",
                "- This postmortem is blameless. Systems fail; people learn.",
            ],
            tags=["postmortem", "template", "sre", "incident-management"],
        ),
        KnowledgeBase(
            title="Investigation Template — Error Spike",
            symptom_pattern="error OR exception OR timeout OR 5xx",
            root_cause="Standard investigation template for error spikes",
            resolution_steps=[
                "## Investigation: Error Spike",
                "**Opened:** {date}  **Triggered by:** {monitor_name}",
                "### Step 1: Scope",
                "- Which services/endpoints affected?",
                "- When did the spike start? (compare to deploy times)",
                "- Any code/config deploys in the window?",
            ],
            tags=["investigation", "template", "error-spike"],
        ),
        KnowledgeBase(
            title="Investigation Template — Performance Degradation",
            symptom_pattern="latency OR slow OR high OR p99 OR p95",
            root_cause="Standard investigation for latency/performance issues",
            resolution_steps=[
                "## Investigation: Performance Degradation",
                "**Opened:** {date}  **Service:** {service}",
                "### Step 1: Baseline comparison",
                "- Compare p50/p95/p99 to same time last week",
                "- Check for correlated deploys, config changes, auto-scaling events",
                "- Verify database query performance (slow query log, connection pool)",
            ],
            tags=["investigation", "template", "performance"],
        ),
        KnowledgeBase(
            title="Investigation Template — Cost Anomaly",
            symptom_pattern="cost OR spend OR budget OR billing",
            root_cause="Standard investigation for unexpected cost increases",
            resolution_steps=[
                "## Investigation: Cost Anomaly",
                "**Opened:** {date}  **Period:** {period}",
                "### Step 1: Identify change vectors",
                "- Host count spike? Auto-scaling triggered by load test?",
                "- New feature deployed causing higher resource usage?",
                "- Log volume increase? New index/retention policy?",
                "- Transfer cost increase (multi-region data flow)?",
            ],
            tags=["investigation", "template", "cost"],
        ),
        KnowledgeBase(
            title="RCA Pattern — Memory Exhaustion",
            symptom_pattern="memory OR OOM OR out of memory OR heap OR gc",
            root_cause="Memory leak: unreleased references accumulating over time",
            resolution_steps=[
                "1. Capture heap dump / memory profile during peak",
                "2. Identify largest retained objects and their GC roots",
                "3. Check connection pools (DB, HTTP, gRPC) for leak",
                "4. Review code for unbounded caches, missed cleanup, circular references",
                "5. Set memory limit on container/enforce heap size",
                "6. Add memory utilization monitor with warning at 80%",
            ],
            tags=["rca", "pattern", "memory", "performance"],
        ),
        KnowledgeBase(
            title="RCA Pattern — Database Connection Exhaustion",
            symptom_pattern="connection timeout OR too many connections OR pool exhausted OR 533",
            root_cause="Connection pool depleted: connections not returned or pool too small",
            resolution_steps=[
                "1. Check connection pool settings (max_connections, pool_timeout, pool_recycle)",
                "2. Verify application properly closes connections (db.close(), with statement)",
                "3. Audit long-running queries holding connections open",
                "4. Increase pool size and enable connection pooling metrics",
                "5. Add PGBouncer / proxy for connection pooling on PostgreSQL",
            ],
            tags=["rca", "pattern", "database", "connection"],
        ),
        KnowledgeBase(
            title="RCA Pattern — Health Check Cascade Failure",
            symptom_pattern="health check OR unhealthy OR 503 OR lb OR load balancer OR OOM killed",
            root_cause=(
                "Cascade failure: LB health check timeout → service drain "
                "→ traffic surge to remaining instances"
            ),
            resolution_steps=[
                "1. Widen health check interval from 5s to 15s, increase failure threshold to 3",
                "2. Add startup probe (180s grace) so slow-boot services aren't killed immediately",
                "3. Set proper drain timeout (60s+) to let in-flight requests finish",
                "4. Implement circuit breaker pattern upstream of failing service",
                "5. Ensure at least N+1 capacity so draining one doesn't overload rest",
            ],
            tags=["rca", "pattern", "infrastructure", "resilience"],
        ),
    ]

    for entry in entries:
        db.add(entry)
    await db.flush()

    return {"seeded": len(entries), "message": f"{len(entries)} KB entries created"}
