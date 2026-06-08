"""Financial domain models — Pydantic v2 contracts.

All monetary values use Decimal in Python, NUMERIC(15,4) in PostgreSQL,
and serialise as strings in JSON responses.
"""

from __future__ import annotations

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


# Fix forward references
BankablePlanSnapshot.model_rebuild()
BankablePlanVersion.model_rebuild()
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


class ValueBridgeResponse(BaseModel):
    """Three-column Value Bridge: Benefits / Costs / Net."""

    initiative_id: str | None = None  # None for portfolio-level
    base_case: ValueBridgeCase
    high_case: ValueBridgeCase
    actual: ValueBridgeCase


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
