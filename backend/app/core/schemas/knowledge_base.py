"""Pydantic schemas for knowledge base."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class KnowledgeBaseCreate(BaseModel):
    title: str = Field(max_length=500)
    symptom_pattern: str | None = None
    root_cause: str | None = None
    resolution_steps: list[str] | None = None
    tags: list[str] | None = None


class KnowledgeBaseRead(BaseModel):
    id: uuid.UUID
    title: str
    symptom_pattern: str | None = None
    root_cause: str | None = None
    resolution_steps: list[str] | None = None
    tags: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
