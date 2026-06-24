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
    "savings_weighted",
    "direct_cost_weighted",
    "headcount_weighted",
    "metric_weighted",
]
AllocationScenario = Literal["plan", "actual", "forecast", "baseline"]
SharedCostPeriodGrain = Literal["annual", "quarterly", "monthly"]
SharedCostReportingTreatment = Literal["report_only", "post_cost_lines", "report_and_post"]
AllocationRunStatus = Literal["preview", "approved", "locked", "posted", "completed", "voided"]
AllocationRunType = Literal["preview", "posting"]
MissingBasisBehavior = Literal["fail", "zero", "equal_split"]
DriverPeriodMode = Literal["pool_period", "fiscal_year", "trailing_12", "custom"]
AllocationTargetMode = Literal["include", "exclude"]
AllocationTargetDimension = Literal[
    "all",
    "initiative",
    "workstream",
    "business_unit",
    "tag",
    "country",
    "stage",
    "owner",
    "rag_status",
]


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
    cost_category_id: str | None = None
    scenario_id: str | None = None
    year: int = Field(..., ge=2020, le=2040)
    quarter: int | None = Field(None, ge=1, le=4)
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal = Decimal("0")
    amount_actual: Decimal | None = None
    is_recurring: bool = False
    status: Literal["draft", "active", "archived"] = "draft"
    period_grain: SharedCostPeriodGrain = "annual"
    reporting_treatment: SharedCostReportingTreatment = "report_only"
    currency_code: str = Field("USD", min_length=3, max_length=3)
    owner_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SharedCostPoolUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    category_key: str | None = Field(None, min_length=1, max_length=120)
    cost_category_id: str | None = None
    scenario_id: str | None = None
    year: int | None = Field(None, ge=2020, le=2040)
    quarter: int | None = Field(None, ge=1, le=4)
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal | None = None
    amount_actual: Decimal | None = None
    is_recurring: bool | None = None
    status: Literal["draft", "active", "archived"] | None = None
    period_grain: SharedCostPeriodGrain | None = None
    reporting_treatment: SharedCostReportingTreatment | None = None
    currency_code: str | None = Field(None, min_length=3, max_length=3)
    owner_id: str | None = None
    metadata: dict[str, Any] | None = None


class SharedCostPoolItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    category_key: str = "other"
    cost_category_id: str | None = None
    category_label: str | None = None
    scenario_id: str | None = None
    scenario_key: str | None = None
    scenario_label: str | None = None
    year: int
    quarter: int | None = None
    month: int | None = None
    amount_plan: str = "0"
    amount_actual: str | None = None
    is_recurring: bool = False
    status: str = "draft"
    period_grain: SharedCostPeriodGrain = "annual"
    reporting_treatment: SharedCostReportingTreatment = "report_only"
    currency_code: str = "USD"
    owner_id: str | None = None
    locked_at: str | None = None
    allocated_plan: str = "0"
    allocated_actual: str = "0"
    unallocated_plan: str = "0"
    unallocated_actual: str = "0"
    latest_run_status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
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
    driver_metric_definition_id: str | None = None
    driver_cost_category_id: str | None = None
    driver_scenario_id: str | None = None
    driver_period_mode: DriverPeriodMode = "pool_period"
    missing_basis_behavior: MissingBasisBehavior = "fail"
    cap_floor_config: dict[str, Any] = Field(default_factory=dict)
    targets: list[AllocationTargetUpsert] = Field(default_factory=list)
    structured_weights: list[AllocationWeightUpsert] = Field(default_factory=list)


class AllocationRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    allocation_method: AllocationMethod | None = None
    filters: dict[str, Any] | None = None
    weights: dict[str, Any] | None = None
    is_active: bool | None = None
    driver_metric_definition_id: str | None = None
    driver_cost_category_id: str | None = None
    driver_scenario_id: str | None = None
    driver_period_mode: DriverPeriodMode | None = None
    missing_basis_behavior: MissingBasisBehavior | None = None
    cap_floor_config: dict[str, Any] | None = None


class AllocationRuleItem(BaseModel):
    id: str
    pool_id: str
    name: str
    allocation_method: AllocationMethod
    filters: dict[str, Any] = Field(default_factory=dict)
    weights: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    version: int = 1
    policy_status: str = "active"
    driver_metric_definition_id: str | None = None
    driver_metric_label: str | None = None
    driver_cost_category_id: str | None = None
    driver_cost_category_label: str | None = None
    driver_scenario_id: str | None = None
    driver_scenario_label: str | None = None
    driver_period_mode: DriverPeriodMode = "pool_period"
    missing_basis_behavior: MissingBasisBehavior = "fail"
    cap_floor_config: dict[str, Any] = Field(default_factory=dict)
    is_locked: bool = False
    targets: list[AllocationTargetItem] = Field(default_factory=list)
    structured_weights: list[AllocationWeightItem] = Field(default_factory=list)


class AllocationTargetUpsert(BaseModel):
    target_mode: AllocationTargetMode = "include"
    dimension_type: AllocationTargetDimension = "all"
    dimension_value: str | None = None
    label: str | None = None


