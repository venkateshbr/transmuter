"""Meeting domain models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

MeetingScope = Literal["workstream", "all"]
MeetingRecurrence = Literal["weekly", "biweekly", "monthly", "ad_hoc"]
SessionStatus = Literal["scheduled", "in_progress", "completed"]
ActionPriority = Literal["high", "medium", "low"]
ActionStatus = Literal["open", "in_progress", "completed", "cancelled"]
MeetingArtifactType = Literal["action", "decision", "risk", "assumption", "issue"]
MeetingArtifactStatus = Literal[
    "open",
    "in_progress",
    "completed",
    "cancelled",
    "accepted",
    "rejected",
    "noted",
]
MinutesStatus = Literal["not_generated", "draft", "sent"]


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
    transcript_source: str | None = None
    has_transcript: bool | None = None
    ai_optimised: bool | None = None
    status: SessionStatus | None = None
    minutes_markdown: str | None = None
    minutes_status: MinutesStatus | None = None


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


class MeetingArtifactCreate(BaseModel):
    artifact_type: MeetingArtifactType
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    agenda_item_id: str | None = None
    initiative_id: str | None = None
    status: MeetingArtifactStatus = "open"
    priority: ActionPriority = "medium"
    owner_id: str | None = None
    assignee_id: str | None = None
    due_date: str | None = None


class MeetingArtifactUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    agenda_item_id: str | None = None
    initiative_id: str | None = None
    status: MeetingArtifactStatus | None = None
    priority: ActionPriority | None = None
    owner_id: str | None = None
    assignee_id: str | None = None
    due_date: str | None = None


class MeetingTranscriptImport(BaseModel):
    transcript_text: str | None = None
    transcript_source: str = "manual"


class MeetingMinutesGenerateRequest(BaseModel):
    force: bool = False


class MeetingExternalEventCreate(BaseModel):
    organizer_email: str | None = None
    start_date_time: str | None = None
    end_date_time: str | None = None
    time_zone: str = "UTC"


class MeetingExternalEventResponse(BaseModel):
    id: str
    provider: str
    meeting_id: str
    external_event_id: str | None = None
    online_meeting_id: str | None = None
    join_url: str | None = None
    organizer_email: str | None = None
    sync_status: str
    sync_error: str | None = None
    last_synced_at: str | None = None


class MeetingListResponse(BaseModel):
    items: list[dict[str, Any]]


class ActionItemStats(BaseModel):
    total: int = 0
    open: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0
    overdue: int = 0


class ActionItemListResponse(BaseModel):
    items: list[dict[str, Any]]
    stats: ActionItemStats = Field(default_factory=ActionItemStats)
