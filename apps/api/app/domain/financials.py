"""Financial domain models — Pydantic v2 contracts.

All monetary values use Decimal in Python, NUMERIC(15,4) in PostgreSQL,
and serialise as strings in JSON responses.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

# ── Enums ─────────────────────────────────────────────────────────────────────

Quarter = Literal[1, 2, 3, 4]
FinancialScenario = Literal["base", "high", "actual"]
FinancialConfigGroupKind = Literal["calculation", "metric", "cost_category"]
FinancialConfigItemType = Literal["metric", "cost_category"]
FinancialRollupType = Literal[
    "benefit",
    "recurring_cost",
    "one_off_cost",
    "total_cost",
    "net_value",
]
PortfolioGranularity = Literal["monthly", "quarterly", "yearly"]
FinancialModeKey = Literal["pre_lock", "planned_vs_actual", "multi_scenario", "bankable_locked"]
BenefitLedgerGranularity = Literal["weekly", "monthly", "yearly"]
WorkstreamLockCadence = Literal["one_off", "annual", "cycle_based"]
WorkstreamCutoffRule = Literal["approved_at_lte_lock_date"]
WorkstreamValuationMethod = Literal["run_rate"]
WorkstreamLockedValueBasis = Literal["net_run_rate", "benefit_run_rate"]
FinancialForecastLineType = Literal["metric", "cost"]
FinancialMetricValueType = Literal["currency", "percent", "number"]
FinancialMetricDirection = Literal["increase_good", "decrease_good", "neutral"]
FinancialMetricAggregation = Literal["sum", "avg", "last", "formula"]
FinancialMetricAppliesTo = Literal["all", "opt_in"]
FinancialBenefitClass = Literal["savings", "avoidance", "revenue", "margin", "other"]
FinancialCostBehavior = Literal["recurring", "one_time"]
FinancialScenarioKind = Literal["baseline", "plan", "forecast", "actual"]
FinancialLineImpactType = Literal["recurring", "one_time"]
FinancialValueStatus = Literal["draft", "submitted", "approved"]
FinancialAttributeEntityType = Literal["benefit_line", "cost_line"]
FinancialAttributeValueType = Literal[
    "text", "number", "currency", "percent", "date", "select", "boolean"
]


class FinancialModeDescriptor(BaseModel):
    key: FinancialModeKey
    label: str
    description: str | None = None
    locked: bool = False
    scenarios: list[str] = Field(default_factory=list)


class FinancialGovernanceSettings(BaseModel):
    initiative_plan_lock_gate_number: int = Field(1, ge=1, le=10)
    plan_lock_on_approval: bool = True
    allow_rebaseline: bool = True
    rebaseline_roles: list[str] = Field(default_factory=lambda: ["transformation_office"])
    workstream_lock_cadence: WorkstreamLockCadence = "one_off"
    initiative_inclusion_cutoff: WorkstreamCutoffRule = "approved_at_lte_lock_date"
    valuation_method: WorkstreamValuationMethod = "run_rate"
    locked_value_basis: WorkstreamLockedValueBasis = "net_run_rate"
    workstream_target_versioning: bool = True


class FinancialGovernanceSettingsUpdate(BaseModel):
    initiative_plan_lock_gate_number: int | None = Field(None, ge=1, le=10)
    plan_lock_on_approval: bool | None = None
    allow_rebaseline: bool | None = None
    rebaseline_roles: list[str] | None = None
    workstream_lock_cadence: WorkstreamLockCadence | None = None
    initiative_inclusion_cutoff: WorkstreamCutoffRule | None = None
    valuation_method: WorkstreamValuationMethod | None = None
    locked_value_basis: WorkstreamLockedValueBasis | None = None
    workstream_target_versioning: bool | None = None


class FinancialReportingSettings(BaseModel):
    fiscal_year_start_month: int = Field(1, ge=1, le=12)
    reporting_currency: str = Field("USD", min_length=3, max_length=3)


class FinancialReportingSettingsUpdate(BaseModel):
    fiscal_year_start_month: int | None = Field(None, ge=1, le=12)
    reporting_currency: str | None = Field(None, min_length=3, max_length=3)


class FinancialMetricDefinitionBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    group_key: str | None = Field(None, max_length=120)
    value_type: FinancialMetricValueType
    unit: str | None = Field(None, max_length=40)
    direction: FinancialMetricDirection = "increase_good"
    aggregation: FinancialMetricAggregation = "sum"
    rollup_type: FinancialRollupType | None = None
    is_benefit: bool = False
    benefit_class: FinancialBenefitClass | None = None
    cost_behavior: FinancialCostBehavior | None = None
    formula: str | None = None
    formula_inputs: list[str] = Field(default_factory=list)
    precision: int = Field(4, ge=0, le=8)
    display_order: int = 0
    applies_to: FinancialMetricAppliesTo = "opt_in"
    validation: dict[str, object] = Field(default_factory=dict)
    is_system: bool = False
    is_active: bool = True


class FinancialMetricDefinitionCreate(FinancialMetricDefinitionBase):
    pass


class FinancialMetricDefinitionUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    group_key: str | None = Field(None, max_length=120)
    value_type: FinancialMetricValueType | None = None
    unit: str | None = Field(None, max_length=40)
    direction: FinancialMetricDirection | None = None
    aggregation: FinancialMetricAggregation | None = None
    rollup_type: FinancialRollupType | None = None
    is_benefit: bool | None = None
    benefit_class: FinancialBenefitClass | None = None
    cost_behavior: FinancialCostBehavior | None = None
    formula: str | None = None
    formula_inputs: list[str] | None = None
    precision: int | None = Field(None, ge=0, le=8)
    display_order: int | None = None
    applies_to: FinancialMetricAppliesTo | None = None
    validation: dict[str, object] | None = None
    is_active: bool | None = None


class FinancialMetricDefinition(FinancialMetricDefinitionBase):
    id: str
    created_by: str | None = None
    updated_by: str | None = None


class FinancialScenarioDefinitionBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    kind: FinancialScenarioKind
    is_primary: bool = False
    is_system: bool = False
    is_active: bool = True
    display_order: int = 0


class FinancialScenarioDefinitionCreate(FinancialScenarioDefinitionBase):
    pass


class FinancialScenarioDefinitionUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=200)
    kind: FinancialScenarioKind | None = None
    is_primary: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None


class FinancialScenarioDefinition(FinancialScenarioDefinitionBase):
    id: str


class FinancialBridgeRow(BaseModel):
    id: str | None = None
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    row_kind: Literal["metric_set", "cost_set", "subtotal", "net"]
    metric_definition_ids: list[str] = Field(default_factory=list)
    cost_category_keys: list[str] = Field(default_factory=list)
    sign: Literal[-1, 1] = 1
    display_order: int = 0
    is_active: bool = True


class FinancialAttributeDefinition(BaseModel):
    id: str | None = None
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    entity_type: FinancialAttributeEntityType
    value_type: FinancialAttributeValueType = "text"
    options: list[str] = Field(default_factory=list)
    is_required: bool = False
    display_order: int = 0
    is_active: bool = True


class FinancialEngineConfigurationResponse(BaseModel):
    definitions: list[FinancialMetricDefinition]
    scenarios: list[FinancialScenarioDefinition]
    bridge_rows: list[FinancialBridgeRow]
    attribute_definitions: list[FinancialAttributeDefinition] = Field(default_factory=list)
    settings: FinancialReportingSettings


class FinancialBenefitLineBase(BaseModel):
    metric_definition_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    impact_type: FinancialLineImpactType | None = None
    timing: str | None = Field(None, max_length=120)
    confidence: Decimal | None = Field(None, ge=0, le=100)
    phasing: dict[str, object] = Field(default_factory=dict)
    attributes: dict[str, object] = Field(default_factory=dict)
    show_in_summary: bool = True
    display_order: int = 0


class FinancialBenefitLineCreate(FinancialBenefitLineBase):
    pass


class FinancialBenefitLineUpdate(BaseModel):
    metric_definition_id: str | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    impact_type: FinancialLineImpactType | None = None
    timing: str | None = Field(None, max_length=120)
    confidence: Decimal | None = Field(None, ge=0, le=100)
    phasing: dict[str, object] | None = None
    attributes: dict[str, object] | None = None
    show_in_summary: bool | None = None
    display_order: int | None = None


class FinancialBenefitLine(FinancialBenefitLineBase):
    id: str
    created_by: str | None = None
    updated_by: str | None = None


class FinancialMetricValue(BaseModel):
    metric_definition_id: str
    scenario_id: str
    year: int = Field(..., ge=2020, le=2060)
    month: int = Field(..., ge=1, le=12)
    value: Decimal = Decimal("0")
    benefit_line_id: str | None = None
    status: FinancialValueStatus = "draft"
    note: str | None = None


class ConfigurableFinancialMetricValueRow(FinancialMetricValue):
    id: str
    value: str = "0"


class ConfigurableFinancialGridUpdate(BaseModel):
    values: list[FinancialMetricValue] = Field(default_factory=list)
    benefit_lines: list[FinancialBenefitLineCreate] | None = None
    cost_lines: list[CostLineCreate] | None = None


class ConfigurableFinancialGridResponse(BaseModel):
    initiative_id: str
    definitions: list[FinancialMetricDefinition]
    scenarios: list[FinancialScenarioDefinition]
    benefit_lines: list[FinancialBenefitLine] = Field(default_factory=list)
    values: list[ConfigurableFinancialMetricValueRow] = Field(default_factory=list)
    cost_lines: list[CostLineItem] = Field(default_factory=list)
    settings: FinancialReportingSettings
    entries: list[FinancialEntryRow] = Field(default_factory=list)
    metric_values: list[FinancialMetricValueRow] = Field(default_factory=list)
    selections: InitiativeFinancialSelections | None = None
    summary: FinancialSummary | None = None
    locked: bool = False
    lock_reason: str | None = None


class FinancialConfigGroup(BaseModel):
    id: str | None = None
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    kind: FinancialConfigGroupKind
    rollup_type: FinancialRollupType | None = None
    display_order: int = 0
    is_system: bool = False
    is_active: bool = True


class FinancialConfigItem(BaseModel):
    id: str | None = None
    group_id: str | None = None
    group_key: str | None = None
    key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    item_type: FinancialConfigItemType
    system_metric_key: str | None = Field(None, max_length=120)
    rollup_type: FinancialRollupType | None = None
    display_order: int = 0
    is_system: bool = False
    is_active: bool = True


class FinancialConfigurationResponse(BaseModel):
    groups: list[FinancialConfigGroup]
    items: list[FinancialConfigItem]


class FinancialConfigurationUpdate(BaseModel):
    groups: list[FinancialConfigGroup]
    items: list[FinancialConfigItem]


class FinancialCategoryDeleteRequest(BaseModel):
    category_key: str = Field(..., min_length=1, max_length=120)
    replacement_key: str = Field(..., min_length=1, max_length=120)


class FinancialMetricDeactivateRequest(BaseModel):
    metric_key: str = Field(..., min_length=1, max_length=120)


class InitiativeFinancialSelections(BaseModel):
    metric_keys: list[str] = Field(default_factory=list)
    cost_category_keys: list[str] = Field(default_factory=list)


class InitiativeFinancialSelectionsResponse(BaseModel):
    available: FinancialConfigurationResponse
    selected: InitiativeFinancialSelections
    locked: bool = False
    lock_reason: str | None = None


# ── Financial entries (revenue uplift, gross margin per quarter) ──────────────


class FinancialEntryRow(BaseModel):
    """Single quarter/month/year row from the financial_entries table."""

    year: int
    quarter: int | None = None  # None = full-year aggregate
    month: int | None = None  # 1-12 for monthly granularity
    revenue_uplift_base: str = "0"
    revenue_uplift_high: str = "0"
    revenue_uplift_actual: str | None = None
    revenue_uplift_pct_base: str = "0"
    revenue_uplift_pct_high: str = "0"
    revenue_uplift_pct_actual: str | None = None
    gross_margin_base: str = "0"
    gross_margin_high: str = "0"
    gross_margin_actual: str | None = None
    gm_pct_base: str = "0"
    gm_pct_high: str = "0"
    gm_pct_actual: str | None = None
    gm_uplift_base: str = "0"
    gm_uplift_high: str = "0"
    gm_uplift_actual: str | None = None
    gm_uplift_pct_base: str = "0"
    gm_uplift_pct_high: str = "0"
    gm_uplift_pct_actual: str | None = None
    cogs_base: str = "0"
    cogs_high: str = "0"
    cogs_actual: str | None = None
    cogs_pct_base: str = "0"
    cogs_pct_high: str = "0"
    cogs_pct_actual: str | None = None


class FinancialEntryUpdate(BaseModel):
    """Upsert payload for a single quarter or month."""

    year: int = Field(..., ge=2020, le=2040)
    quarter: Quarter | None = None
    month: int | None = Field(None, ge=1, le=12)
    revenue_uplift_base: Decimal = Decimal("0")
    revenue_uplift_high: Decimal = Decimal("0")
    revenue_uplift_actual: Decimal | None = None
    revenue_uplift_pct_base: Decimal = Decimal("0")
    revenue_uplift_pct_high: Decimal = Decimal("0")
    revenue_uplift_pct_actual: Decimal | None = None
    gross_margin_base: Decimal = Decimal("0")
    gross_margin_high: Decimal = Decimal("0")
    gross_margin_actual: Decimal | None = None
    gm_pct_base: Decimal = Decimal("0")
    gm_pct_high: Decimal = Decimal("0")
    gm_pct_actual: Decimal | None = None
    gm_uplift_base: Decimal = Decimal("0")
    gm_uplift_high: Decimal = Decimal("0")
    gm_uplift_actual: Decimal | None = None
    gm_uplift_pct_base: Decimal = Decimal("0")
    gm_uplift_pct_high: Decimal = Decimal("0")
    gm_uplift_pct_actual: Decimal | None = None
    cogs_base: Decimal = Decimal("0")
    cogs_high: Decimal = Decimal("0")
    cogs_actual: Decimal | None = None
    cogs_pct_base: Decimal = Decimal("0")
    cogs_pct_high: Decimal = Decimal("0")
    cogs_pct_actual: Decimal | None = None


class FinancialGridUpdate(BaseModel):
    """Batch upsert for the entire financial grid."""

    entries: list[FinancialEntryUpdate]
    cost_lines: list[CostLineCreate] | None = None
    metric_values: list[FinancialMetricValueUpdate] | None = None


class FinancialGridResponse(BaseModel):
    """Full financial grid for an initiative."""

    initiative_id: str
    entries: list[FinancialEntryRow]
    metric_values: list[FinancialMetricValueRow] = Field(default_factory=list)
    selections: InitiativeFinancialSelections = Field(default_factory=InitiativeFinancialSelections)
    locked: bool = False
    lock_reason: str | None = None
    financial_mode: FinancialModeDescriptor | None = None
    summary: FinancialSummary


class FinancialSummary(BaseModel):
    """Header summary cards — aggregated across all years.

    Net Run-rate Impact = Total Benefits − Recurring Costs (one-off costs shown separately).
    """

    # Revenue uplift
    revenue_uplift_plan_base: str = "0"
    revenue_uplift_plan_high: str = "0"
    revenue_uplift_actual: str | None = None
    # Gross margin
    gross_margin_plan_base: str = "0"
    gross_margin_plan_high: str = "0"
    gross_margin_actual: str | None = None
    gm_pct_plan_base: str = "0"
    gm_pct_plan_high: str = "0"
    gm_pct_actual: str | None = None
    # Gross margin uplift
    gm_uplift_plan_base: str = "0"
    gm_uplift_plan_high: str = "0"
    gm_uplift_actual: str | None = None
    # COGS
    cogs_plan_base: str = "0"
    cogs_plan_high: str = "0"
    cogs_actual: str | None = None
    # Costs (split)
    costs_recurring_plan: str = "0"
    costs_recurring_actual: str | None = None
    costs_one_off_plan: str = "0"
    costs_one_off_actual: str | None = None
    costs_plan: str = "0"  # total
    costs_actual: str | None = None  # total
    # Net run-rate impact = total benefits - recurring costs
    net_value_plan: str = "0"
    net_value_actual: str | None = None
    # Run rates (annualised)
    benefit_run_rate: str = "0"
    cost_run_rate: str = "0"


# ── Cost lines ────────────────────────────────────────────────────────────────


class CostLineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    category_key: str = Field("other", min_length=1, max_length=120)
    year: int = Field(..., ge=2020, le=2040)
    quarter: Quarter | None = None
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal = Decimal("0")
    amount_actual: Decimal | None = None
    is_recurring: bool = False


class CostLineUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    category_key: str | None = Field(None, min_length=1, max_length=120)
    year: int | None = Field(None, ge=2020, le=2040)
    quarter: Quarter | None = None
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal | None = None
    amount_actual: Decimal | None = None
    is_recurring: bool | None = None


class CostLineItem(BaseModel):
    id: str
    initiative_id: str
    name: str
    category_key: str = "other"
    year: int
    quarter: int | None = None
    month: int | None = None
    amount_plan: str = "0"
    amount_actual: str | None = None
    is_recurring: bool = False


class PortfolioFinancialSummaryCard(BaseModel):
    key: str
    label: str
    plan: str = "0"
    actual: str = "0"
    variance: str = "0"


class PortfolioFinancialPeriod(BaseModel):
    period: str
    year: int
    quarter: int | None = None
    month: int | None = None
    benefits_plan: str = "0"
    benefits_actual: str = "0"
    recurring_costs_plan: str = "0"
    recurring_costs_actual: str = "0"
    one_off_costs_plan: str = "0"
    one_off_costs_actual: str = "0"
    total_costs_plan: str = "0"
    total_costs_actual: str = "0"
    net_value_plan: str = "0"
    net_value_actual: str = "0"


class PortfolioValueRampPeriod(PortfolioFinancialPeriod):
    cumulative_net_value_plan: str = "0"
    cumulative_net_value_actual: str = "0"


class PortfolioInYearValueCard(BaseModel):
    key: str
    label: str
    plan: str = "0"
    actual: str = "0"
    variance: str = "0"


class PortfolioValueRampResponse(BaseModel):
    granularity: PortfolioGranularity
    run_rate_year: int | None = None
    as_of_date: date | None = None
    stage: str | None = None
    periods: list[PortfolioValueRampPeriod]
    in_year: list[PortfolioInYearValueCard]
    financial_mode: FinancialModeDescriptor | None = None


class PortfolioFinancialBreakdown(BaseModel):
    key: str
    label: str
    group_key: str | None = None
    group_label: str | None = None
    plan: str = "0"
    actual: str = "0"
    variance: str = "0"


class PortfolioFinancialCostLineContribution(BaseModel):
    id: str
    name: str
    category_key: str = "other"
    category_label: str | None = None
    is_recurring: bool = False
    plan: str = "0"
    actual: str = "0"


class PortfolioFinancialInitiativeContribution(BaseModel):
    initiative_id: str
    initiative_name: str
    benefits_plan: str = "0"
    benefits_actual: str = "0"
    recurring_costs_plan: str = "0"
    recurring_costs_actual: str = "0"
    one_off_costs_plan: str = "0"
    one_off_costs_actual: str = "0"
    total_costs_plan: str = "0"
    total_costs_actual: str = "0"
    net_value_plan: str = "0"
    net_value_actual: str = "0"
    cost_lines: list[PortfolioFinancialCostLineContribution] = Field(default_factory=list)


class PortfolioFinancialContributorsResponse(BaseModel):
    granularity: PortfolioGranularity
    period: str
    year: int
    quarter: int | None = None
    month: int | None = None
    contributors: list[PortfolioFinancialInitiativeContribution]


class PortfolioFinancialsResponse(BaseModel):
    granularity: PortfolioGranularity
    summary: list[PortfolioFinancialSummaryCard]
    periods: list[PortfolioFinancialPeriod]
    broader_period_totals: list[PortfolioFinancialPeriod]
    cost_breakdown: list[PortfolioFinancialBreakdown]
    metric_breakdown: list[PortfolioFinancialBreakdown]
    financial_mode: FinancialModeDescriptor | None = None


class CostLineListResponse(BaseModel):
    items: list[CostLineItem]
    total: int


class FinancialMetricValueRow(BaseModel):
    metric_key: str
    year: int
    quarter: int | None = None
    month: int | None = None
    value_base: str = "0"
    value_high: str = "0"
    value_actual: str | None = None


class FinancialMetricValueUpdate(BaseModel):
    metric_key: str = Field(..., min_length=1, max_length=120)
    year: int = Field(..., ge=2020, le=2040)
    quarter: Quarter | None = None
    month: int | None = Field(None, ge=1, le=12)
    value_base: Decimal = Decimal("0")
    value_high: Decimal = Decimal("0")
    value_actual: Decimal | None = None


class BankablePlanSnapshot(BaseModel):
    entries: list[FinancialEntryRow] = Field(default_factory=list)
    cost_lines: list[CostLineItem] = Field(default_factory=list)
    metric_values: list[FinancialMetricValueRow] = Field(default_factory=list)
    selections: InitiativeFinancialSelections = Field(default_factory=InitiativeFinancialSelections)
    financial_mode: FinancialModeDescriptor | None = None
    summary: FinancialSummary


class BankablePlanVersion(BaseModel):
    id: str
    initiative_id: str
    version: int
    trigger_type: Literal["approval", "rebaseline"]
    trigger_submission_id: str | None = None
    locked_by_id: str | None = None
    locked_at: str
    locked_reason: str | None = None
    snapshot: BankablePlanSnapshot


class BankablePlanResponse(BaseModel):
    current: BankablePlanVersion | None = None
    history: list[BankablePlanVersion] = Field(default_factory=list)


class BankablePlanRebaselineRequest(BaseModel):
    reason: str | None = None


class BenefitLedgerEntryCreate(BaseModel):
    period_granularity: BenefitLedgerGranularity
    period_start: date
    period_end: date | None = None
    bankable_plan_amount: Decimal = Decimal("0")
    actual_amount: Decimal = Decimal("0")
    description: str | None = Field(None, max_length=2000)


class BenefitLedgerEntryUpdate(BaseModel):
    period_granularity: BenefitLedgerGranularity | None = None
    period_start: date | None = None
    period_end: date | None = None
    bankable_plan_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    description: str | None = Field(None, max_length=2000)


class BenefitLedgerEntry(BaseModel):
    id: str
    initiative_id: str
    period_granularity: BenefitLedgerGranularity
    period_start: date
    period_end: date
    bankable_plan_amount: str = "0"
    actual_amount: str = "0"
    variance: str = "0"
    description: str | None = None
    created_at: str
    updated_at: str


class BenefitLedgerPeriodSummary(BaseModel):
    period: str
    year: int
    week: int | None = None
    month: int | None = None
    period_start: date | None = None
    period_end: date | None = None
    period_granularity: BenefitLedgerGranularity
    bankable_plan_amount: str = "0"
    actual_amount: str = "0"
    variance: str = "0"


class BenefitLedgerSummaryResponse(BaseModel):
    initiative_id: str
    granularity: BenefitLedgerGranularity
    locked_bankable_plan_version: int | None = None
    periods: list[BenefitLedgerPeriodSummary] = Field(default_factory=list)
    bankable_plan_amount: str = "0"
    actual_amount: str = "0"
    variance: str = "0"


class BenefitLedgerInitiativeRollup(BaseModel):
    initiative_id: str
    initiative_code: str | None = None
    name: str
    stage: str | None = None
    workstream_id: str | None = None
    workstream_name: str | None = None
    locked_bankable_plan_version: int | None = None
    bankable_plan_amount: str = "0"
    actual_amount: str = "0"
    variance: str = "0"


class BenefitLedgerWorkstreamRollup(BaseModel):
    workstream_id: str | None = None
    workstream_name: str
    initiative_count: int = 0
    locked_initiative_count: int = 0
    bankable_plan_amount: str = "0"
    actual_amount: str = "0"
    variance: str = "0"


class BenefitLedgerRollupSummaryResponse(BaseModel):
    scope: str
    scope_id: str | None = None
    scope_name: str
    granularity: BenefitLedgerGranularity
    periods: list[BenefitLedgerPeriodSummary] = Field(default_factory=list)
    bankable_plan_amount: str = "0"
    actual_amount: str = "0"
    variance: str = "0"
    workstreams: list[BenefitLedgerWorkstreamRollup] = Field(default_factory=list)
    initiatives: list[BenefitLedgerInitiativeRollup] = Field(default_factory=list)


class FinancialForecastRow(BaseModel):
    id: str | None = None
    initiative_id: str
    line_type: FinancialForecastLineType
    line_key: str = Field(..., min_length=1, max_length=120)
    year: int = Field(..., ge=2020, le=2040)
    quarter: Quarter | None = None
    month: int | None = Field(None, ge=1, le=12)
    amount_forecast: str = "0"
    notes: str | None = None


class FinancialForecastUpdate(BaseModel):
    line_type: FinancialForecastLineType
    line_key: str = Field(..., min_length=1, max_length=120)
    year: int = Field(..., ge=2020, le=2040)
    quarter: Quarter | None = None
    month: int | None = Field(None, ge=1, le=12)
    amount_forecast: Decimal = Decimal("0")
    notes: str | None = Field(None, max_length=2000)


class FinancialForecastResponse(BaseModel):
    initiative_id: str
    items: list[FinancialForecastRow] = Field(default_factory=list)


class WorkstreamTargetInitiative(BaseModel):
    initiative_id: str
    initiative_code: str | None = None
    name: str
    stage: str | None = None
    approved_at: str | None = None
    bankable_plan_version: int | None = None
    value_source: str
    net_run_rate_value: str = "0"
    actual_value: str = "0"


class WorkstreamTargetSnapshot(BaseModel):
    workstream_id: str
    workstream_name: str | None = None
    lock_date: date
    settings: FinancialGovernanceSettings
    included: list[WorkstreamTargetInitiative] = Field(default_factory=list)
    excluded: list[WorkstreamTargetInitiative] = Field(default_factory=list)
    locked_run_rate_value: str = "0"
    plan_total: str = "0"
    actual_total: str = "0"
    variance: str = "0"


class WorkstreamTargetPreviewResponse(WorkstreamTargetSnapshot):
    latest_locked_version: int | None = None


class WorkstreamTargetLockRequest(BaseModel):
    lock_date: date


class WorkstreamTargetLockVersion(BaseModel):
    id: str
    workstream_id: str
    version: int
    lock_date: date
    locked_at: str
    locked_by_id: str | None = None
    lock_cadence: WorkstreamLockCadence
    cutoff_rule: WorkstreamCutoffRule
    valuation_method: WorkstreamValuationMethod
    locked_value_basis: WorkstreamLockedValueBasis
    included_initiative_ids: list[str] = Field(default_factory=list)
    excluded_initiative_ids: list[str] = Field(default_factory=list)
    locked_run_rate_value: str = "0"
    plan_total: str = "0"
    actual_total: str = "0"
    variance: str = "0"
    snapshot: WorkstreamTargetSnapshot


class WorkstreamTargetLockResponse(BaseModel):
    current: WorkstreamTargetLockVersion | None = None
    history: list[WorkstreamTargetLockVersion] = Field(default_factory=list)


# Fix forward references
BankablePlanSnapshot.model_rebuild()
BankablePlanVersion.model_rebuild()
ConfigurableFinancialGridUpdate.model_rebuild()
ConfigurableFinancialGridResponse.model_rebuild()
FinancialGridUpdate.model_rebuild()
FinancialGridResponse.model_rebuild()


# ── Value Bridge ──────────────────────────────────────────────────────────────


class ValueBridgeCase(BaseModel):
    """Single row: base, high, or actual."""

    revenue_uplift: str = "0"
    gross_margin: str = "0"
    gm_uplift: str = "0"
    other_benefits: str = "0"
    benefits_total: str = "0"
    cogs: str = "0"
    costs_recurring: str = "0"
    costs_one_off: str = "0"
    costs_total: str = "0"
    net: str = "0"  # Total benefits - recurring costs


class ValueBridgeRow(BaseModel):
    key: str
    label: str
    row_kind: Literal["metric_set", "cost_set", "subtotal", "net"]
    base_case: str = "0"
    high_case: str = "0"
    actual: str = "0"
    sign: Literal[-1, 1] = 1
    display_order: int = 0


class ValueBridgeResponse(BaseModel):
    """Three-column Value Bridge: Benefits / Costs / Net."""

    initiative_id: str | None = None  # None for portfolio-level
    base_case: ValueBridgeCase
    high_case: ValueBridgeCase
    actual: ValueBridgeCase
    rows: list[ValueBridgeRow] = Field(default_factory=list)
    financial_mode: FinancialModeDescriptor | None = None


class ScenarioFinancialSummary(BaseModel):
    scenario: FinancialScenario
    revenue_uplift: str = "0"
    gross_margin: str = "0"
    gm_uplift: str = "0"
    other_benefits: str = "0"
    benefits_total: str = "0"
    cogs: str = "0"
    costs_recurring: str = "0"
    costs_one_off: str = "0"
    costs_total: str = "0"
    net_value: str = "0"
    financial_mode: FinancialModeDescriptor | None = None


class BreakEvenPoint(BaseModel):
    period: str
    year: int
    quarter: int | None = None
    month: int | None = None
    cumulative_gm_uplift: str = "0"
    cumulative_costs: str = "0"
    cumulative_net: str = "0"
    run_rate_gm_uplift: str = "0"
    run_rate_costs: str = "0"
    is_break_even: bool = False


class BreakEvenResponse(BaseModel):
    initiative_id: str
    scenario: FinancialScenario
    break_even_period: str | None = None
    points: list[BreakEvenPoint]
    financial_mode: FinancialModeDescriptor | None = None


class FinancialCellAssumptionCreate(BaseModel):
    row_key: str = Field(..., min_length=1, max_length=120)
    column_key: str = Field(..., min_length=1, max_length=120)
    comment: str = Field(..., min_length=1, max_length=2000)


class FinancialCellAssumptionUpdate(BaseModel):
    comment: str = Field(..., min_length=1, max_length=2000)


class FinancialCellAssumption(BaseModel):
    id: str
    initiative_id: str
    row_key: str
    column_key: str
    comment: str
    created_by: str | None = None
    updated_by: str | None = None
    created_at: str
    updated_at: str


class FinancialCellAssumptionListResponse(BaseModel):
    items: list[FinancialCellAssumption]
    total: int
