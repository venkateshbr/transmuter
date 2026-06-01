from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.domain.financials import (
    CostLineCreate,
    CostLineUpdate,
    FinancialCellAssumptionUpdate,
    FinancialConfigGroup,
    FinancialConfigItem,
    FinancialConfigurationResponse,
    FinancialEntryUpdate,
    FinancialGridUpdate,
    FinancialMetricValueUpdate,
    InitiativeFinancialSelections,
)
from app.services.financial import FinancialService


def _config() -> FinancialConfigurationResponse:
    return FinancialConfigurationResponse(
        groups=[
            FinancialConfigGroup(
                id="g1",
                key="gross_margin",
                label="Gross Margin",
                kind="metric",
                display_order=1,
                is_system=True,
            ),
            FinancialConfigGroup(
                id="g2",
                key="operating",
                label="Operating Costs",
                kind="cost_category",
                display_order=2,
                is_system=True,
            ),
            FinancialConfigGroup(
                id="g3",
                key="savings",
                label="Savings",
                kind="metric",
                display_order=3,
                is_system=True,
            ),
        ],
        items=[
            FinancialConfigItem(
                id="m1",
                group_id="g1",
                group_key="gross_margin",
                key="gm_uplift_base",
                label="GM Uplift (Base)",
                item_type="metric",
                system_metric_key="gm_uplift_base",
                display_order=1,
                is_system=True,
            ),
            FinancialConfigItem(
                id="c1",
                group_id="g2",
                group_key="operating",
                key="software",
                label="Software",
                item_type="cost_category",
                rollup_type="recurring_cost",
                display_order=1,
                is_system=True,
            ),
            FinancialConfigItem(
                id="m2",
                group_id="g3",
                group_key="savings",
                key="cost_savings",
                label="Cost Savings ($)",
                item_type="metric",
                rollup_type="benefit",
                display_order=1,
                is_system=True,
            ),
        ],
    )


class _SummaryRepo:
    def list_cost_lines(self, _initiative_id: str) -> list[dict]:
        return []


def test_default_financial_scope_includes_all_system_cost_categories() -> None:
    assert set(FinancialService._default_cost_category_keys()) >= {
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
    }


def test_financial_summary_cogs_does_not_double_count_quarters_with_monthly_rows() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _SummaryRepo()

    summary = service._compute_summary(
        [
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": 1,
                "month": None,
                "revenue_uplift_base": "900.0000",
                "revenue_uplift_high": "1200.0000",
                "gross_margin_base": "450.0000",
                "gross_margin_high": "600.0000",
                "gm_uplift_base": "450.0000",
                "gm_uplift_high": "600.0000",
                "cogs_base": "450.0000",
                "cogs_high": "600.0000",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "revenue_uplift_base": "100.0000",
                "revenue_uplift_high": "150.0000",
                "gross_margin_base": "60.0000",
                "gross_margin_high": "90.0000",
                "gm_uplift_base": "60.0000",
                "gm_uplift_high": "90.0000",
                "cogs_base": "40.0000",
                "cogs_high": "60.0000",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": None,
                "month": 2,
                "revenue_uplift_base": "200.0000",
                "revenue_uplift_high": "250.0000",
                "gross_margin_base": "120.0000",
                "gross_margin_high": "150.0000",
                "gm_uplift_base": "120.0000",
                "gm_uplift_high": "150.0000",
                "cogs_base": "80.0000",
                "cogs_high": "100.0000",
            },
        ],
        "i1",
    )

    assert summary.revenue_uplift_plan_base == "300.0000"
    assert summary.gross_margin_plan_base == "180.0000"
    assert summary.gm_uplift_plan_base == "180.0000"
    assert summary.cogs_plan_base == "120.0000"


