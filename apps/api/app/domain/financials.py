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


class FinancialGridResponse(BaseModel):
    """Full financial grid for an initiative."""
    initiative_id: str
    entries: list[FinancialEntryRow]
    summary: FinancialSummary


class FinancialSummary(BaseModel):
    """Header summary cards — aggregated across all years.

    Net Value = GM Uplift − Recurring Costs (one-off costs shown separately).
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
    # Net value = GM Uplift - Recurring Costs
    net_value_plan: str = "0"
    net_value_actual: str | None = None
    # Run rates (annualised)
    benefit_run_rate: str = "0"
    cost_run_rate: str = "0"


# Fix forward reference
FinancialGridResponse.model_rebuild()


# ── Cost lines ────────────────────────────────────────────────────────────────

class CostLineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    year: int = Field(..., ge=2020, le=2040)
    quarter: Quarter | None = None
    month: int | None = Field(None, ge=1, le=12)
    amount_plan: Decimal = Decimal("0")
    amount_actual: Decimal | None = None
    is_recurring: bool = False


class CostLineUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
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
    year: int
    quarter: int | None = None
    month: int | None = None
    amount_plan: str = "0"
    amount_actual: str | None = None
    is_recurring: bool = False


class CostLineListResponse(BaseModel):
    items: list[CostLineItem]
    total: int


# ── Value Bridge ──────────────────────────────────────────────────────────────

class ValueBridgeCase(BaseModel):
    """Single row: base, high, or actual."""
    revenue_uplift: str = "0"
    gross_margin: str = "0"
    gm_uplift: str = "0"
    costs_recurring: str = "0"
    costs_one_off: str = "0"
    costs_total: str = "0"
    net: str = "0"  # GM Uplift - Recurring Costs


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
