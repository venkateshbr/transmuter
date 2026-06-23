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


class GateCriteriaCreate(BaseModel):
    gate_number: int = Field(..., ge=1, le=10)
    criterion_id: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=300)
    guidance: str | None = None
    sort_order: int = 0
    is_active: bool = True


class GateCriteriaUpdate(BaseModel):
    gate_number: int | None = Field(None, ge=1, le=10)
    criterion_id: str | None = Field(None, min_length=1, max_length=120)
    label: str | None = Field(None, min_length=1, max_length=300)
    guidance: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class StageGateDefinitionBase(BaseModel):
    gate_number: int = Field(..., ge=1, le=10)
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    from_stage: str = Field(..., min_length=1, max_length=120)
    to_stage: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    approval_required: bool = True
    approver_roles: list[str] = Field(default_factory=lambda: ["transformation_office"])
    require_all_criteria: bool = True
    sort_order: int = 0
    is_system: bool = False
    is_active: bool = True


class StageGateDefinitionCreate(StageGateDefinitionBase):
    pass


class StageGateDefinitionUpdate(BaseModel):
    gate_number: int | None = Field(None, ge=1, le=10)
    key: str | None = Field(None, min_length=1, max_length=120)
    label: str | None = Field(None, min_length=1, max_length=200)
    from_stage: str | None = Field(None, min_length=1, max_length=120)
    to_stage: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None
    approval_required: bool | None = None
    approver_roles: list[str] | None = None
    require_all_criteria: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class StageGateDefinition(StageGateDefinitionBase):
    id: str


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
    approval_required: bool = True
    approver_roles: list[str] = Field(default_factory=lambda: ["transformation_office"])
    require_all_criteria: bool = True


class GateSubmissionCreate(BaseModel):
    criteria_snapshot: list[dict[str, Any]] = Field(..., description="Snapshot of ticked criteria")
    commentary: str | None = None


class GateDecisionPatch(BaseModel):
    decision: Literal["approved", "rejected", "conditional"]
    commentary: str | None = None


class GateSubmissionItem(BaseModel):
    id: str
    initiative_id: str
    initiative_code: str | None = None
    initiative_name: str | None = None
    initiatives: dict[str, Any] | None = None
    gate_number: int
    submission_type: Literal["stage_gate", "bankable_plan_rebaseline"] = "stage_gate"
    submitted_by_id: str
    submitted_by_name: str | None = None
    submitted_at: str
    decision: str
    decided_by_id: str | None = None
    decided_by_name: str | None = None
    decided_at: str | None = None
    commentary: str | None = None
    criteria_snapshot: list[dict[str, Any]] | None = None
    requested_bankable_plan_version: int | None = None
    requested_snapshot: dict[str, Any] | None = None


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
