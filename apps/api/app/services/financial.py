"""Financial service — business logic layer.

All financial calculations use Decimal arithmetic. Never float.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.domain.financials import (
    BreakEvenPoint,
    BreakEvenResponse,
    CostLineCreate,
    CostLineItem,
    CostLineListResponse,
    CostLineUpdate,
    FinancialCategoryDeleteRequest,
    FinancialCellAssumption,
    FinancialCellAssumptionCreate,
    FinancialCellAssumptionListResponse,
    FinancialCellAssumptionUpdate,
    FinancialConfigGroup,
    FinancialConfigItem,
    FinancialConfigurationResponse,
    FinancialConfigurationUpdate,
    FinancialEntryRow,
    FinancialGridResponse,
    FinancialGridUpdate,
    FinancialMetricDeactivateRequest,
    FinancialScenario,
    FinancialSummary,
    PortfolioFinancialBreakdown,
    PortfolioFinancialContributorsResponse,
    PortfolioFinancialCostLineContribution,
    PortfolioFinancialInitiativeContribution,
    PortfolioFinancialPeriod,
    PortfolioFinancialsResponse,
    PortfolioFinancialSummaryCard,
    PortfolioGranularity,
    ScenarioFinancialSummary,
    ValueBridgeCase,
    ValueBridgeResponse,
)
from app.repositories.financial import FinancialRepository
from app.services.financial_workbook import build_financial_workbook, parse_financial_workbook


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
        rows = self._repo.get_entries(initiative_id)
        entries = [self._to_entry_row(r) for r in rows]
        summary = self._compute_summary(rows, initiative_id)
        return FinancialGridResponse(
            initiative_id=initiative_id,
            entries=entries,
            summary=summary,
        )

    def get_financial_summary(self, initiative_id: str) -> FinancialSummary:
        """Aggregated summary cards only."""
        rows = self._repo.get_entries(initiative_id)
        return self._compute_summary(rows, initiative_id)

    def update_financial_grid(
        self, initiative_id: str, data: FinancialGridUpdate
    ) -> FinancialGridResponse:
        """Upsert the full financial grid."""
        self._ensure_tenant_initiative(initiative_id)
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

            db_rows.append(row)

        if db_rows:
            self._repo.upsert_entries_batch(initiative_id, db_rows)

        # Process cost lines if present
        if data.cost_lines:
            cost_rows = []
            for cl in data.cost_lines:
                cost_rows.append(
                    {
                        "name": cl.name,
                        "category_key": cl.category_key,
                        "year": cl.year,
                        "quarter": cl.quarter,
                        "month": cl.month,
                        "amount_plan": _money(cl.amount_plan),
                        "amount_actual": _money(cl.amount_actual)
                        if cl.amount_actual is not None
                        else None,
                        "is_recurring": cl.is_recurring,
                    }
                )
            self._repo.upsert_cost_lines_batch(initiative_id, cost_rows)

        return self.get_financial_grid(initiative_id)

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
        for field in ("name", "category_key", "year", "quarter", "month", "is_recurring"):
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

    # ── Tenant financial configuration ───────────────────────────────────────

    def get_configuration(self) -> FinancialConfigurationResponse:
        groups = [self._to_config_group(row) for row in self._repo.list_config_groups()]
        group_key_by_id = {group.id: group.key for group in groups if group.id}
        items = [
            self._to_config_item(row, group_key_by_id.get(row.get("group_id")))
            for row in self._repo.list_config_items()
        ]
        return FinancialConfigurationResponse(groups=groups, items=items)

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

    def get_portfolio_financials(
        self,
        granularity: PortfolioGranularity,
        year: int | None = None,
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        tag: str | None = None,
        category_key: str | None = None,
    ) -> PortfolioFinancialsResponse:
        initiatives = {
            row["id"]: row
            for row in self._repo.get_portfolio_initiatives()
            if (not initiative_id or row["id"] == initiative_id)
            and (not workstream_id or row.get("workstream_id") == workstream_id)
            and (not business_unit_id or row.get("business_unit_id") == business_unit_id)
            and (not tag or row.get("tag") == tag)
        }
        entries = [
            row
            for row in self._reporting_rows(self._repo.get_all_entries())
            if row.get("initiative_id") in initiatives and (year is None or row.get("year") == year)
        ]
        costs = [
            row
            for row in self._repo.get_all_cost_lines()
            if row.get("initiative_id") in initiatives
            and (year is None or row.get("year") == year)
            and (not category_key or row.get("category_key", "other") == category_key)
        ]
        config = self.get_configuration()
        return self._compute_portfolio_financials(entries, costs, config, granularity)

    def get_portfolio_financial_contributors(
        self,
        granularity: PortfolioGranularity,
        period: str,
        year: int | None = None,
        initiative_id: str | None = None,
        workstream_id: str | None = None,
        business_unit_id: str | None = None,
        tag: str | None = None,
        category_key: str | None = None,
    ) -> PortfolioFinancialContributorsResponse:
        period_key = self._parse_portfolio_period(period, granularity)
        effective_year = year or period_key[1]
        initiatives = {
            row["id"]: row
            for row in self._repo.get_portfolio_initiatives()
            if (not initiative_id or row["id"] == initiative_id)
            and (not workstream_id or row.get("workstream_id") == workstream_id)
            and (not business_unit_id or row.get("business_unit_id") == business_unit_id)
            and (not tag or row.get("tag") == tag)
        }
        entries = [
            row
            for row in self._reporting_rows(self._repo.get_all_entries())
            if row.get("initiative_id") in initiatives
            and row.get("year") == effective_year
            and self._portfolio_row_period_label(row, granularity) == period
        ]
        costs = [
            row
            for row in self._repo.get_all_cost_lines()
            if row.get("initiative_id") in initiatives
            and row.get("year") == effective_year
            and self._portfolio_row_period_label(row, granularity) == period
            and (not category_key or row.get("category_key", "other") == category_key)
        ]
        config = self.get_configuration()
        return self._compute_portfolio_contributors(
            entries,
            costs,
            initiatives,
            config,
            granularity,
            period,
            period_key,
        )

    # ── Value Bridge ──────────────────────────────────────────────────────────

    def get_value_bridge(self, initiative_id: str) -> ValueBridgeResponse:
        """Value Bridge for a single initiative."""
        entries = self._reporting_rows(self._repo.get_entries(initiative_id))
        cost_lines = self._repo.list_cost_lines(initiative_id)
        return self._compute_value_bridge(entries, cost_lines, initiative_id)

    def get_scenario_summary(
        self,
        initiative_id: str,
        scenario: FinancialScenario,
    ) -> ScenarioFinancialSummary:
        entries = self._reporting_rows(self._repo.get_entries(initiative_id))
        cost_lines = self._repo.list_cost_lines(initiative_id)
        return self._compute_scenario_summary(entries, cost_lines, scenario)

    def get_break_even(
        self,
        initiative_id: str,
        scenario: FinancialScenario,
    ) -> BreakEvenResponse:
        entries = self._reporting_rows(self._repo.get_entries(initiative_id))
        cost_lines = self._repo.list_cost_lines(initiative_id)
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
        )

    def get_portfolio_value_bridge(self) -> ValueBridgeResponse:
        """Portfolio-level Value Bridge across all initiatives."""
        entries = self._reporting_rows(self._repo.get_all_entries())
        cost_lines = self._repo.get_all_cost_lines()
        return self._compute_value_bridge(entries, cost_lines, initiative_id=None)

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

    def _compute_summary(self, rows: list[dict], initiative_id: str) -> FinancialSummary:  # type: ignore[type-arg]
        """Aggregate summary cards from all entries + cost lines.

        Net Value = GM Uplift - Recurring Costs.
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
        cost_lines = self._repo.list_cost_lines(initiative_id)
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

        costs_plan = costs_recurring_plan + costs_one_off_plan
        costs_actual: Decimal | None = None
        if costs_recurring_actual is not None or costs_one_off_actual is not None:
            costs_actual = (costs_recurring_actual or Decimal("0")) + (
                costs_one_off_actual or Decimal("0")
            )

        # Net Value = GM Uplift - Recurring Costs
        net_plan = gm_up_base - costs_recurring_plan
        net_actual: Decimal | None = None
        if gm_up_actual is not None and costs_recurring_actual is not None:
            net_actual = gm_up_actual - costs_recurring_actual

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
            benefit_run_rate=_money(gm_up_base),  # annualised GM uplift (base)
            cost_run_rate=_money(costs_recurring_plan),  # annualised recurring costs
        )

    @staticmethod
    def _reporting_rows(rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        """Return rows for rollups without counting quarter rows covered by month rows."""
        month_keys = {
            (row["initiative_id"], row["year"], ((row["month"] - 1) // 3) + 1)
            for row in rows
            if row.get("month") is not None
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
    def _compute_value_bridge(
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        initiative_id: str | None,
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

        return ValueBridgeResponse(
            initiative_id=initiative_id,
            base_case=ValueBridgeCase(
                revenue_uplift=_money(rev_base),
                gross_margin=_money(gm_base),
                gm_uplift=_money(gm_up_base),
                costs_recurring=_money(costs_recurring_plan),
                costs_one_off=_money(costs_one_off_plan),
                costs_total=_money(total_costs_plan),
                net=_money(gm_up_base - costs_recurring_plan),
            ),
            high_case=ValueBridgeCase(
                revenue_uplift=_money(rev_high),
                gross_margin=_money(gm_high),
                gm_uplift=_money(gm_up_high),
                costs_recurring=_money(costs_recurring_plan),
                costs_one_off=_money(costs_one_off_plan),
                costs_total=_money(total_costs_plan),
                net=_money(gm_up_high - costs_recurring_plan),
            ),
            actual=ValueBridgeCase(
                revenue_uplift=_money(rev_actual),
                gross_margin=_money(gm_actual),
                gm_uplift=_money(gm_up_actual),
                costs_recurring=_money(costs_recurring_actual),
                costs_one_off=_money(costs_one_off_actual),
                costs_total=_money(total_costs_actual),
                net=_money(gm_up_actual - costs_recurring_actual),
            ),
        )

    @staticmethod
    def _compute_scenario_summary(
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        scenario: FinancialScenario,
    ) -> ScenarioFinancialSummary:
        revenue = Decimal("0")
        gross_margin = Decimal("0")
        gm_uplift = Decimal("0")
        for row in entries:
            revenue += FinancialService._scenario_entry_value(row, "revenue_uplift", scenario)
            gross_margin += FinancialService._scenario_entry_value(row, "gross_margin", scenario)
            gm_uplift += FinancialService._scenario_entry_value(row, "gm_uplift", scenario)

        recurring = Decimal("0")
        one_off = Decimal("0")
        for row in cost_lines:
            value = FinancialService._scenario_cost_value(row, scenario)
            if row.get("is_recurring", False):
                recurring += value
            else:
                one_off += value
        total_costs = recurring + one_off
        return ScenarioFinancialSummary(
            scenario=scenario,
            revenue_uplift=_money(revenue),
            gross_margin=_money(gross_margin),
            gm_uplift=_money(gm_uplift),
            cogs=_money(revenue - gross_margin),
            costs_recurring=_money(recurring),
            costs_one_off=_money(one_off),
            costs_total=_money(total_costs),
            net_value=_money(gm_uplift - recurring),
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
            net_value_plan=_money(benefits_plan - total_plan),
            net_value_actual=_money(benefits_actual - total_actual),
        )

    @classmethod
    def _compute_portfolio_financials(
        cls,
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        config: FinancialConfigurationResponse,
        granularity: PortfolioGranularity,
    ) -> PortfolioFinancialsResponse:
        buckets: dict[tuple[str, int, int | None, int | None], dict] = {}  # type: ignore[type-arg]
        broader: dict[tuple[str, int, int | None, int | None], dict] = {}  # type: ignore[type-arg]
        metric_breakdown: dict[str, dict[str, object]] = {}
        cost_breakdown: dict[str, dict[str, object]] = {}
        groups = {group.key: group for group in config.groups}
        items = {item.key: item for item in config.items}

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
            ("benefits", "Benefits", total_period.benefits_plan, total_period.benefits_actual),
            (
                "recurring_costs",
                "Recurring Costs",
                total_period.recurring_costs_plan,
                total_period.recurring_costs_actual,
            ),
            (
                "one_off_costs",
                "One-time Costs",
                total_period.one_off_costs_plan,
                total_period.one_off_costs_actual,
            ),
            (
                "total_costs",
                "Total Costs",
                total_period.total_costs_plan,
                total_period.total_costs_actual,
            ),
            ("net_value", "Net Value", total_period.net_value_plan, total_period.net_value_actual),
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
        initiatives: dict[str, dict],  # type: ignore[type-arg]
        config: FinancialConfigurationResponse,
        granularity: PortfolioGranularity,
        period: str,
        period_key: tuple[str, int, int | None, int | None],
    ) -> PortfolioFinancialContributorsResponse:
        items = {item.key: item for item in config.items}
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
                    net_value_plan=_money(benefits_plan - total_plan),  # type: ignore[operator]
                    net_value_actual=_money(benefits_actual - total_actual),  # type: ignore[operator]
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
