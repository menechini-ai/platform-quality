"""Pydantic schemas for Self-Healing."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class RunbookCreate(BaseModel):
    name: str
    description: str | None = None
    triggers: Any | None = None
    steps: list[dict]
    is_active: bool = True


class RunbookRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    triggers: Any | None = None
    steps: list[dict]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AutoHealActionRead(BaseModel):
    id: UUID
    incident_id: UUID | None = None
    monitor_id: str | None = None
    action_type: str
    action_config: Any | None = None
    triggered_by: str
    status: str
    result: Any | None = None
    requested_at: datetime
    executed_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