def test_financial_summary_zero_month_rows_do_not_hide_quarter_values() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _SummaryRepo()

    summary = service._compute_summary(
        [
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": 1,
                "month": None,
                "revenue_uplift_base": "125000.0000",
                "revenue_uplift_high": "0.0000",
                "gross_margin_base": "0.0000",
                "gross_margin_high": "0.0000",
                "gm_uplift_base": "125000.0000",
                "gm_uplift_high": "0.0000",
                "cogs_base": "0.0000",
                "cogs_high": "0.0000",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "revenue_uplift_base": "0.0000",
                "revenue_uplift_high": "0.0000",
                "gross_margin_base": "0.0000",
                "gross_margin_high": "0.0000",
                "gm_uplift_base": "0.0000",
                "gm_uplift_high": "0.0000",
                "cogs_base": "0.0000",
                "cogs_high": "0.0000",
            },
        ],
        "i1",
    )

    assert summary.revenue_uplift_plan_base == "125000.0000"
    assert summary.gm_uplift_plan_base == "125000.0000"


def test_reporting_cost_lines_do_not_double_count_quarter_with_monthly_lines() -> None:
    rows = FinancialService._reporting_cost_lines(
        [
            {
                "id": "quarter",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": 1,
                "month": None,
                "category_key": "implementation",
                "amount_plan": "900.0000",
                "amount_actual": None,
                "is_recurring": False,
            },
            {
                "id": "monthly",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "category_key": "implementation",
                "amount_plan": "300.0000",
                "amount_actual": None,
                "is_recurring": False,
            },
            {
                "id": "other-category-quarter",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "quarter": 1,
                "month": None,
                "category_key": "software",
                "amount_plan": "120.0000",
                "amount_actual": None,
                "is_recurring": True,
            },
        ]
    )

    assert [row["id"] for row in rows] == ["monthly", "other-category-quarter"]


def test_value_bridge_uses_explicit_cogs_instead_of_deriving_from_revenue() -> None:
    bridge = FinancialService._compute_value_bridge(
        [
            {
                "tenant_id": "t1",
                "initiative_id": "initiative-1",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "revenue_uplift_base": "10000.0000",
                "gross_margin_base": "0.0000",
                "gm_uplift_base": "20000.0000",
                "cogs_base": "0.0000",
            }
        ],
        [],
        "initiative-1",
        [
            {
                "tenant_id": "t1",
                "initiative_id": "initiative-1",
                "metric_key": "cost_savings",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "value_base": "5000.0000",
                "value_high": "7500.0000",
                "value_actual": None,
            }
        ],
        _config(),
    )

    assert bridge.base_case.revenue_uplift == "10000.0000"
    assert bridge.base_case.cogs == "0.0000"
    assert bridge.base_case.benefits_total == "25000.0000"
    assert bridge.base_case.net == "25000.0000"


def test_scenario_summary_uses_explicit_cogs_instead_of_deriving_from_revenue() -> None:
    summary = FinancialService._compute_scenario_summary(
        [
            {
                "tenant_id": "t1",
                "initiative_id": "initiative-1",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "revenue_uplift_base": "10000.0000",
                "gross_margin_base": "0.0000",
                "gm_uplift_base": "20000.0000",
                "cogs_base": "0.0000",
            }
        ],
        [],
        [],
        None,
        "base",
    )

    assert summary.revenue_uplift == "10000.0000"
    assert summary.cogs == "0.0000"


def test_financial_scope_filters_hidden_metrics_and_costs_from_summary() -> None:
    service = FinancialService.__new__(FinancialService)
    rows, costs = service._apply_financial_scope(
        [
            {
                "tenant_id": "t1",
                "initiative_id": "initiative-1",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "revenue_uplift_base": "10000.0000",
                "gm_uplift_base": "6000.0000",
                "cogs_base": "4000.0000",
            }
        ],
        [
            {
                "tenant_id": "t1",
                "initiative_id": "initiative-1",
                "year": 2026,
                "quarter": None,
                "month": 1,
                "category_key": "maintenance",
                "amount_plan": "1000.0000",
                "amount_actual": None,
                "is_recurring": True,
            }
        ],
        InitiativeFinancialSelections(
            metric_keys=["revenue_uplift_base", "gm_uplift_base"],
            cost_category_keys=[],
        ),
    )
    service._repo = _SummaryRepo()

    summary = service._compute_summary(rows, "initiative-1", costs)

    assert summary.revenue_uplift_plan_base == "10000.0000"
    assert summary.gm_uplift_plan_base == "6000.0000"
    assert summary.cogs_plan_base == "0.0000"
    assert summary.costs_plan == "0.0000"


