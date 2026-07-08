"""Pydantic schemas for Health / SLO."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SloCreate(BaseModel):
    dd_id: str | None = None
    name: str = Field(..., max_length=500)
    description: str | None = None
    target: float = Field(..., ge=0, le=1)
    time_window: str = Field(default="30d", pattern=r"^(7|30|90)d$")
    service: str | None = Field(default=None, max_length=200)


class SloRead(BaseModel):
    id: UUID
    dd_id: str | None = None
    name: str
    description: str | None = None
    target: float
    time_window: str
    service: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthSnapshotRead(BaseModel):
    id: UUID
    service: str
    sli_name: str
    slo_target: float | None = None
    current_value: float | None = None
    burn_rate: float | None = None
    error_budget_remaining: float | None = None
    status: str | None = None
    snapshot_at: datetime

    model_config = {"from_attributes": True}
