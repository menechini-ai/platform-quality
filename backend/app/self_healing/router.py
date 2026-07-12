"""Self-Healing router: runbooks and auto-heal actions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.core.db import get_db
from app.core.models.self_healing import AutoHealAction, Runbook
from app.core.schemas.self_healing import AutoHealActionRead, RunbookCreate, RunbookRead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# --- Runbooks ---


@router.get("/runbooks", response_model=list[RunbookRead])
async def list_runbooks(
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all runbooks."""
    stmt = select(Runbook).order_by(Runbook.created_at.desc())
    if is_active is not None:
        stmt = stmt.where(Runbook.is_active == is_active)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/runbooks", response_model=RunbookRead, status_code=201)
async def create_runbook(data: RunbookCreate, db: AsyncSession = Depends(get_db)):
    """Create a new runbook."""
    runbook = Runbook(**data.model_dump())
    db.add(runbook)
    await db.flush()
    await db.refresh(runbook)
    return runbook


@router.get("/runbooks/{runbook_id}", response_model=RunbookRead)
async def get_runbook(runbook_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific runbook."""
    try:
        uid = uuid.UUID(runbook_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid runbook ID") from None

    result = await db.execute(select(Runbook).where(Runbook.id == uid))
    runbook = result.scalar_one_or_none()
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return runbook


# --- Auto-Heal Actions ---


@router.get("/actions", response_model=list[AutoHealActionRead])
async def list_actions(
    status: str | None = Query(
        None, pattern=r"^(pending|approved|rejected|running|success|failed)$"
    ),
    action_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List auto-heal actions."""
    stmt = select(AutoHealAction).order_by(AutoHealAction.requested_at.desc())
    if status:
        stmt = stmt.where(AutoHealAction.status == status)
    if action_type:
        stmt = stmt.where(AutoHealAction.action_type == action_type)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/actions/{action_id}/approve", response_model=AutoHealActionRead)
async def approve_action(action_id: str, db: AsyncSession = Depends(get_db)):
    """Approve a pending auto-heal action."""
    try:
        uid = uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID") from None

    result = await db.execute(select(AutoHealAction).where(AutoHealAction.id == uid))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"Action is not pending (status: {action.status})"
        )

    action.status = "approved"
    action.completed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(action)
    return action


@router.post("/actions/{action_id}/reject", response_model=AutoHealActionRead)
async def reject_action(action_id: str, db: AsyncSession = Depends(get_db)):
    """Reject a pending auto-heal action."""
    try:
        uid = uuid.UUID(action_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action ID") from None

    result = await db.execute(select(AutoHealAction).where(AutoHealAction.id == uid))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"Action is not pending (status: {action.status})"
        )

    action.status = "rejected"
    action.completed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(action)
    return action