def test_portfolio_financials_keeps_broader_periods_separate_for_monthly_view() -> None:
    response = FinancialService._compute_portfolio_financials(
        entries=[
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": 1,
                "quarter": None,
                "gm_uplift_base": "1000.0000",
                "gm_uplift_actual": "900.0000",
                "revenue_uplift_base": "1500.0000",
                "cogs_base": "500.0000",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": None,
                "quarter": 1,
                "gm_uplift_base": "3000.0000",
                "gm_uplift_actual": "2500.0000",
                "revenue_uplift_base": "4500.0000",
                "cogs_base": "1500.0000",
            },
        ],
        cost_lines=[
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": 1,
                "quarter": None,
                "amount_plan": "100.0000",
                "amount_actual": "90.0000",
                "is_recurring": True,
                "category_key": "software",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": 1,
                "quarter": None,
                "amount_plan": "200.0000",
                "amount_actual": "180.0000",
                "is_recurring": False,
                "category_key": "implementation",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": None,
                "quarter": 1,
                "amount_plan": "300.0000",
                "amount_actual": "275.0000",
                "is_recurring": True,
                "category_key": "software",
            },
        ],
        metric_values=[],
        config=_config(),
        granularity="monthly",
    )

    assert response.periods[0].period == "2026-M01"
    assert response.periods[0].benefits_plan == "1000.0000"
    assert response.periods[0].recurring_costs_actual == "90.0000"
    assert response.periods[0].one_off_costs_plan == "200.0000"
    assert response.periods[0].net_value_plan == "900.0000"
    assert response.broader_period_totals[0].period == "2026-Q1"
    assert response.broader_period_totals[0].benefits_plan == "3000.0000"
    assert response.broader_period_totals[0].recurring_costs_actual == "275.0000"
    assert response.summary[0].plan == "4000.0000"
    assert response.summary[1].actual == "365.0000"


def test_portfolio_contributors_group_period_values_by_initiative() -> None:
    response = FinancialService._compute_portfolio_contributors(
        entries=[
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": 6,
                "quarter": None,
                "gm_uplift_base": "60000.0000",
                "gm_uplift_actual": "45000.0000",
            }
        ],
        cost_lines=[
            {
                "id": "cl1",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "name": "Implementation partner",
                "year": 2026,
                "month": 6,
                "quarter": None,
                "amount_plan": "180000.0000",
                "amount_actual": "125000.0000",
                "is_recurring": False,
                "category_key": "software",
            },
            {
                "id": "cl2",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "name": "Platform subscription",
                "year": 2026,
                "month": 6,
                "quarter": None,
                "amount_plan": "10000.0000",
                "amount_actual": "9500.0000",
                "is_recurring": True,
                "category_key": "software",
            },
        ],
        metric_values=[
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "metric_key": "cost_savings",
                "year": 2026,
                "month": 6,
                "quarter": None,
                "value_base": "15000.0000",
                "value_actual": "12000.0000",
            }
        ],
        initiatives={"i1": {"id": "i1", "name": "ERP modernization"}},
        config=_config(),
        granularity="monthly",
        period="2026-M06",
        period_key=("2026-M06", 2026, None, 6),
    )

    assert response.period == "2026-M06"
    assert len(response.contributors) == 1
    contributor = response.contributors[0]
    assert contributor.initiative_name == "ERP modernization"
    assert contributor.benefits_plan == "75000.0000"
    assert contributor.benefits_actual == "57000.0000"
    assert contributor.one_off_costs_actual == "125000.0000"
    assert contributor.recurring_costs_plan == "10000.0000"
    assert contributor.total_costs_plan == "190000.0000"
    assert contributor.net_value_plan == "65000.0000"
    assert contributor.net_value_actual == "47500.0000"
    assert contributor.cost_lines[0].category_label == "Software"