class AllocationTargetItem(AllocationTargetUpsert):
    id: str


class AllocationWeightUpsert(BaseModel):
    initiative_id: str | None = None
    dimension_type: AllocationTargetDimension | None = None
    dimension_value: str | None = None
    weight_value: Decimal | None = None
    percentage: Decimal | None = None
    manual_amount: Decimal | None = None
    label: str | None = None


class AllocationWeightItem(BaseModel):
    id: str
    initiative_id: str | None = None
    dimension_type: str | None = None
    dimension_value: str | None = None
    weight_value: str | None = None
    percentage: str | None = None
    manual_amount: str | None = None
    label: str | None = None


class AllocationRunCreate(BaseModel):
    rule_id: str
    scenario: AllocationScenario = "plan"
    scenario_id: str | None = None
    run_type: AllocationRunType = "posting"
    status: AllocationRunStatus = "locked"


class SharedCostAllocationItem(BaseModel):
    id: str
    initiative_id: str
    initiative_name: str | None = None
    allocation_basis: str
    basis_value: str
    allocated_plan: str
    allocated_actual: str | None = None
    allocation_share: str = "0"
    rounding_adjustment: str = "0"
    basis_label: str | None = None
    explanation: str | None = None
    exception_flags: dict[str, Any] = Field(default_factory=dict)


class AllocationRunItem(BaseModel):
    id: str
    pool_id: str
    rule_id: str
    scenario: AllocationScenario
    scenario_id: str | None = None
    status: AllocationRunStatus
    run_type: AllocationRunType = "posting"
    rule_version: int = 1
    total_amount_plan: str
    total_amount_actual: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    reporting_treatment: SharedCostReportingTreatment = "report_only"
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    exception_summary: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None
    approved_at: str | None = None
    locked_by: str | None = None
    locked_at: str | None = None
    void_reason: str | None = None
    created_by: str | None = None
    created_at: str
    allocations: list[SharedCostAllocationItem] = Field(default_factory=list)


class AllocationReconciliation(BaseModel):
    pool_amount_plan: str
    allocated_plan: str
    unallocated_plan: str
    pool_amount_actual: str | None = None
    allocated_actual: str | None = None
    unallocated_actual: str | None = None
    rounding_adjustment: str = "0"
    reconciled: bool = False


class AllocationExceptionItem(BaseModel):
    exception_type: str
    severity: Literal["info", "warning", "blocking"] = "warning"
    message: str
    initiative_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AllocationPreviewRequest(BaseModel):
    rule_id: str
    scenario: AllocationScenario = "plan"
    scenario_id: str | None = None


class AllocationPreviewResponse(BaseModel):
    pool: SharedCostPoolItem
    rule: AllocationRuleItem
    scenario: AllocationScenario = "plan"
    scenario_id: str | None = None
    candidate_count: int = 0
    excluded_count: int = 0
    allocations: list[SharedCostAllocationItem] = Field(default_factory=list)
    exceptions: list[AllocationExceptionItem] = Field(default_factory=list)
    reconciliation: AllocationReconciliation
    reporting_impact: dict[str, str] = Field(default_factory=dict)


class SharedCostPoolPeriodUpsert(BaseModel):
    scenario_id: str | None = None
    year: int = Field(..., ge=2020, le=2060)
    quarter: int | None = Field(None, ge=1, le=4)
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal = Decimal("0")
    amount_actual: Decimal | None = None
    status: Literal["draft", "active", "locked", "archived"] = "active"


class SharedCostPoolPeriodItem(BaseModel):
    id: str
    pool_id: str
    scenario_id: str | None = None
    year: int
    quarter: int | None = None
    month: int | None = None
    period_start: str
    period_end: str
    amount_plan: str
    amount_actual: str | None = None
    status: str = "active"


class SharedCostReportingSettings(BaseModel):
    include_in_executive_control_tower: bool = True
    include_in_dashboard_executive_brief: bool = True
    include_in_portfolio_financials: bool = False
    include_in_initiative_financials: bool = True
    include_in_bankable_plan: bool = False
    posting_mode: SharedCostReportingTreatment = "report_only"


class SharedCostConfigResponse(BaseModel):
    cost_categories: list[dict[str, Any]] = Field(default_factory=list)
    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    metric_definitions: list[dict[str, Any]] = Field(default_factory=list)
    initiatives: list[dict[str, Any]] = Field(default_factory=list)
    workstreams: list[dict[str, Any]] = Field(default_factory=list)
    business_units: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)
    allocation_methods: list[dict[str, str]] = Field(default_factory=list)
    reporting_settings: SharedCostReportingSettings


class ValueRealizationNoteCreate(BaseModel):
    note_type: Literal[
        "variance", "benefit_confidence", "allocation", "realization", "board_note"
    ] = "variance"
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
    selected_year: int | None = None
    available_years: list[int] = Field(default_factory=list)
    summary: dict[str, Any]
    value_bridge: dict[str, str]
    cost_allocation: dict[str, str]
    dependency_risk: InitiativeDependencyRollups
    needs_attention: list[dict[str, Any]]
    initiatives: list[dict[str, Any]]
