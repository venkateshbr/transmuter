"""Financial service — business logic layer.

All financial calculations use Decimal arithmetic. Never float.
"""

from __future__ import annotations

# ruff: noqa: F401
import ast
import csv
import operator
from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal
from io import StringIO
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.domain.financials import (
    AnnualBaselineMetricValueRow,
    BankablePlanResponse,
    BankablePlanSnapshot,
    BankablePlanVersion,
    BenefitLedgerEntry,
    BenefitLedgerEntryCreate,
    BenefitLedgerEntryUpdate,
    BenefitLedgerGranularity,
    BenefitLedgerImportError,
    BenefitLedgerImportResult,
    BenefitLedgerInitiativeRollup,
    BenefitLedgerPeriodSummary,
    BenefitLedgerRollupSummaryResponse,
    BenefitLedgerSummaryResponse,
    BenefitLedgerWorkstreamRollup,
    BreakEvenPoint,
    BreakEvenResponse,
    ConfigurableFinancialGridResponse,
    ConfigurableFinancialGridUpdate,
    ConfigurableFinancialMetricValueRow,
    CostLineCreate,
    CostLineItem,
    CostLineListResponse,
    CostLineUpdate,
    FinancialAttributeDefinition,
    FinancialBenefitLine,
    FinancialBenefitLineHandoffUpdate,
    FinancialBenefitLineValidationEvent,
    FinancialBenefitLineValidationRequest,
    FinancialBenefitValidationStatus,
    FinancialBridgeRow,
    FinancialCategoryDeleteRequest,
    FinancialCellAssumption,
    FinancialCellAssumptionCreate,
    FinancialCellAssumptionListResponse,
    FinancialCellAssumptionUpdate,
    FinancialConfigGroup,
    FinancialConfigItem,
    FinancialConfigurationResponse,
    FinancialConfigurationUpdate,
    FinancialCostCategory,
    FinancialEngineConfigurationResponse,
    FinancialEntryRow,
    FinancialEntryUpdate,
    FinancialForecastResponse,
    FinancialForecastRow,
    FinancialForecastUpdate,
    FinancialGovernanceSettings,
    FinancialGovernanceSettingsUpdate,
    FinancialGridResponse,
    FinancialGridUpdate,
    FinancialMetricDeactivateRequest,
    FinancialMetricDefinition,
    FinancialMetricDefinitionCreate,
    FinancialMetricDefinitionUpdate,
    FinancialMetricValueRow,
    FinancialMetricValueUpdate,
    FinancialModeDescriptor,
    FinancialReportingSettings,
    FinancialReportingSettingsUpdate,
    FinancialScenario,
    FinancialScenarioDefinition,
    FinancialScenarioDefinitionCreate,
    FinancialScenarioDefinitionUpdate,
    FinancialSummary,
    InitiativeAnnualBaselineResponse,
    InitiativeAnnualBaselineUpdate,
    InitiativeFinancialSelections,
    InitiativeFinancialSelectionsResponse,
    InitiativePnlBridge,
    PnlBridgeCase,
    PnlBridgeStep,
    PortfolioBenefitsRegisterItem,
    PortfolioBenefitsRegisterResponse,
    PortfolioBenefitsRegisterTotals,
    PortfolioFinancialBenefitLineContribution,
    PortfolioFinancialBreakdown,
    PortfolioFinancialContributorsResponse,
    PortfolioFinancialCostLineContribution,
    PortfolioFinancialInitiativeContribution,
    PortfolioFinancialPeriod,
    PortfolioFinancialsResponse,
    PortfolioFinancialSummaryCard,
    PortfolioGranularity,
    PortfolioInitiativeBaselineReconciliation,
    PortfolioInitiativeMetricColumn,
    PortfolioInitiativePortfolioResponse,
    PortfolioInitiativePortfolioRow,
    PortfolioInitiativePortfolioTotals,
    PortfolioInvestmentPaybackResponse,
    PortfolioInvestmentPaybackRow,
    PortfolioInvestmentPaybackSummary,
    PortfolioInYearValueCard,
    PortfolioValueBridgeBasis,
    PortfolioValueRampPeriod,
    PortfolioValueRampResponse,
    ScenarioFinancialSummary,
    TenantAnnualBaselineResponse,
    TenantAnnualBaselineUpdate,
    ValueBridgeCase,
    ValueBridgeResponse,
    ValueBridgeRow,
    WorkstreamTargetInitiative,
    WorkstreamTargetLockRequest,
    WorkstreamTargetLockResponse,
    WorkstreamTargetLockVersion,
    WorkstreamTargetPreviewResponse,
    WorkstreamTargetSnapshot,
)
from app.repositories.financial import FinancialRepository
from app.services.financial_workbook import (
    build_board_pack_workbook,
    build_financial_workbook,
    parse_financial_workbook,
)


def _dec(val: object) -> Decimal:
    """Safely convert a value to Decimal, defaulting to 0."""
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _str_or_none(val: Decimal | None) -> str | None:
    """Serialise Decimal to string, or None if no actual value exists."""
    if val is None:
        return None
    return _money(val)


def _money(val: object) -> str:
    """Serialise a monetary Decimal as a stable NUMERIC(15,4)-style string."""
    return format(_dec(val).quantize(Decimal("0.0001")), "f")


# Fields that exist on financial_entries for the new uplift model
_ENTRY_FIELDS = [
    "revenue_uplift_base",
    "revenue_uplift_high",
    "revenue_uplift_actual",
    "revenue_uplift_pct_base",
    "revenue_uplift_pct_high",
    "revenue_uplift_pct_actual",
    "gross_margin_base",
    "gross_margin_high",
    "gross_margin_actual",
    "gm_pct_base",
    "gm_pct_high",
    "gm_pct_actual",
    "gm_uplift_base",
    "gm_uplift_high",
    "gm_uplift_actual",
    "gm_uplift_pct_base",
    "gm_uplift_pct_high",
    "gm_uplift_pct_actual",
    "cogs_base",
    "cogs_high",
    "cogs_actual",
    "cogs_pct_base",
    "cogs_pct_high",
    "cogs_pct_actual",
]


_FORMULA_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
}


class FormulaValidationError(ValueError):
    pass


class FormulaDivideByZeroError(ZeroDivisionError):
    pass


