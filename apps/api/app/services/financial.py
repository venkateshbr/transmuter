"""Financial service — business logic layer.

All financial calculations use Decimal arithmetic. Never float.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from supabase import Client

from app.domain.financials import (
    CostLineCreate,
    CostLineItem,
    CostLineListResponse,
    CostLineUpdate,
    FinancialEntryRow,
    FinancialGridResponse,
    FinancialGridUpdate,
    FinancialSummary,
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
    return str(val)


# Fields that exist on financial_entries for the new uplift model
_ENTRY_FIELDS = [
    "revenue_uplift_base", "revenue_uplift_high", "revenue_uplift_actual",
    "revenue_uplift_pct_base", "revenue_uplift_pct_high", "revenue_uplift_pct_actual",
    "gross_margin_base", "gross_margin_high", "gross_margin_high",
    "gross_margin_actual",
    "gm_pct_base", "gm_pct_high", "gm_pct_actual",
    "gm_uplift_base", "gm_uplift_high", "gm_uplift_actual",
    "gm_uplift_pct_base", "gm_uplift_pct_high", "gm_uplift_pct_actual",
    "cogs_base", "cogs_high", "cogs_actual",
    "cogs_pct_base", "cogs_pct_high", "cogs_pct_actual",
]


class FinancialService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = FinancialRepository(client, tenant_id)
        self._tenant_id = tenant_id

    # ── Financial grid ────────────────────────────────────────────────────────

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
        db_rows: list[dict[str, object]] = []
        for entry in data.entries:
            row: dict[str, object] = {
                "year": entry.year,
                "quarter": entry.quarter,
                "month": entry.month,
            }
            # Add all numeric fields — base/high as required, actual as optional
            for field_name in [
                "revenue_uplift_base", "revenue_uplift_high",
                "revenue_uplift_pct_base", "revenue_uplift_pct_high",
            "gross_margin_base", "gross_margin_high",
                "gm_pct_base", "gm_pct_high",
                "gm_uplift_base", "gm_uplift_high",
                "gm_uplift_pct_base", "gm_uplift_pct_high",
                "cogs_base", "cogs_high",
                "cogs_pct_base", "cogs_pct_high",
            ]:
                row[field_name] = str(getattr(entry, field_name))

            for field_name in [
                "revenue_uplift_actual", "revenue_uplift_pct_actual",
                "gross_margin_actual", "gm_pct_actual",
                "gm_uplift_actual", "gm_uplift_pct_actual",
                "cogs_actual", "cogs_pct_actual",
            ]:
                val = getattr(entry, field_name)
                row[field_name] = str(val) if val is not None else None

            db_rows.append(row)

        if db_rows:
            self._repo.upsert_entries_batch(initiative_id, db_rows)

        # Process cost lines if present
        if data.cost_lines:
            cost_rows = []
            for cl in data.cost_lines:
                cost_rows.append({
                    "name": cl.name,
                    "year": cl.year,
                    "quarter": cl.quarter,
                    "month": cl.month,
                    "amount_plan": str(cl.amount_plan),
                    "amount_actual": str(cl.amount_actual) if cl.amount_actual is not None else None,
                    "is_recurring": cl.is_recurring,
                })
            self._repo.upsert_cost_lines_batch(initiative_id, cost_rows)

        return self.get_financial_grid(initiative_id)

    def export_workbook(self, initiative_id: str) -> bytes:
        """Export initiative financial entries and cost lines as an XLSX workbook."""
        entries = self._unique_entries(self._repo.get_entries(initiative_id))
        cost_lines = self._unique_cost_lines(self._repo.list_cost_lines(initiative_id))
        return build_financial_workbook(entries, cost_lines)

    def import_workbook(self, initiative_id: str, data: bytes) -> FinancialGridResponse:
        """Import an XLSX workbook into the initiative financial grid."""
        update = parse_financial_workbook(data)
        return self.update_financial_grid(initiative_id, update)

    # ── Cost lines ────────────────────────────────────────────────────────────

    def list_cost_lines(self, initiative_id: str) -> CostLineListResponse:
        rows = self._repo.list_cost_lines(initiative_id)
        items = [self._to_cost_line(r) for r in rows]
        return CostLineListResponse(items=items, total=len(items))

    def create_cost_line(self, initiative_id: str, data: CostLineCreate) -> CostLineItem:
        row = self._repo.create_cost_line(initiative_id, {
            "name": data.name,
            "year": data.year,
            "quarter": data.quarter,
            "month": data.month,
            "amount_plan": str(data.amount_plan),
            "amount_actual": str(data.amount_actual) if data.amount_actual is not None else None,
            "is_recurring": data.is_recurring,
        })
        return self._to_cost_line(row)

    def update_cost_line(self, cost_line_id: str, data: CostLineUpdate) -> CostLineItem:
        patch: dict[str, object] = {}
        for field in ("name", "year", "quarter", "month", "is_recurring"):
            val = getattr(data, field)
            if val is not None:
                patch[field] = val
        if data.amount_plan is not None:
            patch["amount_plan"] = str(data.amount_plan)
        if data.amount_actual is not None:
            patch["amount_actual"] = str(data.amount_actual)
        row = self._repo.update_cost_line(cost_line_id, patch)
        return self._to_cost_line(row)

    def delete_cost_line(self, cost_line_id: str) -> None:
        self._repo.delete_cost_line(cost_line_id)

    # ── Value Bridge ──────────────────────────────────────────────────────────

    def get_value_bridge(self, initiative_id: str) -> ValueBridgeResponse:
        """Value Bridge for a single initiative."""
        entries = self._reporting_rows(self._repo.get_entries(initiative_id))
        cost_lines = self._repo.list_cost_lines(initiative_id)
        return self._compute_value_bridge(entries, cost_lines, initiative_id)

    def get_portfolio_value_bridge(self) -> ValueBridgeResponse:
        """Portfolio-level Value Bridge across all initiatives."""
        entries = self._reporting_rows(self._repo.get_all_entries())
        cost_lines = self._repo.get_all_cost_lines()
        return self._compute_value_bridge(entries, cost_lines, initiative_id=None)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _to_entry_row(row: dict) -> FinancialEntryRow:  # type: ignore[type-arg]
        def _actual(key: str) -> str | None:
            v = row.get(key)
            return str(_dec(v)) if v is not None else None

        return FinancialEntryRow(
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            revenue_uplift_base=str(_dec(row.get("revenue_uplift_base"))),
            revenue_uplift_high=str(_dec(row.get("revenue_uplift_high"))),
            revenue_uplift_actual=_actual("revenue_uplift_actual"),
            revenue_uplift_pct_base=str(_dec(row.get("revenue_uplift_pct_base"))),
            revenue_uplift_pct_high=str(_dec(row.get("revenue_uplift_pct_high"))),
            revenue_uplift_pct_actual=_actual("revenue_uplift_pct_actual"),
            gross_margin_base=str(_dec(row.get("gross_margin_base"))),
            gross_margin_high=str(_dec(row.get("gross_margin_high"))),
            gross_margin_actual=_actual("gross_margin_actual"),
            gm_pct_base=str(_dec(row.get("gm_pct_base"))),
            gm_pct_high=str(_dec(row.get("gm_pct_high"))),
            gm_pct_actual=_actual("gm_pct_actual"),
            gm_uplift_base=str(_dec(row.get("gm_uplift_base"))),
            gm_uplift_high=str(_dec(row.get("gm_uplift_high"))),
            gm_uplift_actual=_actual("gm_uplift_actual"),
            gm_uplift_pct_base=str(_dec(row.get("gm_uplift_pct_base"))),
            gm_uplift_pct_high=str(_dec(row.get("gm_uplift_pct_high"))),
            gm_uplift_pct_actual=_actual("gm_uplift_pct_actual"),
            cogs_base=str(_dec(row.get("cogs_base"))),
            cogs_high=str(_dec(row.get("cogs_high"))),
            cogs_actual=_actual("cogs_actual"),
            cogs_pct_base=str(_dec(row.get("cogs_pct_base"))),
            cogs_pct_high=str(_dec(row.get("cogs_pct_high"))),
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
                    costs_recurring_actual = (costs_recurring_actual or Decimal("0")) + _dec(actual_val)
            else:
                costs_one_off_plan += plan
                if actual_val is not None:
                    costs_one_off_actual = (costs_one_off_actual or Decimal("0")) + _dec(actual_val)

        costs_plan = costs_recurring_plan + costs_one_off_plan
        costs_actual: Decimal | None = None
        if costs_recurring_actual is not None or costs_one_off_actual is not None:
            costs_actual = (costs_recurring_actual or Decimal("0")) + (costs_one_off_actual or Decimal("0"))

        # Net Value = GM Uplift - Recurring Costs
        net_plan = gm_up_base - costs_recurring_plan
        net_actual: Decimal | None = None
        if gm_up_actual is not None and costs_recurring_actual is not None:
            net_actual = gm_up_actual - costs_recurring_actual

        return FinancialSummary(
            revenue_uplift_plan_base=str(rev_base),
            revenue_uplift_plan_high=str(rev_high),
            revenue_uplift_actual=_str_or_none(rev_actual),
            gross_margin_plan_base=str(gm_base),
            gross_margin_plan_high=str(gm_high),
            gross_margin_actual=_str_or_none(gm_actual),
            gm_uplift_plan_base=str(gm_up_base),
            gm_uplift_plan_high=str(gm_up_high),
            gm_uplift_actual=_str_or_none(gm_up_actual),
            cogs_plan_base=str(cogs_base),
            cogs_plan_high=str(cogs_high),
            cogs_actual=_str_or_none(cogs_actual),
            costs_recurring_plan=str(costs_recurring_plan),
            costs_recurring_actual=_str_or_none(costs_recurring_actual),
            costs_one_off_plan=str(costs_one_off_plan),
            costs_one_off_actual=_str_or_none(costs_one_off_actual),
            costs_plan=str(costs_plan),
            costs_actual=_str_or_none(costs_actual),
            net_value_plan=str(net_plan),
            net_value_actual=_str_or_none(net_actual),
            benefit_run_rate=str(gm_up_base),  # annualised GM uplift (base)
            cost_run_rate=str(costs_recurring_plan),  # annualised recurring costs
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
                revenue_uplift=str(rev_base),
                gross_margin=str(gm_base),
                gm_uplift=str(gm_up_base),
                costs_recurring=str(costs_recurring_plan),
                costs_one_off=str(costs_one_off_plan),
                costs_total=str(total_costs_plan),
                net=str(gm_up_base - costs_recurring_plan),
            ),
            high_case=ValueBridgeCase(
                revenue_uplift=str(rev_high),
                gross_margin=str(gm_high),
                gm_uplift=str(gm_up_high),
                costs_recurring=str(costs_recurring_plan),
                costs_one_off=str(costs_one_off_plan),
                costs_total=str(total_costs_plan),
                net=str(gm_up_high - costs_recurring_plan),
            ),
            actual=ValueBridgeCase(
                revenue_uplift=str(rev_actual),
                gross_margin=str(gm_actual),
                gm_uplift=str(gm_up_actual),
                costs_recurring=str(costs_recurring_actual),
                costs_one_off=str(costs_one_off_actual),
                costs_total=str(total_costs_actual),
                net=str(gm_up_actual - costs_recurring_actual),
            ),
        )

    @staticmethod
    def _to_cost_line(row: dict) -> CostLineItem:  # type: ignore[type-arg]
        return CostLineItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            name=row["name"],
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            amount_plan=str(_dec(row.get("amount_plan"))),
            amount_actual=_str_or_none(
                _dec(row["amount_actual"]) if row.get("amount_actual") is not None else None
            ),
            is_recurring=row.get("is_recurring", False),
        )
