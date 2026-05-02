"""Meeting domain models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


MeetingScope = Literal["workstream", "all"]
MeetingRecurrence = Literal["weekly", "biweekly", "monthly", "ad_hoc"]
SessionStatus = Literal["scheduled", "in_progress", "completed"]
ActionPriority = Literal["high", "medium", "low"]
ActionStatus = Literal["open", "in_progress", "completed", "cancelled"]


class MeetingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    workstream_id: str | None = None
    scope: MeetingScope = "all"
    recurrence: MeetingRecurrence = "weekly"
    description: str | None = None
    owner_id: str | None = None


class MeetingUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    workstream_id: str | None = None
    scope: MeetingScope | None = None
    recurrence: MeetingRecurrence | None = None
    description: str | None = None
    owner_id: str | None = None


class AgendaItemCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    initiative_id: str | None = None
    sort_order: int | None = None


class AgendaItemUpdate(BaseModel):
    text: str | None = Field(None, min_length=1, max_length=1000)
    initiative_id: str | None = None
    sort_order: int | None = None


class AttendeeCreate(BaseModel):
    user_id: str


class MeetingInitiativeCreate(BaseModel):
    initiative_id: str


class SessionUpdate(BaseModel):
    notes: str | None = None
    transcript_text: str | None = None
    has_transcript: bool | None = None
    ai_optimised: bool | None = None
    status: SessionStatus | None = None


class ActionItemCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)
    initiative_id: str | None = None
    assignee_id: str | None = None
    priority: ActionPriority = "medium"
    status: ActionStatus = "open"
    due_date: str | None = None


class ActionItemUpdate(BaseModel):
    description: str | None = Field(None, min_length=1, max_length=1000)
    initiative_id: str | None = None
    assignee_id: str | None = None
    priority: ActionPriority | None = None
    status: ActionStatus | None = None
    due_date: str | None = None


class MeetingListResponse(BaseModel):
    items: list[dict[str, Any]]


class ActionItemListResponse(BaseModel):
    items: list[dict[str, Any]]
