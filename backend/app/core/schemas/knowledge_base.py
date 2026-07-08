"""Pydantic schemas for knowledge base."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    title: str = Field(max_length=500)
    symptom_pattern: str | None = None
    root_cause: str | None = None
    resolution_steps: list[str] | None = None
    tags: list[str] | None = None


class KnowledgeBaseRead(BaseModel):
    id: UUID
    title: str
    symptom_pattern: str | None = None
    root_cause: str | None = None
    resolution_steps: list[str] | None = None
    tags: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
