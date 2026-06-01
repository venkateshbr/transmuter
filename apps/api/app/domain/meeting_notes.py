"""Meeting-notes extraction contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MeetingAttendeeContext(BaseModel):
    user_id: str
    display_name: str | None = None


class LinkedInitiativeContext(BaseModel):
    id: str
    name: str
    initiative_code: str | None = None


class TranscriptChunk(BaseModel):
    index: int
    speaker: str | None = None
    text: str
    topic_hint: str | None = None


class TranscriptChunkingRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=50000)


class TranscriptChunkingResult(BaseModel):
    trace_id: str
    trace_url: str | None = None
    agent_status: Literal["generated", "deterministic_fallback"] = "deterministic_fallback"
    chunks: list[TranscriptChunk] = Field(default_factory=list)


class MeetingActionItemSuggestion(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)
    suggested_assignee_id: str | None = None
    suggested_assignee_name: str | None = None
    due_date: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    accepted: bool = True
    rationale: str | None = None


class ActionItemExtractionRequest(BaseModel):
    chunks: list[TranscriptChunk]
    attendees: list[MeetingAttendeeContext] = Field(default_factory=list)


class ActionItemExtractionResult(BaseModel):
    trace_id: str
    trace_url: str | None = None
    agent_status: Literal["generated", "deterministic_fallback"] = "deterministic_fallback"
    action_items: list[MeetingActionItemSuggestion] = Field(default_factory=list)


class MeetingDecision(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    accepted: bool = True
    rationale: str | None = None


class InitiativeStatusSignal(BaseModel):
    initiative_id: str | None = None
    initiative_name: str | None = None
    summary: str = Field(..., min_length=1, max_length=2000)
    rag_status: Literal["red", "amber", "green"] = "green"
    accepted: bool = True


class MeetingDecisionsExtractionRequest(BaseModel):
    chunks: list[TranscriptChunk]
    linked_initiatives: list[LinkedInitiativeContext] = Field(default_factory=list)


class MeetingDecisionsExtractionResult(BaseModel):
    trace_id: str
    trace_url: str | None = None
    agent_status: Literal["generated", "deterministic_fallback"] = "deterministic_fallback"
    decisions: list[MeetingDecision] = Field(default_factory=list)
    initiative_updates: list[InitiativeStatusSignal] = Field(default_factory=list)


class MeetingTranscriptUpload(BaseModel):
    transcript_text: str = Field(..., min_length=1, max_length=50000)


class MeetingNotesWorkflowReview(BaseModel):
    workflow_run_id: str
    workflow_type: Literal["meeting_notes_extraction"] = "meeting_notes_extraction"
    status: str
    expires_at: str
    session_id: str
    meeting_id: str
    action_items: list[MeetingActionItemSuggestion] = Field(default_factory=list)
    decisions: list[MeetingDecision] = Field(default_factory=list)
    initiative_updates: list[InitiativeStatusSignal] = Field(default_factory=list)


class MeetingNotesApproveRequest(BaseModel):
    action_items: list[MeetingActionItemSuggestion] = Field(default_factory=list)
    decisions: list[MeetingDecision] = Field(default_factory=list)
    initiative_updates: list[InitiativeStatusSignal] = Field(default_factory=list)
