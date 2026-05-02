"""Status Update domain models — Pydantic v2 contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StatusUpdateCreate(BaseModel):
    rag_status: Literal["red", "amber", "green"]
    summary: str = Field(..., min_length=1, max_length=2000)
    achievements: str | None = None
    issues: str | None = None
    next_steps: str | None = None
    is_draft: bool = True


class StatusUpdatePatch(BaseModel):
    rag_status: Literal["red", "amber", "green"] | None = None
    summary: str | None = Field(None, min_length=1, max_length=2000)
    achievements: str | None = None
    issues: str | None = None
    next_steps: str | None = None
    is_draft: bool | None = None


class StatusUpdateItem(BaseModel):
    id: str
    initiative_id: str
    author_id: str
    author_name: str | None = None
    rag_status: str
    summary: str
    achievements: str | None = None
    issues: str | None = None
    next_steps: str | None = None
    is_draft: bool
    submitted_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class StatusUpdateListResponse(BaseModel):
    items: list[StatusUpdateItem]
    total: int
