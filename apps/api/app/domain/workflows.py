"""Workflow contracts for HITL agent orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.initiative_intake import (
    InitiativeDraft,
    InitiativeIntakeSuggestions,
    KPISuggestion,
    RiskPattern,
)
from app.domain.initiatives import InitiativeCreate, InitiativeDetail
from app.domain.meeting_notes import (
    InitiativeStatusSignal,
    MeetingActionItemSuggestion,
    MeetingDecision,
)

WorkflowStatusValue = Literal[
    "extracting",
    "suggesting",
    "chunking",
    "awaiting_review",
    "approved",
    "rejected",
    "expired",
    "failed",
]


class InitiativeIntakeWorkflowStart(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=12000)


class WorkflowRunCreated(BaseModel):
    workflow_run_id: UUID
    status: WorkflowStatusValue
    expires_at: datetime


class WorkflowStatus(BaseModel):
    workflow_run_id: UUID
    status: WorkflowStatusValue
    expires_at: datetime
    created_initiative_id: UUID | None = None
    error: str | None = None


class WorkflowReview(BaseModel):
    workflow_run_id: UUID
    status: WorkflowStatusValue
    expires_at: datetime
    extracted_draft: InitiativeDraft
    field_confidence: dict[str, Literal["high", "medium", "low"]] = Field(default_factory=dict)
    kpi_suggestions: list[KPISuggestion] = Field(default_factory=list)
    risk_suggestions: list[RiskPattern] = Field(default_factory=list)


class WorkflowApproveRequest(BaseModel):
    initiative: InitiativeCreate | None = None
    suggestions: InitiativeIntakeSuggestions | None = None
    action_items: list[MeetingActionItemSuggestion] = Field(default_factory=list)
    decisions: list[MeetingDecision] = Field(default_factory=list)
    initiative_updates: list[InitiativeStatusSignal] = Field(default_factory=list)


class WorkflowApproveResponse(BaseModel):
    workflow_run_id: UUID
    status: Literal["approved"]
    initiative: InitiativeDetail


class WorkflowRejectRequest(BaseModel):
    reason: str | None = Field(None, max_length=1000)


class WorkflowRejectResponse(BaseModel):
    workflow_run_id: UUID
    status: Literal["rejected"]