class _ConfigRepo:
    def __init__(self) -> None:
        self.groups = {
            "kept": {
                "id": "g1",
                "key": "kept",
                "label": "Kept",
                "kind": "cost_category",
                "display_order": 1,
                "is_system": False,
                "is_active": True,
            },
            "omitted": {
                "id": "g2",
                "key": "omitted",
                "label": "Omitted",
                "kind": "cost_category",
                "display_order": 2,
                "is_system": False,
                "is_active": True,
            },
        }
        self.items = {
            "kept_item": {
                "id": "i1",
                "group_id": "g1",
                "key": "kept_item",
                "label": "Kept item",
                "item_type": "cost_category",
                "display_order": 1,
                "is_system": False,
                "is_active": True,
            },
            "omitted_item": {
                "id": "i2",
                "group_id": "g2",
                "key": "omitted_item",
                "label": "Omitted item",
                "item_type": "cost_category",
                "display_order": 2,
                "is_system": False,
                "is_active": True,
            },
        }

    def list_config_groups(self) -> list[dict]:
        return list(self.groups.values())

    def list_config_items(self) -> list[dict]:
        return list(self.items.values())

    def upsert_config_group(self, data: dict) -> dict:
        current = self.groups.get(data["key"], {"id": f"g{len(self.groups) + 1}"})
        current.update(data)
        self.groups[data["key"]] = current
        return current

    def upsert_config_item(self, data: dict) -> dict:
        current = self.items.get(data["key"], {"id": f"i{len(self.items) + 1}"})
        current.update(data)
        self.items[data["key"]] = current
        return current

    def deactivate_config_groups_except(self, active_keys: set[str]) -> None:
        for key, group in self.groups.items():
            if key not in active_keys:
                group["is_active"] = False

    def deactivate_config_items_except(self, active_keys: set[str]) -> None:
        for key, item in self.items.items():
            if key not in active_keys:
                item["is_active"] = False


def test_update_configuration_deactivates_omitted_groups_and_items() -> None:
    repo = _ConfigRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    response = service.update_configuration(
        FinancialConfigurationResponse(
            groups=[
                FinancialConfigGroup(
                    id="g1",
                    key="kept",
                    label="Kept",
                    kind="cost_category",
                    display_order=1,
                    is_active=True,
                )
            ],
            items=[
                FinancialConfigItem(
                    id="i1",
                    group_id="g1",
                    group_key="kept",
                    key="kept_item",
                    label="Kept item",
                    item_type="cost_category",
                    display_order=1,
                    is_active=True,
                )
            ],
        )
    )

    groups = {group.key: group for group in response.groups}
    items = {item.key: item for item in response.items}
    assert groups["kept"].is_active is True
    assert groups["omitted"].is_active is False
    assert items["kept_item"].is_active is True
    assert items["omitted_item"].is_active is False


def test_update_configuration_rejects_cross_tenant_group_id() -> None:
    repo = _ConfigRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    with pytest.raises(HTTPException) as exc:
        service.update_configuration(
            FinancialConfigurationResponse(
                groups=[
                    FinancialConfigGroup(
                        id="g1",
                        key="kept",
                        label="Kept",
                        kind="cost_category",
                        display_order=1,
                        is_active=True,
                    )
                ],
                items=[
                    FinancialConfigItem(
                        group_id="foreign-group-id",
                        group_key="kept",
                        key="foreign_item",
                        label="Foreign item",
                        item_type="cost_category",
                        display_order=1,
                        is_active=True,
                    )
                ],
            )
        )

    assert exc.value.status_code == 400


class _MissingInitiativeRepo:
    def initiative_exists(self, initiative_id: str) -> bool:
        return False


def test_create_cost_line_rejects_missing_tenant_initiative() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _MissingInitiativeRepo()

    with pytest.raises(HTTPException) as exc:
        service.create_cost_line(
            "foreign-initiative-id",
            CostLineCreate(
                name="Cross tenant attempt",
                year=2026,
                amount_plan="1.0000",
                is_recurring=False,
            ),
        )

    assert exc.value.status_code == 404


