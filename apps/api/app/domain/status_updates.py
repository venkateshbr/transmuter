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


class StatusUpdateDraftSuggestion(BaseModel):
    trace_id: str | None = None
    trace_url: str | None = None
    rag_status: Literal["red", "amber", "green"]
    summary: str
    achievements: str | None = None
    issues: str | None = None
    next_steps: str | None = None
    confidence: float = Field(0.75, ge=0, le=1)
    agent_status: Literal["generated", "deterministic_fallback"] = "deterministic_fallback"
    sources: list[str] = Field(default_factory=list)


class StatusUpdateItem(BaseModel):
    id: str
    initiative_id: str
    initiative_name: str | None = None
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


class StatusComplianceItem(BaseModel):
    initiative_id: str
    initiative_name: str
    owner_name: str | None = None
    last_update_at: str | None = None
    days_since: int
    status: Literal["on_time", "overdue", "nuclear"]
    rag_status: Literal["red", "amber", "green"]
    nudge_count: int = 0


class StatusComplianceSummary(BaseModel):
    total: int
    on_time: int
    overdue: int
    nuclear: int


class StatusComplianceResponse(BaseModel):
    summary: StatusComplianceSummary
    initiatives: list[StatusComplianceItem]


class NudgeCreate(BaseModel):
    channel: Literal["email", "in_app", "both"] = "both"


class NudgeItem(BaseModel):
    id: str
    initiative_id: str
    sent_by_id: str | None = None
    channel: str
    sent_at: str
    initiatives: dict | None = None
    users: dict | None = None


class NudgeResponse(BaseModel):
    success: bool
    nudge_id: str | None = None
    initiative_id: str
    sent_at: str | None = None
    channel: str
    delivery_status: Literal["queued", "sent", "failed"] = "queued"
