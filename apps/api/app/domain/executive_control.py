"""Executive Control Tower contracts."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

DependencyType = Literal["blocks", "enables", "informs", "duplicates", "requires_decision"]
DependencyStatus = Literal["proposed", "active", "at_risk", "blocking", "resolved", "cancelled"]
Severity = Literal["high", "medium", "low"]
AllocationMethod = Literal[
    "fixed_percentage",
    "equal_split",
    "manual_amount",
    "benefit_weighted",
    "revenue_weighted",
    "headcount_weighted",
]
AllocationScenario = Literal["plan", "actual"]


class InitiativeRef(BaseModel):
    id: str
    initiative_code: str | None = None
    name: str
    owner_id: str | None = None
    owner_name: str | None = None
    workstream_id: str | None = None
    workstream_name: str | None = None
    rag_status: str | None = None
    stage: str | None = None


class InitiativeDependencyCreate(BaseModel):
    upstream_initiative_id: str
    downstream_initiative_id: str
    dependency_type: DependencyType = "blocks"
    status: DependencyStatus = "proposed"
    severity: Severity = "medium"
    owner_id: str | None = None
    due_date: str | None = None
    resolution_notes: str | None = None
    linked_milestone_id: str | None = None
    linked_action_item_id: str | None = None


class InitiativeDependencyUpdate(BaseModel):
    dependency_type: DependencyType | None = None
    status: DependencyStatus | None = None
    severity: Severity | None = None
    owner_id: str | None = None
    due_date: str | None = None
    resolution_notes: str | None = None
    linked_milestone_id: str | None = None
    linked_action_item_id: str | None = None


class InitiativeDependencyItem(BaseModel):
    id: str
    upstream: InitiativeRef
    downstream: InitiativeRef
    dependency_type: DependencyType
    status: DependencyStatus
    severity: Severity
    owner_id: str | None = None
    owner_name: str | None = None
    due_date: str | None = None
    resolution_notes: str | None = None
    linked_milestone_id: str | None = None
    linked_action_item_id: str | None = None
    is_overdue: bool = False
    blast_radius: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class InitiativeDependencyRollups(BaseModel):
    total: int = 0
    blocking: int = 0
    at_risk: int = 0
    overdue: int = 0
    resolved: int = 0
    critical_path_risk: int = 0
    blocked_initiatives: list[InitiativeRef] = Field(default_factory=list)
    top_blockers: list[dict[str, Any]] = Field(default_factory=list)


class InitiativeDependencyListResponse(BaseModel):
    items: list[InitiativeDependencyItem]
    total: int
    rollups: InitiativeDependencyRollups


class SharedCostPoolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    category_key: str = Field("other", min_length=1, max_length=120)
    year: int = Field(..., ge=2020, le=2040)
    quarter: int | None = Field(None, ge=1, le=4)
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal = Decimal("0")
    amount_actual: Decimal | None = None
    is_recurring: bool = False
    status: Literal["draft", "active", "archived"] = "draft"


class SharedCostPoolUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    category_key: str | None = Field(None, min_length=1, max_length=120)
    year: int | None = Field(None, ge=2020, le=2040)
    quarter: int | None = Field(None, ge=1, le=4)
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal | None = None
    amount_actual: Decimal | None = None
    is_recurring: bool | None = None
    status: Literal["draft", "active", "archived"] | None = None


class SharedCostPoolItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    category_key: str = "other"
    year: int
    quarter: int | None = None
    month: int | None = None
    amount_plan: str = "0"
    amount_actual: str | None = None
    is_recurring: bool = False
    status: str = "draft"
    allocated_plan: str = "0"
    allocated_actual: str = "0"
    created_at: str | None = None


class SharedCostPoolListResponse(BaseModel):
    items: list[SharedCostPoolItem]
    total: int


class AllocationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    allocation_method: AllocationMethod
    filters: dict[str, Any] = Field(default_factory=dict)
    weights: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AllocationRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    allocation_method: AllocationMethod | None = None
    filters: dict[str, Any] | None = None
    weights: dict[str, Any] | None = None
    is_active: bool | None = None


class AllocationRuleItem(BaseModel):
    id: str
    pool_id: str
    name: str
    allocation_method: AllocationMethod
    filters: dict[str, Any] = Field(default_factory=dict)
    weights: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AllocationRunCreate(BaseModel):
    rule_id: str
    scenario: AllocationScenario = "plan"


class SharedCostAllocationItem(BaseModel):
    id: str
    initiative_id: str
    initiative_name: str | None = None
    allocation_basis: str
    basis_value: str
    allocated_plan: str
    allocated_actual: str | None = None


class AllocationRunItem(BaseModel):
    id: str
    pool_id: str
    rule_id: str
    scenario: AllocationScenario
    status: str
    total_amount_plan: str
    total_amount_actual: str | None = None
    created_by: str | None = None
    created_at: str
    allocations: list[SharedCostAllocationItem] = Field(default_factory=list)


class ValueRealizationNoteCreate(BaseModel):
    note_type: Literal["variance", "benefit_confidence", "allocation", "realization", "board_note"] = (
        "variance"
    )
    period_label: str | None = None
    planned_value: Decimal | None = None
    actual_value: Decimal | None = None
    explanation: str = Field(..., min_length=1, max_length=4000)


class ValueRealizationNoteItem(BaseModel):
    id: str
    initiative_id: str
    author_id: str | None = None
    note_type: str
    period_label: str | None = None
    planned_value: str | None = None
    actual_value: str | None = None
    explanation: str
    created_at: str


class ReportFilterParams(BaseModel):
    business_unit_id: str | None = None
    workstream_id: str | None = None
    tag: str | None = None
    country: str | None = None
    owner_id: str | None = None
    rag_status: str | None = None
    stage: str | None = None
    target_year: int | None = None


class ReportResponse(BaseModel):
    persona: Literal["owner", "management", "investor"]
    summary: dict[str, Any]
    value_bridge: dict[str, str]
    cost_allocation: dict[str, str]
    dependency_risk: InitiativeDependencyRollups
    needs_attention: list[dict[str, Any]]
    initiatives: list[dict[str, Any]]