class _InitiativeBoundMutationRepo:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def initiative_exists(self, initiative_id: str) -> bool:
        return initiative_id == "initiative-1"

    def update_cost_line(self, initiative_id: str, cost_line_id: str, data: dict) -> dict:
        self.calls.append(("update_cost_line", initiative_id, cost_line_id))
        return {
            "id": cost_line_id,
            "initiative_id": initiative_id,
            "name": data.get("name", "Updated cost"),
            "category_key": "other",
            "year": 2026,
            "quarter": None,
            "month": None,
            "amount_plan": "1.0000",
            "amount_actual": None,
            "is_recurring": False,
        }

    def delete_cost_line(self, initiative_id: str, cost_line_id: str) -> None:
        self.calls.append(("delete_cost_line", initiative_id, cost_line_id))

    def update_cell_assumption(
        self,
        initiative_id: str,
        assumption_id: str,
        comment: str,
        user_id: str,
    ) -> dict:
        self.calls.append(("update_cell_assumption", initiative_id, assumption_id))
        return {
            "id": assumption_id,
            "initiative_id": initiative_id,
            "row_key": "gm_uplift_base",
            "column_key": "col_2026_q1",
            "comment": comment,
            "updated_by": user_id,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

    def delete_cell_assumption(self, initiative_id: str, assumption_id: str) -> None:
        self.calls.append(("delete_cell_assumption", initiative_id, assumption_id))


def test_nested_financial_mutations_bind_rows_to_url_initiative() -> None:
    repo = _InitiativeBoundMutationRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    service.update_cost_line("initiative-1", "cost-1", CostLineUpdate(name="Updated cost"))
    service.delete_cost_line("initiative-1", "cost-1")
    service.update_cell_assumption(
        "initiative-1",
        "assumption-1",
        FinancialCellAssumptionUpdate(comment="Updated"),
        "user-1",
    )
    service.delete_cell_assumption("initiative-1", "assumption-1")

    assert repo.calls == [
        ("update_cost_line", "initiative-1", "cost-1"),
        ("delete_cost_line", "initiative-1", "cost-1"),
        ("update_cell_assumption", "initiative-1", "assumption-1"),
        ("delete_cell_assumption", "initiative-1", "assumption-1"),
    ]


class _PlannedWindowRepo:
    def get_initiative_period(self, _initiative_id: str) -> dict:
        return {
            "stage": "scoping",
            "planned_start": "2026-04-01",
            "planned_end": "2026-06-30",
        }


def test_financial_grid_normalization_moves_values_to_first_planned_month() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _PlannedWindowRepo()

    normalized = service._normalize_grid_to_planned_window(
        "initiative-1",
        FinancialGridUpdate(
            entries=[
                FinancialEntryUpdate(year=2026, month=1, revenue_uplift_base="100.0000"),
                FinancialEntryUpdate(year=2026, month=4, revenue_uplift_base="200.0000"),
            ],
            cost_lines=[
                CostLineCreate(
                    name="Legacy implementation",
                    category_key="implementation",
                    year=2026,
                    month=1,
                    amount_plan="25.0000",
                    is_recurring=False,
                ),
                CostLineCreate(
                    name="Legacy implementation 2",
                    category_key="implementation",
                    year=2026,
                    month=2,
                    amount_plan="75.0000",
                    is_recurring=False,
                ),
            ],
            metric_values=[
                FinancialMetricValueUpdate(
                    metric_key="custom_retention",
                    year=2025,
                    month=12,
                    value_base="3.0000",
                ),
            ],
        ),
    )

    assert [(row.year, row.month, row.revenue_uplift_base) for row in normalized.entries] == [
        (2026, 4, 300),
    ]
    assert len(normalized.cost_lines or []) == 1
    cost = (normalized.cost_lines or [])[0]
    assert (cost.year, cost.month, cost.amount_plan) == (2026, 4, 100)
    metric = (normalized.metric_values or [])[0]
    assert (metric.year, metric.month, metric.value_base) == (2026, 4, 3)


class _LockStateRepo:
    def __init__(self, stage: str) -> None:
        self.stage = stage

    def get_initiative_period(self, _initiative_id: str) -> dict:
        return {
            "stage": self.stage,
            "planned_start": "2026-04-01",
            "planned_end": "2026-06-30",
        }


def test_financial_lock_state_only_allows_planned_stage_edits() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _LockStateRepo("scoping")
    service._assert_financials_editable("initiative-1")

    service._repo = _LockStateRepo("in_progress")
    with pytest.raises(HTTPException) as exc:
        service._assert_financials_editable("initiative-1")

    assert exc.value.status_code == 409


class _SelectionRepo:
    def __init__(self, stage: str = "scoping") -> None:
        self.stage = stage
        self.saved_metric_keys: list[str] = []
        self.saved_cost_keys: list[str] = []
        self.saved_all_metric_keys: list[str] = []
        self.saved_all_cost_keys: list[str] = []

    def initiative_exists(self, _initiative_id: str) -> bool:
        return True

    def get_initiative_period(self, _initiative_id: str) -> dict:
        return {
            "stage": self.stage,
            "planned_start": "2026-04-01",
            "planned_end": "2026-06-30",
        }

    def list_config_groups(self) -> list[dict]:
        return [
            {
                "id": "g1",
                "key": "gross_margin",
                "label": "Gross Margin",
                "kind": "metric",
                "display_order": 1,
                "is_system": True,
                "is_active": True,
            },
            {
                "id": "g2",
                "key": "operating",
                "label": "Operating Costs",
                "kind": "cost_category",
                "display_order": 2,
                "is_system": True,
                "is_active": True,
            },
        ]

    def list_config_items(self) -> list[dict]:
        return [
            {
                "id": "m1",
                "group_id": "g1",
                "key": "gross_margin_percent",
                "label": "Gross Margin %",
                "item_type": "metric",
                "system_metric_key": "gm_pct_base",
                "display_order": 1,
                "is_system": True,
                "is_active": True,
            },
            {
                "id": "m2",
                "group_id": "g1",
                "key": "gross_margin_percent_high",
                "label": "Gross Margin % (High)",
                "item_type": "metric",
                "system_metric_key": "gm_pct_high",
                "display_order": 2,
                "is_system": True,
                "is_active": True,
            },
            {
                "id": "m3",
                "group_id": "g1",
                "key": "gross_margin_percent_actual",
                "label": "Gross Margin % (Actual)",
                "item_type": "metric",
                "system_metric_key": "gm_pct_actual",
                "display_order": 3,
                "is_system": True,
                "is_active": True,
            },
            {
                "id": "c1",
                "group_id": "g2",
                "key": "maintenance",
                "label": "Maintenance",
                "item_type": "cost_category",
                "rollup_type": "recurring_cost",
                "display_order": 1,
                "is_system": True,
                "is_active": True,
            },
        ]

    def replace_financial_selections(
        self,
        _initiative_id: str,
        metric_keys: list[str],
        cost_category_keys: list[str],
        all_metric_keys: list[str] | None = None,
        all_cost_category_keys: list[str] | None = None,
    ) -> None:
        self.saved_metric_keys = metric_keys
        self.saved_cost_keys = cost_category_keys
        self.saved_all_metric_keys = all_metric_keys or metric_keys
        self.saved_all_cost_keys = all_cost_category_keys or cost_category_keys

    def list_financial_selections(self, _initiative_id: str) -> list[dict]:
        return [
            {"item_key": key, "item_type": "metric", "is_active": key in self.saved_metric_keys}
            for key in self.saved_all_metric_keys
        ] + [
            {
                "item_key": key,
                "item_type": "cost_category",
                "is_active": key in self.saved_cost_keys,
            }
            for key in self.saved_all_cost_keys
        ]

    def get_entries(self, _initiative_id: str) -> list[dict]:
        return []

    def list_cost_lines(self, _initiative_id: str) -> list[dict]:
        return []

    def list_metric_values(self, _initiative_id: str) -> list[dict]:
        return []


def test_financial_selection_persists_system_metric_keys() -> None:
    repo = _SelectionRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    response = service.update_initiative_selections(
        "initiative-1",
        InitiativeFinancialSelections(
            metric_keys=["gm_pct_base"],
            cost_category_keys=["maintenance"],
        ),
    )

    assert repo.saved_metric_keys == ["gm_pct_base"]
    assert repo.saved_cost_keys == ["maintenance"]
    assert "gm_pct_high" in repo.saved_all_metric_keys
    assert response.selected.metric_keys == ["gm_pct_base"]


def test_financial_selection_keeps_data_bearing_percentage_metrics_enabled() -> None:
    repo = _SelectionRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    selected = service._resolve_selections(
        "initiative-1",
        [
            {
                "year": 2026,
                "quarter": None,
                "month": 4,
                "gm_pct_base": "42.5000",
            }
        ],
        [],
        [],
    )

    assert "gm_pct_base" in selected.metric_keys
    assert "gm_pct_high" in selected.metric_keys
    assert "gm_pct_actual" in selected.metric_keys


def test_explicit_financial_selection_does_not_reenable_hidden_data_bearing_rows() -> None:
    repo = _SelectionRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo
    repo.replace_financial_selections(
        "initiative-1",
        [],
        [],
        ["gm_pct_base", "gm_pct_high", "gm_pct_actual"],
        ["maintenance"],
    )

    selected = service._resolve_selections(
        "initiative-1",
        [
            {
                "year": 2026,
                "quarter": None,
                "month": 4,
                "gm_pct_base": "42.5000",
            }
        ],
        [
            {
                "year": 2026,
                "quarter": None,
                "month": 4,
                "category_key": "maintenance",
                "amount_plan": "1000.0000",
                "is_recurring": True,
            }
        ],
        [],
    )

    assert selected.metric_keys == []
    assert selected.cost_category_keys == []


def test_financial_selection_updates_are_allowed_after_financial_values_lock() -> None:
    repo = _SelectionRepo(stage="in_progress")
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    response = service.update_initiative_selections(
        "initiative-1",
        InitiativeFinancialSelections(
            metric_keys=["gm_pct_base"],
            cost_category_keys=["maintenance"],
        ),
    )

    assert repo.saved_metric_keys == ["gm_pct_base"]
    assert response.locked is True
    assert response.selected.metric_keys == ["gm_pct_base"]


class _ExistingMigrationRepo:
    def __init__(self) -> None:
        self.deleted = False
        self.saved_costs: list[dict] = []

    def get_initiative_period(self, _initiative_id: str) -> dict:
        return {
            "stage": "scoping",
            "planned_start": "2026-04-01",
            "planned_end": "2026-06-30",
        }

    def get_entries(self, _initiative_id: str) -> list[dict]:
        return []

    def list_metric_values(self, _initiative_id: str) -> list[dict]:
        return []

    def list_cost_lines(self, _initiative_id: str) -> list[dict]:
        return [
            {
                "name": "Original vendor row",
                "category_key": "implementation",
                "year": 2025,
                "quarter": None,
                "month": 12,
                "amount_plan": "10.0000",
                "amount_actual": None,
                "is_recurring": False,
            },
            {
                "name": "Second vendor row",
                "category_key": "implementation",
                "year": 2026,
                "quarter": 1,
                "month": None,
                "amount_plan": "15.0000",
                "amount_actual": None,
                "is_recurring": False,
            },
        ]

    def delete_grid(self, _initiative_id: str) -> None:
        self.deleted = True

    def upsert_entries_batch(self, _initiative_id: str, _rows: list[dict]) -> list[dict]:
        return []

    def upsert_metric_values_batch(self, _initiative_id: str, _rows: list[dict]) -> list[dict]:
        return []

    def upsert_cost_lines_batch(self, _initiative_id: str, rows: list[dict]) -> list[dict]:
        self.saved_costs = rows
        return rows


def test_existing_out_of_window_costs_are_migrated_once_to_first_planned_month() -> None:
    repo = _ExistingMigrationRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    service._migrate_existing_grid_to_planned_window("initiative-1")

    assert repo.deleted is True
    assert repo.saved_costs == [
        {
            "name": "Original vendor row",
            "category_key": "implementation",
            "year": 2026,
            "quarter": None,
            "month": 4,
            "amount_plan": "25.0000",
            "amount_actual": None,
            "is_recurring": False,
        }
    ]
