"""Governance & Stage Gate domain models — Pydantic v2."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GateCriteriaItem(BaseModel):
    id: str
    gate_number: int
    criterion_id: str
    label: str
    guidance: str | None = None
    sort_order: int = 0
    is_active: bool = True


class GateCriteriaState(BaseModel):
    id: str
    criterion_id: str
    label: str
    guidance: str | None = None
    sort_order: int = 0
    ticked: bool = False
    ticked_by: str | None = None
    ticked_at: str | None = None


class GateItem(BaseModel):
    id: str | None = None
    initiative_id: str
    gate_number: int
    label: str
    from_stage: str
    to_stage: str


class GateSubmissionCreate(BaseModel):
    criteria_snapshot: list[dict[str, Any]] = Field(..., description="Snapshot of ticked criteria")
    commentary: str | None = None


class GateDecisionPatch(BaseModel):
    decision: Literal["approved", "rejected", "conditional"]
    commentary: str | None = None


class GateSubmissionItem(BaseModel):
    id: str
    initiative_id: str
    gate_number: int
    submitted_by_id: str
    submitted_by_name: str | None = None
    submitted_at: str
    decision: str
    decided_by_id: str | None = None
    decided_by_name: str | None = None
    decided_at: str | None = None
    commentary: str | None = None
    criteria_snapshot: list[dict[str, Any]] | None = None


class GovernanceStatusResponse(BaseModel):
    gates: list[GateItem]
    active_submission: GateSubmissionItem | None = None
    history: list[GateSubmissionItem]


class PortfolioGovernanceResponse(BaseModel):
    health_score: str
    approved: int
    pending: int
    rejected: int
    conditional: int
    total_submissions: int
    submissions: list[GateSubmissionItem]
