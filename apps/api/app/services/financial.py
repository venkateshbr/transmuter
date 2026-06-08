"""Financial service — business logic layer.

All financial calculations use Decimal arithmetic. Never float.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.domain.financials import (
    BankablePlanResponse,
    BankablePlanSnapshot,
    BankablePlanVersion,
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
    FinancialEntryUpdate,
    FinancialGridResponse,
    FinancialGridUpdate,
    FinancialMetricDeactivateRequest,
    FinancialMetricValueRow,
    FinancialMetricValueUpdate,
    FinancialScenario,
    FinancialSummary,
    InitiativeFinancialSelections,
    InitiativeFinancialSelectionsResponse,
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
        locked, lock_reason = self._financial_lock_state(initiative_id)
        if not locked:
            self._migrate_existing_grid_to_planned_window(initiative_id)
        rows = self._repo.get_entries(initiative_id)
        costs = self._repo.list_cost_lines(initiative_id)
        raw_metric_values = self._repo.list_metric_values(initiative_id)
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
        return FinancialGridResponse(
            initiative_id=initiative_id,
            entries=entries,
            metric_values=metric_values,
            selections=selections,
            locked=locked,
            lock_reason=lock_reason,
            summary=summary,
        )

    def get_financial_summary(self, initiative_id: str) -> FinancialSummary:
        """Aggregated summary cards only."""
        rows = self._repo.get_entries(initiative_id)
        costs = self._repo.list_cost_lines(initiative_id)
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
        self._assert_financials_editable(initiative_id)
        data = self._normalize_grid_to_planned_window(initiative_id, data)
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

        if data.metric_values:
            metric_rows = []
            for metric in data.metric_values:
                metric_rows.append(
                    {
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
                )
            self._repo.upsert_metric_values_batch(initiative_id, metric_rows)

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
        config = self.get_configuration()
        valid_metric_keys, valid_cost_keys = self._active_selection_keys(config)
        metric_keys = [key for key in selections.metric_keys if key in valid_metric_keys]
        cost_keys = [key for key in selections.cost_category_keys if key in valid_cost_keys]
        self._repo.replace_financial_selections(
            initiative_id,
            metric_keys,
            cost_keys,
            sorted(valid_metric_keys),
            sorted(valid_cost_keys),
        )
        return self.get_initiative_selections(initiative_id)

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

    def lock_bankable_plan_from_approval(
        self,
        initiative_id: str,
        submission_id: str,
        locked_by_id: str,
        locked_reason: str | None = None,
    ) -> BankablePlanVersion:
        self._ensure_tenant_initiative(initiative_id)
        latest = self._repo.get_latest_bankable_plan(initiative_id)
        if latest and latest.get("trigger_type") == "approval" and latest.get("trigger_submission_id") == submission_id:
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
            selections=selections,
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

    # ── Portfolio financials ─────────────────────────────────────────────────

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
        return self._compute_portfolio_financials(
            entries, costs, metric_values, config, granularity
        )

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

    # ── Value Bridge ──────────────────────────────────────────────────────────

    def get_value_bridge(self, initiative_id: str) -> ValueBridgeResponse:
        """Value Bridge for a single initiative."""
        raw_entries = self._repo.get_entries(initiative_id)
        raw_cost_lines = self._repo.list_cost_lines(initiative_id)
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
        )

    def get_scenario_summary(
        self,
        initiative_id: str,
        scenario: FinancialScenario,
    ) -> ScenarioFinancialSummary:
        raw_entries = self._repo.get_entries(initiative_id)
        raw_cost_lines = self._repo.list_cost_lines(initiative_id)
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
        )

    def get_portfolio_value_bridge(self) -> ValueBridgeResponse:
        """Portfolio-level Value Bridge across all initiatives."""
        entries = self._reporting_rows(self._repo.get_all_entries())
        cost_lines = self._reporting_cost_lines(self._repo.get_all_cost_lines())
        metric_values = self._reporting_metric_values(self._repo.get_all_metric_values())
        return self._compute_value_bridge(
            entries,
            cost_lines,
            initiative_id=None,
            metric_values=metric_values,
            config=self.get_configuration(),
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

    def _financial_lock_state(self, initiative_id: str) -> tuple[bool, str | None]:
        initiative = self._repo.get_initiative_period(initiative_id)
        stage = str((initiative or {}).get("stage") or "")
        if stage and stage != "scoping":
            return True, "Financials are locked after the initiative moves to execution."
        return False, None

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

        return InitiativeFinancialSelections(
            metric_keys=sorted(metric_keys & valid_metric_keys),
            cost_category_keys=sorted(cost_keys & valid_cost_keys),
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
            "revenue_uplift_base",
            "revenue_uplift_high",
            "revenue_uplift_actual",
            "gm_uplift_base",
            "gm_uplift_high",
            "gm_uplift_actual",
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

    @staticmethod
    def _compute_value_bridge(
        entries: list[dict],  # type: ignore[type-arg]
        cost_lines: list[dict],  # type: ignore[type-arg]
        initiative_id: str | None,
        metric_values: list[dict] | None = None,  # type: ignore[type-arg]
        config: FinancialConfigurationResponse | None = None,
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

        return ValueBridgeResponse(
            initiative_id=initiative_id,
            base_case=ValueBridgeCase(
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
            ),
            high_case=ValueBridgeCase(
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
            ),
            actual=ValueBridgeCase(
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
            ),
        )

    @staticmethod
    def _compute_scenario_summary(
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