class FinancialService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = FinancialRepository(client, tenant_id)
        self._tenant_id = tenant_id

    # ── Financial grid ────────────────────────────────────────────────────────

    def _ensure_tenant_initiative(self, initiative_id: str) -> None:
        if not self._repo.initiative_exists(initiative_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Initiative not found",
            )

    def get_financial_grid(self, initiative_id: str) -> FinancialGridResponse:
        """Return the full financial grid with summary cards."""
        locked, lock_reason = self._financial_lock_state(initiative_id)
        if not locked:
            self._migrate_existing_grid_to_planned_window(initiative_id)
        rows = self._repo.get_entries(initiative_id)
        costs = self._repo.list_cost_lines(initiative_id)
        raw_metric_values = self._repo.list_metric_values(initiative_id)
        clean_metric_values = self._repo.list_configurable_metric_values(initiative_id)
        if not rows and clean_metric_values:
            rows = self._legacy_rows_from_metric_values(clean_metric_values)
        elif not rows and raw_metric_values:
            rows = self._legacy_rows_from_metric_values(raw_metric_values)
        entries = [self._to_entry_row(r) for r in rows]
        metric_values = [self._to_metric_value_row(r) for r in raw_metric_values]
        config = self.get_configuration()
        selections = self._resolve_selections(initiative_id, rows, costs, raw_metric_values, config)
        scoped_rows, scoped_costs = self._apply_financial_scope(rows, costs, selections)
        scoped_metric_values = self._scope_metric_values(raw_metric_values, selections)
        summary = self._compute_summary(
            scoped_rows,
            initiative_id,
            scoped_costs,
            scoped_metric_values,
            config,
        )
        financial_mode = self._financial_mode_descriptor(
            initiative_id,
            rows,
            costs,
            raw_metric_values,
            config=config,
            bankable_plan=self.get_current_bankable_plan(initiative_id),
        )
        return FinancialGridResponse(
            initiative_id=initiative_id,
            entries=entries,
            metric_values=metric_values,
            selections=selections,
            locked=locked,
            lock_reason=lock_reason,
            financial_mode=financial_mode,
            summary=summary,
        )

    def _legacy_rows_from_metric_values(self, raw_metric_values: list[dict]) -> list[dict]:
        engine = self.get_engine_configuration()
        definitions = {row.id: row for row in engine.definitions}
        scenarios = {row.id: row for row in engine.scenarios}
        grouped: dict[tuple[int, int | None, int | None], dict[str, Decimal | int | None]] = {}

        def bucket(
            year: int, quarter: int | None, month: int | None
        ) -> dict[str, Decimal | int | None]:
            return grouped.setdefault(
                (year, quarter, month),
                {
                    "year": year,
                    "quarter": quarter,
                    "month": month,
                    "revenue_uplift_base": Decimal("0"),
                    "revenue_uplift_high": Decimal("0"),
                    "revenue_uplift_actual": None,
                    "revenue_uplift_pct_base": Decimal("0"),
                    "revenue_uplift_pct_high": Decimal("0"),
                    "revenue_uplift_pct_actual": None,
                    "gross_margin_base": Decimal("0"),
                    "gross_margin_high": Decimal("0"),
                    "gross_margin_actual": None,
                    "gm_pct_base": Decimal("0"),
                    "gm_pct_high": Decimal("0"),
                    "gm_pct_actual": None,
                    "gm_uplift_base": Decimal("0"),
                    "gm_uplift_high": Decimal("0"),
                    "gm_uplift_actual": None,
                    "gm_uplift_pct_base": Decimal("0"),
                    "gm_uplift_pct_high": Decimal("0"),
                    "gm_uplift_pct_actual": None,
                    "cogs_base": Decimal("0"),
                    "cogs_high": Decimal("0"),
                    "cogs_actual": None,
                    "cogs_pct_base": Decimal("0"),
                    "cogs_pct_high": Decimal("0"),
                    "cogs_pct_actual": None,
                },
            )

        for row in raw_metric_values:
            definition = definitions.get(row.get("metric_definition_id"))
            scenario = scenarios.get(row.get("scenario_id"))
            if not definition or not scenario:
                continue
            year = int(row["year"])
            month = int(row["month"])
            quarter = ((month - 1) // 3) + 1
            target = (
                "actual"
                if scenario.kind == "actual"
                else ("high" if scenario.key == "plan_high" else "base")
            )
            amount = _dec(row.get("value"))
            item = bucket(year, quarter, month)
            key = str(definition.key)
            if key == "revenue_uplift":
                item[f"revenue_uplift_{target}"] = _dec(item[f"revenue_uplift_{target}"]) + amount  # type: ignore[index]
            elif key == "gross_margin":
                item[f"gross_margin_{target}"] = _dec(item[f"gross_margin_{target}"]) + amount  # type: ignore[index]
            elif key == "gm_uplift":
                item[f"gm_uplift_{target}"] = _dec(item[f"gm_uplift_{target}"]) + amount  # type: ignore[index]
            elif key == "cogs":
                item[f"cogs_{target}"] = _dec(item[f"cogs_{target}"]) + amount  # type: ignore[index]

        rows: list[dict] = []
        for item in grouped.values():
            rows.append(
                {
                    "year": item["year"],
                    "quarter": item["quarter"],
                    "month": item["month"],
                    "revenue_uplift_base": str(item["revenue_uplift_base"]),
                    "revenue_uplift_high": str(item["revenue_uplift_high"]),
                    "revenue_uplift_actual": (
                        str(item["revenue_uplift_actual"])
                        if item["revenue_uplift_actual"] is not None
                        else None
                    ),
                    "revenue_uplift_pct_base": str(item["revenue_uplift_pct_base"]),
                    "revenue_uplift_pct_high": str(item["revenue_uplift_pct_high"]),
                    "revenue_uplift_pct_actual": None,
                    "gross_margin_base": str(item["gross_margin_base"]),
                    "gross_margin_high": str(item["gross_margin_high"]),
                    "gross_margin_actual": (
                        str(item["gross_margin_actual"])
                        if item["gross_margin_actual"] is not None
                        else None
                    ),
                    "gm_pct_base": str(item["gm_pct_base"]),
                    "gm_pct_high": str(item["gm_pct_high"]),
                    "gm_pct_actual": None,
                    "gm_uplift_base": str(item["gm_uplift_base"]),
                    "gm_uplift_high": str(item["gm_uplift_high"]),
                    "gm_uplift_actual": (
                        str(item["gm_uplift_actual"])
                        if item["gm_uplift_actual"] is not None
                        else None
                    ),
                    "gm_uplift_pct_base": str(item["gm_uplift_pct_base"]),
                    "gm_uplift_pct_high": str(item["gm_uplift_pct_high"]),
                    "gm_uplift_pct_actual": None,
                    "cogs_base": str(item["cogs_base"]),
                    "cogs_high": str(item["cogs_high"]),
                    "cogs_actual": (
                        str(item["cogs_actual"]) if item["cogs_actual"] is not None else None
                    ),
                    "cogs_pct_base": str(item["cogs_pct_base"]),
                    "cogs_pct_high": str(item["cogs_pct_high"]),
                    "cogs_pct_actual": None,
                }
            )
        return rows

    def get_configurable_financial_grid(
        self,
        initiative_id: str,
    ) -> ConfigurableFinancialGridResponse:
        """Return the clean configurable financial grid for an initiative."""
        self._ensure_tenant_initiative(initiative_id)
        locked, lock_reason = self._financial_lock_state(initiative_id)
        config = self.get_engine_configuration()
        legacy_summary = self.get_financial_summary(initiative_id)
        stored_values = self._repo.list_configurable_metric_values(initiative_id)
        baseline = self.get_initiative_annual_baseline(initiative_id)
        values = self._values_with_formula_metrics(
            stored_values,
            self._repo.list_initiative_annual_baselines(initiative_id),
        )
        return ConfigurableFinancialGridResponse(
            initiative_id=initiative_id,
            definitions=config.definitions,
            scenarios=config.scenarios,
            cost_categories=config.cost_categories,
            baseline=baseline,
            benefit_lines=[
                self._to_benefit_line(row) for row in self._repo.list_benefit_lines(initiative_id)
            ],
            values=[self._to_configurable_metric_value(row) for row in values],
            cost_lines=[
                self._to_cost_line(row) for row in self._repo.list_cost_lines(initiative_id)
            ],
            settings=config.settings,
            entries=[],
            metric_values=[],
            selections=InitiativeFinancialSelections(),
            summary=legacy_summary,
            locked=locked,
            lock_reason=lock_reason,
        )

    def get_financial_summary(self, initiative_id: str) -> FinancialSummary:
        """Aggregated summary cards only."""
        rows = self._repo.get_entries(initiative_id)
        costs = self._repo.list_cost_lines(initiative_id)
        clean_values = self._repo.list_configurable_metric_values(initiative_id)
        if clean_values or (not rows and self._repo.list_metric_definitions()):
            return self._compute_clean_summary(
                self._values_with_formula_metrics(
                    clean_values,
                    self._repo.list_initiative_annual_baselines(initiative_id),
                ),
                costs,
            )
        metric_values = self._repo.list_metric_values(initiative_id)
        config = self.get_configuration()
        selections = self._resolve_selections(initiative_id, rows, costs, metric_values, config)
        scoped_rows, scoped_costs = self._apply_financial_scope(rows, costs, selections)
        scoped_metric_values = self._scope_metric_values(metric_values, selections)
        return self._compute_summary(
            scoped_rows, initiative_id, scoped_costs, scoped_metric_values, config
        )

    def update_financial_grid(
        self, initiative_id: str, data: FinancialGridUpdate
    ) -> FinancialGridResponse:
        """Upsert the full financial grid."""
        self._ensure_tenant_initiative(initiative_id)
        locked, _ = self._financial_lock_state(initiative_id)
        data = self._normalize_grid_to_planned_window(initiative_id, data)
        existing_entries = (
            {self._period_key(row): row for row in self._repo.get_entries(initiative_id)}
            if locked
            else {}
        )
        existing_costs = (
            {self._cost_period_key(row): row for row in self._repo.list_cost_lines(initiative_id)}
            if locked
            else {}
        )
        existing_metrics = (
            {
                self._metric_period_key(row): row
                for row in self._repo.list_metric_values(initiative_id)
            }
            if locked
            else {}
        )
        db_rows: list[dict[str, object]] = []
        for entry in data.entries:
            row: dict[str, object] = {
                "year": entry.year,
                "quarter": entry.quarter,
                "month": entry.month,
            }
            # Add all numeric fields — base/high as required, actual as optional
            for field_name in [
                "revenue_uplift_base",
                "revenue_uplift_high",
                "revenue_uplift_pct_base",
                "revenue_uplift_pct_high",
                "gross_margin_base",
                "gross_margin_high",
                "gm_pct_base",
                "gm_pct_high",
                "gm_uplift_base",
                "gm_uplift_high",
                "gm_uplift_pct_base",
                "gm_uplift_pct_high",
                "cogs_base",
                "cogs_high",
                "cogs_pct_base",
                "cogs_pct_high",
            ]:
                row[field_name] = _money(getattr(entry, field_name))

            for field_name in [
                "revenue_uplift_actual",
                "revenue_uplift_pct_actual",
                "gross_margin_actual",
                "gm_pct_actual",
                "gm_uplift_actual",
                "gm_uplift_pct_actual",
                "cogs_actual",
                "cogs_pct_actual",
            ]:
                val = getattr(entry, field_name)
                row[field_name] = _money(val) if val is not None else None

            if locked:
                existing = existing_entries.get(self._period_key(row))
                if existing:
                    for field_name in [
                        "revenue_uplift_base",
                        "revenue_uplift_high",
                        "revenue_uplift_pct_base",
                        "revenue_uplift_pct_high",
                        "gross_margin_base",
                        "gross_margin_high",
                        "gm_pct_base",
                        "gm_pct_high",
                        "gm_uplift_base",
                        "gm_uplift_high",
                        "gm_uplift_pct_base",
                        "gm_uplift_pct_high",
                        "cogs_base",
                        "cogs_high",
                        "cogs_pct_base",
                        "cogs_pct_high",
                    ]:
                        row[field_name] = _money(existing.get(field_name))
                else:
                    continue

            db_rows.append(row)

        if db_rows:
            self._repo.upsert_entries_batch(initiative_id, db_rows)

        # Process cost lines if present
        if data.cost_lines:
            cost_rows = []
            for cl in data.cost_lines:
                row = {
                    "name": cl.name,
                    "category_key": cl.category_key,
                    "category_id": cl.category_id,
                    "year": cl.year,
                    "quarter": cl.quarter,
                    "month": cl.month,
                    "amount_plan": _money(cl.amount_plan),
                    "amount_actual": _money(cl.amount_actual)
                    if cl.amount_actual is not None
                    else None,
                    "is_recurring": cl.is_recurring,
                }
                if locked:
                    existing = existing_costs.get(self._cost_period_key(row))
                    if not existing:
                        continue
                    row["name"] = existing.get("name") or row["name"]
                    row["amount_plan"] = _money(existing.get("amount_plan"))
                cost_rows.append(row)
            self._repo.upsert_cost_lines_batch(initiative_id, cost_rows)

        if data.metric_values:
            metric_rows = []
            for metric in data.metric_values:
                row = {
                    "metric_key": metric.metric_key,
                    "year": metric.year,
                    "quarter": metric.quarter,
                    "month": metric.month,
                    "value_base": _money(metric.value_base),
                    "value_high": _money(metric.value_high),
                    "value_actual": _money(metric.value_actual)
                    if metric.value_actual is not None
                    else None,
                }
                if locked:
                    existing = existing_metrics.get(self._metric_period_key(row))
                    if not existing:
                        continue
                    row["value_base"] = _money(existing.get("value_base"))
                    row["value_high"] = _money(existing.get("value_high"))
                metric_rows.append(row)
            self._repo.upsert_metric_values_batch(initiative_id, metric_rows)

        return self.get_financial_grid(initiative_id)

    def update_configurable_financial_grid(
        self,
        initiative_id: str,
        data: ConfigurableFinancialGridUpdate,
        user_id: str | None = None,
    ) -> ConfigurableFinancialGridResponse:
        """Upsert configurable monthly metric values and optional new lines."""
        self._ensure_tenant_initiative(initiative_id)
        locked, _ = self._financial_lock_state(initiative_id)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Financials are locked for this initiative",
            )

        if data.benefit_lines:
            self._repo.create_benefit_lines_batch(
                initiative_id,
                [
                    {
                        "metric_definition_id": line.metric_definition_id,
                        "name": line.name,
                        "description": line.description,
                        "impact_type": line.impact_type,
                        "timing": line.timing,
                        "confidence": _money(line.confidence)
                        if line.confidence is not None
                        else None,
                        "phasing": line.phasing,
                        "attributes": line.attributes,
                        "show_in_summary": line.show_in_summary,
                        "display_order": line.display_order,
                    }
                    for line in data.benefit_lines
                ],
                user_id=user_id,
            )

        if data.cost_lines:
            self._repo.upsert_cost_lines_batch(
                initiative_id,
                [
                    {
                        "name": line.name,
                        "category_key": line.category_key,
                        "category_id": line.category_id,
                        "year": line.year,
                        "quarter": line.quarter,
                        "month": line.month,
                        "amount_plan": _money(line.amount_plan),
                        "amount_actual": _money(line.amount_actual)
                        if line.amount_actual is not None
                        else None,
                        "is_recurring": line.is_recurring,
                    }
                    for line in data.cost_lines
                ],
            )

        if data.values:
            self._assert_no_formula_metric_values(data.values)
            self._repo.upsert_configurable_metric_values_batch(
                initiative_id,
                [
                    {
                        "metric_definition_id": value.metric_definition_id,
                        "scenario_id": value.scenario_id,
                        "benefit_line_id": value.benefit_line_id,
                        "year": value.year,
                        "month": value.month,
                        "value": _money(value.value),
                        "status": value.status,
                        "note": value.note,
                    }
                    for value in data.values
                ],
                user_id=user_id,
            )

        return self.get_configurable_financial_grid(initiative_id)

    def replace_financial_grid(
        self, initiative_id: str, data: FinancialGridUpdate
    ) -> FinancialGridResponse:
        """Replace every financial row for a workbook-style full import."""
        self._ensure_tenant_initiative(initiative_id)
        self._repo.delete_grid(initiative_id)
        return self.update_financial_grid(initiative_id, data)

    def export_workbook(self, initiative_id: str) -> bytes:
        """Export initiative financial entries and cost lines as an XLSX workbook."""
        entries = self._unique_entries(self._repo.get_entries(initiative_id))
        cost_lines = self._unique_cost_lines(self._repo.list_cost_lines(initiative_id))
        return build_financial_workbook(entries, cost_lines)

    def import_workbook(self, initiative_id: str, data: bytes) -> FinancialGridResponse:
        """Import an XLSX workbook into the initiative financial grid."""
        self._ensure_tenant_initiative(initiative_id)
        update = parse_financial_workbook(data)
        return self.update_financial_grid(initiative_id, update)

    # ── Cost lines ────────────────────────────────────────────────────────────

    def list_cost_lines(self, initiative_id: str) -> CostLineListResponse:
        rows = self._repo.list_cost_lines(initiative_id)
        items = [self._to_cost_line(r) for r in rows]
        return CostLineListResponse(items=items, total=len(items))

    def create_cost_line(self, initiative_id: str, data: CostLineCreate) -> CostLineItem:
        self._ensure_tenant_initiative(initiative_id)
        row = self._repo.create_cost_line(
            initiative_id,
            {
                "name": data.name,
                "category_key": data.category_key,
                "category_id": data.category_id,
                "year": data.year,
                "quarter": data.quarter,
                "month": data.month,
                "amount_plan": _money(data.amount_plan),
                "amount_actual": _money(data.amount_actual)
                if data.amount_actual is not None
                else None,
                "is_recurring": data.is_recurring,
            },
        )
        return self._to_cost_line(row)

    def update_cost_line(
        self,
        initiative_id: str,
        cost_line_id: str,
        data: CostLineUpdate,
    ) -> CostLineItem:
        self._ensure_tenant_initiative(initiative_id)
        patch: dict[str, object] = {}
        for field in (
            "name",
            "category_key",
            "category_id",
            "year",
            "quarter",
            "month",
            "is_recurring",
        ):
            val = getattr(data, field)
            if val is not None:
                patch[field] = val
        if data.amount_plan is not None:
            patch["amount_plan"] = _money(data.amount_plan)
        if data.amount_actual is not None:
            patch["amount_actual"] = _money(data.amount_actual)
        row = self._repo.update_cost_line(initiative_id, cost_line_id, patch)
        return self._to_cost_line(row)

    def delete_cost_line(self, initiative_id: str, cost_line_id: str) -> None:
        self._ensure_tenant_initiative(initiative_id)
        self._repo.delete_cost_line(initiative_id, cost_line_id)

    # -- Benefit-line validation ---------------------------------------------

    def submit_benefit_line_for_validation(
        self,
        initiative_id: str,
        benefit_line_id: str,
        data: FinancialBenefitLineValidationRequest,
        user_id: str,
    ) -> FinancialBenefitLine:
        return self._transition_benefit_line_validation(
            initiative_id,
            benefit_line_id,
            status_value="submitted",
            event_type="submit",
            data=data,
            user_id=user_id,
        )

    def validate_benefit_line(
        self,
        initiative_id: str,
        benefit_line_id: str,
        data: FinancialBenefitLineValidationRequest,
        user_id: str,
    ) -> FinancialBenefitLine:
        return self._transition_benefit_line_validation(
            initiative_id,
            benefit_line_id,
            status_value="finance_validated",
            event_type="validate",
            data=data,
            user_id=user_id,
        )

    def reject_benefit_line(
        self,
        initiative_id: str,
        benefit_line_id: str,
        data: FinancialBenefitLineValidationRequest,
        user_id: str,
    ) -> FinancialBenefitLine:
        return self._transition_benefit_line_validation(
            initiative_id,
            benefit_line_id,
            status_value="rejected",
            event_type="reject",
            data=data,
            user_id=user_id,
        )

    def update_benefit_line_handoff(
        self,
        initiative_id: str,
        benefit_line_id: str,
        data: FinancialBenefitLineHandoffUpdate,
        user_id: str,
    ) -> FinancialBenefitLine:
        self._ensure_tenant_initiative(initiative_id)
        existing = self._repo.get_benefit_line(initiative_id, benefit_line_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benefit line not found",
            )
        if data.realization_owner_id and not self._repo.tenant_user_exists(
            data.realization_owner_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Realization owner must belong to the current tenant",
            )
        patch: dict[str, object] = {}
        for field in ("realization_owner_id", "handoff_status", "risk_rating"):
            value = getattr(data, field)
            if value is not None:
                patch[field] = value
        if data.handoff_due_date is not None:
            patch["handoff_due_date"] = data.handoff_due_date.isoformat()
        if data.risk_adjustment_pct is not None:
            patch["risk_adjustment_pct"] = _money(data.risk_adjustment_pct)
        row = self._repo.update_benefit_line(initiative_id, benefit_line_id, patch, user_id)
        self._record_benefit_line_event(
            initiative_id,
            benefit_line_id,
            event_type="handoff_update",
            user_id=user_id,
            comment=data.comment,
            metadata=patch,
        )
        return self._to_benefit_line(row)

    def list_benefit_line_validation_events(
        self,
        initiative_id: str,
        benefit_line_id: str,
    ) -> list[FinancialBenefitLineValidationEvent]:
        self._ensure_tenant_initiative(initiative_id)
        if not self._repo.get_benefit_line(initiative_id, benefit_line_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benefit line not found",
            )
        return [
            self._to_benefit_line_validation_event(row)
            for row in self._repo.list_benefit_line_validation_events(
                initiative_id, benefit_line_id
            )
        ]

    # ── Tenant financial configuration ───────────────────────────────────────

    def get_configuration(self) -> FinancialConfigurationResponse:
        engine_config = self.get_engine_configuration()
        if engine_config.definitions or engine_config.cost_categories:
            if not engine_config.cost_categories:
                legacy_items = getattr(self._repo, "list_config_items", lambda: [])()
                if any(row.get("item_type") == "cost_category" for row in legacy_items):
                    groups = [
                        self._to_config_group(row)
                        for row in getattr(self._repo, "list_config_groups", lambda: [])()
                    ]
                    group_key_by_id = {group.id: group.key for group in groups if group.id}
                    items = [
                        self._to_config_item(row, group_key_by_id.get(row.get("group_id")))
                        for row in legacy_items
                    ]
                    return FinancialConfigurationResponse(groups=groups, items=items)
            return self._engine_configuration_as_legacy_response(engine_config)
        groups = [self._to_config_group(row) for row in self._repo.list_config_groups()]
        group_key_by_id = {group.id: group.key for group in groups if group.id}
        items = [
            self._to_config_item(row, group_key_by_id.get(row.get("group_id")))
            for row in self._repo.list_config_items()
        ]
        return FinancialConfigurationResponse(groups=groups, items=items)

    def get_engine_configuration(self) -> FinancialEngineConfigurationResponse:
        settings_row = getattr(self._repo, "get_reporting_settings", lambda: {})()
        return FinancialEngineConfigurationResponse(
            definitions=[
                self._to_metric_definition(row)
                for row in getattr(self._repo, "list_metric_definitions", lambda: [])()
            ],
            scenarios=[
                self._to_scenario_definition(row)
                for row in getattr(self._repo, "list_financial_scenarios", lambda: [])()
            ],
            cost_categories=[
                self._to_cost_category(row)
                for row in getattr(self._repo, "list_cost_categories", lambda: [])()
            ],
            bridge_rows=[
                self._to_bridge_row(row)
                for row in getattr(self._repo, "list_financial_bridge_rows", lambda: [])()
            ],
            attribute_definitions=[
                self._to_attribute_definition(row)
                for row in getattr(self._repo, "list_financial_attribute_definitions", lambda: [])()
            ],
            settings=FinancialReportingSettings(
                fiscal_year_start_month=settings_row.get("fiscal_year_start_month") or 1,
                reporting_currency=settings_row.get("reporting_currency") or "USD",
            ),
        )

    def update_reporting_settings(
        self,
        data: FinancialReportingSettingsUpdate,
    ) -> FinancialReportingSettings:
        patch = data.model_dump(exclude_none=True)
        if not patch:
            settings_row = self._repo.get_reporting_settings()
        else:
            settings_row = self._repo.update_reporting_settings(patch)
        return FinancialReportingSettings(
            fiscal_year_start_month=settings_row.get("fiscal_year_start_month") or 1,
            reporting_currency=settings_row.get("reporting_currency") or "USD",
        )

    def create_metric_definition(
        self,
        data: FinancialMetricDefinitionCreate,
        user_id: str | None = None,
    ) -> FinancialMetricDefinition:
        self._validate_metric_definition_payload(data.model_dump(mode="json"))
        row = self._repo.create_metric_definition(data.model_dump(mode="json"), user_id=user_id)
        return self._to_metric_definition(row)

    def update_metric_definition(
        self,
        metric_definition_id: str,
        data: FinancialMetricDefinitionUpdate,
        user_id: str | None = None,
    ) -> FinancialMetricDefinition:
        self._validate_metric_definition_update(metric_definition_id, data)
        row = self._repo.update_metric_definition(
            metric_definition_id,
            data.model_dump(mode="json", exclude_none=True),
            user_id=user_id,
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Financial metric definition not found",
            )
        return self._to_metric_definition(row)

    def create_scenario_definition(
        self,
        data: FinancialScenarioDefinitionCreate,
    ) -> FinancialScenarioDefinition:
        row = self._repo.create_financial_scenario(data.model_dump(mode="json"))
        return self._to_scenario_definition(row)

    def update_scenario_definition(
        self,
        scenario_id: str,
        data: FinancialScenarioDefinitionUpdate,
    ) -> FinancialScenarioDefinition:
        row = self._repo.update_financial_scenario(
            scenario_id,
            data.model_dump(mode="json", exclude_none=True),
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Financial scenario not found",
            )
        return self._to_scenario_definition(row)

    def create_bridge_row(self, data: FinancialBridgeRow) -> FinancialBridgeRow:
        payload = self._bridge_row_payload(data)
        payload.pop("id", None)
        row = self._repo.create_financial_bridge_row(payload)
        return self._to_bridge_row(row)

    def update_bridge_row(
        self,
        bridge_row_id: str,
        data: FinancialBridgeRow,
    ) -> FinancialBridgeRow:
        payload = self._bridge_row_payload(data)
        payload.pop("id", None)
        row = self._repo.update_financial_bridge_row(bridge_row_id, payload)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Financial bridge row not found",
            )
        return self._to_bridge_row(row)

    def create_cost_category(self, data: FinancialCostCategory) -> FinancialCostCategory:
        payload = self._cost_category_payload(data)
        payload.pop("id", None)
        row = self._repo.create_cost_category(payload)
        return self._to_cost_category(row)

    def update_cost_category(
        self,
        cost_category_id: str,
        data: FinancialCostCategory,
    ) -> FinancialCostCategory:
        payload = self._cost_category_payload(data)
        payload.pop("id", None)
        row = self._repo.update_cost_category(cost_category_id, payload)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Financial cost category not found",
            )
        return self._to_cost_category(row)

    def create_attribute_definition(
        self,
        data: FinancialAttributeDefinition,
    ) -> FinancialAttributeDefinition:
        payload = self._attribute_definition_payload(data)
        payload.pop("id", None)
        row = self._repo.create_financial_attribute_definition(payload)
        return self._to_attribute_definition(row)

    def update_attribute_definition(
        self,
        attribute_definition_id: str,
        data: FinancialAttributeDefinition,
    ) -> FinancialAttributeDefinition:
        payload = self._attribute_definition_payload(data)
        payload.pop("id", None)
        row = self._repo.update_financial_attribute_definition(attribute_definition_id, payload)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Financial attribute definition not found",
            )
        return self._to_attribute_definition(row)

    @staticmethod
    def _attribute_definition_payload(data: FinancialAttributeDefinition) -> dict:
        payload = data.model_dump(mode="json", exclude_none=True)
        payload["options"] = [
            str(item).strip() for item in payload.get("options") or [] if str(item).strip()
        ]
        return payload

    def _bridge_row_payload(self, data: FinancialBridgeRow) -> dict:
        payload = data.model_dump(mode="json", exclude_none=True)
        categories_by_id = {
            str(category.id): category
            for category in self.get_engine_configuration().cost_categories
        }
        categories_by_key = {
            category.key: category for category in self.get_engine_configuration().cost_categories
        }
        if payload.get("cost_category_ids"):
            payload["cost_category_keys"] = [
                categories_by_id[category_id].key
                for category_id in payload["cost_category_ids"]
                if category_id in categories_by_id
            ]
        elif payload.get("cost_category_keys"):
            payload["cost_category_ids"] = [
                str(categories_by_key[category_key].id)
                for category_key in payload["cost_category_keys"]
                if category_key in categories_by_key and categories_by_key[category_key].id
            ]
        return payload

    @staticmethod
    def _cost_category_payload(data: FinancialCostCategory) -> dict:
        payload = data.model_dump(mode="json", exclude_none=True)
        payload["attributes"] = payload.get("attributes") or {}
        return payload

    def get_governance_settings(self) -> FinancialGovernanceSettings:
        settings = self._repo.get_organization_settings()
        raw = settings.get("bankable_plan_governance") or {}
        if not isinstance(raw, dict):
            raw = {}
        return FinancialGovernanceSettings.model_validate(raw)

    def update_governance_settings(
        self,
        data: FinancialGovernanceSettingsUpdate,
    ) -> FinancialGovernanceSettings:
        current = self.get_governance_settings()
        patch = data.model_dump(exclude_none=True)
        next_settings = current.model_copy(update=patch)
        org_settings = self._repo.get_organization_settings()
        org_settings["bankable_plan_governance"] = next_settings.model_dump(mode="json")
        self._repo.update_organization_settings(org_settings)
        return next_settings

    def get_tenant_annual_baselines(
        self,
        baseline_year: int | None = None,
    ) -> TenantAnnualBaselineResponse:
        definitions = {row["id"]: row for row in self._repo.list_metric_definitions()}
        return TenantAnnualBaselineResponse(
            values=[
                self._to_annual_baseline_value(row, definitions)
                for row in self._repo.list_tenant_annual_baselines(baseline_year)
            ]
        )

    def update_tenant_annual_baselines(
        self,
        data: TenantAnnualBaselineUpdate,
        user_id: str | None = None,
    ) -> TenantAnnualBaselineResponse:
        valid_metric_ids = {row["id"] for row in self._repo.list_metric_definitions()}
        rows = []
        for value in data.values:
            if value.metric_definition_id not in valid_metric_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Baseline metric definition is not configured for this tenant",
                )
            rows.append(
                {
                    "metric_definition_id": value.metric_definition_id,
                    "baseline_year": value.baseline_year,
                    "value": _money(value.value),
                    "note": value.note,
                }
            )
        if rows:
            self._repo.upsert_tenant_annual_baselines(rows, user_id=user_id)
        return self.get_tenant_annual_baselines()

    def get_initiative_annual_baseline(
        self,
        initiative_id: str,
        baseline_year: int | None = None,
    ) -> InitiativeAnnualBaselineResponse:
        self._ensure_tenant_initiative(initiative_id)
        rows = self._repo.list_initiative_annual_baselines(initiative_id, baseline_year)
        locked, lock_reason = self._baseline_lock_state(initiative_id)
        response_year = baseline_year
        if response_year is None and rows:
            response_year = int(rows[0]["baseline_year"])
        definitions = {row["id"]: row for row in self._repo.list_metric_definitions()}
        return InitiativeAnnualBaselineResponse(
            initiative_id=initiative_id,
            baseline_year=response_year,
            values=[self._to_annual_baseline_value(row, definitions) for row in rows],
            locked=locked,
            lock_reason=lock_reason,
        )

    def update_initiative_annual_baseline(
        self,
        initiative_id: str,
        data: InitiativeAnnualBaselineUpdate,
        user_id: str | None = None,
    ) -> InitiativeAnnualBaselineResponse:
        self._ensure_tenant_initiative(initiative_id)
        locked, lock_reason = self._baseline_lock_state(initiative_id)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=lock_reason or "Initiative baseline is locked",
            )
        valid_metric_ids = {row["id"] for row in self._repo.list_metric_definitions()}
        settings = self.get_governance_settings()
        rows = []
        for value in data.values:
            if value.metric_definition_id not in valid_metric_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Baseline metric definition is not configured for this tenant",
                )
            rows.append(
                {
                    "metric_definition_id": value.metric_definition_id,
                    "baseline_year": data.baseline_year,
                    "value": _money(value.value),
                    "source": "initiative",
                    "lock_gate_number": settings.baseline_lock_gate_number,
                    "note": value.note,
                }
            )
        if rows:
            self._repo.upsert_initiative_annual_baselines(
                initiative_id,
                rows,
                user_id=user_id,
            )
        return self.get_initiative_annual_baseline(initiative_id, data.baseline_year)

    def update_configuration(
        self, data: FinancialConfigurationUpdate
    ) -> FinancialConfigurationResponse:
        saved_groups: dict[str, str] = {}
        active_group_keys = {group.key for group in data.groups if group.is_active}
        active_item_keys = {item.key for item in data.items if item.is_active}
        for group in data.groups:
            row = self._repo.upsert_config_group(
                {
                    "key": group.key,
                    "label": group.label,
                    "kind": group.kind,
                    "rollup_type": group.rollup_type,
                    "display_order": group.display_order,
                    "is_system": group.is_system,
                    "is_active": group.is_active,
                }
            )
            saved_groups[row["key"]] = row["id"]

        existing_group_rows = self._repo.list_config_groups()
        existing_groups = {row["key"]: row["id"] for row in existing_group_rows}
        existing_group_ids = {row["id"] for row in existing_group_rows}
        saved_groups.update(existing_groups)
        for item in data.items:
            if item.group_id and item.group_id not in existing_group_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Financial configuration group not found",
                )
            group_id = saved_groups.get(item.group_key or "") or item.group_id
            if not group_id:
                continue
            self._repo.upsert_config_item(
                {
                    "group_id": group_id,
                    "key": item.key,
                    "label": item.label,
                    "item_type": item.item_type,
                    "system_metric_key": item.system_metric_key,
                    "rollup_type": item.rollup_type,
                    "display_order": item.display_order,
                    "is_system": item.is_system,
                    "is_active": item.is_active,
                }
            )
        self._repo.deactivate_config_groups_except(active_group_keys)
        self._repo.deactivate_config_items_except(active_item_keys)
        return self.get_configuration()

    def delete_cost_category(self, data: FinancialCategoryDeleteRequest) -> dict[str, object]:
        if data.category_key == data.replacement_key:
            return {"reassigned": 0, "category_key": data.category_key}
        reassigned = self._repo.reassign_cost_category(data.category_key, data.replacement_key)
        return {
            "category_key": data.category_key,
            "replacement_key": data.replacement_key,
            "reassigned": reassigned,
        }

    def deactivate_metric(self, data: FinancialMetricDeactivateRequest) -> dict[str, object]:
        self._repo.deactivate_metric(data.metric_key)
        return {"metric_key": data.metric_key, "is_active": False}

    def get_initiative_selections(
        self, initiative_id: str
    ) -> InitiativeFinancialSelectionsResponse:
        self._ensure_tenant_initiative(initiative_id)
        entries = self._repo.get_entries(initiative_id)
        costs = self._repo.list_cost_lines(initiative_id)
        metric_values = self._repo.list_metric_values(initiative_id)
        locked, lock_reason = self._financial_lock_state(initiative_id)
        config = self.get_configuration()
        return InitiativeFinancialSelectionsResponse(
            available=config,
            selected=self._resolve_selections(initiative_id, entries, costs, metric_values, config),
            locked=locked,
            lock_reason=lock_reason,
        )

    def update_initiative_selections(
        self,
        initiative_id: str,
        selections: InitiativeFinancialSelections,
    ) -> InitiativeFinancialSelectionsResponse:
        self._ensure_tenant_initiative(initiative_id)
        self._assert_financials_editable(initiative_id)
        config = self.get_configuration()
        valid_metric_keys, valid_cost_keys = self._active_selection_keys(config)
        metric_keys = [key for key in selections.metric_keys if key in valid_metric_keys]
        cost_keys = [key for key in selections.cost_category_keys if key in valid_cost_keys]
        engine = self.get_engine_configuration()
        metric_ids_by_key = {
            definition.key: str(definition.id) for definition in engine.definitions
        }
        category_ids_by_key = {
            category.key: str(category.id) for category in engine.cost_categories if category.id
        }
        metric_definition_ids = [
            metric_ids_by_key[key] for key in metric_keys if key in metric_ids_by_key
        ]
        cost_category_ids = [
            category_ids_by_key[key] for key in cost_keys if key in category_ids_by_key
        ]
        getattr(self._repo, "replace_financial_scope", lambda *args, **kwargs: None)(
            initiative_id,
            metric_definition_ids,
            cost_category_ids,
            sorted(metric_ids_by_key.values()),
            sorted(category_ids_by_key.values()),
        )
        self._repo.replace_financial_selections(
            initiative_id,
            metric_keys,
            cost_keys,
            sorted(valid_metric_keys),
            sorted(valid_cost_keys),
        )
        return self.get_initiative_selections(initiative_id)

    def list_forecasts(self, initiative_id: str) -> FinancialForecastResponse:
        self._ensure_tenant_initiative(initiative_id)
        return FinancialForecastResponse(
            initiative_id=initiative_id,
            items=[self._to_forecast_row(row) for row in self._repo.list_forecasts(initiative_id)],
        )

    def update_forecasts(
        self,
        initiative_id: str,
        forecasts: list[FinancialForecastUpdate],
    ) -> FinancialForecastResponse:
        self._ensure_tenant_initiative(initiative_id)
        rows = [
            {
                "line_type": item.line_type,
                "line_key": item.line_key,
                "year": item.year,
                "quarter": item.quarter,
                "month": item.month,
                "amount_forecast": _money(item.amount_forecast),
                "notes": item.notes,
            }
            for item in forecasts
        ]
        if rows:
            self._repo.upsert_forecasts_batch(initiative_id, rows)
        return self.list_forecasts(initiative_id)

    def get_current_bankable_plan(self, initiative_id: str) -> BankablePlanVersion | None:
        self._ensure_tenant_initiative(initiative_id)
        row = self._repo.get_latest_bankable_plan(initiative_id)
        return self._to_bankable_plan_version(row) if row else None

    def list_bankable_plan_history(self, initiative_id: str) -> list[BankablePlanVersion]:
        self._ensure_tenant_initiative(initiative_id)
        return [
            self._to_bankable_plan_version(row)
            for row in self._repo.list_bankable_plans(initiative_id)
        ]

    def get_bankable_plan_history(self, initiative_id: str) -> BankablePlanResponse:
        history = self.list_bankable_plan_history(initiative_id)
        return BankablePlanResponse(current=history[-1] if history else None, history=history)

    # ── Benefit realization ledger ───────────────────────────────────────────

    def list_benefit_ledger_entries(self, initiative_id: str) -> list[BenefitLedgerEntry]:
        self._ensure_tenant_initiative(initiative_id)
        return [
            self._to_benefit_ledger_entry(row)
            for row in self._repo.list_benefit_ledger_entries(initiative_id)
        ]

    def create_benefit_ledger_entry(
        self,
        initiative_id: str,
        data: BenefitLedgerEntryCreate,
    ) -> BenefitLedgerEntry:
        self._ensure_tenant_initiative(initiative_id)
        try:
            payload = self._benefit_entry_payload(initiative_id, data)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        row = self._repo.create_benefit_ledger_entry(
            initiative_id,
            payload,
        )
        return self._to_benefit_ledger_entry(row)

    def import_benefit_ledger_csv(self, data: bytes) -> BenefitLedgerImportResult:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Benefit ledger import must be a UTF-8 CSV file.",
            ) from exc

        reader = csv.DictReader(StringIO(text))
        required = {
            "initiative_code",
            "period_granularity",
            "period_start",
            "period_end",
            "actual_amount",
            "description",
        }
        headers = {str(field or "").strip() for field in reader.fieldnames or []}
        missing = sorted(required - headers)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Benefit ledger CSV is missing required column(s): {', '.join(missing)}",
            )

        initiatives = self._repo.initiatives_by_code()
        created = 0
        updated = 0
        errors: list[BenefitLedgerImportError] = []
        for index, row in enumerate(reader, start=2):
            initiative_code = str(row.get("initiative_code") or "").strip().upper()
            try:
                initiative = initiatives.get(initiative_code)
                if not initiative:
                    raise ValueError(f"Initiative code '{initiative_code}' was not found.")
                payload = self._benefit_import_payload(str(initiative["id"]), row)
                _, was_created = self._repo.upsert_benefit_ledger_entry(
                    str(initiative["id"]),
                    payload,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except ValueError as exc:
                errors.append(
                    BenefitLedgerImportError(
                        row=index,
                        initiative_code=initiative_code or None,
                        message=str(exc),
                    )
                )
        return BenefitLedgerImportResult(created=created, updated=updated, errors=errors)

    def update_benefit_ledger_entry(
        self,
        initiative_id: str,
        entry_id: str,
        data: BenefitLedgerEntryUpdate,
    ) -> BenefitLedgerEntry:
        self._ensure_tenant_initiative(initiative_id)
        patch: dict[str, object] = {}
        for field in ("period_granularity", "period_start", "period_end", "description"):
            val = getattr(data, field)
            if val is not None:
                patch[field] = val.isoformat() if isinstance(val, date) else val
        if data.bankable_plan_amount is not None:
            patch["bankable_plan_amount"] = _money(data.bankable_plan_amount)
        elif any(field in patch for field in ("period_granularity", "period_start", "period_end")):
            current = self._repo.list_benefit_ledger_entries(initiative_id)
            existing = next((row for row in current if row.get("id") == entry_id), None)
            if existing:
                granularity = str(patch.get("period_granularity") or existing["period_granularity"])
                period_start = self._as_date(patch.get("period_start") or existing["period_start"])
                period_end = self._as_date(
                    patch.get("period_end") or existing.get("period_end") or period_start
                )
                try:
                    patch["bankable_plan_amount"] = _money(
                        self._derived_bankable_plan_amount(
                            initiative_id,
                            granularity,  # type: ignore[arg-type]
                            period_start,
                            period_end,
                        )
                    )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(exc),
                    ) from exc
        if data.actual_amount is not None:
            patch["actual_amount"] = _money(data.actual_amount)
        row = self._repo.update_benefit_ledger_entry(initiative_id, entry_id, patch)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Benefit ledger entry not found"
            )
        return self._to_benefit_ledger_entry(row)

    def delete_benefit_ledger_entry(self, initiative_id: str, entry_id: str) -> None:
        self._ensure_tenant_initiative(initiative_id)
        self._repo.delete_benefit_ledger_entry(initiative_id, entry_id)

    def get_benefit_ledger_summary(
        self,
        initiative_id: str,
        granularity: BenefitLedgerGranularity,
    ) -> BenefitLedgerSummaryResponse:
        self._ensure_tenant_initiative(initiative_id)
        rows = self._repo.list_benefit_ledger_entries(initiative_id)
        locked_plan = self.get_current_bankable_plan(initiative_id)
        if not rows:
            return BenefitLedgerSummaryResponse(
                initiative_id=initiative_id,
                granularity=granularity,
                locked_bankable_plan_version=locked_plan.version if locked_plan else None,
                bankable_plan_amount="0.0000",
                actual_amount="0.0000",
                variance="0.0000",
            )

        periods = self._benefit_ledger_period_summaries(rows, granularity)
        total_plan = sum((_dec(period.bankable_plan_amount) for period in periods), Decimal("0"))
        total_actual = sum((_dec(period.actual_amount) for period in periods), Decimal("0"))
        return BenefitLedgerSummaryResponse(
            initiative_id=initiative_id,
            granularity=granularity,
            locked_bankable_plan_version=locked_plan.version if locked_plan else None,
            periods=periods,
            bankable_plan_amount=_money(total_plan),
            actual_amount=_money(total_actual),
            variance=_money(total_actual - total_plan),
        )

    def get_benefit_ledger_rollup_summary(
        self,
        granularity: BenefitLedgerGranularity,
        workstream_id: str | None = None,
    ) -> BenefitLedgerRollupSummaryResponse:
        initiatives = [
            row
            for row in self._repo.get_portfolio_initiatives()
            if not workstream_id or row.get("workstream_id") == workstream_id
        ]
        initiative_ids = [str(row["id"]) for row in initiatives]
        ledger_rows = self._repo.list_benefit_ledger_entries_for_initiatives(initiative_ids)
        plans = self._repo.list_latest_bankable_plans_for_initiatives(initiative_ids)
        plan_by_initiative = {str(row["initiative_id"]): row for row in plans}

        ledger_by_initiative: dict[str, list[dict]] = {}
        for row in ledger_rows:
            ledger_by_initiative.setdefault(str(row["initiative_id"]), []).append(row)

        initiative_rollups: list[BenefitLedgerInitiativeRollup] = []
        workstream_groups: dict[str, dict[str, object]] = {}
        total_plan = Decimal("0")
        total_actual = Decimal("0")

        for initiative in initiatives:
            initiative_id = str(initiative["id"])
            ws = initiative.get("workstreams") or {}
            ws_id = str(initiative.get("workstream_id") or "unassigned")
            ws_name = ws.get("name") or "Unassigned"
            rows = ledger_by_initiative.get(initiative_id, [])
            plan_row = plan_by_initiative.get(initiative_id)
            ledger_plan = sum((_dec(row.get("bankable_plan_amount")) for row in rows), Decimal("0"))
            actual = sum((_dec(row.get("actual_amount")) for row in rows), Decimal("0"))
            fallback_plan = self._locked_plan_value(plan_row)
            plan = ledger_plan if rows else fallback_plan
            total_plan += plan
            total_actual += actual

            group = workstream_groups.setdefault(
                ws_id,
                {
                    "workstream_id": None if ws_id == "unassigned" else ws_id,
                    "workstream_name": ws_name,
                    "initiative_count": 0,
                    "locked_initiative_count": 0,
                    "bankable_plan_amount": Decimal("0"),
                    "actual_amount": Decimal("0"),
                },
            )
            group["initiative_count"] = int(group["initiative_count"]) + 1
            if plan_row:
                group["locked_initiative_count"] = int(group["locked_initiative_count"]) + 1
            group["bankable_plan_amount"] = _dec(group["bankable_plan_amount"]) + plan
            group["actual_amount"] = _dec(group["actual_amount"]) + actual

            initiative_rollups.append(
                BenefitLedgerInitiativeRollup(
                    initiative_id=initiative_id,
                    initiative_code=initiative.get("initiative_code"),
                    name=initiative.get("name") or "Initiative",
                    stage=initiative.get("stage"),
                    workstream_id=None if ws_id == "unassigned" else ws_id,
                    workstream_name=ws_name,
                    locked_bankable_plan_version=int(plan_row["version"]) if plan_row else None,
                    bankable_plan_amount=_money(plan),
                    actual_amount=_money(actual),
                    variance=_money(actual - plan),
                )
            )

        workstream_rollups = []
        for group in workstream_groups.values():
            plan = _dec(group["bankable_plan_amount"])
            actual = _dec(group["actual_amount"])
            workstream_rollups.append(
                BenefitLedgerWorkstreamRollup(
                    workstream_id=group["workstream_id"],  # type: ignore[arg-type]
                    workstream_name=str(group["workstream_name"]),
                    initiative_count=int(group["initiative_count"]),
                    locked_initiative_count=int(group["locked_initiative_count"]),
                    bankable_plan_amount=_money(plan),
                    actual_amount=_money(actual),
                    variance=_money(actual - plan),
                )
            )

        scope_name = "Portfolio"
        if workstream_id:
            scope_name = next(
                (
                    str((row.get("workstreams") or {}).get("name") or "Workstream")
                    for row in initiatives
                    if row.get("workstream_id") == workstream_id
                ),
                "Workstream",
            )

        return BenefitLedgerRollupSummaryResponse(
            scope="workstream" if workstream_id else "portfolio",
            scope_id=workstream_id,
            scope_name=scope_name,
            granularity=granularity,
            periods=self._benefit_ledger_period_summaries(ledger_rows, granularity),
            bankable_plan_amount=_money(total_plan),
            actual_amount=_money(total_actual),
            variance=_money(total_actual - total_plan),
            workstreams=sorted(workstream_rollups, key=lambda item: item.workstream_name),
            initiatives=sorted(
                initiative_rollups,
                key=lambda item: (item.workstream_name or "", item.initiative_code or item.name),
            ),
        )

    def get_workstream_target_preview(
        self,
        workstream_id: str,
        lock_date: date,
    ) -> WorkstreamTargetPreviewResponse:
        snapshot = self._build_workstream_target_snapshot(workstream_id, lock_date)
        latest = self._repo.get_latest_workstream_target_lock(workstream_id)
        return WorkstreamTargetPreviewResponse(
            **snapshot.model_dump(),
            latest_locked_version=int(latest["version"]) if latest else None,
        )

    def get_workstream_target_history(self, workstream_id: str) -> WorkstreamTargetLockResponse:
        rows = self._repo.list_workstream_target_locks(workstream_id)
        history = [self._to_workstream_target_lock_version(row) for row in rows]
        return WorkstreamTargetLockResponse(
            current=history[-1] if history else None,
            history=history,
        )

    def lock_workstream_target(
        self,
        workstream_id: str,
        data: WorkstreamTargetLockRequest,
        locked_by_id: str,
    ) -> WorkstreamTargetLockVersion:
        snapshot = self._build_workstream_target_snapshot(workstream_id, data.lock_date)
        latest = self._repo.get_latest_workstream_target_lock(workstream_id)
        version = int(latest["version"]) + 1 if latest else 1
        row = self._repo.create_workstream_target_lock(
            {
                "workstream_id": workstream_id,
                "version": version,
                "lock_date": data.lock_date.isoformat(),
                "locked_at": datetime.now(UTC).isoformat(),
                "locked_by_id": locked_by_id,
                "lock_cadence": snapshot.settings.workstream_lock_cadence,
                "cutoff_rule": snapshot.settings.initiative_inclusion_cutoff,
                "valuation_method": snapshot.settings.valuation_method,
                "locked_value_basis": snapshot.settings.locked_value_basis,
                "included_initiative_ids": [item.initiative_id for item in snapshot.included],
                "excluded_initiative_ids": [item.initiative_id for item in snapshot.excluded],
                "locked_run_rate_value": snapshot.locked_run_rate_value,
                "plan_total": snapshot.plan_total,
                "actual_total": snapshot.actual_total,
                "variance": snapshot.variance,
                "snapshot": snapshot.model_dump(mode="json"),
            }
        )
        return self._to_workstream_target_lock_version(row)

    def lock_bankable_plan_from_approval(
        self,
        initiative_id: str,
        submission_id: str,
        locked_by_id: str,
        locked_reason: str | None = None,
    ) -> BankablePlanVersion:
        self._ensure_tenant_initiative(initiative_id)
        latest = self._repo.get_latest_bankable_plan(initiative_id)
        if (
            latest
            and latest.get("trigger_type") == "approval"
            and latest.get("trigger_submission_id") == submission_id
        ):
            return self._to_bankable_plan_version(latest)

        snapshot = self._build_bankable_plan_snapshot(initiative_id)
        version = int(latest["version"]) + 1 if latest else 1
        row = self._repo.create_bankable_plan(
            {
                "initiative_id": initiative_id,
                "version": version,
                "trigger_type": "approval",
                "trigger_submission_id": submission_id,
                "locked_by_id": locked_by_id,
                "locked_at": datetime.now(UTC).isoformat(),
                "locked_reason": locked_reason,
                "snapshot": snapshot.model_dump(mode="json"),
            }
        )
        return self._to_bankable_plan_version(row)

    def rebaseline_bankable_plan(
        self,
        initiative_id: str,
        locked_by_id: str,
        reason: str | None = None,
    ) -> BankablePlanVersion:
        self._ensure_tenant_initiative(initiative_id)
        latest = self._repo.get_latest_bankable_plan(initiative_id)
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No bankable plan exists for this initiative.",
            )

        snapshot = self._build_bankable_plan_snapshot(initiative_id)
        row = self._repo.create_bankable_plan(
            {
                "initiative_id": initiative_id,
                "version": int(latest["version"]) + 1,
                "trigger_type": "rebaseline",
                "trigger_submission_id": latest.get("trigger_submission_id"),
                "locked_by_id": locked_by_id,
                "locked_at": datetime.now(UTC).isoformat(),
                "locked_reason": reason or latest.get("locked_reason"),
                "snapshot": snapshot.model_dump(mode="json"),
            }
        )
        return self._to_bankable_plan_version(row)

    def get_bankable_plan_snapshot(self, initiative_id: str) -> BankablePlanSnapshot:
        self._ensure_tenant_initiative(initiative_id)
        return self._build_bankable_plan_snapshot(initiative_id)

    def _build_bankable_plan_snapshot(self, initiative_id: str) -> BankablePlanSnapshot:
        entries = self._repo.get_entries(initiative_id)
        costs = self._repo.list_cost_lines(initiative_id)
        baseline = self.get_initiative_annual_baseline(initiative_id)
        clean_values = self._repo.list_configurable_metric_values(initiative_id)
        if clean_values:
            values = self._values_with_formula_metrics(
                clean_values,
                self._repo.list_initiative_annual_baselines(initiative_id),
            )
            summary = self._compute_clean_summary(values, costs)
            return BankablePlanSnapshot(
                entries=[],
                cost_lines=[self._to_cost_line(row) for row in costs],
                metric_values=[],
                configurable_values=[self._to_configurable_metric_value(row) for row in values],
                baseline=baseline,
                selections=InitiativeFinancialSelections(),
                financial_mode=FinancialModeDescriptor(
                    key="multi_scenario",
                    label="Configurable metric engine",
                    scenarios=["baseline", "plan_base", "plan_high", "actual"],
                ),
                summary=summary,
            )
        metric_values = self._repo.list_metric_values(initiative_id)
        config = self.get_configuration()
        selections = self._resolve_selections(initiative_id, entries, costs, metric_values, config)
        scoped_rows, scoped_costs = self._apply_financial_scope(entries, costs, selections)
        scoped_metric_values = self._scope_metric_values(metric_values, selections)
        summary = self._compute_summary(
            scoped_rows,
            initiative_id,
            scoped_costs,
            scoped_metric_values,
            config,
        )
        return BankablePlanSnapshot(
            entries=[self._to_entry_row(row) for row in entries],
            cost_lines=[self._to_cost_line(row) for row in costs],
            metric_values=[self._to_metric_value_row(row) for row in metric_values],
            configurable_values=[],
            baseline=baseline,
            selections=selections,
            financial_mode=self._financial_mode_descriptor(
                initiative_id,
                entries,
                costs,
                metric_values,
                config=config,
            ),
            summary=summary,
        )

    @staticmethod
    def _to_bankable_plan_version(row: dict) -> BankablePlanVersion:  # type: ignore[type-arg]
        return BankablePlanVersion(
            id=row["id"],
            initiative_id=row["initiative_id"],
            version=row["version"],
            trigger_type=row["trigger_type"],
            trigger_submission_id=row.get("trigger_submission_id"),
            locked_by_id=row.get("locked_by_id"),
            locked_at=row["locked_at"],
            locked_reason=row.get("locked_reason"),
            snapshot=BankablePlanSnapshot.model_validate(row["snapshot"]),
        )

    @staticmethod
    def _locked_plan_value(row: dict | None) -> Decimal:  # type: ignore[type-arg]
        if not row:
            return Decimal("0")
        snapshot = row.get("snapshot") or {}
        if isinstance(snapshot, BankablePlanSnapshot):
            return _dec(snapshot.summary.net_value_plan)
        summary = snapshot.get("summary") if isinstance(snapshot, dict) else {}
        if isinstance(summary, dict):
            return _dec(summary.get("net_value_plan"))
        return Decimal("0")

    @staticmethod
    def _as_date(value: object) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @staticmethod
    def _period_key(row: dict) -> tuple[object, object, object]:  # type: ignore[type-arg]
        return (row.get("year"), row.get("quarter"), row.get("month"))

    @staticmethod
    def _cost_period_key(row: dict) -> tuple[object, object, object, object, object]:  # type: ignore[type-arg]
        return (
            row.get("category_key", "other"),
            row.get("year"),
            row.get("quarter"),
            row.get("month"),
            row.get("is_recurring"),
        )

    @staticmethod
    def _metric_period_key(row: dict) -> tuple[object, object, object, object]:  # type: ignore[type-arg]
        return (
            row.get("metric_key"),
            row.get("year"),
            row.get("quarter"),
            row.get("month"),
        )

    def _benefit_entry_payload(
        self,
        initiative_id: str,
        data: BenefitLedgerEntryCreate,
    ) -> dict[str, object]:
        period_end = data.period_end or data.period_start
        bankable_plan_amount = data.bankable_plan_amount
        if bankable_plan_amount is None:
            bankable_plan_amount = self._derived_bankable_plan_amount(
                initiative_id,
                data.period_granularity,
                data.period_start,
                period_end,
            )
        return {
            "period_granularity": data.period_granularity,
            "period_start": data.period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "bankable_plan_amount": _money(bankable_plan_amount),
            "actual_amount": _money(data.actual_amount),
            "description": data.description,
        }

    def _benefit_import_payload(
        self,
        initiative_id: str,
        row: dict[str, str | None],
    ) -> dict[str, object]:
        granularity = str(row.get("period_granularity") or "").strip().lower()
        if granularity not in {"weekly", "monthly", "yearly"}:
            raise ValueError("period_granularity must be weekly, monthly, or yearly.")
        period_start = self._parse_import_date(row.get("period_start"), "period_start")
        period_end = self._parse_import_date(row.get("period_end"), "period_end")
        if period_end < period_start:
            raise ValueError("period_end must be on or after period_start.")
        actual_amount = self._parse_import_decimal(row.get("actual_amount"), "actual_amount")
        return {
            "period_granularity": granularity,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "bankable_plan_amount": _money(
                self._derived_bankable_plan_amount(
                    initiative_id,
                    granularity,  # type: ignore[arg-type]
                    period_start,
                    period_end,
                )
            ),
            "actual_amount": _money(actual_amount),
            "description": (row.get("description") or "").strip() or None,
        }

    def _derived_bankable_plan_amount(
        self,
        initiative_id: str,
        granularity: BenefitLedgerGranularity,
        period_start: date,
        period_end: date,
    ) -> Decimal:
        plan = self.get_current_bankable_plan(initiative_id) if initiative_id else None
        if not plan:
            raise ValueError(
                "A locked bankable plan is required before ledger rows can be created."
            )
        period_plan = self._bankable_plan_amount_for_period(
            plan,
            granularity,
            period_start,
            period_end,
        )
        if period_plan is not None:
            return period_plan
        locked_total = _dec(plan.snapshot.summary.net_value_plan)
        if granularity == "yearly":
            return locked_total
        if granularity == "monthly":
            return locked_total / Decimal("12")
        days = Decimal(str(max((period_end - period_start).days + 1, 1)))
        return locked_total * days / Decimal("365")

    def _bankable_plan_amount_for_period(
        self,
        plan: BankablePlanVersion,
        granularity: BenefitLedgerGranularity,
        period_start: date,
        period_end: date,
    ) -> Decimal | None:
        snapshot = plan.snapshot
        values = [row.model_dump(mode="json") for row in snapshot.configurable_values]
        if values:
            values = self._values_with_formula_metrics(values)
            costs = [row.model_dump(mode="json") for row in snapshot.cost_lines]
            amount = self._period_net_value_from_clean_snapshot(
                values,
                costs,
                granularity,
                period_start,
            )
            return self._prorate_weekly_month_amount(amount, granularity, period_start, period_end)
        if snapshot.entries:
            entries = [row.model_dump(mode="json") for row in snapshot.entries]
            costs = [row.model_dump(mode="json") for row in snapshot.cost_lines]
            amount = self._period_net_value_from_legacy_snapshot(
                entries,
                costs,
                granularity,
                period_start,
            )
            return self._prorate_weekly_month_amount(amount, granularity, period_start, period_end)
        return None

    @staticmethod
    def _prorate_weekly_month_amount(
        amount: Decimal | None,
        granularity: BenefitLedgerGranularity,
        period_start: date,
        period_end: date,
    ) -> Decimal | None:
        if amount is None or granularity != "weekly":
            return amount
        days_in_period = Decimal(str(max((period_end - period_start).days + 1, 1)))
        days_in_month = Decimal(str(monthrange(period_start.year, period_start.month)[1]))
        return amount * days_in_period / days_in_month

    def _period_net_value_from_clean_snapshot(
        self,
        values: list[dict],  # type: ignore[type-arg]
        costs: list[dict],  # type: ignore[type-arg]
        granularity: BenefitLedgerGranularity,
        period_start: date,
    ) -> Decimal | None:
        period_values = [
            row for row in values if self._ledger_row_matches_period(row, granularity, period_start)
        ]
        period_costs = [
            row for row in costs if self._ledger_row_matches_period(row, granularity, period_start)
        ]
        if not period_values and not period_costs:
            return None
        base = self._clean_value_case(period_values, "plan_base")
        costs_total = self._clean_cost_totals(period_costs, actual=False)
        return _dec(base["benefits_total"]) - _dec(costs_total["recurring"])

    def _period_net_value_from_legacy_snapshot(
        self,
        entries: list[dict],  # type: ignore[type-arg]
        costs: list[dict],  # type: ignore[type-arg]
        granularity: BenefitLedgerGranularity,
        period_start: date,
    ) -> Decimal | None:
        period_entries = [
            row
            for row in entries
            if self._ledger_row_matches_period(row, granularity, period_start)
        ]
        period_costs = [
            row for row in costs if self._ledger_row_matches_period(row, granularity, period_start)
        ]
        if not period_entries and not period_costs:
            return None
        benefits = sum(
            (_dec(row.get("gm_uplift_base")) for row in period_entries),
            Decimal("0"),
        )
        recurring_costs = sum(
            (_dec(row.get("amount_plan")) for row in period_costs if row.get("is_recurring")),
            Decimal("0"),
        )
        return benefits - recurring_costs

    @staticmethod
    def _ledger_row_matches_period(
        row: dict,  # type: ignore[type-arg]
        granularity: BenefitLedgerGranularity,
        period_start: date,
    ) -> bool:
        year = int(row.get("year") or 0)
        if year != period_start.year:
            return False
        month = row.get("month")
        if granularity == "monthly":
            return int(month or 0) == period_start.month
        if granularity == "weekly":
            if not month:
                return False
            return int(month) == period_start.month
        return True

    @staticmethod
    def _parse_import_date(value: object, field: str) -> date:
        try:
            return date.fromisoformat(str(value or "").strip())
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO date in YYYY-MM-DD format.") from exc

    @staticmethod
    def _parse_import_decimal(value: object, field: str) -> Decimal:
        try:
            result = Decimal(str(value or "").strip())
        except Exception as exc:
            raise ValueError(f"{field} must be a decimal number.") from exc
        if not result.is_finite():
            raise ValueError(f"{field} must be a finite decimal number.")
        return result

    @staticmethod
    def _to_benefit_ledger_entry(row: dict) -> BenefitLedgerEntry:  # type: ignore[type-arg]
        bankable_plan_amount = _dec(row.get("bankable_plan_amount"))
        actual_amount = _dec(row.get("actual_amount"))
        variance = actual_amount - bankable_plan_amount
        return BenefitLedgerEntry(
            id=row["id"],
            initiative_id=row["initiative_id"],
            period_granularity=row["period_granularity"],
            period_start=FinancialService._as_date(row["period_start"]),
            period_end=FinancialService._as_date(row.get("period_end") or row["period_start"]),
            bankable_plan_amount=_money(bankable_plan_amount),
            actual_amount=_money(actual_amount),
            variance=_money(variance),
            description=row.get("description"),
            created_at=str(row.get("created_at") or ""),
            updated_at=str(row.get("updated_at") or ""),
        )

    @staticmethod
    def _to_forecast_row(row: dict) -> FinancialForecastRow:  # type: ignore[type-arg]
        return FinancialForecastRow(
            id=row.get("id"),
            initiative_id=row["initiative_id"],
            line_type=row["line_type"],
            line_key=row["line_key"],
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            amount_forecast=_money(row.get("amount_forecast")),
            notes=row.get("notes"),
        )

    def _build_workstream_target_snapshot(
        self,
        workstream_id: str,
        lock_date: date,
    ) -> WorkstreamTargetSnapshot:
        settings = self.get_governance_settings()
        workstream = next(
            (row for row in self._repo.list_workstreams() if row["id"] == workstream_id),
            None,
        )
        if not workstream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workstream not found",
            )

        initiatives = self._repo.list_workstream_initiatives(workstream_id)
        initiative_ids = [row["id"] for row in initiatives]
        approvals = self._repo.list_approved_gate_submissions(
            initiative_ids,
            settings.initiative_plan_lock_gate_number,
            lock_date,
        )
        approved_at_by_initiative: dict[str, str] = {}
        for row in approvals:
            decided_at = row.get("decided_at")
            if decided_at:
                approved_at_by_initiative[row["initiative_id"]] = str(decided_at)

        included: list[WorkstreamTargetInitiative] = []
        excluded: list[WorkstreamTargetInitiative] = []
        for initiative in initiatives:
            item = self._workstream_target_initiative(
                initiative,
                approved_at_by_initiative.get(initiative["id"]),
            )
            if item.approved_at:
                included.append(item)
            else:
                excluded.append(item)

        plan_total = sum((_dec(item.net_run_rate_value) for item in included), Decimal("0"))
        actual_total = sum((_dec(item.actual_value) for item in included), Decimal("0"))
        return WorkstreamTargetSnapshot(
            workstream_id=workstream_id,
            workstream_name=workstream.get("name"),
            lock_date=lock_date,
            settings=settings,
            included=included,
            excluded=excluded,
            locked_run_rate_value=_money(plan_total),
            plan_total=_money(plan_total),
            actual_total=_money(actual_total),
            variance=_money(actual_total - plan_total),
        )

    def _workstream_target_initiative(
        self,
        initiative: dict,  # type: ignore[type-arg]
        approved_at: str | None,
    ) -> WorkstreamTargetInitiative:
        bankable_plan = self.get_current_bankable_plan(initiative["id"])
        if bankable_plan:
            summary = bankable_plan.snapshot.summary
            value_source = "bankable_plan"
            version = bankable_plan.version
        else:
            summary = self.get_financial_summary(initiative["id"])
            value_source = "current_financials_preview"
            version = None
        return WorkstreamTargetInitiative(
            initiative_id=initiative["id"],
            initiative_code=initiative.get("initiative_code"),
            name=initiative.get("name") or initiative["id"],
            stage=initiative.get("stage"),
            approved_at=approved_at,
            bankable_plan_version=version,
            value_source=value_source,
            net_run_rate_value=_money(summary.net_value_plan),
            actual_value=_money(summary.net_value_actual),
        )

    @staticmethod
    def _to_workstream_target_lock_version(row: dict) -> WorkstreamTargetLockVersion:  # type: ignore[type-arg]
        return WorkstreamTargetLockVersion(
            id=row["id"],
            workstream_id=row["workstream_id"],
            version=row["version"],
            lock_date=FinancialService._as_date(row["lock_date"]),
            locked_at=str(row.get("locked_at") or ""),
            locked_by_id=row.get("locked_by_id"),
            lock_cadence=row.get("lock_cadence") or "one_off",
            cutoff_rule=row.get("cutoff_rule") or "approved_at_lte_lock_date",
            valuation_method=row.get("valuation_method") or "run_rate",
            locked_value_basis=row.get("locked_value_basis") or "net_run_rate",
            included_initiative_ids=[
                str(item) for item in row.get("included_initiative_ids") or []
            ],
            excluded_initiative_ids=[
                str(item) for item in row.get("excluded_initiative_ids") or []
            ],
            locked_run_rate_value=_money(row.get("locked_run_rate_value")),
            plan_total=_money(row.get("plan_total")),
            actual_total=_money(row.get("actual_total")),
            variance=_money(row.get("variance")),
            snapshot=WorkstreamTargetSnapshot.model_validate(row["snapshot"]),
        )

    def _benefit_ledger_period_summaries(
        self,
        rows: list[dict],  # type: ignore[type-arg]
        granularity: BenefitLedgerGranularity,
    ) -> list[BenefitLedgerPeriodSummary]:
        grouped: dict[tuple[int, int | None, int | None], dict[str, object]] = {}
        for row in rows:
            period_start = self._as_date(row["period_start"])
            key = self._benefit_period_key(period_start, granularity)
            bucket = grouped.setdefault(
                key,
                {
                    "bankable_plan_amount": Decimal("0"),
                    "actual_amount": Decimal("0"),
                    "year": key[0],
                    "week": key[1],
                    "month": key[2],
                    "period_start": period_start,
                    "period_end": self._as_date(row.get("period_end") or row["period_start"]),
                },
            )
            bucket["bankable_plan_amount"] = _dec(bucket["bankable_plan_amount"]) + _dec(
                row.get("bankable_plan_amount")
            )
            bucket["actual_amount"] = _dec(bucket["actual_amount"]) + _dec(row.get("actual_amount"))
            row_end = self._as_date(row.get("period_end") or row["period_start"])
            bucket["period_start"] = min(bucket["period_start"], period_start)  # type: ignore[type-var]
            bucket["period_end"] = max(bucket["period_end"], row_end)  # type: ignore[type-var]

        periods: list[BenefitLedgerPeriodSummary] = []
        for year, week, month in sorted(
            grouped, key=lambda item: self._benefit_period_sort(item, granularity)
        ):
            bucket = grouped[(year, week, month)]
            bankable = _dec(bucket["bankable_plan_amount"])
            actual = _dec(bucket["actual_amount"])
            periods.append(
                BenefitLedgerPeriodSummary(
                    period=self._benefit_period_label(year, week, month, granularity),
                    year=year,
                    week=week,
                    month=month,
                    period_start=bucket["period_start"],  # type: ignore[arg-type]
                    period_end=bucket["period_end"],  # type: ignore[arg-type]
                    period_granularity=granularity,
                    bankable_plan_amount=_money(bankable),
                    actual_amount=_money(actual),
                    variance=_money(actual - bankable),
                )
            )
        return periods

    @staticmethod
    def _benefit_period_key(
        period_start: date,
        granularity: BenefitLedgerGranularity,
    ) -> tuple[int, int | None, int | None]:
        if granularity == "weekly":
            iso = period_start.isocalendar()
            return (iso.year, iso.week, None)
        if granularity == "monthly":
            return (period_start.year, None, period_start.month)
        return (period_start.year, None, None)

    @staticmethod
    def _benefit_period_sort(
        key: tuple[int, int | None, int | None],
        granularity: BenefitLedgerGranularity,
    ) -> tuple[int, int]:
        year, week, month = key
        if granularity == "weekly":
            return (year, week or 0)
        if granularity == "monthly":
            return (year, month or 0)
        return (year, 0)

    @staticmethod
    def _benefit_period_label(
        year: int,
        week: int | None,
        month: int | None,
        granularity: BenefitLedgerGranularity,
    ) -> str:
        if granularity == "weekly":
            return f"{year}-W{(week or 0):02d}"
        if granularity == "monthly":
            return f"{year}-M{(month or 0):02d}"
        return str(year)

    # ── Portfolio financials ─────────────────────────────────────────────────

    def get_portfolio_initiative_portfolio(
        self,
        baseline_year: int | None = None,
        value_year: int | None = None,
        scenario: str = "plan_base",
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        stage: str | None = None,
        tag: str | None = None,
    ) -> PortfolioInitiativePortfolioResponse:
        scenario_key = scenario or "plan_base"
        if scenario_key not in {"plan_base", "plan_high", "actual"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scenario must be one of plan_base, plan_high, or actual",
            )

        business_unit_ids = self._split_filter_values(business_unit_id)
        workstream_ids = self._split_filter_values(workstream_id)
        stages = self._split_filter_values(stage)
        tags = self._split_filter_values(tag)
        initiatives = {
            str(row["id"]): row
            for row in self._repo.get_portfolio_initiatives()
            if self._portfolio_initiative_matches(
                row,
                initiative_id=initiative_id,
                workstream_ids=workstream_ids,
                business_unit_ids=business_unit_ids,
                stages=stages,
                tags=tags,
            )
        }

        definitions = [
            row for row in self._repo.list_metric_definitions() if row.get("is_active", True)
        ]
        definitions_by_id = {str(row["id"]): row for row in definitions}
        baseline_definitions = self._baseline_metric_definitions(definitions)
        value_definitions = [
            row
            for row in definitions
            if row.get("is_benefit") and row.get("aggregation") != "formula"
        ]
        value_definition_by_key = {str(row["key"]): row for row in value_definitions}
        scenarios = {str(row["id"]): row for row in self._repo.list_financial_scenarios()}

        all_baselines = [
            row
            for row in self._repo.list_all_initiative_annual_baselines()
            if str(row.get("initiative_id")) in initiatives
        ]
        tenant_baselines_all = self._repo.list_tenant_annual_baselines()
        available_baseline_years = sorted(
            {
                int(row["baseline_year"])
                for row in [*all_baselines, *tenant_baselines_all]
                if row.get("baseline_year") is not None
            }
        )
        effective_baseline_year = baseline_year
        if effective_baseline_year is None and available_baseline_years:
            effective_baseline_year = available_baseline_years[-1]

        all_values = [
            row
            for row in self._repo.get_all_metric_values()
            if str(row.get("initiative_id")) in initiatives
        ]
        all_costs = [
            row
            for row in self._repo.get_all_cost_lines()
            if str(row.get("initiative_id")) in initiatives
        ]
        available_value_years = sorted(
            {int(row["year"]) for row in [*all_values, *all_costs] if row.get("year") is not None}
        )
        effective_value_year = value_year
        if effective_value_year is None and available_value_years:
            effective_value_year = available_value_years[-1]

        tenant_baseline_values: dict[str, Decimal] = {}
        for row in tenant_baselines_all:
            if (
                effective_baseline_year is not None
                and int(row["baseline_year"]) != effective_baseline_year
            ):
                continue
            definition = definitions_by_id.get(str(row.get("metric_definition_id")))
            if not definition:
                continue
            tenant_baseline_values[str(definition["key"])] = _dec(row.get("value"))

        baseline_values_by_initiative: dict[str, dict[str, Decimal]] = {}
        for row in all_baselines:
            if (
                effective_baseline_year is not None
                and int(row["baseline_year"]) != effective_baseline_year
            ):
                continue
            definition = definitions_by_id.get(str(row.get("metric_definition_id")))
            if not definition:
                continue
            initiative_key = str(row.get("initiative_id"))
            values = baseline_values_by_initiative.setdefault(initiative_key, {})
            values[str(definition["key"])] = values.get(
                str(definition["key"]), Decimal("0")
            ) + _dec(row.get("value"))

        scenario_ids = {
            str(scenario_id)
            for scenario_id, row in scenarios.items()
            if row.get("key") == scenario_key
        }
        value_metric_values_by_initiative: dict[str, dict[str, Decimal]] = {}
        for row in all_values:
            if effective_value_year is not None and int(row["year"]) != effective_value_year:
                continue
            if str(row.get("scenario_id")) not in scenario_ids:
                continue
            definition = definitions_by_id.get(str(row.get("metric_definition_id")))
            if (
                not definition
                or not definition.get("is_benefit")
                or definition.get("aggregation") == "formula"
            ):
                continue
            initiative_key = str(row.get("initiative_id"))
            metric_key = str(definition["key"])
            values = value_metric_values_by_initiative.setdefault(initiative_key, {})
            values[metric_key] = values.get(metric_key, Decimal("0")) + _dec(row.get("value"))

        costs_by_initiative: dict[str, dict[str, Decimal]] = {}
        for row in all_costs:
            if effective_value_year is not None and int(row["year"]) != effective_value_year:
                continue
            initiative_key = str(row.get("initiative_id"))
            costs = costs_by_initiative.setdefault(
                initiative_key,
                {"recurring": Decimal("0"), "one_off": Decimal("0")},
            )
            raw_amount = (
                row.get("amount_actual") if scenario_key == "actual" else row.get("amount_plan")
            )
            bucket = "recurring" if row.get("is_recurring", False) else "one_off"
            costs[bucket] = costs[bucket] + _dec(raw_amount)

        rows: list[PortfolioInitiativePortfolioRow] = []
        totals_baseline = {str(row["key"]): Decimal("0") for row in baseline_definitions}
        totals_values = {str(row["key"]): Decimal("0") for row in value_definitions}
        total_benefits = Decimal("0")
        total_recurring = Decimal("0")
        total_one_off = Decimal("0")
        for initiative in sorted(
            initiatives.values(),
            key=lambda item: str(item.get("initiative_code") or item.get("name") or ""),
        ):
            initiative_key = str(initiative["id"])
            baseline_values = baseline_values_by_initiative.get(initiative_key, {})
            value_values = value_metric_values_by_initiative.get(initiative_key, {})
            costs = costs_by_initiative.get(
                initiative_key,
                {"recurring": Decimal("0"), "one_off": Decimal("0")},
            )
            benefits_total = sum(
                amount
                for key, amount in value_values.items()
                if value_definition_by_key.get(key, {}).get("benefit_class") != "revenue"
            )
            recurring = _dec(costs["recurring"])
            one_off = _dec(costs["one_off"])
            for key, amount in baseline_values.items():
                if key in totals_baseline:
                    totals_baseline[key] += amount
            for key, amount in value_values.items():
                if key in totals_values:
                    totals_values[key] += amount
            total_benefits += benefits_total
            total_recurring += recurring
            total_one_off += one_off
            business_units = self._initiative_business_units(initiative)
            rows.append(
                PortfolioInitiativePortfolioRow(
                    initiative_id=initiative_key,
                    initiative_code=initiative.get("initiative_code"),
                    initiative_name=initiative.get("name") or "Untitled initiative",
                    stage=initiative.get("stage"),
                    tag=initiative.get("tag"),
                    workstream_id=(
                        str(initiative.get("workstream_id"))
                        if initiative.get("workstream_id")
                        else None
                    ),
                    workstream_name=self._initiative_workstream_name(initiative),
                    business_unit_ids=[item[0] for item in business_units],
                    business_unit_names=[item[1] for item in business_units if item[1]],
                    baseline_values={
                        str(definition["key"]): _money(
                            baseline_values.get(str(definition["key"]), Decimal("0"))
                        )
                        for definition in baseline_definitions
                    },
                    baseline_complete=all(
                        str(definition["key"]) in baseline_values
                        for definition in baseline_definitions
                    ),
                    value_metric_values={
                        str(definition["key"]): _money(
                            value_values.get(str(definition["key"]), Decimal("0"))
                        )
                        for definition in value_definitions
                    },
                    benefits_total=_money(benefits_total),
                    recurring_costs=_money(recurring),
                    one_off_costs=_money(one_off),
                    net_run_rate_value=_money(benefits_total - recurring),
                )
            )

        reconciliation = []
        for definition in baseline_definitions:
            key = str(definition["key"])
            tenant_value = tenant_baseline_values.get(key, Decimal("0"))
            initiative_total = totals_baseline.get(key, Decimal("0"))
            variance = initiative_total - tenant_value
            reconciliation.append(
                PortfolioInitiativeBaselineReconciliation(
                    metric_key=key,
                    metric_label=str(definition["label"]),
                    tenant_value=_money(tenant_value),
                    initiative_total=_money(initiative_total),
                    variance=_money(variance),
                    reconciled=abs(variance) <= Decimal("0.01"),
                )
            )

        return PortfolioInitiativePortfolioResponse(
            baseline_year=effective_baseline_year,
            value_year=effective_value_year,
            scenario=scenario_key,
            available_baseline_years=available_baseline_years,
            available_value_years=available_value_years,
            baseline_metrics=[
                self._to_portfolio_metric_column(row) for row in baseline_definitions
            ],
            value_metrics=[self._to_portfolio_metric_column(row) for row in value_definitions],
            tenant_baseline_values={
                key: _money(value) for key, value in tenant_baseline_values.items()
            },
            baseline_reconciliation=reconciliation,
            rows=rows,
            totals=PortfolioInitiativePortfolioTotals(
                baseline_values={key: _money(value) for key, value in totals_baseline.items()},
                value_metric_values={key: _money(value) for key, value in totals_values.items()},
                benefits_total=_money(total_benefits),
                recurring_costs=_money(total_recurring),
                one_off_costs=_money(total_one_off),
                net_run_rate_value=_money(total_benefits - total_recurring),
            ),
        )

    def get_portfolio_financials(
        self,
        granularity: PortfolioGranularity,
        year: int | None = None,
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        stage: str | None = None,
        tag: str | None = None,
        category_key: str | None = None,
    ) -> PortfolioFinancialsResponse:
        business_unit_ids = self._split_filter_values(business_unit_id)
        workstream_ids = self._split_filter_values(workstream_id)
        stages = self._split_filter_values(stage)
        tags = self._split_filter_values(tag)
        initiatives = {
            row["id"]: row
            for row in self._repo.get_portfolio_initiatives()
            if self._portfolio_initiative_matches(
                row,
                initiative_id=initiative_id,
                workstream_ids=workstream_ids,
                business_unit_ids=business_unit_ids,
                stages=stages,
                tags=tags,
            )
        }
        raw_entries = self._repo.get_all_entries()
        if not raw_entries:
            return self._get_clean_portfolio_financials(
                granularity,
                year=year,
                initiative_id=initiative_id,
                workstream_id=workstream_id,
                business_unit_id=business_unit_id,
                stage=stage,
                tag=tag,
                category_key=category_key,
            )
        entries = [
            row
            for row in self._reporting_rows(raw_entries)
            if row.get("initiative_id") in initiatives and (year is None or row.get("year") == year)
        ]
        costs = [
            row
            for row in self._reporting_cost_lines(self._repo.get_all_cost_lines())
            if row.get("initiative_id") in initiatives
            and (year is None or row.get("year") == year)
            and (not category_key or row.get("category_key", "other") == category_key)
        ]
        metric_values = [
            row
            for row in self._reporting_metric_values(self._repo.get_all_metric_values())
            if row.get("initiative_id") in initiatives and (year is None or row.get("year") == year)
        ]
        config = self.get_configuration()
        response = self._compute_portfolio_financials(
            entries, costs, metric_values, config, granularity
        )
        response.financial_mode = self._financial_mode_descriptor(
            "",
            entries,
            costs,
            metric_values,
            config=config,
        )
        return response

    def get_portfolio_investments_payback(
        self,
        value_year: int | None = None,
        scenario: str = "plan_base",
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        stage: str | None = None,
        tag: str | None = None,
    ) -> PortfolioInvestmentPaybackResponse:
        portfolio = self.get_portfolio_initiative_portfolio(
            value_year=value_year,
            scenario=scenario,
            initiative_id=initiative_id,
            workstream_id=workstream_id,
            business_unit_id=business_unit_id,
            stage=stage,
            tag=tag,
        )
        one_off_by_initiative = self._cumulative_one_off_investments(
            initiative_ids={row.initiative_id for row in portfolio.rows},
            value_year=portfolio.value_year,
            scenario_key=portfolio.scenario,
        )
        rows = [
            self._to_payback_row(
                row,
                one_off_investment=one_off_by_initiative.get(
                    row.initiative_id, Decimal("0")
                ),
            )
            for row in portfolio.rows
        ]
        rows.sort(
            key=lambda row: (
                row.payback_months is None,
                _dec(row.payback_months or "999999999"),
                -_dec(row.net_run_rate_value),
                row.initiative_name,
            )
        )
        total_one_off = sum(one_off_by_initiative.values(), Decimal("0"))
        total_net = _dec(portfolio.totals.net_run_rate_value)
        summary_months, summary_label = self._payback_months_and_label(total_one_off, total_net)
        return PortfolioInvestmentPaybackResponse(
            value_year=portfolio.value_year,
            scenario=portfolio.scenario,
            summary=PortfolioInvestmentPaybackSummary(
                benefits_total=portfolio.totals.benefits_total,
                recurring_costs=portfolio.totals.recurring_costs,
                one_off_investment=_money(total_one_off),
                net_run_rate_value=portfolio.totals.net_run_rate_value,
                payback_months=summary_months,
                payback_label=summary_label,
                initiatives_with_payback=len(
                    [row for row in rows if row.payback_status in {"immediate", "payback"}]
                ),
                initiatives_not_reached=len(
                    [row for row in rows if row.payback_status == "not_reached"]
                ),
            ),
            rows=rows,
        )

    def get_portfolio_financial_contributors(
        self,
        granularity: PortfolioGranularity,
        period: str,
        year: int | None = None,
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        stage: str | None = None,
        tag: str | None = None,
        category_key: str | None = None,
    ) -> PortfolioFinancialContributorsResponse:
        period_key = self._parse_portfolio_period(period, granularity)
        effective_year = year or period_key[1]
        business_unit_ids = self._split_filter_values(business_unit_id)
        workstream_ids = self._split_filter_values(workstream_id)
        stages = self._split_filter_values(stage)
        tags = self._split_filter_values(tag)
        initiatives = {
            row["id"]: row
            for row in self._repo.get_portfolio_initiatives()
            if self._portfolio_initiative_matches(
                row,
                initiative_id=initiative_id,
                workstream_ids=workstream_ids,
                business_unit_ids=business_unit_ids,
                stages=stages,
                tags=tags,
            )
        }
        raw_entries = self._repo.get_all_entries()
        if not raw_entries:
            return self._get_clean_portfolio_financial_contributors(
                granularity=granularity,
                period=period,
                period_key=period_key,
                effective_year=effective_year,
                initiatives=initiatives,
                category_key=category_key,
            )
        entries = [
            row
            for row in self._reporting_rows(raw_entries)
            if row.get("initiative_id") in initiatives
            and row.get("year") == effective_year
            and self._portfolio_row_period_label(row, granularity) == period
        ]
        costs = [
            row
            for row in self._reporting_cost_lines(self._repo.get_all_cost_lines())
            if row.get("initiative_id") in initiatives
            and row.get("year") == effective_year
            and self._portfolio_row_period_label(row, granularity) == period
            and (not category_key or row.get("category_key", "other") == category_key)
        ]
        metric_values = [
            row
            for row in self._reporting_metric_values(self._repo.get_all_metric_values())
            if row.get("initiative_id") in initiatives
            and row.get("year") == effective_year
            and self._portfolio_row_period_label(row, granularity) == period
        ]
        config = self.get_configuration()
        return self._compute_portfolio_contributors(
            entries,
            costs,
            metric_values,
            initiatives,
            config,
            granularity,
            period,
            period_key,
        )

    def _get_clean_portfolio_financial_contributors(
        self,
        granularity: PortfolioGranularity,
        period: str,
        period_key: tuple[str, int, int | None, int | None],
        effective_year: int,
        initiatives: dict[str, dict],  # type: ignore[type-arg]
        category_key: str | None = None,
    ) -> PortfolioFinancialContributorsResponse:
        values = self._values_with_formula_metrics(
            [
                row
                for row in self._repo.get_all_metric_values()
                if row.get("initiative_id") in initiatives
                and row.get("year") == effective_year
                and self._clean_portfolio_period_key(row, granularity)[0] == period
            ],
            [
                row
                for row in self._repo.list_all_initiative_annual_baselines()
                if row.get("initiative_id") in initiatives
            ],
        )
        costs = [
            row
            for row in self._repo.get_all_cost_lines()
            if row.get("initiative_id") in initiatives
            and row.get("year") == effective_year
            and self._clean_portfolio_period_key(row, granularity)[0] == period
            and (not category_key or row.get("category_key", "other") == category_key)
        ]
        definitions = {row["id"]: row for row in self._repo.list_metric_definitions()}
        scenarios = {row["id"]: row for row in self._repo.list_financial_scenarios()}
        benefit_lines = {row["id"]: row for row in self._repo.list_all_benefit_lines()}
        config = self.get_configuration()
        cost_categories = {
            item.key: item for item in config.items if item.item_type == "cost_category"
        }
        contributors: dict[str, dict[str, object]] = {}

        def record_for(initiative_id: str) -> dict[str, object]:
            initiative = initiatives.get(initiative_id, {})
            return contributors.setdefault(
                initiative_id,
                {
                    "initiative_id": initiative_id,
                    "initiative_name": initiative.get("name") or "Untitled initiative",
                    "benefits_plan": Decimal("0"),
                    "benefits_actual": Decimal("0"),
                    "recurring_costs_plan": Decimal("0"),
                    "recurring_costs_actual": Decimal("0"),
                    "one_off_costs_plan": Decimal("0"),
                    "one_off_costs_actual": Decimal("0"),
                    "benefit_lines": {},
                    "cost_lines": [],
                },
            )

        for initiative_id in initiatives:
            initiative_values = [
                row for row in values if str(row.get("initiative_id")) == str(initiative_id)
            ]
            if not initiative_values:
                continue
            record = record_for(str(initiative_id))
            plan = self._clean_value_case(initiative_values, "plan_base")
            actual = self._clean_value_case(initiative_values, "actual")
            record["benefits_plan"] = _dec(record["benefits_plan"]) + _dec(plan["benefits_total"])
            record["benefits_actual"] = _dec(record["benefits_actual"]) + _dec(
                actual["benefits_total"]
            )

        for row in values:
            scenario = scenarios.get(row.get("scenario_id"))
            if not scenario or scenario.get("key") not in {"plan_base", "actual"}:
                continue
            definition = definitions.get(row.get("metric_definition_id"))
            if not definition or not definition.get("is_benefit"):
                continue
            if definition.get("aggregation") == "formula":
                continue
            record = record_for(str(row["initiative_id"]))
            benefit_line_id = row.get("benefit_line_id")
            benefit_line = benefit_lines.get(benefit_line_id) if benefit_line_id else None
            contribution_id = str(benefit_line_id or f"metric:{definition['id']}")
            contribution_key = (contribution_id, str(definition["id"]))
            benefit_records = record["benefit_lines"]  # type: ignore[assignment]
            contribution = benefit_records.setdefault(  # type: ignore[union-attr]
                contribution_key,
                {
                    "id": contribution_id,
                    "name": benefit_line.get("name") if benefit_line else definition["label"],
                    "metric_key": definition["key"],
                    "metric_label": definition["label"],
                    "benefit_class": definition.get("benefit_class"),
                    "validation_status": (benefit_line or {}).get("validation_status") or "draft",
                    "evidence_url": (benefit_line or {}).get("evidence_url"),
                    "evidence_label": (benefit_line or {}).get("evidence_label"),
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                },
            )
            amount = _dec(row.get("value"))
            if scenario.get("key") == "actual":
                contribution["actual"] += amount
            else:
                contribution["plan"] += amount

        for row in costs:
            record = record_for(str(row["initiative_id"]))
            plan = _dec(row.get("amount_plan"))
            actual = _dec(row.get("amount_actual"))
            category_key_value = row.get("category_key") or "other"
            category = cost_categories.get(category_key_value)
            if row.get("is_recurring", False):
                record["recurring_costs_plan"] = _dec(record["recurring_costs_plan"]) + plan
                record["recurring_costs_actual"] = _dec(record["recurring_costs_actual"]) + actual
            else:
                record["one_off_costs_plan"] = _dec(record["one_off_costs_plan"]) + plan
                record["one_off_costs_actual"] = _dec(record["one_off_costs_actual"]) + actual
            record["cost_lines"].append(  # type: ignore[union-attr]
                PortfolioFinancialCostLineContribution(
                    id=row["id"],
                    name=row["name"],
                    category_key=category_key_value,
                    category_label=category.label if category else None,
                    is_recurring=row.get("is_recurring", False),
                    plan=_money(plan),
                    actual=_money(actual),
                )
            )

        contribution_items: list[PortfolioFinancialInitiativeContribution] = []
        for record in contributors.values():
            benefits_plan = _dec(record["benefits_plan"])
            benefits_actual = _dec(record["benefits_actual"])
            recurring_plan = _dec(record["recurring_costs_plan"])
            recurring_actual = _dec(record["recurring_costs_actual"])
            one_off_plan = _dec(record["one_off_costs_plan"])
            one_off_actual = _dec(record["one_off_costs_actual"])
            total_plan = recurring_plan + one_off_plan
            total_actual = recurring_actual + one_off_actual
            benefit_line_records: list[PortfolioFinancialBenefitLineContribution] = []
            for item in record["benefit_lines"].values():  # type: ignore[union-attr]
                plan_amount = _dec(item["plan"])
                actual_amount = _dec(item["actual"])
                benefit_line_records.append(
                    PortfolioFinancialBenefitLineContribution(
                        id=str(item["id"]),
                        name=str(item["name"]),
                        metric_key=str(item["metric_key"]),
                        metric_label=str(item["metric_label"]),
                        benefit_class=item.get("benefit_class"),
                        plan=_money(plan_amount),
                        actual=_money(actual_amount),
                        variance=_money(actual_amount - plan_amount),
                        validation_status=item.get("validation_status") or "draft",
                        evidence_url=item.get("evidence_url"),
                        evidence_label=item.get("evidence_label"),
                    )
                )
            benefit_line_records.sort(key=lambda item: (item.metric_label, item.name))
            contribution_items.append(
                PortfolioFinancialInitiativeContribution(
                    initiative_id=str(record["initiative_id"]),
                    initiative_name=str(record["initiative_name"]),
                    benefits_plan=_money(benefits_plan),
                    benefits_actual=_money(benefits_actual),
                    recurring_costs_plan=_money(recurring_plan),
                    recurring_costs_actual=_money(recurring_actual),
                    one_off_costs_plan=_money(one_off_plan),
                    one_off_costs_actual=_money(one_off_actual),
                    total_costs_plan=_money(total_plan),
                    total_costs_actual=_money(total_actual),
                    net_value_plan=_money(benefits_plan - recurring_plan),
                    net_value_actual=_money(benefits_actual - recurring_actual),
                    benefit_lines=benefit_line_records,
                    cost_lines=record["cost_lines"],  # type: ignore[arg-type]
                )
            )

        contribution_items.sort(
            key=lambda item: (
                -abs(_dec(item.benefits_plan)) - abs(_dec(item.total_costs_plan)),
                item.initiative_name,
            )
        )
        return PortfolioFinancialContributorsResponse(
            granularity=granularity,
            period=period,
            year=period_key[1],
            quarter=period_key[2],
            month=period_key[3],
            contributors=contribution_items,
        )

    def get_portfolio_value_ramp(
        self,
        granularity: PortfolioGranularity,
        run_rate_year: int | None = None,
        as_of_date: date | None = None,
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        stage: str | None = None,
        tag: str | None = None,
        category_key: str | None = None,
    ) -> PortfolioValueRampResponse:
        response = self.get_portfolio_financials(
            granularity=granularity,
            year=run_rate_year,
            initiative_id=initiative_id,
            workstream_id=workstream_id,
            business_unit_id=business_unit_id,
            stage=stage,
            tag=tag,
            category_key=category_key,
        )
        periods = [
            row
            for row in response.periods
            if as_of_date is None or self._portfolio_period_start(row) <= as_of_date
        ]
        ramp = self._portfolio_value_ramp_periods(periods)
        in_year = self._portfolio_in_year_cards(ramp)
        return PortfolioValueRampResponse(
            granularity=granularity,
            run_rate_year=run_rate_year,
            as_of_date=as_of_date,
            stage=stage,
            periods=ramp,
            in_year=in_year,
            financial_mode=response.financial_mode,
        )

    @staticmethod
    def _split_filter_values(value: str | None) -> set[str]:
        if not value:
            return set()
        return {item.strip() for item in value.split(",") if item.strip()}

    @staticmethod
    def _initiative_business_unit_ids(row: dict) -> set[str]:  # type: ignore[type-arg]
        return {
            str(link.get("business_unit_id"))
            for link in row.get("initiative_business_units") or []
            if link.get("business_unit_id")
        }

    @staticmethod
    def _initiative_business_units(row: dict) -> list[tuple[str, str]]:  # type: ignore[type-arg]
        units: list[tuple[str, str]] = []
        for link in row.get("initiative_business_units") or []:
            business_unit_id = str(link.get("business_unit_id") or "")
            business_unit = link.get("business_units") if isinstance(link, dict) else None
            name = ""
            if isinstance(business_unit, dict):
                business_unit_id = str(business_unit.get("id") or business_unit_id)
                name = str(business_unit.get("name") or "")
            if business_unit_id:
                units.append((business_unit_id, name))
        return units

    @staticmethod
    def _initiative_workstream_name(row: dict) -> str | None:  # type: ignore[type-arg]
        workstream = row.get("workstreams")
        if isinstance(workstream, dict):
            name = workstream.get("name")
            return str(name) if name else None
        return None

    @classmethod
    def _portfolio_initiative_matches(
        cls,
        row: dict,  # type: ignore[type-arg]
        *,
        initiative_id: str | None,
        workstream_ids: set[str],
        business_unit_ids: set[str],
        stages: set[str],
        tags: set[str],
    ) -> bool:
        if initiative_id and row.get("id") != initiative_id:
            return False
        if workstream_ids and str(row.get("workstream_id") or "") not in workstream_ids:
            return False
        if business_unit_ids and not (cls._initiative_business_unit_ids(row) & business_unit_ids):
            return False
        if stages and str(row.get("stage") or "") not in stages:
            return False
        return not (tags and str(row.get("tag") or "") not in tags)

    def _baseline_metric_definitions(
        self,
        definitions: list[dict],  # type: ignore[type-arg]
    ) -> list[dict]:  # type: ignore[type-arg]
        active_by_key = {
            str(row["key"]): row
            for row in definitions
            if row.get("is_active", True) and row.get("aggregation") != "formula"
        }
        baseline_keys = {
            str(row["key"])
            for row in active_by_key.values()
            if str(row.get("group_key") or "") == "baseline"
        }
        for row in definitions:
            if not row.get("is_active", True) or row.get("aggregation") != "formula":
                continue
            identifiers = set(str(item) for item in row.get("formula_inputs") or [])
            formula = str(row.get("formula") or "").strip()
            if formula:
                identifiers |= self._formula_identifiers(formula)
            for identifier in identifiers:
                if identifier.startswith("baseline_"):
                    metric_key = identifier.removeprefix("baseline_")
                    if metric_key in active_by_key:
                        baseline_keys.add(metric_key)
        return sorted(
            [row for key, row in active_by_key.items() if key in baseline_keys],
            key=lambda item: (
                int(item.get("display_order") or 0),
                str(item.get("label") or ""),
            ),
        )

    @staticmethod
    def _to_portfolio_metric_column(row: dict) -> PortfolioInitiativeMetricColumn:  # type: ignore[type-arg]
        return PortfolioInitiativeMetricColumn(
            metric_definition_id=str(row["id"]),
            key=str(row["key"]),
            label=str(row["label"]),
            value_type=row.get("value_type") or "currency",
            unit=row.get("unit"),
        )

    @classmethod
    def _portfolio_value_ramp_periods(
        cls,
        periods: list[PortfolioFinancialPeriod],
    ) -> list[PortfolioValueRampPeriod]:
        cumulative_plan = Decimal("0")
        cumulative_actual = Decimal("0")
        ramp: list[PortfolioValueRampPeriod] = []
        for row in sorted(
            periods, key=lambda item: cls._period_sort((item.year, item.quarter, item.month))
        ):
            cumulative_plan += _dec(row.net_value_plan)
            cumulative_actual += _dec(row.net_value_actual)
            ramp.append(
                PortfolioValueRampPeriod(
                    **row.model_dump(),
                    cumulative_net_value_plan=_money(cumulative_plan),
                    cumulative_net_value_actual=_money(cumulative_actual),
                )
            )
        return ramp

    @classmethod
    def _portfolio_in_year_cards(
        cls,
        periods: list[PortfolioValueRampPeriod],
    ) -> list[PortfolioInYearValueCard]:
        totals = cls._empty_portfolio_period("In-year", 0, None, None)
        for row in periods:
            totals["benefits_plan"] += _dec(row.benefits_plan)
            totals["benefits_actual"] += _dec(row.benefits_actual)
            totals["recurring_costs_plan"] += _dec(row.recurring_costs_plan)
            totals["recurring_costs_actual"] += _dec(row.recurring_costs_actual)
            totals["one_off_costs_plan"] += _dec(row.one_off_costs_plan)
            totals["one_off_costs_actual"] += _dec(row.one_off_costs_actual)
        total_period = cls._to_portfolio_period(totals)
        cards = [
            (
                "benefits",
                "In-year Benefits",
                total_period.benefits_plan,
                total_period.benefits_actual,
            ),
            (
                "recurring_costs",
                "In-year Recurring Costs",
                total_period.recurring_costs_plan,
                total_period.recurring_costs_actual,
            ),
            (
                "one_off_costs",
                "In-year One-time Costs",
                total_period.one_off_costs_plan,
                total_period.one_off_costs_actual,
            ),
            (
                "net_value",
                "In-year Net Value",
                total_period.net_value_plan,
                total_period.net_value_actual,
            ),
        ]
        return [
            PortfolioInYearValueCard(
                key=key,
                label=label,
                plan=plan,
                actual=actual,
                variance=_money(_dec(actual) - _dec(plan)),
            )
            for key, label, plan, actual in cards
        ]

    @staticmethod
    def _portfolio_period_start(row: PortfolioFinancialPeriod) -> date:
        if row.month is not None:
            return date(row.year, row.month, 1)
        if row.quarter is not None:
            return date(row.year, ((row.quarter - 1) * 3) + 1, 1)
        return date(row.year, 1, 1)

    @staticmethod
    def _filter_value_bridge_rows(
        rows: list[dict],  # type: ignore[type-arg]
        basis: PortfolioValueBridgeBasis,
        year: int | None,
    ) -> list[dict]:  # type: ignore[type-arg]
        if basis == "all_years" or year is None:
            return rows
        if basis == "cumulative":
            return [row for row in rows if int(row.get("year") or 0) <= year]
        return [row for row in rows if int(row.get("year") or 0) == year]

    @staticmethod
    def _value_bridge_basis_label(
        basis: PortfolioValueBridgeBasis,
        year: int | None,
    ) -> str:
        if basis == "in_year":
            return f"FY{year} in-year" if year else "Selected year in-year"
        if basis == "target_year_run_rate":
            return f"FY{year} target-year run-rate" if year else "Target-year run-rate"
        if basis == "cumulative":
            return f"Cumulative through FY{year}" if year else "Cumulative"
        return "All years"

    # ── Value Bridge ──────────────────────────────────────────────────────────

    def get_value_bridge(self, initiative_id: str) -> ValueBridgeResponse:
        """Value Bridge for a single initiative."""
        raw_entries = self._repo.get_entries(initiative_id)
        raw_cost_lines = self._repo.list_cost_lines(initiative_id)
        clean_values = self._repo.list_configurable_metric_values(initiative_id)
        baseline_values = self._repo.list_initiative_annual_baselines(initiative_id)
        if clean_values or not raw_entries:
            return self._compute_clean_value_bridge(
                self._values_with_formula_metrics(
                    clean_values,
                    baseline_values,
                ),
                raw_cost_lines,
                initiative_id=initiative_id,
                baseline_values=baseline_values,
            )
        metric_values = self._repo.list_metric_values(initiative_id)
        config = self.get_configuration()
        selections = self._resolve_selections(
            initiative_id, raw_entries, raw_cost_lines, metric_values, config
        )
        scoped_entries, scoped_cost_lines = self._apply_financial_scope(
            raw_entries, raw_cost_lines, selections
        )
        scoped_metric_values = self._scope_metric_values(metric_values, selections)
        entries = self._reporting_rows(scoped_entries)
        cost_lines = self._reporting_cost_lines(scoped_cost_lines)
        return self._compute_value_bridge(
            entries,
            cost_lines,
            initiative_id,
            scoped_metric_values,
            config,
            baseline_values=self._repo.list_initiative_annual_baselines(initiative_id),
        )

    def get_scenario_summary(
        self,
        initiative_id: str,
        scenario: FinancialScenario,
    ) -> ScenarioFinancialSummary:
        raw_entries = self._repo.get_entries(initiative_id)
        raw_cost_lines = self._repo.list_cost_lines(initiative_id)
        clean_values = self._repo.list_configurable_metric_values(initiative_id)
        if clean_values or not raw_entries:
            return self._compute_clean_scenario_summary(
                self._values_with_formula_metrics(
                    clean_values,
                    self._repo.list_initiative_annual_baselines(initiative_id),
                ),
                raw_cost_lines,
                scenario,
            )
        metric_values = self._repo.list_metric_values(initiative_id)
        config = self.get_configuration()
        selections = self._resolve_selections(
            initiative_id, raw_entries, raw_cost_lines, metric_values, config
        )
        scoped_entries, scoped_cost_lines = self._apply_financial_scope(
            raw_entries, raw_cost_lines, selections
        )
        scoped_metric_values = self._scope_metric_values(metric_values, selections)
        entries = self._reporting_rows(scoped_entries)
        cost_lines = self._reporting_cost_lines(scoped_cost_lines)
        return self._compute_scenario_summary(
            entries, cost_lines, scoped_metric_values, config, scenario
        )

    def get_break_even(
        self,
        initiative_id: str,
        scenario: FinancialScenario,
    ) -> BreakEvenResponse:
        raw_entries = self._repo.get_entries(initiative_id)
        raw_cost_lines = self._repo.list_cost_lines(initiative_id)
        clean_values = self._repo.list_configurable_metric_values(initiative_id)
        if clean_values or not raw_entries:
            return self._compute_clean_break_even(
                initiative_id,
                self._values_with_formula_metrics(
                    clean_values,
                    self._repo.list_initiative_annual_baselines(initiative_id),
                ),
                raw_cost_lines,
                scenario,
            )
        metric_values = self._repo.list_metric_values(initiative_id)
        selections = self._resolve_selections(
            initiative_id, raw_entries, raw_cost_lines, metric_values
        )
        scoped_entries, scoped_cost_lines = self._apply_financial_scope(
            raw_entries, raw_cost_lines, selections
        )
        entries = self._reporting_rows(scoped_entries)
        cost_lines = self._reporting_cost_lines(scoped_cost_lines)
        periods = sorted(
            {
                self._period_key(row)
                for row in [*entries, *cost_lines]
                if row.get("year") is not None
            },
            key=self._period_sort,
        )
        points: list[BreakEvenPoint] = []
        cumulative_gm = Decimal("0")
        cumulative_costs = Decimal("0")
        break_even_period: str | None = None
        for year, quarter, month in periods:
            period_entries = [
                row
                for row in entries
                if row["year"] == year
                and row.get("quarter") == quarter
                and row.get("month") == month
            ]
            period_costs = [
                row
                for row in cost_lines
                if row["year"] == year
                and row.get("quarter") == quarter
                and row.get("month") == month
            ]
            period_gm = sum(
                (self._scenario_entry_value(row, "gm_uplift", scenario) for row in period_entries),
                Decimal("0"),
            )
            period_cost = sum(
                (self._scenario_cost_value(row, scenario) for row in period_costs), Decimal("0")
            )
            cumulative_gm += period_gm
            cumulative_costs += period_cost
            cumulative_net = cumulative_gm - cumulative_costs
            label = self._period_label(year, quarter, month)
            crossed = (
                break_even_period is None
                and cumulative_net >= Decimal("0")
                and cumulative_costs > Decimal("0")
            )
            if crossed:
                break_even_period = label
            points.append(
                BreakEvenPoint(
                    period=label,
                    year=year,
                    quarter=quarter,
                    month=month,
                    cumulative_gm_uplift=_money(cumulative_gm),
                    cumulative_costs=_money(cumulative_costs),
                    cumulative_net=_money(cumulative_net),
                    run_rate_gm_uplift=_money(period_gm),
                    run_rate_costs=_money(period_cost),
                    is_break_even=crossed,
                )
            )
        return BreakEvenResponse(
            initiative_id=initiative_id,
            scenario=scenario,
            break_even_period=break_even_period,
            points=points,
            financial_mode=self._financial_mode_descriptor(
                initiative_id,
                raw_entries,
                raw_cost_lines,
                metric_values,
                config=self.get_configuration(),
            ),
        )

    def get_portfolio_value_bridge(
        self,
        basis: PortfolioValueBridgeBasis = "all_years",
        year: int | None = None,
    ) -> ValueBridgeResponse:
        """Portfolio-level Value Bridge across all initiatives."""
        raw_entries = self._repo.get_all_entries()
        if not raw_entries:
            values = self._filter_value_bridge_rows(self._repo.get_all_metric_values(), basis, year)
            costs = self._filter_value_bridge_rows(self._repo.get_all_cost_lines(), basis, year)
            return self._compute_clean_value_bridge(
                self._values_with_formula_metrics(
                    values,
                    self._repo.list_all_initiative_annual_baselines(),
                ),
                costs,
                initiative_id=None,
                basis=basis,
                year=year,
            )
        entries = self._filter_value_bridge_rows(self._reporting_rows(raw_entries), basis, year)
        cost_lines = self._filter_value_bridge_rows(
            self._reporting_cost_lines(self._repo.get_all_cost_lines()),
            basis,
            year,
        )
        metric_values = self._filter_value_bridge_rows(
            self._reporting_metric_values(self._repo.get_all_metric_values()),
            basis,
            year,
        )
        return self._compute_value_bridge(
            entries,
            cost_lines,
            initiative_id=None,
            metric_values=metric_values,
            config=self.get_configuration(),
            basis=basis,
            year=year,
        )

    def get_portfolio_benefits_register(
        self,
        year: int | None = None,
        validation_status: FinancialBenefitValidationStatus | None = None,
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        stage: str | None = None,
        tag: str | None = None,
    ) -> PortfolioBenefitsRegisterResponse:
        business_unit_ids = self._split_filter_values(business_unit_id)
        workstream_ids = self._split_filter_values(workstream_id)
        stages = self._split_filter_values(stage)
        tags = self._split_filter_values(tag)
        initiatives = {
            str(row["id"]): row
            for row in self._repo.get_portfolio_initiatives()
            if self._portfolio_initiative_matches(
                row,
                initiative_id=initiative_id,
                workstream_ids=workstream_ids,
                business_unit_ids=business_unit_ids,
                stages=stages,
                tags=tags,
            )
        }
        definitions = {row["id"]: row for row in self._repo.list_metric_definitions()}
        scenarios = {row["id"]: row for row in self._repo.list_financial_scenarios()}
        benefit_lines = [
            row
            for row in self._repo.list_all_benefit_lines()
            if str(row.get("initiative_id")) in initiatives
            and (
                validation_status is None
                or (row.get("validation_status") or "draft") == validation_status
            )
        ]
        totals_by_line: dict[str, dict[str, Decimal]] = {
            str(row["id"]): {"plan": Decimal("0"), "actual": Decimal("0")} for row in benefit_lines
        }
        values = self._values_with_formula_metrics(
            [
                row
                for row in self._repo.get_all_metric_values()
                if str(row.get("initiative_id")) in initiatives
                and row.get("benefit_line_id") in totals_by_line
                and (year is None or row.get("year") == year)
            ],
            [
                row
                for row in self._repo.list_all_initiative_annual_baselines()
                if str(row.get("initiative_id")) in initiatives
            ],
        )
        for row in values:
            scenario = scenarios.get(row.get("scenario_id"))
            if not scenario:
                continue
            bucket = totals_by_line.get(str(row.get("benefit_line_id")))
            if not bucket:
                continue
            if scenario.get("key") == "actual":
                bucket["actual"] += _dec(row.get("value"))
            elif scenario.get("key") == "plan_base":
                bucket["plan"] += _dec(row.get("value"))

        items: list[PortfolioBenefitsRegisterItem] = []
        totals = {
            "plan": Decimal("0"),
            "actual": Decimal("0"),
            "risk_adjusted_plan": Decimal("0"),
            "validated_plan": Decimal("0"),
            "submitted_plan": Decimal("0"),
            "rejected_plan": Decimal("0"),
        }
        for line in benefit_lines:
            initiative = initiatives.get(str(line["initiative_id"]), {})
            definition = definitions.get(line.get("metric_definition_id"), {})
            amounts = totals_by_line.get(str(line["id"]), {})
            plan = _dec(amounts.get("plan"))
            actual = _dec(amounts.get("actual"))
            risk_pct = _dec(line.get("risk_adjustment_pct") or line.get("confidence") or 100)
            risk_adjusted = plan * risk_pct / Decimal("100")
            status_value = line.get("validation_status") or "draft"
            totals["plan"] += plan
            totals["actual"] += actual
            totals["risk_adjusted_plan"] += risk_adjusted
            if status_value == "finance_validated":
                totals["validated_plan"] += plan
            elif status_value == "submitted":
                totals["submitted_plan"] += plan
            elif status_value == "rejected":
                totals["rejected_plan"] += plan
            workstream = initiative.get("workstreams") or {}
            items.append(
                PortfolioBenefitsRegisterItem(
                    initiative_id=str(line["initiative_id"]),
                    initiative_code=initiative.get("initiative_code"),
                    initiative_name=initiative.get("name") or "Untitled initiative",
                    stage=initiative.get("stage"),
                    workstream_id=initiative.get("workstream_id"),
                    workstream_name=workstream.get("name"),
                    benefit_line_id=str(line["id"]),
                    benefit_line_name=line.get("name") or "Untitled benefit",
                    metric_key=str(definition.get("key") or ""),
                    metric_label=str(definition.get("label") or "Benefit"),
                    benefit_class=definition.get("benefit_class"),
                    validation_status=status_value,
                    confidence=_money(line.get("confidence"))
                    if line.get("confidence") is not None
                    else None,
                    risk_rating=line.get("risk_rating") or "medium",
                    risk_adjustment_pct=_money(risk_pct),
                    plan=_money(plan),
                    actual=_money(actual),
                    variance=_money(actual - plan),
                    risk_adjusted_plan=_money(risk_adjusted),
                    evidence_url=line.get("evidence_url"),
                    evidence_label=line.get("evidence_label"),
                    submitted_at=line.get("submitted_at"),
                    validated_at=line.get("validated_at"),
                    validation_comment=line.get("validation_comment"),
                    rejection_reason=line.get("rejection_reason"),
                    realization_owner_id=line.get("realization_owner_id"),
                    handoff_status=line.get("handoff_status") or "not_started",
                    handoff_due_date=self._as_date(line["handoff_due_date"])
                    if line.get("handoff_due_date")
                    else None,
                )
            )
        items.sort(
            key=lambda item: (-abs(_dec(item.plan)), item.initiative_name, item.benefit_line_name)
        )
        return PortfolioBenefitsRegisterResponse(
            year=year,
            validation_status=validation_status,
            totals=PortfolioBenefitsRegisterTotals(
                plan=_money(totals["plan"]),
                actual=_money(totals["actual"]),
                variance=_money(totals["actual"] - totals["plan"]),
                risk_adjusted_plan=_money(totals["risk_adjusted_plan"]),
                validated_plan=_money(totals["validated_plan"]),
                submitted_plan=_money(totals["submitted_plan"]),
                rejected_plan=_money(totals["rejected_plan"]),
            ),
            items=items,
        )

    def export_portfolio_board_pack(
        self,
        year: int | None = None,
        basis: PortfolioValueBridgeBasis = "all_years",
    ) -> bytes:
        financials = self.get_portfolio_financials("yearly", year=year)
        value_bridge = self.get_portfolio_value_bridge(basis=basis, year=year)
        benefits_register = self.get_portfolio_benefits_register(year=year)
        ledger = self.get_benefit_ledger_rollup_summary("monthly")
        return build_board_pack_workbook(
            financials=financials,
            value_bridge=value_bridge,
            benefits_register=benefits_register,
            benefit_ledger=ledger,
        )

    def list_cell_assumptions(self, initiative_id: str) -> FinancialCellAssumptionListResponse:
        items = [
            self._to_cell_assumption(row) for row in self._repo.list_cell_assumptions(initiative_id)
        ]
        return FinancialCellAssumptionListResponse(items=items, total=len(items))

    def upsert_cell_assumption(
        self,
        initiative_id: str,
        data: FinancialCellAssumptionCreate,
        user_id: UUID,
    ) -> FinancialCellAssumption:
        self._ensure_tenant_initiative(initiative_id)
        row = self._repo.upsert_cell_assumption(
            initiative_id,
            data.model_dump(),
            str(user_id),
        )
        return self._to_cell_assumption(row)

    def update_cell_assumption(
        self,
        initiative_id: str,
        assumption_id: str,
        data: FinancialCellAssumptionUpdate,
        user_id: UUID,
    ) -> FinancialCellAssumption:
        self._ensure_tenant_initiative(initiative_id)
        row = self._repo.update_cell_assumption(
            initiative_id,
            assumption_id,
            data.comment,
            str(user_id),
        )
        return self._to_cell_assumption(row)

    def delete_cell_assumption(self, initiative_id: str, assumption_id: str) -> None:
        self._ensure_tenant_initiative(initiative_id)
        self._repo.delete_cell_assumption(initiative_id, assumption_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _transition_benefit_line_validation(
        self,
        initiative_id: str,
        benefit_line_id: str,
        *,
        status_value: FinancialBenefitValidationStatus,
        event_type: str,
        data: FinancialBenefitLineValidationRequest,
        user_id: str,
    ) -> FinancialBenefitLine:
        self._ensure_tenant_initiative(initiative_id)
        if not self._repo.get_benefit_line(initiative_id, benefit_line_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benefit line not found",
            )
        now = datetime.now(UTC).isoformat()
        patch: dict[str, object | None] = {
            "validation_status": status_value,
            "evidence_url": data.evidence_url,
            "evidence_label": data.evidence_label,
        }
        if status_value == "submitted":
            patch.update(
                {
                    "submitted_at": now,
                    "submitted_by": user_id,
                    "validation_comment": data.comment,
                    "rejection_reason": None,
                }
            )
        elif status_value == "finance_validated":
            patch.update(
                {
                    "validated_at": now,
                    "validated_by": user_id,
                    "validation_comment": data.comment,
                    "rejection_reason": None,
                }
            )
        elif status_value == "rejected":
            patch.update(
                {
                    "validated_at": now,
                    "validated_by": user_id,
                    "validation_comment": data.comment,
                    "rejection_reason": data.comment,
                }
            )
        row = self._repo.update_benefit_line(
            initiative_id,
            benefit_line_id,
            patch,
            user_id,
        )
        self._record_benefit_line_event(
            initiative_id,
            benefit_line_id,
            event_type=event_type,
            user_id=user_id,
            comment=data.comment,
            evidence_url=data.evidence_url,
            evidence_label=data.evidence_label,
        )
        return self._to_benefit_line(row)

    def _record_benefit_line_event(
        self,
        initiative_id: str,
        benefit_line_id: str,
        *,
        event_type: str,
        user_id: str,
        comment: str | None = None,
        evidence_url: str | None = None,
        evidence_label: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self._repo.create_benefit_line_validation_event(
            initiative_id,
            benefit_line_id,
            {
                "event_type": event_type,
                "actor_user_id": user_id,
                "comment": comment,
                "evidence_url": evidence_url,
                "evidence_label": evidence_label,
                "metadata": metadata or {},
            },
        )

    def _assert_no_formula_metric_values(self, values: list[object]) -> None:
        formula_definition_ids = {
            row["id"]
            for row in self._repo.list_metric_definitions()
            if row.get("aggregation") == "formula"
        }
        for value in values:
            if getattr(value, "metric_definition_id", None) in formula_definition_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formula metrics are read-only and are computed from input metrics",
                )

    def _validate_metric_definition_update(
        self,
        metric_definition_id: str,
        data: FinancialMetricDefinitionUpdate,
    ) -> None:
        existing = self._repo.list_metric_definitions()
        current = next((row for row in existing if row.get("id") == metric_definition_id), None)
        if not current:
            return
        candidate = {**current, **data.model_dump(mode="json", exclude_none=True)}
        self._validate_metric_definition_payload(candidate, existing, metric_definition_id)

    def _validate_metric_definition_payload(
        self,
        candidate: dict[str, object],
        existing: list[dict] | None = None,  # type: ignore[type-arg]
        existing_id: str | None = None,
    ) -> None:
        definitions = list(
            existing if existing is not None else self._repo.list_metric_definitions()
        )
        if existing_id:
            definitions = [row for row in definitions if row.get("id") != existing_id]
        definitions.append(candidate)

        if candidate.get("aggregation") != "formula":
            return

        formula = str(candidate.get("formula") or "").strip()
        if not formula:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formula metrics require a formula expression",
            )

        metric_keys = {str(row["key"]) for row in definitions if row.get("is_active", True)}
        metric_keys |= {f"baseline_{key}" for key in metric_keys}
        try:
            referenced_keys = self._formula_identifiers(formula)
            self._validate_formula_expression(formula, metric_keys)
        except FormulaValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        formula_inputs = {str(item) for item in candidate.get("formula_inputs") or []}
        if formula_inputs and formula_inputs != referenced_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formula inputs must match the metric keys referenced in the formula",
            )
        if str(candidate.get("key")) in referenced_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formula metrics cannot reference themselves",
            )
        self._validate_formula_graph(definitions)

    def _validate_formula_graph(self, definitions: list[dict]) -> None:  # type: ignore[type-arg]
        formula_keys = {
            str(row["key"])
            for row in definitions
            if row.get("aggregation") == "formula" and row.get("is_active", True)
        }
        graph: dict[str, set[str]] = {}
        for row in definitions:
            key = str(row["key"])
            if key not in formula_keys:
                continue
            formula = str(row.get("formula") or "").strip()
            if not formula:
                continue
            graph[key] = self._formula_identifiers(formula) & formula_keys

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visited:
                return
            if key in visiting:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Formula metric dependencies cannot contain cycles",
                )
            visiting.add(key)
            for dependency in graph.get(key, set()):
                visit(dependency)
            visiting.remove(key)
            visited.add(key)

        for key in graph:
            visit(key)

    def _values_with_formula_metrics(
        self,
        values: list[dict],  # type: ignore[type-arg]
        baseline_values: list[dict] | None = None,  # type: ignore[type-arg]
    ) -> list[dict]:  # type: ignore[type-arg]
        if not values:
            return values
        definitions = self._repo.list_metric_definitions()
        definition_by_id = {row["id"]: row for row in definitions}
        formula_definitions = self._ordered_formula_definitions(
            [
                row
                for row in definitions
                if row.get("aggregation") == "formula"
                and row.get("is_active", True)
                and row.get("formula")
            ]
        )
        if not formula_definitions:
            return values

        stored_values = [
            row
            for row in values
            if definition_by_id.get(row.get("metric_definition_id"), {}).get("aggregation")
            != "formula"
        ]
        group_keys = sorted(
            {
                (
                    row.get("tenant_id"),
                    row.get("initiative_id"),
                    row.get("scenario_id"),
                    int(row["year"]),
                    int(row["month"]),
                )
                for row in stored_values
            },
            key=lambda item: tuple(str(part) for part in item),
        )
        baseline_env_by_initiative: dict[object, dict[str, Decimal]] = {}
        for row in baseline_values or []:
            definition = definition_by_id.get(row.get("metric_definition_id"))
            if not definition:
                continue
            initiative_id = row.get("initiative_id")
            key = str(definition["key"])
            env = baseline_env_by_initiative.setdefault(initiative_id, {})
            amount = _dec(row.get("value"))
            env.setdefault(key, amount)
            env[f"baseline_{key}"] = amount
        computed: list[dict] = []
        for tenant_id, initiative_id, scenario_id, year, month in group_keys:
            env: dict[str, Decimal] = dict(baseline_env_by_initiative.get(initiative_id, {}))
            for row in stored_values:
                if (
                    row.get("tenant_id"),
                    row.get("initiative_id"),
                    row.get("scenario_id"),
                    int(row["year"]),
                    int(row["month"]),
                ) != (tenant_id, initiative_id, scenario_id, year, month):
                    continue
                definition = definition_by_id.get(row.get("metric_definition_id"))
                if not definition:
                    continue
                key = str(definition["key"])
                env[key] = env.get(key, Decimal("0")) + _dec(row.get("value"))

            for definition in formula_definitions:
                key = str(definition["key"])
                formula = str(definition.get("formula") or "")
                try:
                    env[key] = self._evaluate_formula(formula, env)
                except (FormulaValidationError, FormulaDivideByZeroError):
                    env[key] = Decimal("0")
                computed.append(
                    {
                        "id": (
                            f"formula:{initiative_id or 'portfolio'}:{scenario_id}:"
                            f"{year}:{month}:{definition['id']}"
                        ),
                        "tenant_id": tenant_id,
                        "initiative_id": initiative_id,
                        "metric_definition_id": definition["id"],
                        "benefit_line_id": None,
                        "scenario_id": scenario_id,
                        "year": year,
                        "month": month,
                        "value": _money(env[key]),
                        "status": "approved",
                        "note": "Computed formula metric",
                        "_computed_formula": True,
                    }
                )
        return [*stored_values, *computed]

    @staticmethod
    def _formula_identifiers(formula: str) -> set[str]:
        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError as exc:
            raise FormulaValidationError("Formula expression is invalid") from exc
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

    @classmethod
    def _ordered_formula_definitions(cls, definitions: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        definition_by_key = {str(row["key"]): row for row in definitions}
        formula_keys = set(definition_by_key)
        graph = {
            key: cls._formula_identifiers(str(row.get("formula") or "")) & formula_keys
            for key, row in definition_by_key.items()
        }
        ordered: list[dict] = []  # type: ignore[type-arg]
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visited:
                return
            if key in visiting:
                raise FormulaValidationError("Formula metric dependencies cannot contain cycles")
            visiting.add(key)
            for dependency in sorted(graph.get(key, set())):
                visit(dependency)
            visiting.remove(key)
            visited.add(key)
            ordered.append(definition_by_key[key])

        for row in definitions:
            visit(str(row["key"]))
        return ordered

    @classmethod
    def _validate_formula_expression(cls, formula: str, metric_keys: set[str]) -> None:
        referenced_keys = cls._formula_identifiers(formula)
        unknown = sorted(referenced_keys - metric_keys)
        if unknown:
            raise FormulaValidationError(
                f"Formula references unknown metric keys: {', '.join(unknown)}"
            )
        cls._evaluate_formula(formula, {key: Decimal("1") for key in referenced_keys})

    @classmethod
    def _evaluate_formula(cls, formula: str, values: dict[str, Decimal]) -> Decimal:
        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError as exc:
            raise FormulaValidationError("Formula expression is invalid") from exc
        return cls._evaluate_formula_node(tree.body, values)

    @classmethod
    def _evaluate_formula_node(cls, node: ast.AST, values: dict[str, Decimal]) -> Decimal:
        if isinstance(node, ast.BinOp):
            left = cls._evaluate_formula_node(node.left, values)
            right = cls._evaluate_formula_node(node.right, values)
            if isinstance(node.op, ast.Div):
                if right == Decimal("0"):
                    raise FormulaDivideByZeroError("Formula division by zero")
                return left / right
            operator_fn = _FORMULA_OPERATORS.get(type(node.op))
            if operator_fn is None:
                raise FormulaValidationError("Formula uses an unsupported operator")
            return operator_fn(left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = cls._evaluate_formula_node(node.operand, values)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.Name):
            return values.get(node.id, Decimal("0"))
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return Decimal(str(node.value))
        raise FormulaValidationError("Formula uses unsupported syntax")

    @staticmethod
    def _to_entry_row(row: dict) -> FinancialEntryRow:  # type: ignore[type-arg]
        def _actual(key: str) -> str | None:
            v = row.get(key)
            return _money(v) if v is not None else None

        return FinancialEntryRow(
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            revenue_uplift_base=_money(row.get("revenue_uplift_base")),
            revenue_uplift_high=_money(row.get("revenue_uplift_high")),
            revenue_uplift_actual=_actual("revenue_uplift_actual"),
            revenue_uplift_pct_base=_money(row.get("revenue_uplift_pct_base")),
            revenue_uplift_pct_high=_money(row.get("revenue_uplift_pct_high")),
            revenue_uplift_pct_actual=_actual("revenue_uplift_pct_actual"),
            gross_margin_base=_money(row.get("gross_margin_base")),
            gross_margin_high=_money(row.get("gross_margin_high")),
            gross_margin_actual=_actual("gross_margin_actual"),
            gm_pct_base=_money(row.get("gm_pct_base")),
            gm_pct_high=_money(row.get("gm_pct_high")),
            gm_pct_actual=_actual("gm_pct_actual"),
            gm_uplift_base=_money(row.get("gm_uplift_base")),
            gm_uplift_high=_money(row.get("gm_uplift_high")),
            gm_uplift_actual=_actual("gm_uplift_actual"),
            gm_uplift_pct_base=_money(row.get("gm_uplift_pct_base")),
            gm_uplift_pct_high=_money(row.get("gm_uplift_pct_high")),
            gm_uplift_pct_actual=_actual("gm_uplift_pct_actual"),
            cogs_base=_money(row.get("cogs_base")),
            cogs_high=_money(row.get("cogs_high")),
            cogs_actual=_actual("cogs_actual"),
            cogs_pct_base=_money(row.get("cogs_pct_base")),
            cogs_pct_high=_money(row.get("cogs_pct_high")),
            cogs_pct_actual=_actual("cogs_pct_actual"),
        )

    @staticmethod
    def _to_metric_value_row(row: dict) -> FinancialMetricValueRow:  # type: ignore[type-arg]
        def _actual(key: str) -> str | None:
            value = row.get(key)
            return _money(value) if value is not None else None

        return FinancialMetricValueRow(
            metric_key=row["metric_key"],
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            value_base=_money(row.get("value_base")),
            value_high=_money(row.get("value_high")),
            value_actual=_actual("value_actual"),
        )

    @staticmethod
    def _to_annual_baseline_value(
        row: dict,  # type: ignore[type-arg]
        definitions: dict[str, dict] | None = None,  # type: ignore[type-arg]
    ) -> AnnualBaselineMetricValueRow:
        definition = (definitions or {}).get(row.get("metric_definition_id")) or {}
        return AnnualBaselineMetricValueRow(
            id=row["id"],
            metric_definition_id=row["metric_definition_id"],
            metric_key=definition.get("key"),
            metric_label=definition.get("label"),
            baseline_year=int(row["baseline_year"]),
            value=_money(row.get("value")),
            note=row.get("note"),
            source=row.get("source"),
            locked_at=str(row["locked_at"]) if row.get("locked_at") else None,
            locked_by=row.get("locked_by"),
            lock_gate_number=row.get("lock_gate_number"),
        )

    def _baseline_lock_state(self, initiative_id: str) -> tuple[bool, str | None]:
        settings = self.get_governance_settings()
        if settings.baseline_lock_on_approval and self._repo.has_approved_gate_submission(
            initiative_id,
            settings.baseline_lock_gate_number,
        ):
            return (
                True,
                f"Annual baseline values are locked after Gate {settings.baseline_lock_gate_number} approval.",
            )
        return False, None

    def _financial_lock_state(self, initiative_id: str) -> tuple[bool, str | None]:
        settings = self.get_governance_settings()
        if settings.plan_lock_on_approval and self._repo.get_latest_bankable_plan(initiative_id):
            return (
                True,
                "Approved plan values are locked; forecast and actual values remain editable.",
            )
        return False, None

    def _financial_mode_descriptor(
        self,
        initiative_id: str,
        entries: list[dict],  # type: ignore[type-arg]
        costs: list[dict],  # type: ignore[type-arg]
        metric_values: list[dict],  # type: ignore[type-arg]
        *,
        config: FinancialConfigurationResponse | None = None,
        bankable_plan: BankablePlanVersion | None = None,
    ) -> FinancialModeDescriptor:
        if bankable_plan is None and initiative_id:
            bankable_plan = self.get_current_bankable_plan(initiative_id)
        if bankable_plan:
            return FinancialModeDescriptor(
                key="bankable_locked",
                label="Locked bankable plan",
                description="Immutable baseline created from an approved stage-gate submission.",
                locked=True,
                scenarios=["approval", "rebaseline"],
            )

        mode_key = "planned_vs_actual"
        label = "Planned vs actual"
        description = "Planned vs actual reporting is active."
        scenarios = ["planned", "actual"]
        if self._has_multi_scenario_signal(entries, metric_values, config=config):
            mode_key = "multi_scenario"
            label = "Multi-scenario plan"
            description = "Base, high, and actual scenarios are available."
            scenarios = ["base", "high", "actual"]
        elif not self._has_any_actual_signal(entries, costs, metric_values):
            mode_key = "pre_lock"
            label = "Pre-lock plan"
            description = "Editable planning surface before approval."
            scenarios = ["planned"]
        return FinancialModeDescriptor(
            key=mode_key,
            label=label,
            description=description,
            locked=False,
            scenarios=scenarios,
        )

    @staticmethod
    def _has_any_actual_signal(
        entries: list[dict],  # type: ignore[type-arg]
        costs: list[dict],  # type: ignore[type-arg]
        metric_values: list[dict],  # type: ignore[type-arg]
    ) -> bool:
        for row in entries:
            if any(
                _dec(row.get(field)) != Decimal("0")
                for field in (
                    "revenue_uplift_actual",
                    "gross_margin_actual",
                    "gm_uplift_actual",
                    "cogs_actual",
                )
            ):
                return True
        for row in costs:
            if row.get("amount_actual") is not None:
                return True
        return any(row.get("value_actual") is not None for row in metric_values)

    @staticmethod
    def _has_multi_scenario_signal(
        entries: list[dict],  # type: ignore[type-arg]
        metric_values: list[dict],  # type: ignore[type-arg]
        *,
        config: FinancialConfigurationResponse | None = None,
    ) -> bool:
        for row in entries:
            for base_field, high_field in (
                ("revenue_uplift_base", "revenue_uplift_high"),
                ("gross_margin_base", "gross_margin_high"),
                ("gm_uplift_base", "gm_uplift_high"),
                ("cogs_base", "cogs_high"),
            ):
                if _dec(row.get(base_field)) != _dec(row.get(high_field)):
                    return True
        for row in metric_values:
            if _dec(row.get("value_base")) != _dec(row.get("value_high")):
                return True
        if config:
            return any(
                item.is_active
                and item.item_type == "metric"
                and item.system_metric_key
                in {
                    "revenue_uplift_base",
                    "revenue_uplift_high",
                    "gross_margin_base",
                    "gross_margin_high",
                }
                for item in config.items
            )
        return False

    def _assert_financials_editable(self, initiative_id: str) -> None:
        locked, reason = self._financial_lock_state(initiative_id)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=reason or "Financials are locked for this initiative.",
            )

    def _resolve_selections(
        self,
        initiative_id: str,
        entries: list[dict],  # type: ignore[type-arg]
        costs: list[dict],  # type: ignore[type-arg]
        metric_values: list[dict],  # type: ignore[type-arg]
        config: FinancialConfigurationResponse | None = None,
    ) -> InitiativeFinancialSelections:
        valid_metric_keys, valid_cost_keys = self._active_selection_keys(config)
        scope_rows = getattr(self._repo, "list_financial_scope", lambda _initiative_id: [])(
            initiative_id
        )
        if scope_rows:
            definitions = {
                row["id"]: row
                for row in getattr(self._repo, "list_metric_definitions", lambda: [])()
            }
            categories = {
                row["id"]: row for row in getattr(self._repo, "list_cost_categories", lambda: [])()
            }
            metric_definition_ids = {
                str(row["metric_definition_id"])
                for row in scope_rows
                if row.get("scope_type") == "metric_definition"
                and row.get("is_active", True)
                and row.get("metric_definition_id") in definitions
            }
            cost_category_ids = {
                str(row["cost_category_id"])
                for row in scope_rows
                if row.get("scope_type") == "cost_category"
                and row.get("is_active", True)
                and row.get("cost_category_id") in categories
            }
            metric_keys = {
                str(definitions[metric_id]["key"])
                for metric_id in metric_definition_ids
                if str(definitions[metric_id]["key"]) in valid_metric_keys
            }
            cost_keys = {
                str(categories[category_id]["key"])
                for category_id in cost_category_ids
                if str(categories[category_id]["key"]) in valid_cost_keys
            }
            return InitiativeFinancialSelections(
                metric_keys=sorted(metric_keys),
                cost_category_keys=sorted(cost_keys),
                metric_definition_ids=sorted(metric_definition_ids),
                cost_category_ids=sorted(cost_category_ids),
            )
        selection_rows = self._repo.list_financial_selections(initiative_id)
        if selection_rows:
            metric_keys = {
                row["item_key"]
                for row in selection_rows
                if row.get("item_type") == "metric"
                and row.get("is_active", True)
                and row["item_key"] in valid_metric_keys
            }
            cost_keys = {
                row["item_key"]
                for row in selection_rows
                if row.get("item_type") == "cost_category"
                and row.get("is_active", True)
                and row["item_key"] in valid_cost_keys
            }
        else:
            metric_keys = set(self._default_metric_keys())
            cost_keys = set(self._default_cost_category_keys())
            for row in entries:
                self._add_data_bearing_metric_keys(
                    metric_keys,
                    row,
                    [
                        "revenue_uplift",
                        "revenue_uplift_pct",
                        "gross_margin",
                        "gm_pct",
                        "gm_uplift",
                        "gm_uplift_pct",
                        "cogs",
                        "cogs_pct",
                    ],
                )
            for row in metric_values:
                if (
                    self._metric_value_has_value(row)
                    and str(row["metric_key"]) in valid_metric_keys
                ):
                    metric_keys.add(str(row["metric_key"]))

            for row in costs:
                category_key = str(row.get("category_key") or "other")
                if self._cost_line_has_value(row) and category_key in valid_cost_keys:
                    cost_keys.add(category_key)

        metric_keys = metric_keys & valid_metric_keys
        cost_keys = cost_keys & valid_cost_keys
        definitions_by_key = {
            row["key"]: row for row in getattr(self._repo, "list_metric_definitions", lambda: [])()
        }
        categories_by_key = {
            row["key"]: row for row in getattr(self._repo, "list_cost_categories", lambda: [])()
        }
        return InitiativeFinancialSelections(
            metric_keys=sorted(metric_keys),
            cost_category_keys=sorted(cost_keys),
            metric_definition_ids=sorted(
                str(definitions_by_key[key]["id"])
                for key in metric_keys
                if key in definitions_by_key
            ),
            cost_category_ids=sorted(
                str(categories_by_key[key]["id"]) for key in cost_keys if key in categories_by_key
            ),
        )

    def _active_selection_keys(
        self,
        config: FinancialConfigurationResponse | None = None,
    ) -> tuple[set[str], set[str]]:
        config = config or self.get_configuration()
        return (
            {
                item.system_metric_key or item.key
                for item in config.items
                if item.item_type == "metric" and item.is_active
            },
            {
                item.key
                for item in config.items
                if item.item_type == "cost_category" and item.is_active
            },
        )

    def initialize_default_selections(self, initiative_id: str) -> None:
        valid_metric_keys, valid_cost_keys = self._active_selection_keys()
        engine = self.get_engine_configuration()
        metric_ids_by_key = {
            definition.key: str(definition.id) for definition in engine.definitions
        }
        category_ids_by_key = {
            category.key: str(category.id) for category in engine.cost_categories if category.id
        }
        default_metric_ids = [
            metric_ids_by_key[key]
            for key in self._default_metric_keys()
            if key in metric_ids_by_key
        ]
        default_category_ids = [
            category_ids_by_key[key]
            for key in self._default_cost_category_keys()
            if key in category_ids_by_key
        ]
        getattr(self._repo, "replace_financial_scope", lambda *args, **kwargs: None)(
            initiative_id,
            default_metric_ids,
            default_category_ids,
            sorted(metric_ids_by_key.values()),
            sorted(category_ids_by_key.values()),
        )
        self._repo.replace_financial_selections(
            initiative_id,
            self._default_metric_keys(),
            self._default_cost_category_keys(),
            sorted(valid_metric_keys),
            sorted(valid_cost_keys),
        )

    @staticmethod
    def _default_metric_keys() -> list[str]:
        return [
            "revenue_uplift",
            "gross_margin",
            "gm_uplift",
            "cost_savings",
        ]

    @staticmethod
    def _add_data_bearing_metric_keys(
        metric_keys: set[str],
        row: dict,  # type: ignore[type-arg]
        prefixes: list[str],
    ) -> None:
        for prefix in prefixes:
            fields = [f"{prefix}_base", f"{prefix}_high", f"{prefix}_actual"]
            if any(_dec(row.get(field)) != Decimal("0") for field in fields):
                metric_keys.update(fields)

    @staticmethod
    def _default_cost_category_keys() -> list[str]:
        return [
            "implementation",
            "technology_tooling",
            "external_consultants",
            "training_change",
            "other_one_off",
            "software_subscriptions",
            "support_maintenance",
            "additional_headcount",
            "run_rate_operating",
            "maintenance",
            "software",
            "labor",
            "other",
        ]

    def _apply_financial_scope(
        self,
        entries: list[dict],  # type: ignore[type-arg]
        costs: list[dict],  # type: ignore[type-arg]
        selections: InitiativeFinancialSelections,
    ) -> tuple[list[dict], list[dict]]:  # type: ignore[type-arg]
        selected_metrics = set(selections.metric_keys)
        selected_costs = set(selections.cost_category_keys)
        scoped_entries = [
            self._entry_with_inactive_metrics_zeroed(row, selected_metrics) for row in entries
        ]
        scoped_costs = [
            row for row in costs if str(row.get("category_key") or "other") in selected_costs
        ]
        return scoped_entries, scoped_costs

    @staticmethod
    def _entry_with_inactive_metrics_zeroed(
        row: dict,  # type: ignore[type-arg]
        selected_metrics: set[str],
    ) -> dict:  # type: ignore[type-arg]
        scoped = dict(row)
        for field in _ENTRY_FIELDS:
            if field not in selected_metrics:
                scoped[field] = None if field.endswith("_actual") else "0"
        return scoped

    def _migrate_existing_grid_to_planned_window(self, initiative_id: str) -> None:
        initiative = self._repo.get_initiative_period(initiative_id)
        start, end = self._planned_month_bounds(initiative)
        if start is None or end is None:
            return

        rows = self._repo.get_entries(initiative_id)
        costs = self._repo.list_cost_lines(initiative_id)
        metric_values = self._repo.list_metric_values(initiative_id)
        if not any(
            self._period_outside_window(row, start, end) for row in [*rows, *costs, *metric_values]
        ):
            return

        normalized = self._normalize_grid_to_planned_window(
            initiative_id,
            FinancialGridUpdate(
                entries=[FinancialEntryUpdate(**self._entry_update_payload(row)) for row in rows],
                cost_lines=[CostLineCreate(**self._cost_line_update_payload(row)) for row in costs],
                metric_values=[
                    FinancialMetricValueUpdate(**self._metric_value_update_payload(row))
                    for row in metric_values
                ],
            ),
        )

        self._repo.delete_grid(initiative_id)
        if normalized.entries:
            self._repo.upsert_entries_batch(
                initiative_id,
                [self._entry_write_payload(entry) for entry in normalized.entries],
            )
        if normalized.cost_lines:
            self._repo.upsert_cost_lines_batch(
                initiative_id,
                [self._cost_line_write_payload(cost) for cost in normalized.cost_lines],
            )
        if normalized.metric_values:
            self._repo.upsert_metric_values_batch(
                initiative_id,
                [self._metric_value_write_payload(metric) for metric in normalized.metric_values],
            )

    @staticmethod
    def _period_outside_window(row: dict, start: int, end: int) -> bool:  # type: ignore[type-arg]
        month = row.get("month")
        quarter = row.get("quarter")
        if month is None:
            row_month = (int(quarter) - 1) * 3 + 1 if quarter is not None else 1
        else:
            row_month = int(month)
        key = int(row["year"]) * 12 + row_month
        return key < start or key > end

    @staticmethod
    def _entry_update_payload(row: dict) -> dict:  # type: ignore[type-arg]
        payload = {
            "year": row["year"],
            "quarter": row.get("quarter"),
            "month": row.get("month"),
        }
        for field in FinancialEntryUpdate.model_fields:
            if field in payload:
                continue
            value = row.get(field)
            if value is not None:
                payload[field] = value
        return payload

    @staticmethod
    def _cost_line_update_payload(row: dict) -> dict:  # type: ignore[type-arg]
        return {
            "name": row.get("name") or "Cost (Grid)",
            "category_key": row.get("category_key") or "other",
            "year": row["year"],
            "quarter": row.get("quarter"),
            "month": row.get("month"),
            "amount_plan": row.get("amount_plan") or "0",
            "amount_actual": row.get("amount_actual"),
            "is_recurring": bool(row.get("is_recurring")),
        }

    @staticmethod
    def _metric_value_update_payload(row: dict) -> dict:  # type: ignore[type-arg]
        return {
            "metric_key": row["metric_key"],
            "year": row["year"],
            "quarter": row.get("quarter"),
            "month": row.get("month"),
            "value_base": row.get("value_base") or "0",
            "value_high": row.get("value_high") or "0",
            "value_actual": row.get("value_actual"),
        }

    @staticmethod
    def _entry_write_payload(entry: FinancialEntryUpdate) -> dict[str, object]:
        row: dict[str, object] = {
            "year": entry.year,
            "quarter": entry.quarter,
            "month": entry.month,
        }
        for field_name in FinancialEntryUpdate.model_fields:
            if field_name in {"year", "quarter", "month"}:
                continue
            value = getattr(entry, field_name)
            row[field_name] = _money(value) if value is not None else None
        return row

    @staticmethod
    def _cost_line_write_payload(cost: CostLineCreate) -> dict[str, object]:
        return {
            "name": cost.name,
            "category_key": cost.category_key,
            "year": cost.year,
            "quarter": cost.quarter,
            "month": cost.month,
            "amount_plan": _money(cost.amount_plan),
            "amount_actual": _money(cost.amount_actual) if cost.amount_actual is not None else None,
            "is_recurring": cost.is_recurring,
        }

    @staticmethod
    def _metric_value_write_payload(metric: FinancialMetricValueUpdate) -> dict[str, object]:
        return {
            "metric_key": metric.metric_key,
            "year": metric.year,
            "quarter": metric.quarter,
            "month": metric.month,
            "value_base": _money(metric.value_base),
            "value_high": _money(metric.value_high),
            "value_actual": _money(metric.value_actual)
            if metric.value_actual is not None
            else None,
        }

    def _normalize_grid_to_planned_window(
        self,
        initiative_id: str,
        data: FinancialGridUpdate,
    ) -> FinancialGridUpdate:
        initiative = self._repo.get_initiative_period(initiative_id)
        first_month = self._first_planned_month(initiative)
        if first_month is None:
            return data

        start, end = self._planned_month_bounds(initiative)
        if start is None or end is None:
            return data

        target_year, target_month = first_month

        def normalize_period(row: object) -> tuple[int, int | None, int | None]:
            year = int(row.year)
            month = row.month
            quarter = row.quarter
            if month is None:
                row_month = (quarter - 1) * 3 + 1 if quarter is not None else 1
            else:
                row_month = int(month)
            key = year * 12 + row_month
            if start <= key <= end:
                return year, month, quarter
            return target_year, target_month, None

        entry_map: dict[tuple[int, int | None, int | None], dict[str, Decimal | None | int]] = {}
        for entry in data.entries:
            year, month, quarter = normalize_period(entry)
            key = (year, month, quarter)
            current = entry_map.setdefault(key, {"year": year, "month": month, "quarter": quarter})
            for field_name in FinancialEntryUpdate.model_fields:
                if field_name in {"year", "month", "quarter"}:
                    continue
                value = getattr(entry, field_name)
                if value is None:
                    continue
                current[field_name] = _dec(current.get(field_name)) + _dec(value)

        metric_map: dict[
            tuple[str, int, int | None, int | None], dict[str, Decimal | None | int | str]
        ] = {}
        for metric in data.metric_values or []:
            year, month, quarter = normalize_period(metric)
            key = (metric.metric_key, year, month, quarter)
            current = metric_map.setdefault(
                key,
                {"metric_key": metric.metric_key, "year": year, "month": month, "quarter": quarter},
            )
            for field_name in ("value_base", "value_high", "value_actual"):
                value = getattr(metric, field_name)
                if value is None:
                    continue
                current[field_name] = _dec(current.get(field_name)) + _dec(value)

        cost_map: dict[
            tuple[str, bool, int, int | None, int | None],
            dict[str, Decimal | None | int | bool | str],
        ] = {}
        for cost in data.cost_lines or []:
            year, month, quarter = normalize_period(cost)
            key = (cost.category_key, cost.is_recurring, year, month, quarter)
            current = cost_map.setdefault(
                key,
                {
                    "name": cost.name,
                    "category_key": cost.category_key,
                    "year": year,
                    "month": month,
                    "quarter": quarter,
                    "amount_plan": Decimal("0"),
                    "amount_actual": None,
                    "is_recurring": cost.is_recurring,
                },
            )
            current["amount_plan"] = _dec(current.get("amount_plan")) + _dec(cost.amount_plan)
            if cost.amount_actual is not None:
                current["amount_actual"] = _dec(current.get("amount_actual")) + _dec(
                    cost.amount_actual
                )

        return FinancialGridUpdate(
            entries=[FinancialEntryUpdate(**row) for row in entry_map.values()],
            cost_lines=[CostLineCreate(**row) for row in cost_map.values()],
            metric_values=[FinancialMetricValueUpdate(**row) for row in metric_map.values()],
        )

    @staticmethod
    def _planned_month_bounds(
        initiative: dict | None,  # type: ignore[type-arg]
    ) -> tuple[int | None, int | None]:
        if (
            not initiative
            or not initiative.get("planned_start")
            or not initiative.get("planned_end")
        ):
            return None, None
        start = date.fromisoformat(str(initiative["planned_start"]))
        end = date.fromisoformat(str(initiative["planned_end"]))
        return start.year * 12 + start.month, end.year * 12 + end.month

    @staticmethod
    def _first_planned_month(initiative: dict | None) -> tuple[int, int] | None:  # type: ignore[type-arg]
        if not initiative or not initiative.get("planned_start"):
            return None
        start = date.fromisoformat(str(initiative["planned_start"]))
        return start.year, start.month

    @staticmethod
    def _unique_entries(rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        by_period: dict[tuple[object, object, object], dict] = {}
        for row in rows:
            key = (row["year"], row.get("quarter"), row.get("month"))
            by_period.setdefault(key, row)
        return list(by_period.values())

    @staticmethod
    def _unique_cost_lines(rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        by_line: dict[tuple[object, object, object, object, object], dict] = {}
        for row in rows:
            key = (
                row["name"],
                row["year"],
                row.get("quarter"),
                row.get("month"),
                row.get("is_recurring", False),
            )
            by_line.setdefault(key, row)
        return list(by_line.values())

    def _compute_summary(
        self,
        rows: list[dict],  # type: ignore[type-arg]
        initiative_id: str,
        cost_lines: list[dict] | None = None,  # type: ignore[type-arg]
        metric_values: list[dict] | None = None,  # type: ignore[type-arg]
        config: FinancialConfigurationResponse | None = None,
    ) -> FinancialSummary:
        """Aggregate summary cards from all entries + cost lines.

        Net Run-rate Impact = Total Benefits - Recurring Costs.
        """
        # Revenue uplift aggregation
        rev_base = Decimal("0")
        rev_high = Decimal("0")
        rev_actual: Decimal | None = None

        # Gross margin aggregation
        gm_base = Decimal("0")
        gm_high = Decimal("0")
        gm_actual: Decimal | None = None

        # GM Uplift aggregation
        gm_up_base = Decimal("0")
        gm_up_high = Decimal("0")
        gm_up_actual: Decimal | None = None

        # COGS aggregation
        cogs_base = Decimal("0")
        cogs_high = Decimal("0")
        cogs_actual: Decimal | None = None

        for r in self._reporting_rows(rows):
            rev_base += _dec(r.get("revenue_uplift_base"))
            rev_high += _dec(r.get("revenue_uplift_high"))
            if r.get("revenue_uplift_actual") is not None:
                rev_actual = (rev_actual or Decimal("0")) + _dec(r["revenue_uplift_actual"])

            gm_base += _dec(r.get("gross_margin_base"))
            gm_high += _dec(r.get("gross_margin_high"))
            if r.get("gross_margin_actual") is not None:
                gm_actual = (gm_actual or Decimal("0")) + _dec(r["gross_margin_actual"])

            gm_up_base += _dec(r.get("gm_uplift_base"))
            gm_up_high += _dec(r.get("gm_uplift_high"))
            if r.get("gm_uplift_actual") is not None:
                gm_up_actual = (gm_up_actual or Decimal("0")) + _dec(r["gm_uplift_actual"])

            cogs_base += _dec(r.get("cogs_base"))
            cogs_high += _dec(r.get("cogs_high"))
            if r.get("cogs_actual") is not None:
                cogs_actual = (cogs_actual or Decimal("0")) + _dec(r["cogs_actual"])

        # Cost aggregation — split by one-off vs recurring
        cost_lines = self._reporting_cost_lines(
            cost_lines if cost_lines is not None else self._repo.list_cost_lines(initiative_id)
        )
        costs_recurring_plan = Decimal("0")
        costs_recurring_actual: Decimal | None = None
        costs_one_off_plan = Decimal("0")
        costs_one_off_actual: Decimal | None = None

        for cl in cost_lines:
            plan = _dec(cl.get("amount_plan"))
            actual_val = cl.get("amount_actual")

            if cl.get("is_recurring", False):
                costs_recurring_plan += plan
                if actual_val is not None:
                    costs_recurring_actual = (costs_recurring_actual or Decimal("0")) + _dec(
                        actual_val
                    )
            else:
                costs_one_off_plan += plan
                if actual_val is not None:
                    costs_one_off_actual = (costs_one_off_actual or Decimal("0")) + _dec(actual_val)

        custom_benefit_base, _, custom_benefit_actual = self._custom_benefit_totals(
            metric_values or [], config
        )
        benefits_base = gm_up_base + custom_benefit_base
        benefits_actual: Decimal | None = gm_up_actual
        if custom_benefit_actual is not None:
            benefits_actual = (benefits_actual or Decimal("0")) + custom_benefit_actual

        costs_plan = costs_recurring_plan + costs_one_off_plan
        costs_actual: Decimal | None = None
        if costs_recurring_actual is not None or costs_one_off_actual is not None:
            costs_actual = (costs_recurring_actual or Decimal("0")) + (
                costs_one_off_actual or Decimal("0")
            )

        net_plan = benefits_base - costs_recurring_plan
        net_actual: Decimal | None = None
        if benefits_actual is not None and costs_recurring_actual is not None:
            net_actual = benefits_actual - costs_recurring_actual

        return FinancialSummary(
            revenue_uplift_plan_base=_money(rev_base),
            revenue_uplift_plan_high=_money(rev_high),
            revenue_uplift_actual=_str_or_none(rev_actual),
            gross_margin_plan_base=_money(gm_base),
            gross_margin_plan_high=_money(gm_high),
            gross_margin_actual=_str_or_none(gm_actual),
            gm_uplift_plan_base=_money(gm_up_base),
            gm_uplift_plan_high=_money(gm_up_high),
            gm_uplift_actual=_str_or_none(gm_up_actual),
            cogs_plan_base=_money(cogs_base),
            cogs_plan_high=_money(cogs_high),
            cogs_actual=_str_or_none(cogs_actual),
            costs_recurring_plan=_money(costs_recurring_plan),
            costs_recurring_actual=_str_or_none(costs_recurring_actual),
            costs_one_off_plan=_money(costs_one_off_plan),
            costs_one_off_actual=_str_or_none(costs_one_off_actual),
            costs_plan=_money(costs_plan),
            costs_actual=_str_or_none(costs_actual),
            net_value_plan=_money(net_plan),
            net_value_actual=_str_or_none(net_actual),
            benefit_run_rate=_money(benefits_base),
            cost_run_rate=_money(costs_recurring_plan),  # annualised recurring costs
        )

    @staticmethod
    def _reporting_rows(rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        """Return rows for rollups without counting quarter rows covered by month rows."""
        month_keys = {
            (row["initiative_id"], row["year"], ((row["month"] - 1) // 3) + 1)
            for row in rows
            if row.get("month") is not None and FinancialService._financial_row_has_value(row)
        }
        reporting = []
        for row in rows:
            if row.get("month") is not None:
                reporting.append(row)
                continue
            quarter = row.get("quarter")
            if quarter is None:
                reporting.append(row)
                continue
            key = (row["initiative_id"], row["year"], quarter)
            if key not in month_keys:
                reporting.append(row)
        return reporting

    @staticmethod
    def _reporting_cost_lines(rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        """Return cost lines for rollups without counting quarter rows covered by month rows."""
        month_keys = {
            (
                row["initiative_id"],
                row["year"],
                ((row["month"] - 1) // 3) + 1,
                row.get("category_key") or "other",
                bool(row.get("is_recurring", False)),
            )
            for row in rows
            if row.get("month") is not None and FinancialService._cost_line_has_value(row)
        }
        reporting = []
        for row in rows:
            if row.get("month") is not None:
                reporting.append(row)
                continue
            quarter = row.get("quarter")
            if quarter is None:
                reporting.append(row)
                continue
            key = (
                row["initiative_id"],
                row["year"],
                quarter,
                row.get("category_key") or "other",
                bool(row.get("is_recurring", False)),
            )
            if key not in month_keys:
                reporting.append(row)
        return reporting

    @staticmethod
    def _reporting_metric_values(rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        """Return custom metric values without counting quarter rows covered by month rows."""
        month_keys = {
            (
                row["initiative_id"],
                row["year"],
                ((row["month"] - 1) // 3) + 1,
                row.get("metric_key"),
            )
            for row in rows
            if row.get("month") is not None and FinancialService._metric_value_has_value(row)
        }
        reporting = []
        for row in rows:
            if row.get("month") is not None:
                reporting.append(row)
                continue
            quarter = row.get("quarter")
            if quarter is None:
                reporting.append(row)
                continue
            key = (row["initiative_id"], row["year"], quarter, row.get("metric_key"))
            if key not in month_keys:
                reporting.append(row)
        return reporting

    @staticmethod
    def _scope_metric_values(
        rows: list[dict],  # type: ignore[type-arg]
        selections: InitiativeFinancialSelections,
    ) -> list[dict]:  # type: ignore[type-arg]
        selected_metrics = set(selections.metric_keys)
        return [row for row in rows if str(row.get("metric_key")) in selected_metrics]

    @staticmethod
    def _custom_benefit_totals(
        metric_values: list[dict],  # type: ignore[type-arg]
        config: FinancialConfigurationResponse | None,
    ) -> tuple[Decimal, Decimal, Decimal | None]:
        if not metric_values or config is None:
            return Decimal("0"), Decimal("0"), None
        benefit_keys = {
            item.key
            for item in config.items
            if item.item_type == "metric"
            and item.is_active
            and item.rollup_type == "benefit"
            and not item.system_metric_key
        }
        base = Decimal("0")
        high = Decimal("0")
        actual: Decimal | None = None
        for row in FinancialService._reporting_metric_values(metric_values):
            if str(row.get("metric_key")) not in benefit_keys:
                continue
            base += _dec(row.get("value_base"))
            high += _dec(row.get("value_high"))
            if row.get("value_actual") is not None:
                actual = (actual or Decimal("0")) + _dec(row.get("value_actual"))
        return base, high, actual

    @staticmethod
    def _financial_row_has_value(row: dict) -> bool:  # type: ignore[type-arg]
        return any(
            _dec(row.get(field)) != Decimal("0")
            for field in (
                "revenue_uplift_base",
                "revenue_uplift_high",
                "revenue_uplift_actual",
                "revenue_uplift_pct_base",
                "revenue_uplift_pct_high",
                "revenue_uplift_pct_actual",
                "gross_margin_base",
                "gross_margin_high",
                "gross_margin_actual",
                "gm_pct_base",
                "gm_pct_high",
                "gm_pct_actual",
                "gm_uplift_base",
                "gm_uplift_high",
                "gm_uplift_actual",
                "gm_uplift_pct_base",
                "gm_uplift_pct_high",
                "gm_uplift_pct_actual",
                "cogs_base",
                "cogs_high",
                "cogs_actual",
                "cogs_pct_base",
                "cogs_pct_high",
                "cogs_pct_actual",
            )
        )

    @staticmethod
    def _cost_line_has_value(row: dict) -> bool:  # type: ignore[type-arg]
        return _dec(row.get("amount_plan")) != Decimal("0") or _dec(
            row.get("amount_actual")
        ) != Decimal("0")

    @staticmethod
    def _metric_value_has_value(row: dict) -> bool:  # type: ignore[type-arg]
        return any(
            _dec(row.get(field)) != Decimal("0")
            for field in ("value_base", "value_high", "value_actual")
        )

    def _compute_value_bridge(
        self,
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        initiative_id: str | None,
        metric_values: list[dict] | None = None,  # type: ignore[type-arg]
        config: FinancialConfigurationResponse | None = None,
        basis: PortfolioValueBridgeBasis = "all_years",
        year: int | None = None,
        baseline_values: list[dict] | None = None,  # type: ignore[type-arg]
    ) -> ValueBridgeResponse:
        """Compute the three-row Value Bridge (Base/High/Actual)."""
        rev_base = Decimal("0")
        rev_high = Decimal("0")
        rev_actual = Decimal("0")
        gm_base = Decimal("0")
        gm_high = Decimal("0")
        gm_actual = Decimal("0")
        gm_up_base = Decimal("0")
        gm_up_high = Decimal("0")
        gm_up_actual = Decimal("0")
        cogs_base = Decimal("0")
        cogs_high = Decimal("0")
        cogs_actual = Decimal("0")

        for r in entries:
            rev_base += _dec(r.get("revenue_uplift_base"))
            rev_high += _dec(r.get("revenue_uplift_high"))
            rev_actual += _dec(r.get("revenue_uplift_actual"))
            gm_base += _dec(r.get("gross_margin_base"))
            gm_high += _dec(r.get("gross_margin_high"))
            gm_actual += _dec(r.get("gross_margin_actual"))
            gm_up_base += _dec(r.get("gm_uplift_base"))
            gm_up_high += _dec(r.get("gm_uplift_high"))
            gm_up_actual += _dec(r.get("gm_uplift_actual"))
            cogs_base += _dec(r.get("cogs_base"))
            cogs_high += _dec(r.get("cogs_high"))
            cogs_actual += _dec(r.get("cogs_actual"))

        # Split costs by one-off vs recurring
        costs_recurring_plan = Decimal("0")
        costs_recurring_actual = Decimal("0")
        costs_one_off_plan = Decimal("0")
        costs_one_off_actual = Decimal("0")

        for cl in cost_lines:
            plan = _dec(cl.get("amount_plan"))
            actual = _dec(cl.get("amount_actual"))
            if cl.get("is_recurring", False):
                costs_recurring_plan += plan
                costs_recurring_actual += actual
            else:
                costs_one_off_plan += plan
                costs_one_off_actual += actual

        total_costs_plan = costs_recurring_plan + costs_one_off_plan
        total_costs_actual = costs_recurring_actual + costs_one_off_actual
        other_base, other_high, other_actual_value = FinancialService._custom_benefit_totals(
            metric_values or [], config
        )
        other_actual = other_actual_value or Decimal("0")
        benefits_base = gm_up_base + other_base
        benefits_high = gm_up_high + other_high
        benefits_actual = gm_up_actual + other_actual
        base_case = ValueBridgeCase(
            revenue_uplift=_money(rev_base),
            gross_margin=_money(gm_base),
            gm_uplift=_money(gm_up_base),
            other_benefits=_money(other_base),
            benefits_total=_money(benefits_base),
            cogs=_money(cogs_base),
            costs_recurring=_money(costs_recurring_plan),
            costs_one_off=_money(costs_one_off_plan),
            costs_total=_money(total_costs_plan),
            net=_money(benefits_base - costs_recurring_plan),
        )
        high_case = ValueBridgeCase(
            revenue_uplift=_money(rev_high),
            gross_margin=_money(gm_high),
            gm_uplift=_money(gm_up_high),
            other_benefits=_money(other_high),
            benefits_total=_money(benefits_high),
            cogs=_money(cogs_high),
            costs_recurring=_money(costs_recurring_plan),
            costs_one_off=_money(costs_one_off_plan),
            costs_total=_money(total_costs_plan),
            net=_money(benefits_high - costs_recurring_plan),
        )
        actual_case = ValueBridgeCase(
            revenue_uplift=_money(rev_actual),
            gross_margin=_money(gm_actual),
            gm_uplift=_money(gm_up_actual),
            other_benefits=_money(other_actual),
            benefits_total=_money(benefits_actual),
            cogs=_money(cogs_actual),
            costs_recurring=_money(costs_recurring_actual),
            costs_one_off=_money(costs_one_off_actual),
            costs_total=_money(total_costs_actual),
            net=_money(benefits_actual - costs_recurring_actual),
        )

        return ValueBridgeResponse(
            initiative_id=initiative_id,
            basis=basis,
            basis_label=self._value_bridge_basis_label(basis, year),
            year=year,
            base_case=base_case,
            high_case=high_case,
            actual=actual_case,
            pnl_bridge=self._initiative_pnl_bridge(
                baseline_values or [],
                base_case,
                high_case,
                actual_case,
            )
            if initiative_id
            else None,
            financial_mode=self._financial_mode_descriptor(
                initiative_id or "",
                entries,
                cost_lines,
                metric_values or [],
                config=config,
            ),
        )

    def _compute_clean_summary(
        self,
        values: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
    ) -> FinancialSummary:
        base = self._clean_value_case(values, "plan_base")
        high = self._clean_value_case(values, "plan_high")
        actual = self._clean_value_case(values, "actual")
        plan_costs = self._clean_cost_totals(cost_lines, actual=False)
        actual_costs = self._clean_cost_totals(cost_lines, actual=True)
        return FinancialSummary(
            revenue_uplift_plan_base=_money(base["revenue_uplift"]),
            revenue_uplift_plan_high=_money(high["revenue_uplift"]),
            revenue_uplift_actual=_money(actual["revenue_uplift"])
            if actual["has_values"]
            else None,
            gross_margin_plan_base=_money(base["gross_margin"]),
            gross_margin_plan_high=_money(high["gross_margin"]),
            gross_margin_actual=_money(actual["gross_margin"]) if actual["has_values"] else None,
            gm_uplift_plan_base=_money(base["gm_uplift"]),
            gm_uplift_plan_high=_money(high["gm_uplift"]),
            gm_uplift_actual=_money(actual["gm_uplift"]) if actual["has_values"] else None,
            cogs_plan_base=_money(base["cogs"]),
            cogs_plan_high=_money(high["cogs"]),
            cogs_actual=_money(actual["cogs"]) if actual["has_values"] else None,
            costs_recurring_plan=_money(plan_costs["recurring"]),
            costs_recurring_actual=_money(actual_costs["recurring"])
            if actual_costs["has_actuals"]
            else None,
            costs_one_off_plan=_money(plan_costs["one_off"]),
            costs_one_off_actual=_money(actual_costs["one_off"])
            if actual_costs["has_actuals"]
            else None,
            costs_plan=_money(plan_costs["total"]),
            costs_actual=_money(actual_costs["total"]) if actual_costs["has_actuals"] else None,
            net_value_plan=_money(base["benefits_total"] - plan_costs["recurring"]),
            net_value_actual=_money(actual["benefits_total"] - actual_costs["recurring"])
            if actual["has_values"] or actual_costs["has_actuals"]
            else None,
            benefit_run_rate=_money(base["benefits_total"]),
            cost_run_rate=_money(plan_costs["recurring"]),
        )

    def _compute_clean_value_bridge(
        self,
        values: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        initiative_id: str | None,
        basis: PortfolioValueBridgeBasis = "all_years",
        year: int | None = None,
        baseline_values: list[dict] | None = None,  # type: ignore[type-arg]
    ) -> ValueBridgeResponse:
        base = self._clean_value_case(values, "plan_base")
        high = self._clean_value_case(values, "plan_high")
        actual = self._clean_value_case(values, "actual")
        plan_costs = self._clean_cost_totals(cost_lines, actual=False)
        actual_costs = self._clean_cost_totals(cost_lines, actual=True)
        base_case = self._clean_bridge_case(base, plan_costs)
        high_case = self._clean_bridge_case(high, plan_costs)
        actual_case = self._clean_bridge_case(actual, actual_costs)
        return ValueBridgeResponse(
            initiative_id=initiative_id,
            basis=basis,
            basis_label=self._value_bridge_basis_label(basis, year),
            year=year,
            base_case=base_case,
            high_case=high_case,
            actual=actual_case,
            rows=self._clean_dynamic_bridge_rows(values, cost_lines),
            pnl_bridge=self._initiative_pnl_bridge(
                baseline_values or [],
                base_case,
                high_case,
                actual_case,
            )
            if initiative_id
            else None,
            financial_mode=FinancialModeDescriptor(
                key="multi_scenario",
                label="Configurable metric engine",
                description="Financials are driven by tenant metric definitions and scenarios.",
                locked=False,
                scenarios=["baseline", "plan_base", "plan_high", "actual"],
            ),
        )

    def _compute_clean_scenario_summary(
        self,
        values: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        scenario: FinancialScenario,
    ) -> ScenarioFinancialSummary:
        scenario_key = {"base": "plan_base", "high": "plan_high", "actual": "actual"}[scenario]
        totals = self._clean_value_case(values, scenario_key)
        costs = self._clean_cost_totals(cost_lines, actual=scenario == "actual")
        return ScenarioFinancialSummary(
            scenario=scenario,
            revenue_uplift=_money(totals["revenue_uplift"]),
            gross_margin=_money(totals["gross_margin"]),
            gm_uplift=_money(totals["gm_uplift"]),
            other_benefits=_money(totals["other_benefits"]),
            benefits_total=_money(totals["benefits_total"]),
            cogs=_money(totals["cogs"]),
            costs_recurring=_money(costs["recurring"]),
            costs_one_off=_money(costs["one_off"]),
            costs_total=_money(costs["total"]),
            net_value=_money(totals["benefits_total"] - costs["recurring"]),
            financial_mode=FinancialModeDescriptor(
                key="multi_scenario",
                label="Configurable metric engine",
                scenarios=["baseline", "plan_base", "plan_high", "actual"],
            ),
        )

    def _compute_clean_break_even(
        self,
        initiative_id: str,
        values: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        scenario: FinancialScenario,
    ) -> BreakEvenResponse:
        scenario_key = {"base": "plan_base", "high": "plan_high", "actual": "actual"}[scenario]
        value_periods = {(row["year"], None, row["month"]) for row in values}
        cost_periods = {(row["year"], row.get("quarter"), row.get("month")) for row in cost_lines}
        periods = sorted(value_periods | cost_periods, key=self._period_sort)
        points: list[BreakEvenPoint] = []
        cumulative_benefits = Decimal("0")
        cumulative_costs = Decimal("0")
        break_even_period: str | None = None
        for year, quarter, month in periods:
            period_values = [
                row for row in values if row["year"] == year and row.get("month") == month
            ]
            period_costs = [
                row
                for row in cost_lines
                if row["year"] == year
                and row.get("quarter") == quarter
                and row.get("month") == month
            ]
            benefits = self._clean_value_case(period_values, scenario_key)["benefits_total"]
            costs = self._clean_cost_totals(period_costs, actual=scenario == "actual")["total"]
            cumulative_benefits += benefits
            cumulative_costs += costs
            cumulative_net = cumulative_benefits - cumulative_costs
            label = self._period_label(year, quarter, month)
            crossed = (
                break_even_period is None
                and cumulative_net >= Decimal("0")
                and cumulative_costs > Decimal("0")
            )
            if crossed:
                break_even_period = label
            points.append(
                BreakEvenPoint(
                    period=label,
                    year=year,
                    quarter=quarter,
                    month=month,
                    cumulative_gm_uplift=_money(cumulative_benefits),
                    cumulative_costs=_money(cumulative_costs),
                    cumulative_net=_money(cumulative_net),
                    run_rate_gm_uplift=_money(benefits),
                    run_rate_costs=_money(costs),
                    is_break_even=crossed,
                )
            )
        return BreakEvenResponse(
            initiative_id=initiative_id,
            scenario=scenario,
            break_even_period=break_even_period,
            points=points,
            financial_mode=FinancialModeDescriptor(
                key="multi_scenario",
                label="Configurable metric engine",
                scenarios=["baseline", "plan_base", "plan_high", "actual"],
            ),
        )

    def _get_clean_portfolio_financials(
        self,
        granularity: PortfolioGranularity,
        year: int | None = None,
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        stage: str | None = None,
        tag: str | None = None,
        category_key: str | None = None,
    ) -> PortfolioFinancialsResponse:
        business_unit_ids = self._split_filter_values(business_unit_id)
        workstream_ids = self._split_filter_values(workstream_id)
        stages = self._split_filter_values(stage)
        tags = self._split_filter_values(tag)
        initiatives = {
            row["id"]: row
            for row in self._repo.get_portfolio_initiatives()
            if self._portfolio_initiative_matches(
                row,
                initiative_id=initiative_id,
                workstream_ids=workstream_ids,
                business_unit_ids=business_unit_ids,
                stages=stages,
                tags=tags,
            )
        }
        values = self._values_with_formula_metrics(
            [
                row
                for row in self._repo.get_all_metric_values()
                if row.get("initiative_id") in initiatives
                and (year is None or row.get("year") == year)
            ],
            [
                row
                for row in self._repo.list_all_initiative_annual_baselines()
                if row.get("initiative_id") in initiatives
            ],
        )
        costs = [
            row
            for row in self._repo.get_all_cost_lines()
            if row.get("initiative_id") in initiatives
            and (year is None or row.get("year") == year)
            and (not category_key or row.get("category_key", "other") == category_key)
        ]
        period_keys = {
            self._clean_portfolio_period_key(row, granularity) for row in [*values, *costs]
        }
        periods: list[PortfolioFinancialPeriod] = []
        for key in sorted(period_keys):
            label, y, q, m = key
            period_values = [
                row for row in values if self._clean_portfolio_period_key(row, granularity) == key
            ]
            period_costs = [
                row for row in costs if self._clean_portfolio_period_key(row, granularity) == key
            ]
            base = self._clean_value_case(period_values, "plan_base")
            actual = self._clean_value_case(period_values, "actual")
            plan_costs = self._clean_cost_totals(period_costs, actual=False)
            actual_costs = self._clean_cost_totals(period_costs, actual=True)
            periods.append(
                PortfolioFinancialPeriod(
                    period=label,
                    year=y,
                    quarter=q,
                    month=m,
                    benefits_plan=_money(base["benefits_total"]),
                    benefits_actual=_money(actual["benefits_total"]),
                    recurring_costs_plan=_money(plan_costs["recurring"]),
                    recurring_costs_actual=_money(actual_costs["recurring"]),
                    one_off_costs_plan=_money(plan_costs["one_off"]),
                    one_off_costs_actual=_money(actual_costs["one_off"]),
                    total_costs_plan=_money(plan_costs["total"]),
                    total_costs_actual=_money(actual_costs["total"]),
                    net_value_plan=_money(base["benefits_total"] - plan_costs["recurring"]),
                    net_value_actual=_money(actual["benefits_total"] - actual_costs["recurring"]),
                )
            )
        summary_totals = self._compute_clean_summary(values, costs)
        return PortfolioFinancialsResponse(
            granularity=granularity,
            summary=[
                PortfolioFinancialSummaryCard(
                    key="benefits",
                    label="Benefits",
                    plan=summary_totals.benefit_run_rate,
                    actual=summary_totals.net_value_actual or "0",
                    variance=_money(
                        _dec(summary_totals.net_value_actual) - _dec(summary_totals.net_value_plan)
                    ),
                ),
                PortfolioFinancialSummaryCard(
                    key="costs",
                    label="Costs",
                    plan=summary_totals.costs_plan,
                    actual=summary_totals.costs_actual or "0",
                    variance=_money(
                        _dec(summary_totals.costs_actual) - _dec(summary_totals.costs_plan)
                    ),
                ),
                PortfolioFinancialSummaryCard(
                    key="net_value",
                    label="Net Value",
                    plan=summary_totals.net_value_plan,
                    actual=summary_totals.net_value_actual or "0",
                    variance=_money(
                        _dec(summary_totals.net_value_actual) - _dec(summary_totals.net_value_plan)
                    ),
                ),
            ],
            periods=periods,
            broader_period_totals=periods,
            cost_breakdown=[],
            metric_breakdown=[],
            financial_mode=FinancialModeDescriptor(
                key="multi_scenario",
                label="Configurable metric engine",
                scenarios=["baseline", "plan_base", "plan_high", "actual"],
            ),
        )

    def _clean_value_case(
        self,
        values: list[dict],  # type: ignore[type-arg]
        scenario_key: str,
    ) -> dict[str, Decimal | bool]:
        definitions = {row["id"]: row for row in self._repo.list_metric_definitions()}
        scenarios = {row["id"]: row for row in self._repo.list_financial_scenarios()}
        totals: dict[str, Decimal | bool] = {
            "revenue_uplift": Decimal("0"),
            "gross_margin": Decimal("0"),
            "gm_uplift": Decimal("0"),
            "cogs": Decimal("0"),
            "other_benefits": Decimal("0"),
            "benefits_total": Decimal("0"),
            "has_values": False,
        }
        for row in values:
            scenario = scenarios.get(row.get("scenario_id"))
            if not scenario or scenario.get("key") != scenario_key:
                continue
            definition = definitions.get(row.get("metric_definition_id"))
            if not definition or (
                definition.get("aggregation") == "formula" and not row.get("_computed_formula")
            ):
                continue
            amount = _dec(row.get("value"))
            totals["has_values"] = True
            key = definition.get("key")
            benefit_class = definition.get("benefit_class")
            if key == "revenue_uplift" or benefit_class == "revenue":
                totals["revenue_uplift"] = _dec(totals["revenue_uplift"]) + amount
            elif key == "gross_margin":
                totals["gross_margin"] = _dec(totals["gross_margin"]) + amount
            elif key == "gm_uplift" or benefit_class == "margin":
                totals["gm_uplift"] = _dec(totals["gm_uplift"]) + amount
            elif key == "cogs" or definition.get("rollup_type") == "total_cost":
                totals["cogs"] = _dec(totals["cogs"]) + amount
            elif definition.get("is_benefit"):
                totals["other_benefits"] = _dec(totals["other_benefits"]) + amount
        totals["benefits_total"] = (
            _dec(totals["gm_uplift"])
            + _dec(totals["gross_margin"])
            + _dec(totals["other_benefits"])
        )
        return totals

    @staticmethod
    def _clean_cost_totals(
        cost_lines: list[dict],  # type: ignore[type-arg]
        actual: bool,
    ) -> dict[str, Decimal | bool]:
        totals: dict[str, Decimal | bool] = {
            "recurring": Decimal("0"),
            "one_off": Decimal("0"),
            "total": Decimal("0"),
            "has_actuals": False,
        }
        for row in cost_lines:
            raw = row.get("amount_actual") if actual else row.get("amount_plan")
            if actual and raw is not None:
                totals["has_actuals"] = True
            amount = _dec(raw)
            bucket = "recurring" if row.get("is_recurring", False) else "one_off"
            totals[bucket] = _dec(totals[bucket]) + amount
            totals["total"] = _dec(totals["total"]) + amount
        return totals

    @classmethod
    def _to_payback_row(
        cls,
        row: PortfolioInitiativePortfolioRow,
        *,
        one_off_investment: Decimal | None = None,
    ) -> PortfolioInvestmentPaybackRow:
        one_off = _dec(one_off_investment if one_off_investment is not None else row.one_off_costs)
        net = _dec(row.net_run_rate_value)
        months, label = cls._payback_months_and_label(one_off, net)
        if one_off <= 0:
            status_value: Literal["immediate", "payback", "not_reached", "no_investment"] = (
                "immediate"
            )
        elif net <= 0:
            status_value = "not_reached"
        else:
            status_value = "payback"
        return PortfolioInvestmentPaybackRow(
            initiative_id=row.initiative_id,
            initiative_code=row.initiative_code,
            initiative_name=row.initiative_name,
            stage=row.stage,
            workstream_name=row.workstream_name,
            benefits_total=row.benefits_total,
            recurring_costs=row.recurring_costs,
            one_off_investment=_money(one_off),
            net_run_rate_value=row.net_run_rate_value,
            payback_months=months,
            payback_label=label,
            payback_status=status_value,
        )

    def _cumulative_one_off_investments(
        self,
        *,
        initiative_ids: set[str],
        value_year: int | None,
        scenario_key: str,
    ) -> dict[str, Decimal]:
        investments = {initiative_id: Decimal("0") for initiative_id in initiative_ids}
        for row in self._repo.get_all_cost_lines():
            initiative_id = str(row.get("initiative_id"))
            if initiative_id not in investments or row.get("is_recurring", False):
                continue
            if value_year is not None and row.get("year") is not None and int(row["year"]) > value_year:
                continue
            raw_amount = (
                row.get("amount_actual") if scenario_key == "actual" else row.get("amount_plan")
            )
            investments[initiative_id] += _dec(raw_amount)
        return investments

    @staticmethod
    def _payback_months_and_label(
        one_off_investment: Decimal,
        annual_net_run_rate: Decimal,
    ) -> tuple[str | None, str]:
        if one_off_investment <= 0:
            return "0.0000", "Immediate"
        if annual_net_run_rate <= 0:
            return None, "Not reached"
        months = (one_off_investment / annual_net_run_rate) * Decimal("12")
        rounded = months.quantize(Decimal("0.0001"))
        if rounded < Decimal("1"):
            return _money(rounded), "<1 month"
        return _money(rounded), f"{rounded.quantize(Decimal('0.1'))} months"

    @staticmethod
    def _clean_bridge_case(
        totals: dict[str, Decimal | bool],
        costs: dict[str, Decimal | bool],
    ) -> ValueBridgeCase:
        benefits_total = _dec(totals["benefits_total"])
        recurring = _dec(costs["recurring"])
        one_off = _dec(costs["one_off"])
        return ValueBridgeCase(
            revenue_uplift=_money(totals["revenue_uplift"]),
            gross_margin=_money(totals["gross_margin"]),
            gm_uplift=_money(totals["gm_uplift"]),
            other_benefits=_money(totals["other_benefits"]),
            benefits_total=_money(benefits_total),
            cogs=_money(totals["cogs"]),
            costs_recurring=_money(recurring),
            costs_one_off=_money(one_off),
            costs_total=_money(recurring + one_off),
            net=_money(benefits_total - recurring),
        )

    def _initiative_pnl_bridge(
        self,
        baseline_values: list[dict],  # type: ignore[type-arg]
        base_case: ValueBridgeCase,
        high_case: ValueBridgeCase,
        actual_case: ValueBridgeCase,
    ) -> InitiativePnlBridge:
        definitions_by_id = self._metric_definitions_by_id()
        baseline_year = self._latest_baseline_year(baseline_values)
        baseline_revenue = self._baseline_amount(
            baseline_values,
            definitions_by_id,
            exact_keys={
                "annual_revenue_baseline",
                "baseline_revenue",
                "revenue_baseline",
            },
            required_tokens={"revenue", "baseline"},
        )
        baseline_gross_margin = self._baseline_amount(
            baseline_values,
            definitions_by_id,
            exact_keys={
                "annual_gross_margin_baseline",
                "baseline_gross_margin",
                "gross_margin_baseline",
            },
            required_tokens={"gross", "margin", "baseline"},
        )

        return InitiativePnlBridge(
            baseline_year=baseline_year,
            base_case=self._initiative_pnl_bridge_case(
                "base",
                "Plan Base",
                baseline_revenue,
                baseline_gross_margin,
                base_case,
            ),
            high_case=self._initiative_pnl_bridge_case(
                "high",
                "Plan High",
                baseline_revenue,
                baseline_gross_margin,
                high_case,
            ),
            actual=self._initiative_pnl_bridge_case(
                "actual",
                "Actual",
                baseline_revenue,
                baseline_gross_margin,
                actual_case,
            ),
        )

    @staticmethod
    def _latest_baseline_year(baseline_values: list[dict]) -> int | None:  # type: ignore[type-arg]
        years = [
            int(row["baseline_year"])
            for row in baseline_values
            if row.get("baseline_year") is not None
        ]
        return max(years) if years else None

    def _metric_definitions_by_id(self) -> dict[str, dict[str, Any]]:
        repo = getattr(self, "_repo", None)
        if repo is None:
            return {}
        return {
            str(row["id"]): row for row in getattr(repo, "list_metric_definitions", lambda: [])()
        }

    @staticmethod
    def _baseline_amount(
        baseline_values: list[dict],  # type: ignore[type-arg]
        definitions_by_id: dict[str, dict[str, Any]],
        exact_keys: set[str],
        required_tokens: set[str],
    ) -> Decimal:
        for row in baseline_values:
            key = FinancialService._baseline_metric_key(row, definitions_by_id)
            if key in exact_keys:
                return _dec(row.get("value"))
        for row in baseline_values:
            key = FinancialService._baseline_metric_key(row, definitions_by_id)
            if key and required_tokens.issubset(set(key.replace("-", "_").split("_"))):
                return _dec(row.get("value"))
        return Decimal("0")

    @staticmethod
    def _baseline_metric_key(
        row: dict,  # type: ignore[type-arg]
        definitions_by_id: dict[str, dict[str, Any]],
    ) -> str:
        if row.get("metric_key"):
            return str(row["metric_key"]).lower()
        definition = definitions_by_id.get(str(row.get("metric_definition_id")))
        return str(definition.get("key") or "").lower() if definition else ""

    def _initiative_pnl_bridge_case(
        self,
        scenario: Literal["base", "high", "actual"],
        label: str,
        baseline_revenue: Decimal,
        baseline_gross_margin: Decimal,
        case: ValueBridgeCase,
    ) -> PnlBridgeCase:
        revenue_uplift = _dec(case.revenue_uplift)
        margin_and_benefit_uplift = (
            _dec(case.gross_margin) + _dec(case.gm_uplift) + _dec(case.other_benefits)
        )
        recurring_opex = _dec(case.costs_recurring)
        one_off_costs = _dec(case.costs_one_off)
        target_revenue = baseline_revenue + revenue_uplift
        target_run_rate_value = baseline_gross_margin + margin_and_benefit_uplift - recurring_opex
        incremental_net = margin_and_benefit_uplift - recurring_opex

        step_specs: list[tuple[str, str, Decimal, str]] = [
            ("baseline_revenue", "Baseline Revenue", baseline_revenue, "baseline"),
            ("revenue_uplift", "Revenue Uplift", revenue_uplift, "increase"),
            ("target_revenue", "Target Revenue", target_revenue, "target"),
            (
                "baseline_gross_margin",
                "Baseline Gross Margin",
                baseline_gross_margin,
                "baseline",
            ),
            (
                "margin_and_benefit_uplift",
                "Margin & Benefit Uplift",
                margin_and_benefit_uplift,
                "increase",
            ),
            ("recurring_opex", "Recurring Opex", -recurring_opex, "decrease"),
            (
                "target_run_rate_value",
                "Target Run-rate Value",
                target_run_rate_value,
                "target",
            ),
        ]

        cumulative = Decimal("0")
        steps: list[PnlBridgeStep] = []
        for display_order, (key, step_label, value, kind) in enumerate(step_specs, start=1):
            if kind == "baseline" or kind == "target":
                cumulative = value
            else:
                cumulative += value
            steps.append(
                PnlBridgeStep(
                    key=key,
                    label=step_label,
                    value=_money(value),
                    cumulative_value=_money(cumulative),
                    step_kind=kind,  # type: ignore[arg-type]
                    display_order=display_order * 10,
                )
            )

        return PnlBridgeCase(
            scenario=scenario,
            label=label,
            baseline_revenue=_money(baseline_revenue),
            revenue_uplift=_money(revenue_uplift),
            target_revenue=_money(target_revenue),
            baseline_gross_margin=_money(baseline_gross_margin),
            margin_and_benefit_uplift=_money(margin_and_benefit_uplift),
            recurring_opex=_money(recurring_opex),
            target_run_rate_value=_money(target_run_rate_value),
            incremental_net_run_rate=_money(incremental_net),
            one_off_costs=_money(one_off_costs),
            steps=steps,
        )

    def _clean_dynamic_bridge_rows(
        self,
        values: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
    ) -> list[ValueBridgeRow]:
        bridge_rows = [
            row for row in self._repo.list_financial_bridge_rows() if row.get("is_active", True)
        ]
        if not bridge_rows:
            return []
        scenarios = {row["id"]: row for row in self._repo.list_financial_scenarios()}
        definitions = {row["id"]: row for row in self._repo.list_metric_definitions()}
        plan_costs = self._clean_cost_totals(cost_lines, actual=False)
        actual_costs = self._clean_cost_totals(cost_lines, actual=True)

        def metric_total(metric_ids: set[str], scenario_key: str) -> Decimal:
            if not metric_ids:
                return Decimal("0")
            total = Decimal("0")
            for row in values:
                scenario = scenarios.get(row.get("scenario_id"))
                if not scenario or scenario.get("key") != scenario_key:
                    continue
                if str(row.get("metric_definition_id")) not in metric_ids:
                    continue
                total += _dec(row.get("value"))
            return total

        def benefit_total(scenario_key: str) -> Decimal:
            total = Decimal("0")
            for row in values:
                scenario = scenarios.get(row.get("scenario_id"))
                if not scenario or scenario.get("key") != scenario_key:
                    continue
                definition = definitions.get(row.get("metric_definition_id"))
                if not definition or not definition.get("is_benefit"):
                    continue
                total += _dec(row.get("value"))
            return total

        def cost_total(category_keys: set[str], actual: bool) -> Decimal:
            total = Decimal("0")
            for row in cost_lines:
                if category_keys and str(row.get("category_key", "other")) not in category_keys:
                    continue
                raw = row.get("amount_actual") if actual else row.get("amount_plan")
                total += _dec(raw)
            return total

        response_rows: list[ValueBridgeRow] = []
        for row in sorted(bridge_rows, key=lambda item: item.get("display_order") or 0):
            row_kind = row.get("row_kind") or "metric_set"
            if row_kind not in {"metric_set", "cost_set", "subtotal", "net"}:
                row_kind = "metric_set"
            sign = -1 if int(row.get("sign") or 1) < 0 else 1
            metric_ids = {str(item) for item in row.get("metric_definition_ids") or [] if item}
            category_keys = {str(item) for item in row.get("cost_category_keys") or [] if item}

            if row_kind == "net":
                base_value = benefit_total("plan_base") - _dec(plan_costs["recurring"])
                high_value = benefit_total("plan_high") - _dec(plan_costs["recurring"])
                actual_value = benefit_total("actual") - _dec(actual_costs["recurring"])
            else:
                include_metrics = row_kind in {"metric_set", "subtotal"}
                include_costs = row_kind in {"cost_set", "subtotal"}
                base_value = (
                    metric_total(metric_ids, "plan_base") if include_metrics else Decimal("0")
                ) + (cost_total(category_keys, actual=False) if include_costs else Decimal("0"))
                high_value = (
                    metric_total(metric_ids, "plan_high") if include_metrics else Decimal("0")
                ) + (cost_total(category_keys, actual=False) if include_costs else Decimal("0"))
                actual_value = (
                    metric_total(metric_ids, "actual") if include_metrics else Decimal("0")
                ) + (cost_total(category_keys, actual=True) if include_costs else Decimal("0"))
                base_value *= Decimal(sign)
                high_value *= Decimal(sign)
                actual_value *= Decimal(sign)

            response_rows.append(
                ValueBridgeRow(
                    key=row["key"],
                    label=row["label"],
                    row_kind=row_kind,
                    base_case=_money(base_value),
                    high_case=_money(high_value),
                    actual=_money(actual_value),
                    sign=sign,
                    display_order=row.get("display_order") or 0,
                )
            )
        return response_rows

    @staticmethod
    def _clean_portfolio_period_key(
        row: dict,  # type: ignore[type-arg]
        granularity: PortfolioGranularity,
    ) -> tuple[str, int, int | None, int | None]:
        year = int(row["year"])
        month = row.get("month")
        quarter = row.get("quarter")
        if granularity == "monthly" and month:
            return (f"{year}-M{int(month):02d}", year, None, int(month))
        if granularity == "quarterly":
            q = int(quarter or (((int(month or 1) - 1) // 3) + 1))
            return (f"{year}-Q{q}", year, q, None)
        return (str(year), year, None, None)

    def _compute_scenario_summary(
        self,
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        metric_values: list[dict],  # type: ignore[type-arg]
        config: FinancialConfigurationResponse | None,
        scenario: FinancialScenario,
    ) -> ScenarioFinancialSummary:
        revenue = Decimal("0")
        gross_margin = Decimal("0")
        gm_uplift = Decimal("0")
        cogs = Decimal("0")
        for row in entries:
            revenue += FinancialService._scenario_entry_value(row, "revenue_uplift", scenario)
            gross_margin += FinancialService._scenario_entry_value(row, "gross_margin", scenario)
            gm_uplift += FinancialService._scenario_entry_value(row, "gm_uplift", scenario)
            cogs += FinancialService._scenario_entry_value(row, "cogs", scenario)

        recurring = Decimal("0")
        one_off = Decimal("0")
        for row in cost_lines:
            value = FinancialService._scenario_cost_value(row, scenario)
            if row.get("is_recurring", False):
                recurring += value
            else:
                one_off += value
        total_costs = recurring + one_off
        other_base, other_high, other_actual_value = FinancialService._custom_benefit_totals(
            metric_values, config
        )
        other = {
            "base": other_base,
            "high": other_high,
            "actual": other_actual_value or Decimal("0"),
        }[scenario]
        benefits_total = gm_uplift + other
        return ScenarioFinancialSummary(
            scenario=scenario,
            revenue_uplift=_money(revenue),
            gross_margin=_money(gross_margin),
            gm_uplift=_money(gm_uplift),
            other_benefits=_money(other),
            benefits_total=_money(benefits_total),
            cogs=_money(cogs),
            costs_recurring=_money(recurring),
            costs_one_off=_money(one_off),
            costs_total=_money(total_costs),
            net_value=_money(benefits_total - recurring),
            financial_mode=self._financial_mode_descriptor(
                "",
                entries,
                cost_lines,
                metric_values,
                config=config,
            ),
        )

    @staticmethod
    def _scenario_entry_value(row: dict, metric: str, scenario: FinancialScenario) -> Decimal:  # type: ignore[type-arg]
        suffix = "base" if scenario == "base" else scenario
        return _dec(row.get(f"{metric}_{suffix}"))

    @staticmethod
    def _scenario_cost_value(row: dict, scenario: FinancialScenario) -> Decimal:  # type: ignore[type-arg]
        if scenario == "actual":
            return _dec(row.get("amount_actual"))
        return _dec(row.get("amount_plan"))

    @staticmethod
    def _period_key(row: dict) -> tuple[int, int | None, int | None]:  # type: ignore[type-arg]
        year = int(row["year"])
        month = row.get("month")
        if month is not None:
            return (year, None, int(month))
        quarter = row.get("quarter")
        if quarter is not None:
            return (year, int(quarter), None)
        return (year, None, None)

    @staticmethod
    def _period_sort(period: tuple[int, int | None, int | None]) -> tuple[int, int]:
        year, quarter, month = period
        if month is not None:
            return (year, month)
        if quarter is not None:
            return (year, quarter * 3)
        return (year, 12)

    @staticmethod
    def _period_label(year: int, quarter: int | None, month: int | None) -> str:
        if month is not None:
            return f"{year}-M{month:02d}"
        if quarter is not None:
            return f"{year}-Q{quarter}"
        return str(year)

    @staticmethod
    def _engine_configuration_as_legacy_response(
        config: FinancialEngineConfigurationResponse,
    ) -> FinancialConfigurationResponse:
        groups: dict[str, FinancialConfigGroup] = {
            "benefits": FinancialConfigGroup(
                key="benefits",
                label="Benefits",
                kind="calculation",
                rollup_type="benefit",
                display_order=10,
                is_system=True,
            ),
            "recurring_costs": FinancialConfigGroup(
                key="recurring_costs",
                label="Recurring Costs",
                kind="calculation",
                rollup_type="recurring_cost",
                display_order=20,
                is_system=True,
            ),
            "one_off_costs": FinancialConfigGroup(
                key="one_off_costs",
                label="One-off Costs",
                kind="calculation",
                rollup_type="one_off_cost",
                display_order=30,
                is_system=True,
            ),
            "net_value": FinancialConfigGroup(
                key="net_value",
                label="Net Value",
                kind="calculation",
                rollup_type="net_value",
                display_order=40,
                is_system=True,
            ),
        }
        items: list[FinancialConfigItem] = []

        for definition in config.definitions:
            group_key = definition.group_key or ("benefits" if definition.is_benefit else "metrics")
            if group_key not in groups:
                groups[group_key] = FinancialConfigGroup(
                    key=group_key,
                    label=group_key.replace("_", " ").title(),
                    kind="metric",
                    display_order=100 + len(groups),
                    is_system=definition.is_system,
                    is_active=True,
                )
            items.append(
                FinancialConfigItem(
                    id=definition.id,
                    group_key=group_key,
                    key=definition.key,
                    label=definition.label,
                    item_type="metric",
                    system_metric_key=definition.key,
                    rollup_type=definition.rollup_type,
                    display_order=definition.display_order,
                    is_system=definition.is_system,
                    is_active=definition.is_active,
                )
            )

        for category in config.cost_categories:
            group_key = category.group_key or "costs"
            if group_key not in groups:
                groups[group_key] = FinancialConfigGroup(
                    key=group_key,
                    label=group_key.replace("_", " ").title(),
                    kind="cost_category",
                    display_order=200 + len(groups),
                    is_system=category.is_system,
                    is_active=True,
                )
            items.append(
                FinancialConfigItem(
                    id=category.id,
                    group_key=group_key,
                    key=category.key,
                    label=category.label,
                    item_type="cost_category",
                    rollup_type=category.rollup_type,
                    display_order=category.display_order,
                    is_system=category.is_system,
                    is_active=category.is_active,
                )
            )

        return FinancialConfigurationResponse(
            groups=sorted(groups.values(), key=lambda group: group.display_order),
            items=sorted(items, key=lambda item: (item.item_type, item.display_order, item.label)),
        )

    @staticmethod
    def _to_config_group(row: dict) -> FinancialConfigGroup:  # type: ignore[type-arg]
        return FinancialConfigGroup(
            id=row.get("id"),
            key=row["key"],
            label=row["label"],
            kind=row["kind"],
            rollup_type=row.get("rollup_type"),
            display_order=row.get("display_order") or 0,
            is_system=row.get("is_system", False),
            is_active=row.get("is_active", True),
        )

    @staticmethod
    def _to_config_item(row: dict, group_key: str | None = None) -> FinancialConfigItem:  # type: ignore[type-arg]
        return FinancialConfigItem(
            id=row.get("id"),
            group_id=row.get("group_id"),
            group_key=group_key,
            key=row["key"],
            label=row["label"],
            item_type=row["item_type"],
            system_metric_key=row.get("system_metric_key"),
            rollup_type=row.get("rollup_type"),
            display_order=row.get("display_order") or 0,
            is_system=row.get("is_system", False),
            is_active=row.get("is_active", True),
        )

    @staticmethod
    def _to_metric_definition(row: dict) -> FinancialMetricDefinition:  # type: ignore[type-arg]
        return FinancialMetricDefinition(
            id=row["id"],
            key=row["key"],
            label=row["label"],
            description=row.get("description"),
            group_key=row.get("group_key"),
            value_type=row.get("value_type") or "currency",
            unit=row.get("unit"),
            direction=row.get("direction") or "increase_good",
            aggregation=row.get("aggregation") or "sum",
            rollup_type=row.get("rollup_type"),
            is_benefit=row.get("is_benefit", False),
            benefit_class=row.get("benefit_class"),
            cost_behavior=row.get("cost_behavior"),
            formula=row.get("formula"),
            formula_inputs=row.get("formula_inputs") or [],
            precision=row.get("precision") or 4,
            display_order=row.get("display_order") or 0,
            applies_to=row.get("applies_to") or "opt_in",
            validation=row.get("validation") or {},
            is_system=row.get("is_system", False),
            is_active=row.get("is_active", True),
            created_by=row.get("created_by"),
            updated_by=row.get("updated_by"),
        )

    @staticmethod
    def _to_scenario_definition(row: dict) -> FinancialScenarioDefinition:  # type: ignore[type-arg]
        return FinancialScenarioDefinition(
            id=row["id"],
            key=row["key"],
            label=row.get("label") or str(row["key"]).replace("_", " ").title(),
            kind=row.get("kind") or ("actual" if row.get("key") == "actual" else "plan"),
            is_primary=row.get("is_primary", False),
            is_system=row.get("is_system", False),
            is_active=row.get("is_active", True),
            display_order=row.get("display_order") or 0,
        )

    @staticmethod
    def _to_bridge_row(row: dict) -> FinancialBridgeRow:  # type: ignore[type-arg]
        return FinancialBridgeRow(
            id=row.get("id"),
            key=row["key"],
            label=row["label"],
            row_kind=row["row_kind"],
            metric_definition_ids=row.get("metric_definition_ids") or [],
            cost_category_ids=row.get("cost_category_ids") or [],
            cost_category_keys=row.get("cost_category_keys") or [],
            sign=row.get("sign") or 1,
            display_order=row.get("display_order") or 0,
            is_active=row.get("is_active", True),
        )

    @staticmethod
    def _to_cost_category(row: dict) -> FinancialCostCategory:  # type: ignore[type-arg]
        return FinancialCostCategory(
            id=row.get("id"),
            key=row["key"],
            label=row["label"],
            group_key=row.get("group_key"),
            rollup_type=row.get("rollup_type"),
            display_order=row.get("display_order") or 0,
            attributes=row.get("attributes") or {},
            is_system=row.get("is_system", False),
            is_active=row.get("is_active", True),
        )

    @staticmethod
    def _to_attribute_definition(row: dict) -> FinancialAttributeDefinition:  # type: ignore[type-arg]
        return FinancialAttributeDefinition(
            id=row.get("id"),
            key=row["key"],
            label=row["label"],
            entity_type=row["entity_type"],
            value_type=row.get("value_type") or "text",
            options=row.get("options") or [],
            is_required=row.get("is_required", False),
            display_order=row.get("display_order") or 0,
            is_active=row.get("is_active", True),
        )

    @staticmethod
    def _to_benefit_line(row: dict) -> FinancialBenefitLine:  # type: ignore[type-arg]
        return FinancialBenefitLine(
            id=row["id"],
            metric_definition_id=row["metric_definition_id"],
            name=row["name"],
            description=row.get("description"),
            impact_type=row.get("impact_type"),
            timing=row.get("timing"),
            confidence=_dec(row["confidence"]) if row.get("confidence") is not None else None,
            phasing=row.get("phasing") or {},
            attributes=row.get("attributes") or {},
            show_in_summary=row.get("show_in_summary", True),
            display_order=row.get("display_order") or 0,
            evidence_url=row.get("evidence_url"),
            evidence_label=row.get("evidence_label"),
            realization_owner_id=row.get("realization_owner_id"),
            handoff_status=row.get("handoff_status") or "not_started",
            handoff_due_date=FinancialService._as_date(row["handoff_due_date"])
            if row.get("handoff_due_date")
            else None,
            risk_rating=row.get("risk_rating") or "medium",
            risk_adjustment_pct=_dec(row.get("risk_adjustment_pct") or "100"),
            validation_status=row.get("validation_status") or "draft",
            submitted_at=row.get("submitted_at"),
            submitted_by=row.get("submitted_by"),
            validated_at=row.get("validated_at"),
            validated_by=row.get("validated_by"),
            validation_comment=row.get("validation_comment"),
            rejection_reason=row.get("rejection_reason"),
            created_by=row.get("created_by"),
            updated_by=row.get("updated_by"),
        )

    @staticmethod
    def _to_benefit_line_validation_event(
        row: dict,  # type: ignore[type-arg]
    ) -> FinancialBenefitLineValidationEvent:
        return FinancialBenefitLineValidationEvent(
            id=row["id"],
            initiative_id=row["initiative_id"],
            benefit_line_id=row["benefit_line_id"],
            event_type=row["event_type"],
            actor_user_id=row.get("actor_user_id"),
            comment=row.get("comment"),
            evidence_url=row.get("evidence_url"),
            evidence_label=row.get("evidence_label"),
            metadata=row.get("metadata") or {},
            created_at=str(row.get("created_at") or ""),
        )

    @staticmethod
    def _to_configurable_metric_value(
        row: dict,  # type: ignore[type-arg]
    ) -> ConfigurableFinancialMetricValueRow:
        return ConfigurableFinancialMetricValueRow(
            id=row["id"],
            metric_definition_id=row["metric_definition_id"],
            scenario_id=row["scenario_id"],
            benefit_line_id=row.get("benefit_line_id"),
            year=row["year"],
            month=row["month"],
            value=_money(row.get("value")),
            status=row.get("status") or "draft",
            note=row.get("note"),
        )

    @staticmethod
    def _portfolio_bucket_key(
        row: dict,  # type: ignore[type-arg]
        granularity: PortfolioGranularity,
    ) -> tuple[str, int, int | None, int | None] | None:
        year = int(row["year"])
        month = row.get("month")
        quarter = row.get("quarter")
        if granularity == "monthly":
            if month is None:
                return None
            return (f"{year}-M{int(month):02d}", year, None, int(month))
        if granularity == "quarterly":
            if month is not None:
                q = ((int(month) - 1) // 3) + 1
                return (f"{year}-Q{q}", year, q, None)
            if quarter is None:
                return None
            return (f"{year}-Q{int(quarter)}", year, int(quarter), None)
        return (str(year), year, None, None)

    @classmethod
    def _portfolio_row_period_label(
        cls,
        row: dict,  # type: ignore[type-arg]
        granularity: PortfolioGranularity,
    ) -> str | None:
        key = cls._portfolio_bucket_key(row, granularity)
        if key is not None:
            return key[0]
        period = cls._period_key(row)
        return cls._period_label(*period)

    @staticmethod
    def _parse_portfolio_period(
        period: str,
        granularity: PortfolioGranularity,
    ) -> tuple[str, int, int | None, int | None]:
        if "-M" in period:
            year_part, month_part = period.split("-M", 1)
            return (period, int(year_part), None, int(month_part))
        if "-Q" in period:
            year_part, quarter_part = period.split("-Q", 1)
            return (period, int(year_part), int(quarter_part), None)
        year = int(period)
        if granularity == "yearly":
            return (period, year, None, None)
        return (period, year, None, None)

    @staticmethod
    def _empty_portfolio_period(
        label: str, year: int, quarter: int | None, month: int | None
    ) -> dict[str, Decimal | int | str | None]:
        return {
            "period": label,
            "year": year,
            "quarter": quarter,
            "month": month,
            "benefits_plan": Decimal("0"),
            "benefits_actual": Decimal("0"),
            "recurring_costs_plan": Decimal("0"),
            "recurring_costs_actual": Decimal("0"),
            "one_off_costs_plan": Decimal("0"),
            "one_off_costs_actual": Decimal("0"),
        }

    @classmethod
    def _to_portfolio_period(cls, row: dict) -> PortfolioFinancialPeriod:  # type: ignore[type-arg]
        recurring_plan = row["recurring_costs_plan"]
        recurring_actual = row["recurring_costs_actual"]
        one_off_plan = row["one_off_costs_plan"]
        one_off_actual = row["one_off_costs_actual"]
        total_plan = recurring_plan + one_off_plan
        total_actual = recurring_actual + one_off_actual
        benefits_plan = row["benefits_plan"]
        benefits_actual = row["benefits_actual"]
        return PortfolioFinancialPeriod(
            period=str(row["period"]),
            year=int(row["year"]),
            quarter=row.get("quarter"),
            month=row.get("month"),
            benefits_plan=_money(benefits_plan),
            benefits_actual=_money(benefits_actual),
            recurring_costs_plan=_money(recurring_plan),
            recurring_costs_actual=_money(recurring_actual),
            one_off_costs_plan=_money(one_off_plan),
            one_off_costs_actual=_money(one_off_actual),
            total_costs_plan=_money(total_plan),
            total_costs_actual=_money(total_actual),
            net_value_plan=_money(benefits_plan - recurring_plan),
            net_value_actual=_money(benefits_actual - recurring_actual),
        )

    @classmethod
    def _compute_portfolio_financials(
        cls,
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        metric_values: list[dict],  # type: ignore[type-arg]
        config: FinancialConfigurationResponse,
        granularity: PortfolioGranularity,
    ) -> PortfolioFinancialsResponse:
        buckets: dict[tuple[str, int, int | None, int | None], dict] = {}  # type: ignore[type-arg]
        broader: dict[tuple[str, int, int | None, int | None], dict] = {}  # type: ignore[type-arg]
        metric_breakdown: dict[str, dict[str, object]] = {}
        cost_breakdown: dict[str, dict[str, object]] = {}
        groups = {group.key: group for group in config.groups}
        items = {item.key: item for item in config.items}
        custom_benefit_keys = {
            item.key
            for item in config.items
            if item.item_type == "metric"
            and item.is_active
            and item.rollup_type == "benefit"
            and not item.system_metric_key
        }

        def target(row: dict) -> dict:  # type: ignore[type-arg]
            key = cls._portfolio_bucket_key(row, granularity)
            if key is None:
                period = cls._period_key(row)
                key = (cls._period_label(*period), period[0], period[1], period[2])
                return broader.setdefault(key, cls._empty_portfolio_period(*key))
            return buckets.setdefault(key, cls._empty_portfolio_period(*key))

        for row in entries:
            period = target(row)
            plan = _dec(row.get("gm_uplift_base"))
            actual = _dec(row.get("gm_uplift_actual"))
            period["benefits_plan"] += plan
            period["benefits_actual"] += actual
            for key in ("revenue_uplift_base", "cogs_base", "gm_uplift_base"):
                item = items.get(key)
                if not item or not item.is_active:
                    continue
                group = groups.get(item.group_key or "")
                record = metric_breakdown.setdefault(
                    key,
                    {
                        "label": item.label,
                        "group_key": item.group_key,
                        "group_label": group.label if group else None,
                        "plan": Decimal("0"),
                        "actual": Decimal("0"),
                    },
                )
                actual_key = key.replace("_base", "_actual")
                record["plan"] += _dec(row.get(key))  # type: ignore[operator]
                record["actual"] += _dec(row.get(actual_key))  # type: ignore[operator]

        for row in metric_values:
            item = items.get(str(row.get("metric_key")))
            if not item or not item.is_active:
                continue
            group = groups.get(item.group_key or "")
            plan = _dec(row.get("value_base"))
            actual = _dec(row.get("value_actual"))
            if item.key in custom_benefit_keys:
                period = target(row)
                period["benefits_plan"] += plan
                period["benefits_actual"] += actual
            record = metric_breakdown.setdefault(
                item.key,
                {
                    "label": item.label,
                    "group_key": item.group_key,
                    "group_label": group.label if group else None,
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                },
            )
            record["plan"] += plan  # type: ignore[operator]
            record["actual"] += actual  # type: ignore[operator]

        for row in cost_lines:
            period = target(row)
            plan = _dec(row.get("amount_plan"))
            actual = _dec(row.get("amount_actual"))
            if row.get("is_recurring", False):
                period["recurring_costs_plan"] += plan
                period["recurring_costs_actual"] += actual
            else:
                period["one_off_costs_plan"] += plan
                period["one_off_costs_actual"] += actual
            category_key = row.get("category_key") or "other"
            item = items.get(category_key)
            group = groups.get(item.group_key or "") if item else None
            label = item.label if item else str(category_key)
            record = cost_breakdown.setdefault(
                category_key,
                {
                    "label": label,
                    "group_key": item.group_key if item else None,
                    "group_label": group.label if group else None,
                    "plan": Decimal("0"),
                    "actual": Decimal("0"),
                },
            )
            record["plan"] += plan  # type: ignore[operator]
            record["actual"] += actual  # type: ignore[operator]

        periods = [cls._to_portfolio_period(row) for row in buckets.values()]
        periods.sort(key=lambda row: cls._period_sort((row.year, row.quarter, row.month)))
        broader_periods = [cls._to_portfolio_period(row) for row in broader.values()]
        broader_periods.sort(key=lambda row: cls._period_sort((row.year, row.quarter, row.month)))

        totals = cls._empty_portfolio_period("Total", 0, None, None)
        for row in [*periods, *broader_periods]:
            totals["benefits_plan"] += _dec(row.benefits_plan)
            totals["benefits_actual"] += _dec(row.benefits_actual)
            totals["recurring_costs_plan"] += _dec(row.recurring_costs_plan)
            totals["recurring_costs_actual"] += _dec(row.recurring_costs_actual)
            totals["one_off_costs_plan"] += _dec(row.one_off_costs_plan)
            totals["one_off_costs_actual"] += _dec(row.one_off_costs_actual)
        total_period = cls._to_portfolio_period(totals)
        summary = [
            (
                "benefits",
                "Total Benefits",
                total_period.benefits_plan,
                total_period.benefits_actual,
            ),
            (
                "recurring_costs",
                "Recurring Costs",
                total_period.recurring_costs_plan,
                total_period.recurring_costs_actual,
            ),
            (
                "one_off_costs",
                "One-off Costs",
                total_period.one_off_costs_plan,
                total_period.one_off_costs_actual,
            ),
            (
                "total_costs",
                "Total Costs",
                total_period.total_costs_plan,
                total_period.total_costs_actual,
            ),
            (
                "net_value",
                "Net Run-rate Impact",
                total_period.net_value_plan,
                total_period.net_value_actual,
            ),
        ]

        def breakdown(records: dict[str, dict[str, object]]) -> list[PortfolioFinancialBreakdown]:
            items_out = []
            for key, record in records.items():
                plan = record["plan"]
                actual = record["actual"]
                items_out.append(
                    PortfolioFinancialBreakdown(
                        key=key,
                        label=str(record["label"]),
                        group_key=record.get("group_key"),  # type: ignore[arg-type]
                        group_label=record.get("group_label"),  # type: ignore[arg-type]
                        plan=_money(plan),
                        actual=_money(actual),
                        variance=_money(actual - plan),  # type: ignore[operator]
                    )
                )
            return sorted(items_out, key=lambda item: (item.group_label or "", item.label))

        return PortfolioFinancialsResponse(
            granularity=granularity,
            summary=[
                PortfolioFinancialSummaryCard(
                    key=key,
                    label=label,
                    plan=plan,
                    actual=actual,
                    variance=_money(_dec(actual) - _dec(plan)),
                )
                for key, label, plan, actual in summary
            ],
            periods=periods,
            broader_period_totals=broader_periods,
            cost_breakdown=breakdown(cost_breakdown),
            metric_breakdown=breakdown(metric_breakdown),
        )

    @classmethod
    def _compute_portfolio_contributors(
        cls,
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        metric_values: list[dict],  # type: ignore[type-arg]
        initiatives: dict[str, dict],  # type: ignore[type-arg]
        config: FinancialConfigurationResponse,
        granularity: PortfolioGranularity,
        period: str,
        period_key: tuple[str, int, int | None, int | None],
    ) -> PortfolioFinancialContributorsResponse:
        items = {item.key: item for item in config.items}
        custom_benefit_keys = {
            item.key
            for item in config.items
            if item.item_type == "metric"
            and item.is_active
            and item.rollup_type == "benefit"
            and not item.system_metric_key
        }
        contributors: dict[str, dict[str, object]] = {}

        def record_for(initiative_id: str) -> dict[str, object]:
            initiative = initiatives.get(initiative_id, {})
            return contributors.setdefault(
                initiative_id,
                {
                    "initiative_id": initiative_id,
                    "initiative_name": initiative.get("name") or "Untitled initiative",
                    "benefits_plan": Decimal("0"),
                    "benefits_actual": Decimal("0"),
                    "recurring_costs_plan": Decimal("0"),
                    "recurring_costs_actual": Decimal("0"),
                    "one_off_costs_plan": Decimal("0"),
                    "one_off_costs_actual": Decimal("0"),
                    "cost_lines": [],
                },
            )

        for row in entries:
            record = record_for(str(row["initiative_id"]))
            record["benefits_plan"] += _dec(row.get("gm_uplift_base"))  # type: ignore[operator]
            record["benefits_actual"] += _dec(row.get("gm_uplift_actual"))  # type: ignore[operator]

        for row in metric_values:
            if str(row.get("metric_key")) not in custom_benefit_keys:
                continue
            record = record_for(str(row["initiative_id"]))
            record["benefits_plan"] += _dec(row.get("value_base"))  # type: ignore[operator]
            record["benefits_actual"] += _dec(row.get("value_actual"))  # type: ignore[operator]

        for row in cost_lines:
            record = record_for(str(row["initiative_id"]))
            plan = _dec(row.get("amount_plan"))
            actual = _dec(row.get("amount_actual"))
            category_key = row.get("category_key") or "other"
            category = items.get(category_key)
            if row.get("is_recurring", False):
                record["recurring_costs_plan"] += plan  # type: ignore[operator]
                record["recurring_costs_actual"] += actual  # type: ignore[operator]
            else:
                record["one_off_costs_plan"] += plan  # type: ignore[operator]
                record["one_off_costs_actual"] += actual  # type: ignore[operator]
            record["cost_lines"].append(  # type: ignore[union-attr]
                PortfolioFinancialCostLineContribution(
                    id=row["id"],
                    name=row["name"],
                    category_key=category_key,
                    category_label=category.label if category else None,
                    is_recurring=row.get("is_recurring", False),
                    plan=_money(plan),
                    actual=_money(actual),
                )
            )

        contribution_items: list[PortfolioFinancialInitiativeContribution] = []
        for record in contributors.values():
            benefits_plan = record["benefits_plan"]
            benefits_actual = record["benefits_actual"]
            recurring_plan = record["recurring_costs_plan"]
            recurring_actual = record["recurring_costs_actual"]
            one_off_plan = record["one_off_costs_plan"]
            one_off_actual = record["one_off_costs_actual"]
            total_plan = recurring_plan + one_off_plan  # type: ignore[operator]
            total_actual = recurring_actual + one_off_actual  # type: ignore[operator]
            contribution_items.append(
                PortfolioFinancialInitiativeContribution(
                    initiative_id=str(record["initiative_id"]),
                    initiative_name=str(record["initiative_name"]),
                    benefits_plan=_money(benefits_plan),
                    benefits_actual=_money(benefits_actual),
                    recurring_costs_plan=_money(recurring_plan),
                    recurring_costs_actual=_money(recurring_actual),
                    one_off_costs_plan=_money(one_off_plan),
                    one_off_costs_actual=_money(one_off_actual),
                    total_costs_plan=_money(total_plan),
                    total_costs_actual=_money(total_actual),
                    net_value_plan=_money(benefits_plan - recurring_plan),  # type: ignore[operator]
                    net_value_actual=_money(benefits_actual - recurring_actual),  # type: ignore[operator]
                    cost_lines=record["cost_lines"],  # type: ignore[arg-type]
                )
            )

        contribution_items.sort(
            key=lambda item: (
                -abs(_dec(item.total_costs_plan)) - abs(_dec(item.benefits_plan)),
                item.initiative_name,
            )
        )
        return PortfolioFinancialContributorsResponse(
            granularity=granularity,
            period=period,
            year=period_key[1],
            quarter=period_key[2],
            month=period_key[3],
            contributors=contribution_items,
        )

    @staticmethod
    def _to_cost_line(row: dict) -> CostLineItem:  # type: ignore[type-arg]
        return CostLineItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            name=row["name"],
            category_id=row.get("category_id"),
            category_key=row.get("category_key") or "other",
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            amount_plan=_money(row.get("amount_plan")),
            amount_actual=_str_or_none(
                _dec(row["amount_actual"]) if row.get("amount_actual") is not None else None
            ),
            is_recurring=row.get("is_recurring", False),
        )

    @staticmethod
    def _to_cell_assumption(row: dict) -> FinancialCellAssumption:  # type: ignore[type-arg]
        return FinancialCellAssumption(
            id=row["id"],
            initiative_id=row["initiative_id"],
            row_key=row["row_key"],
            column_key=row["column_key"],
            comment=row["comment"],
            created_by=row.get("created_by"),
            updated_by=row.get("updated_by"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
