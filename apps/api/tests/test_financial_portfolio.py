from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

import pytest
from fastapi import HTTPException

from app.domain.financials import (
    ConfigurableFinancialGridUpdate,
    CostLineCreate,
    CostLineUpdate,
    FinancialAttributeDefinition,
    FinancialBenefitLineCreate,
    FinancialBenefitLineHandoffUpdate,
    FinancialBenefitLineValidationRequest,
    FinancialCellAssumptionUpdate,
    FinancialConfigGroup,
    FinancialConfigItem,
    FinancialConfigurationResponse,
    FinancialEntryUpdate,
    FinancialGovernanceSettings,
    FinancialGridUpdate,
    FinancialMetricValue,
    FinancialMetricValueUpdate,
    FinancialReportingSettingsUpdate,
    InitiativeFinancialSelections,
    PortfolioFinancialPeriod,
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


class _CleanContributorRepo:
    def get_portfolio_initiatives(self) -> list[dict]:
        return [
            {
                "id": "i1",
                "name": "Pricing optimization",
                "stage": "in_progress",
                "workstream_id": "w1",
                "tag": "commercial",
                "initiative_business_units": [{"business_unit_id": "bu1"}],
            },
            {
                "id": "i2",
                "name": "Procurement savings",
                "stage": "in_progress",
                "workstream_id": "w2",
                "tag": "procurement",
                "initiative_business_units": [{"business_unit_id": "bu2"}],
            },
        ]

    def get_all_entries(self) -> list[dict]:
        return []

    def get_all_metric_values(self) -> list[dict]:
        return [
            {
                "id": "v1",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "metric_definition_id": "m_gm",
                "benefit_line_id": "bl1",
                "scenario_id": "s_plan",
                "year": 2028,
                "month": 1,
                "value": "100.0000",
            },
            {
                "id": "v2",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "metric_definition_id": "m_save",
                "benefit_line_id": "bl2",
                "scenario_id": "s_plan",
                "year": 2028,
                "month": 1,
                "value": "50.0000",
            },
            {
                "id": "v3",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "metric_definition_id": "m_gm",
                "benefit_line_id": "bl1",
                "scenario_id": "s_actual",
                "year": 2028,
                "month": 1,
                "value": "90.0000",
            },
            {
                "id": "v4",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "metric_definition_id": "m_save",
                "benefit_line_id": "bl2",
                "scenario_id": "s_actual",
                "year": 2028,
                "month": 1,
                "value": "45.0000",
            },
            {
                "id": "v5",
                "tenant_id": "t1",
                "initiative_id": "i2",
                "metric_definition_id": "m_save",
                "benefit_line_id": "bl3",
                "scenario_id": "s_plan",
                "year": 2028,
                "month": 1,
                "value": "75.0000",
            },
        ]

    def list_all_initiative_annual_baselines(self) -> list[dict]:
        return []

    def get_all_cost_lines(self) -> list[dict]:
        return [
            {
                "id": "c1",
                "initiative_id": "i1",
                "year": 2028,
                "month": 1,
                "name": "Run support",
                "category_key": "software",
                "is_recurring": True,
                "amount_plan": "25.0000",
                "amount_actual": "20.0000",
            }
        ]

    def list_metric_definitions(self) -> list[dict]:
        return [
            {
                "id": "m_gm",
                "key": "gm_uplift",
                "label": "Gross Margin Uplift",
                "aggregation": "sum",
                "is_benefit": True,
                "benefit_class": "margin",
            },
            {
                "id": "m_save",
                "key": "cost_savings",
                "label": "Cost Savings",
                "aggregation": "sum",
                "is_benefit": True,
                "benefit_class": "savings",
            },
        ]

    def list_financial_scenarios(self) -> list[dict]:
        return [
            {"id": "s_plan", "key": "plan_base"},
            {"id": "s_actual", "key": "actual"},
        ]

    def list_all_benefit_lines(self) -> list[dict]:
        return [
            {"id": "bl1", "name": "Pricing margin uplift"},
            {"id": "bl2", "name": "Pricing operating savings"},
            {"id": "bl3", "name": "Vendor savings"},
        ]

    def list_config_groups(self) -> list[dict]:
        return [
            {
                "id": "g_cost",
                "key": "operating",
                "label": "Operating Costs",
                "kind": "cost_category",
                "display_order": 1,
                "is_system": True,
                "is_active": True,
            }
        ]

    def list_config_items(self) -> list[dict]:
        return [
            {
                "id": "ci_software",
                "group_id": "g_cost",
                "key": "software",
                "label": "Software",
                "item_type": "cost_category",
                "rollup_type": "recurring_cost",
                "display_order": 1,
                "is_system": True,
                "is_active": True,
            }
        ]


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


def test_clean_portfolio_contributors_include_configurable_metric_benefits() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _CleanContributorRepo()

    response = service.get_portfolio_financial_contributors(
        granularity="yearly",
        period="2028",
        year=2028,
    )

    assert response.period == "2028"
    totals = {
        "benefits_plan": sum(Decimal(row.benefits_plan) for row in response.contributors),
        "benefits_actual": sum(Decimal(row.benefits_actual) for row in response.contributors),
        "recurring_costs_plan": sum(
            Decimal(row.recurring_costs_plan) for row in response.contributors
        ),
    }
    assert totals == {
        "benefits_plan": Decimal("225.0000"),
        "benefits_actual": Decimal("135.0000"),
        "recurring_costs_plan": Decimal("25.0000"),
    }
    pricing = next(row for row in response.contributors if row.initiative_id == "i1")
    assert pricing.net_value_plan == "125.0000"
    assert [line.name for line in pricing.benefit_lines] == [
        "Pricing operating savings",
        "Pricing margin uplift",
    ]
    assert pricing.cost_lines[0].category_label == "Software"


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
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = _ModeRepo()

    bridge = service._compute_value_bridge(
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
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = _ModeRepo()

    summary = service._compute_scenario_summary(
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


def test_portfolio_value_ramp_accumulates_net_value_by_period() -> None:
    ramp = FinancialService._portfolio_value_ramp_periods(
        [
            PortfolioFinancialPeriod(
                period="2026-M02",
                year=2026,
                month=2,
                net_value_plan="200.0000",
                net_value_actual="150.0000",
            ),
            PortfolioFinancialPeriod(
                period="2026-M01",
                year=2026,
                month=1,
                net_value_plan="100.0000",
                net_value_actual="75.0000",
            ),
        ]
    )

    assert [row.period for row in ramp] == ["2026-M01", "2026-M02"]
    assert ramp[0].cumulative_net_value_plan == "100.0000"
    assert ramp[1].cumulative_net_value_plan == "300.0000"
    assert ramp[1].cumulative_net_value_actual == "225.0000"


def test_portfolio_filter_matches_explicit_multi_business_unit_link() -> None:
    assert FinancialService._portfolio_initiative_matches(
        {
            "id": "i1",
            "stage": "in_execution",
            "workstream_id": "ws1",
            "tag": "commercial",
            "initiative_business_units": [{"business_unit_id": "bu-explicit"}],
        },
        initiative_id=None,
        workstream_ids={"ws1"},
        business_unit_ids={"bu-explicit"},
        stages={"in_execution"},
        tags={"commercial"},
    )
    assert not FinancialService._portfolio_initiative_matches(
        {
            "id": "i1",
            "stage": "in_execution",
            "workstream_id": "ws1",
            "tag": "commercial",
            "initiative_business_units": [{"business_unit_id": "bu-explicit"}],
        },
        initiative_id=None,
        workstream_ids=set(),
        business_unit_ids={"bu-other"},
        stages=set(),
        tags=set(),
    )


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


class _AttributeDefinitionRepo:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None
        self.updated: dict[str, object] | None = None

    def get_reporting_settings(self) -> dict:
        return {"fiscal_year_start_month": 4, "reporting_currency": "USD"}

    def list_metric_definitions(self) -> list[dict]:
        return []

    def list_financial_scenarios(self) -> list[dict]:
        return []

    def list_financial_bridge_rows(self) -> list[dict]:
        return []

    def list_financial_attribute_definitions(self) -> list[dict]:
        return [
            {
                "id": "attr-1",
                "key": "service_line",
                "label": "Service Line",
                "entity_type": "cost_line",
                "value_type": "select",
                "options": ["Digital", "Operations"],
                "is_required": True,
                "display_order": 10,
                "is_active": True,
            }
        ]

    def create_financial_attribute_definition(self, data: dict) -> dict:
        self.created = data
        return {"id": "created-attr", **data}

    def update_financial_attribute_definition(
        self,
        _attribute_definition_id: str,
        data: dict,
    ) -> dict:
        self.updated = data
        return {"id": "updated-attr", **data}


def test_engine_configuration_includes_attribute_definitions() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _AttributeDefinitionRepo()

    response = service.get_engine_configuration()

    assert response.attribute_definitions[0].key == "service_line"
    assert response.attribute_definitions[0].entity_type == "cost_line"
    assert response.attribute_definitions[0].options == ["Digital", "Operations"]


class _ReportingSettingsRepo(_AttributeDefinitionRepo):
    def __init__(self, persist_reporting: bool = True) -> None:
        super().__init__()
        self.persist_reporting = persist_reporting
        self.reporting = {"fiscal_year_start_month": 1, "reporting_currency": "USD"}
        self.org_settings = {
            "financial_engine": {
                "recurring_cost_inflation_mode": "manual_entry",
                "default_annual_inflation_rate_pct": "0.0000",
                "allow_cost_line_inflation_override": True,
            }
        }

    def get_reporting_settings(self) -> dict:
        return dict(self.reporting)

    def update_reporting_settings(self, data: dict) -> dict:
        if self.persist_reporting:
            self.reporting.update(data)
        return dict(self.reporting)

    def get_organization_settings(self) -> dict:
        return dict(self.org_settings)

    def update_organization_settings(self, settings: dict) -> dict:
        self.org_settings = settings
        return {"settings": self.org_settings}


def test_reporting_settings_update_verifies_persisted_values() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _ReportingSettingsRepo()

    response = service.update_reporting_settings(
        FinancialReportingSettingsUpdate(
            fiscal_year_start_month=4,
            reporting_currency="gbp",
            recurring_cost_inflation_mode="optional_per_line",
            default_annual_inflation_rate_pct="3.0000",
        )
    )

    assert response.fiscal_year_start_month == 4
    assert response.reporting_currency == "GBP"
    assert response.recurring_cost_inflation_mode == "optional_per_line"
    assert response.default_annual_inflation_rate_pct == Decimal("3.0000")

    service._repo = _ReportingSettingsRepo(persist_reporting=False)
    with pytest.raises(HTTPException) as exc:
        service.update_reporting_settings(
            FinancialReportingSettingsUpdate(fiscal_year_start_month=4)
        )

    assert exc.value.status_code == 500


def test_attribute_definition_create_normalizes_options() -> None:
    repo = _AttributeDefinitionRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    response = service.create_attribute_definition(
        FinancialAttributeDefinition(
            key="benefit_owner",
            label="Benefit Owner",
            entity_type="benefit_line",
            value_type="select",
            options=["  CFO  ", "", "COO"],
        )
    )

    assert repo.created is not None
    assert repo.created["options"] == ["CFO", "COO"]
    assert response.options == ["CFO", "COO"]


class _ModeRepo:
    def __init__(self, latest_plan: dict[str, object] | None = None) -> None:
        self.latest_plan = latest_plan

    def initiative_exists(self, _initiative_id: str) -> bool:
        return True

    def get_latest_bankable_plan(self, _initiative_id: str) -> dict[str, object] | None:
        return self.latest_plan


def test_financial_mode_descriptor_uses_multi_scenario_when_base_high_and_actual_exist() -> None:
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = _ModeRepo()

    descriptor = service._financial_mode_descriptor(
        "initiative-1",
        [
            {
                "year": 2026,
                "quarter": 1,
                "month": None,
                "revenue_uplift_base": "100.0000",
                "revenue_uplift_high": "150.0000",
                "gross_margin_base": "80.0000",
                "gross_margin_high": "120.0000",
                "gm_uplift_base": "80.0000",
                "gm_uplift_high": "120.0000",
                "cogs_base": "20.0000",
                "cogs_high": "30.0000",
            }
        ],
        [],
        [
            {
                "metric_key": "cost_savings",
                "year": 2026,
                "quarter": 1,
                "month": None,
                "value_base": "10.0000",
                "value_high": "20.0000",
                "value_actual": "15.0000",
            }
        ],
        config=_config(),
    )

    assert descriptor.key == "multi_scenario"
    assert descriptor.scenarios == ["base", "high", "actual"]
    assert descriptor.locked is False


def test_financial_mode_descriptor_falls_back_to_planned_vs_actual_when_only_actual_signals_exist() -> (
    None
):
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = _ModeRepo()

    descriptor = service._financial_mode_descriptor(
        "initiative-1",
        [
            {
                "year": 2026,
                "quarter": 1,
                "month": None,
                "revenue_uplift_base": "100.0000",
                "revenue_uplift_high": "100.0000",
                "revenue_uplift_actual": "110.0000",
                "gross_margin_base": "80.0000",
                "gross_margin_high": "80.0000",
                "gross_margin_actual": "90.0000",
                "gm_uplift_base": "80.0000",
                "gm_uplift_high": "80.0000",
                "gm_uplift_actual": "90.0000",
                "cogs_base": "20.0000",
                "cogs_high": "20.0000",
                "cogs_actual": "18.0000",
            }
        ],
        [],
        [
            {
                "metric_key": "cost_savings",
                "year": 2026,
                "quarter": 1,
                "month": None,
                "value_base": "10.0000",
                "value_high": "10.0000",
                "value_actual": "12.0000",
            }
        ],
        config=_config(),
    )

    assert descriptor.key == "planned_vs_actual"
    assert descriptor.scenarios == ["planned", "actual"]


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

    def get_organization_settings(self) -> dict:
        return {"bankable_plan_governance": {"plan_lock_on_approval": True}}

    def get_latest_bankable_plan(self, _initiative_id: str) -> dict[str, object] | None:
        return None

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


class _BenefitLineDeleteRepo:
    def __init__(self, locked: bool, validation_status: str = "draft") -> None:
        self.locked = locked
        self.validation_status = validation_status
        self.deleted: list[tuple[str, str]] = []

    def initiative_exists(self, initiative_id: str) -> bool:
        return initiative_id == "initiative-1"

    def get_organization_settings(self) -> dict:
        return {"bankable_plan_governance": {"plan_lock_on_approval": True}}

    def get_latest_bankable_plan(self, _initiative_id: str) -> dict[str, object] | None:
        return {"id": "plan-1"} if self.locked else None

    def get_benefit_line(self, _initiative_id: str, _benefit_line_id: str) -> dict:
        return {
            "id": "benefit-1",
            "initiative_id": "initiative-1",
            "metric_definition_id": "metric-1",
            "name": "Benefit line",
            "validation_status": self.validation_status,
            "show_in_summary": True,
            "display_order": 1,
        }

    def delete_benefit_line(self, initiative_id: str, benefit_line_id: str) -> None:
        self.deleted.append((initiative_id, benefit_line_id))


def test_benefit_line_delete_requires_unlocked_financials() -> None:
    service = FinancialService.__new__(FinancialService)
    unlocked_repo = _BenefitLineDeleteRepo(locked=False)
    service._repo = unlocked_repo

    service.delete_benefit_line("initiative-1", "benefit-1")

    assert unlocked_repo.deleted == [("initiative-1", "benefit-1")]

    locked_repo = _BenefitLineDeleteRepo(locked=True)
    service._repo = locked_repo

    with pytest.raises(HTTPException) as exc:
        service.delete_benefit_line("initiative-1", "benefit-1")

    assert exc.value.status_code == 409
    assert locked_repo.deleted == []


def test_benefit_line_delete_blocks_submitted_and_validated_lines() -> None:
    service = FinancialService.__new__(FinancialService)
    for validation_status in ("submitted", "finance_validated"):
        repo = _BenefitLineDeleteRepo(locked=False, validation_status=validation_status)
        service._repo = repo

        with pytest.raises(HTTPException) as exc:
            service.delete_benefit_line("initiative-1", "benefit-1")

        assert exc.value.status_code == 409
        assert repo.deleted == []


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


class _InflationSettingsRepo:
    def __init__(
        self,
        mode: str = "manual_entry",
        default_rate: str = "0.0000",
        allow_override: bool = True,
    ) -> None:
        self.mode = mode
        self.default_rate = default_rate
        self.allow_override = allow_override

    def get_reporting_settings(self) -> dict:
        return {"fiscal_year_start_month": 1, "reporting_currency": "USD"}

    def get_organization_settings(self) -> dict:
        return {
            "financial_engine": {
                "recurring_cost_inflation_mode": self.mode,
                "default_annual_inflation_rate_pct": self.default_rate,
                "allow_cost_line_inflation_override": self.allow_override,
            }
        }


def test_manual_inflation_mode_rejects_platform_inflation() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _InflationSettingsRepo(mode="manual_entry")

    with pytest.raises(HTTPException) as exc:
        service._prepare_cost_line_payloads(
            [
                CostLineCreate(
                    name="Managed service",
                    category_key="software",
                    year=2026,
                    amount_plan="100.0000",
                    is_recurring=True,
                    inflation_enabled=True,
                    annual_inflation_rate_pct="3.0000",
                )
            ]
        )

    assert exc.value.status_code == 400


def test_optional_per_line_inflation_compounds_recurring_costs_by_year() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _InflationSettingsRepo(mode="optional_per_line")

    rows = service._prepare_cost_line_payloads(
        [
            CostLineCreate(
                name="Managed service",
                category_key="software",
                year=2026,
                month=1,
                amount_plan="100.0000",
                is_recurring=True,
                inflation_enabled=True,
                annual_inflation_rate_pct="3.0000",
            ),
            CostLineCreate(
                name="Managed service",
                category_key="software",
                year=2027,
                month=1,
                amount_plan="100.0000",
                is_recurring=True,
                inflation_enabled=True,
                annual_inflation_rate_pct="3.0000",
            ),
        ]
    )

    assert [row["amount_plan"] for row in rows] == ["100.0000", "103.0000"]
    assert all(row["inflation_enabled"] is True for row in rows)


def test_default_on_inflation_uses_tenant_default_without_override() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _InflationSettingsRepo(
        mode="default_on",
        default_rate="2.5000",
        allow_override=False,
    )

    rows = service._prepare_cost_line_payloads(
        [
            CostLineCreate(
                name="Managed service",
                category_key="software",
                year=2026,
                amount_plan="200.0000",
                is_recurring=True,
            ),
            CostLineCreate(
                name="Managed service",
                category_key="software",
                year=2027,
                amount_plan="200.0000",
                is_recurring=True,
            ),
        ]
    )

    assert [row["amount_plan"] for row in rows] == ["200.0000", "205.0000"]
    assert {row["annual_inflation_rate_pct"] for row in rows} == {"2.5000"}


class _InflationCostLineUpdateRepo(_InflationSettingsRepo):
    def __init__(
        self,
        *,
        existing_recurring: bool,
        existing_inflation: bool,
        mode: str = "manual_entry",
        default_rate: str = "0.0000",
        allow_override: bool = True,
    ) -> None:
        super().__init__(mode=mode, default_rate=default_rate, allow_override=allow_override)
        self.patch: dict[str, object] = {}
        self.row: dict[str, object] = {
            "id": "cost-1",
            "initiative_id": "initiative-1",
            "name": "Managed service",
            "category_key": "software",
            "category_id": None,
            "year": 2026,
            "quarter": None,
            "month": 1,
            "amount_plan": "100.0000",
            "amount_actual": None,
            "is_recurring": existing_recurring,
            "inflation_enabled": existing_inflation,
            "annual_inflation_rate_pct": "3.0000" if existing_inflation else "0.0000",
        }

    def get_cost_line(self, _initiative_id: str, _cost_line_id: str) -> dict[str, object]:
        return dict(self.row)

    def update_cost_line(
        self,
        _initiative_id: str,
        _cost_line_id: str,
        patch: dict[str, object],
    ) -> dict[str, object]:
        self.patch = patch
        self.row.update(patch)
        return dict(self.row)


def test_cost_line_update_clears_inflation_when_line_becomes_non_recurring() -> None:
    repo = _InflationCostLineUpdateRepo(existing_recurring=True, existing_inflation=True)
    service = FinancialService.__new__(FinancialService)
    service._repo = repo
    service._ensure_tenant_initiative = lambda _initiative_id: None
    service._assert_financials_editable = lambda _initiative_id: None

    line = service.update_cost_line(
        "initiative-1",
        "cost-1",
        CostLineUpdate(is_recurring=False),
    )

    assert repo.patch["inflation_enabled"] is False
    assert repo.patch["annual_inflation_rate_pct"] == "0.0000"
    assert line.inflation_enabled is False


def test_cost_line_update_applies_default_inflation_when_line_becomes_recurring() -> None:
    repo = _InflationCostLineUpdateRepo(
        existing_recurring=False,
        existing_inflation=False,
        mode="default_on",
        default_rate="2.5000",
        allow_override=False,
    )
    service = FinancialService.__new__(FinancialService)
    service._repo = repo
    service._ensure_tenant_initiative = lambda _initiative_id: None
    service._assert_financials_editable = lambda _initiative_id: None

    line = service.update_cost_line(
        "initiative-1",
        "cost-1",
        CostLineUpdate(is_recurring=True),
    )

    assert repo.patch["inflation_enabled"] is True
    assert repo.patch["annual_inflation_rate_pct"] == "2.5000"
    assert line.inflation_enabled is True


def test_financial_governance_default_locks_initiative_plan_at_gate_3() -> None:
    assert FinancialGovernanceSettings().initiative_plan_lock_gate_number == 3


class _LockStateRepo:
    def __init__(self, stage: str, latest_plan: dict[str, object] | None = None) -> None:
        self.stage = stage
        self.latest_plan = latest_plan

    def get_initiative_period(self, _initiative_id: str) -> dict:
        return {
            "stage": self.stage,
            "planned_start": "2026-04-01",
            "planned_end": "2026-06-30",
        }

    def get_organization_settings(self) -> dict:
        return {"bankable_plan_governance": {"plan_lock_on_approval": True}}

    def get_latest_bankable_plan(self, _initiative_id: str) -> dict[str, object] | None:
        return self.latest_plan


def test_financial_lock_state_blocks_after_bankable_plan_approval() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _LockStateRepo("scoping")
    service._assert_financials_editable("initiative-1")

    service._repo = _LockStateRepo("in_progress", latest_plan={"id": "plan-1"})
    with pytest.raises(HTTPException) as exc:
        service._assert_financials_editable("initiative-1")

    assert exc.value.status_code == 409


class _LockedConfigurableRepo:
    def __init__(self) -> None:
        self.saved_values: list[dict[str, object]] = []
        self.saved_actual_costs: list[dict[str, object]] = []

    def initiative_exists(self, _initiative_id: str) -> bool:
        return True

    def get_organization_settings(self) -> dict:
        return {"bankable_plan_governance": {"plan_lock_on_approval": True}}

    def get_latest_bankable_plan(self, _initiative_id: str) -> dict[str, object] | None:
        return {"id": "plan-1"}

    def list_financial_scenarios(self) -> list[dict[str, object]]:
        return [
            {"id": "scenario-plan", "key": "plan_base", "kind": "plan"},
            {"id": "scenario-actual", "key": "actual", "kind": "actual"},
        ]

    def list_metric_definitions(self) -> list[dict[str, object]]:
        return [
            {
                "id": "metric-gm-uplift",
                "key": "gm_uplift",
                "aggregation": "sum",
            }
        ]

    def upsert_configurable_metric_values_batch(
        self,
        _initiative_id: str,
        rows: list[dict[str, object]],
        user_id: str | None = None,
    ) -> list[dict[str, object]]:
        self.saved_values.extend({**row, "updated_by": user_id} for row in rows)
        return rows

    def upsert_locked_actual_cost_lines_batch(
        self,
        _initiative_id: str,
        rows: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        self.saved_actual_costs.extend(rows)
        return rows

    def create_benefit_lines_batch(
        self,
        _initiative_id: str,
        _rows: list[dict[str, object]],
        user_id: str | None = None,
    ) -> list[dict[str, object]]:
        raise AssertionError("benefit lines should not be created after plan lock")


def _locked_configurable_service(repo: _LockedConfigurableRepo) -> FinancialService:
    service = FinancialService.__new__(FinancialService)
    service._repo = repo
    service.get_configurable_financial_grid = lambda initiative_id: {  # type: ignore[method-assign]
        "initiative_id": initiative_id
    }
    return service


def test_locked_configurable_financials_allow_actual_values_and_actual_costs() -> None:
    repo = _LockedConfigurableRepo()
    service = _locked_configurable_service(repo)

    result = service.update_configurable_financial_grid(
        "initiative-1",
        ConfigurableFinancialGridUpdate(
            values=[
                FinancialMetricValue(
                    metric_definition_id="metric-gm-uplift",
                    scenario_id="scenario-actual",
                    year=2028,
                    month=1,
                    value="80.0000",
                )
            ],
            cost_lines=[
                CostLineCreate(
                    name="Run support",
                    category_key="software",
                    year=2028,
                    month=1,
                    amount_actual="30.0000",
                    is_recurring=True,
                )
            ],
        ),
        user_id="user-1",
    )

    assert result == {"initiative_id": "initiative-1"}
    assert repo.saved_values == [
        {
            "metric_definition_id": "metric-gm-uplift",
            "scenario_id": "scenario-actual",
            "benefit_line_id": None,
            "year": 2028,
            "month": 1,
            "value": "80.0000",
            "status": "draft",
            "note": None,
            "updated_by": "user-1",
        }
    ]
    assert repo.saved_actual_costs == [
        {
            "name": "Run support",
            "category_key": "software",
            "category_id": None,
            "year": 2028,
            "quarter": None,
            "month": 1,
            "amount_plan": "0.0000",
            "amount_actual": "30.0000",
            "is_recurring": True,
            "inflation_enabled": False,
            "annual_inflation_rate_pct": "0.0000",
        }
    ]


def test_locked_configurable_financials_reject_plan_scenario_values() -> None:
    repo = _LockedConfigurableRepo()
    service = _locked_configurable_service(repo)

    with pytest.raises(HTTPException) as exc:
        service.update_configurable_financial_grid(
            "initiative-1",
            ConfigurableFinancialGridUpdate(
                values=[
                    FinancialMetricValue(
                        metric_definition_id="metric-gm-uplift",
                        scenario_id="scenario-plan",
                        year=2028,
                        month=1,
                        value="120.0000",
                    )
                ]
            ),
            user_id="user-1",
        )

    assert exc.value.status_code == 409
    assert repo.saved_values == []


def test_locked_configurable_financials_reject_benefit_line_changes() -> None:
    repo = _LockedConfigurableRepo()
    service = _locked_configurable_service(repo)

    with pytest.raises(HTTPException) as exc:
        service.update_configurable_financial_grid(
            "initiative-1",
            ConfigurableFinancialGridUpdate(
                benefit_lines=[
                    FinancialBenefitLineCreate(
                        metric_definition_id="metric-gm-uplift",
                        name="New locked plan line",
                    )
                ]
            ),
            user_id="user-1",
        )

    assert exc.value.status_code == 409


class _SelectionRepo:
    def __init__(
        self, stage: str = "scoping", latest_plan: dict[str, object] | None = None
    ) -> None:
        self.stage = stage
        self.latest_plan = latest_plan
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

    def get_organization_settings(self) -> dict:
        return {"bankable_plan_governance": {"plan_lock_on_approval": True}}

    def get_latest_bankable_plan(self, _initiative_id: str) -> dict[str, object] | None:
        return self.latest_plan

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


class _BenefitLineScopeRepo:
    def __init__(self, existing_lines: list[dict] | None = None) -> None:
        self.existing_lines = existing_lines or []
        self.created_payload: dict[str, object] | None = None

    def initiative_exists(self, _initiative_id: str) -> bool:
        return True

    def get_organization_settings(self) -> dict:
        return {"bankable_plan_governance": {"plan_lock_on_approval": True}}

    def get_latest_bankable_plan(self, _initiative_id: str) -> dict[str, object] | None:
        return None

    def get_reporting_settings(self) -> dict:
        return {}

    def list_metric_definitions(self) -> list[dict]:
        return [
            {
                "id": "metric-gm",
                "key": "gm_uplift",
                "label": "Gross Margin Uplift",
                "is_benefit": True,
                "aggregation": "sum",
                "display_order": 1,
                "is_active": True,
            },
            {
                "id": "metric-revenue",
                "key": "revenue_uplift",
                "label": "Revenue Uplift",
                "is_benefit": True,
                "aggregation": "sum",
                "display_order": 2,
                "is_active": True,
            },
        ]

    def list_financial_scenarios(self) -> list[dict]:
        return []

    def list_cost_categories(self) -> list[dict]:
        return []

    def list_financial_bridge_rows(self) -> list[dict]:
        return []

    def list_financial_attribute_definitions(self) -> list[dict]:
        return []

    def list_financial_scope(self, _initiative_id: str) -> list[dict]:
        return [
            {
                "scope_type": "metric_definition",
                "metric_definition_id": "metric-gm",
                "is_active": True,
            }
        ]

    def list_financial_selections(self, _initiative_id: str) -> list[dict]:
        return []

    def list_cost_lines(self, _initiative_id: str) -> list[dict]:
        return []

    def list_benefit_lines(self, _initiative_id: str) -> list[dict]:
        return self.existing_lines

    def create_benefit_line(
        self,
        _initiative_id: str,
        payload: dict[str, object],
        user_id: str | None = None,
    ) -> dict:
        self.created_payload = payload
        return {
            "id": "benefit-line-1",
            **payload,
            "validation_status": "draft",
            "created_by": user_id,
        }


def test_create_benefit_line_rejects_metric_outside_configured_scope() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _BenefitLineScopeRepo()

    with pytest.raises(HTTPException) as exc:
        service.create_benefit_line(
            "initiative-1",
            FinancialBenefitLineCreate(
                metric_definition_id="metric-revenue",
                name="Revenue duplicate",
            ),
        )

    assert exc.value.status_code == 400
    assert "configured financial scope" in str(exc.value.detail)


def test_create_benefit_line_rejects_duplicate_visible_metric() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _BenefitLineScopeRepo(
        existing_lines=[
            {
                "id": "benefit-line-existing",
                "metric_definition_id": "metric-gm",
                "name": "Existing GM uplift",
                "show_in_summary": True,
            }
        ]
    )

    with pytest.raises(HTTPException) as exc:
        service.create_benefit_line(
            "initiative-1",
            FinancialBenefitLineCreate(
                metric_definition_id="metric-gm",
                name="Second GM uplift",
            ),
        )

    assert exc.value.status_code == 409
    assert "already exists" in str(exc.value.detail)


def test_create_benefit_line_allows_readd_after_visible_line_removed() -> None:
    repo = _BenefitLineScopeRepo(
        existing_lines=[
            {
                "id": "benefit-line-hidden",
                "metric_definition_id": "metric-gm",
                "name": "Hidden GM uplift",
                "show_in_summary": False,
            }
        ]
    )
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    line = service.create_benefit_line(
        "initiative-1",
        FinancialBenefitLineCreate(
            metric_definition_id="metric-gm",
            name="Replacement GM uplift",
        ),
    )

    assert line.id == "benefit-line-1"
    assert repo.created_payload is not None
    assert repo.created_payload["metric_definition_id"] == "metric-gm"


def test_financial_selection_updates_raise_conflict_after_financial_values_lock() -> None:
    repo = _SelectionRepo(stage="in_progress", latest_plan={"id": "plan-1"})
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    with pytest.raises(HTTPException) as exc:
        service.update_initiative_selections(
            "initiative-1",
            InitiativeFinancialSelections(
                metric_keys=["gm_pct_base"],
                cost_category_keys=["maintenance"],
            ),
        )

    assert exc.value.status_code == 409


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
            "category_id": None,
            "inflation_enabled": False,
            "annual_inflation_rate_pct": "0.0000",
        }
    ]


class _BenefitRegisterRepo(_CleanContributorRepo):
    def list_all_benefit_lines(self) -> list[dict]:
        return [
            {
                "id": "bl1",
                "initiative_id": "i1",
                "metric_definition_id": "m_gm",
                "name": "Pricing margin uplift",
                "validation_status": "finance_validated",
                "confidence": "85.00",
                "risk_rating": "medium",
                "risk_adjustment_pct": "80.00",
                "evidence_url": "https://example.com/evidence",
                "evidence_label": "Evidence",
                "handoff_status": "handoff_complete",
            },
            {
                "id": "bl2",
                "initiative_id": "i1",
                "metric_definition_id": "m_save",
                "name": "Pricing operating savings",
                "validation_status": "submitted",
                "confidence": "90.00",
                "risk_rating": "low",
                "risk_adjustment_pct": "95.00",
                "handoff_status": "owner_assigned",
            },
        ]


def test_portfolio_benefits_register_rolls_up_validation_and_risk_adjusted_value() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _BenefitRegisterRepo()

    response = service.get_portfolio_benefits_register(year=2028)

    assert response.totals.plan == "150.0000"
    assert response.totals.actual == "135.0000"
    assert response.totals.risk_adjusted_plan == "127.5000"
    assert response.totals.validated_plan == "100.0000"
    assert response.totals.submitted_plan == "50.0000"
    assert [item.validation_status for item in response.items] == [
        "finance_validated",
        "submitted",
    ]


class _BenefitValidationRepo:
    def __init__(self) -> None:
        self.line = {
            "id": "bl1",
            "initiative_id": "i1",
            "metric_definition_id": "m1",
            "name": "Run-rate value",
            "confidence": "80.00",
            "validation_status": "submitted",
            "show_in_summary": True,
            "display_order": 1,
        }
        self.events: list[dict] = []
        self.patch: dict = {}
        self.valid_users = {"user-1"}

    def initiative_exists(self, _initiative_id: str) -> bool:
        return True

    def get_benefit_line(self, _initiative_id: str, _benefit_line_id: str) -> dict:
        return self.line

    def update_benefit_line(
        self,
        _initiative_id: str,
        _benefit_line_id: str,
        data: dict,
        _user_id: str,
    ) -> dict:
        self.patch = data
        self.line = {**self.line, **data}
        return self.line

    def tenant_user_exists(self, user_id: str) -> bool:
        return user_id in self.valid_users

    def create_benefit_line_validation_event(
        self,
        _initiative_id: str,
        _benefit_line_id: str,
        data: dict,
    ) -> dict:
        self.events.append(data)
        return {**data, "id": "evt1", "created_at": "2026-06-17T00:00:00+00:00"}


def test_benefit_line_validation_transition_records_audit_event() -> None:
    repo = _BenefitValidationRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    line = service.validate_benefit_line(
        "i1",
        "bl1",
        FinancialBenefitLineValidationRequest(
            comment="Tied to finance model",
            evidence_url="https://example.com/model",
            evidence_label="Finance model",
        ),
        "user-1",
    )

    assert line.validation_status == "finance_validated"
    assert repo.patch["validated_by"] == "user-1"
    assert repo.events[0]["event_type"] == "validate"
    assert repo.events[0]["comment"] == "Tied to finance model"


def test_benefit_line_validation_rejects_invalid_transitions_and_missing_reason() -> None:
    repo = _BenefitValidationRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    repo.line["validation_status"] = "finance_validated"
    with pytest.raises(HTTPException) as exc:
        service.submit_benefit_line_for_validation(
            "i1",
            "bl1",
            FinancialBenefitLineValidationRequest(comment="Resubmit"),
            "user-1",
        )
    assert exc.value.status_code == 409

    repo.line["validation_status"] = "submitted"
    with pytest.raises(HTTPException) as exc:
        service.reject_benefit_line(
            "i1",
            "bl1",
            FinancialBenefitLineValidationRequest(comment="  "),
            "user-1",
        )
    assert exc.value.status_code == 422


def test_benefit_line_handoff_rejects_owner_outside_current_tenant() -> None:
    repo = _BenefitValidationRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    with pytest.raises(HTTPException) as exc:
        service.update_benefit_line_handoff(
            "i1",
            "bl1",
            FinancialBenefitLineHandoffUpdate(
                realization_owner_id="other-tenant-user",
                handoff_status="owner_assigned",
            ),
            "user-1",
        )

    assert exc.value.status_code == 400
    assert repo.patch == {}


class _InitiativePortfolioRepo:
    def get_portfolio_initiatives(self) -> list[dict]:
        return [
            {
                "id": "i1",
                "initiative_code": "ENT-001",
                "name": "Pricing",
                "stage": "in_progress",
                "workstream_id": "w1",
                "tag": "commercial",
                "workstreams": {"name": "Commercial Growth"},
                "initiative_business_units": [
                    {
                        "business_unit_id": "bu1",
                        "business_units": {"id": "bu1", "name": "Commercial"},
                    }
                ],
            },
            {
                "id": "i2",
                "initiative_code": "ENT-002",
                "name": "Procurement",
                "stage": "in_progress",
                "workstream_id": "w2",
                "tag": "savings",
                "workstreams": {"name": "Procurement"},
                "initiative_business_units": [
                    {
                        "business_unit_id": "bu2",
                        "business_units": {"id": "bu2", "name": "Operations"},
                    }
                ],
            },
        ]

    def list_metric_definitions(self) -> list[dict]:
        return [
            {
                "id": "m_rev_base",
                "key": "annual_revenue_baseline",
                "label": "Annual Revenue Baseline",
                "group_key": "baseline",
                "value_type": "currency",
                "aggregation": "last",
                "is_benefit": False,
                "is_active": True,
                "display_order": 1,
            },
            {
                "id": "m_gm_base",
                "key": "annual_gross_margin_baseline",
                "label": "Annual Gross Margin Baseline",
                "group_key": "baseline",
                "value_type": "currency",
                "aggregation": "last",
                "is_benefit": False,
                "is_active": True,
                "display_order": 2,
            },
            {
                "id": "m_rev",
                "key": "revenue_uplift",
                "label": "Revenue Uplift",
                "group_key": "revenue",
                "value_type": "currency",
                "aggregation": "sum",
                "is_benefit": True,
                "benefit_class": "revenue",
                "is_active": True,
                "display_order": 3,
            },
            {
                "id": "m_gm",
                "key": "gm_uplift",
                "label": "Gross Margin Uplift",
                "group_key": "margin",
                "value_type": "currency",
                "aggregation": "sum",
                "is_benefit": True,
                "benefit_class": "margin",
                "is_active": True,
                "display_order": 4,
            },
            {
                "id": "m_target",
                "key": "target_revenue",
                "label": "Target Revenue",
                "group_key": "revenue",
                "value_type": "currency",
                "aggregation": "formula",
                "formula": "baseline_annual_revenue_baseline + revenue_uplift",
                "formula_inputs": ["baseline_annual_revenue_baseline", "revenue_uplift"],
                "is_benefit": False,
                "is_active": True,
                "display_order": 5,
            },
        ]

    def list_financial_scenarios(self) -> list[dict]:
        return [{"id": "s_base", "key": "plan_base", "label": "Plan Base"}]

    def list_all_initiative_annual_baselines(self) -> list[dict]:
        return [
            {
                "initiative_id": "i1",
                "metric_definition_id": "m_rev_base",
                "baseline_year": 2026,
                "value": "700.0000",
            },
            {
                "initiative_id": "i1",
                "metric_definition_id": "m_gm_base",
                "baseline_year": 2026,
                "value": "300.0000",
            },
            {
                "initiative_id": "i2",
                "metric_definition_id": "m_rev_base",
                "baseline_year": 2026,
                "value": "300.0000",
            },
            {
                "initiative_id": "i2",
                "metric_definition_id": "m_gm_base",
                "baseline_year": 2026,
                "value": "200.0000",
            },
        ]

    def list_tenant_annual_baselines(self, baseline_year: int | None = None) -> list[dict]:
        rows = [
            {
                "metric_definition_id": "m_rev_base",
                "baseline_year": 2026,
                "value": "1000.0000",
            },
            {
                "metric_definition_id": "m_gm_base",
                "baseline_year": 2026,
                "value": "500.0000",
            },
        ]
        return [
            row for row in rows if baseline_year is None or row["baseline_year"] == baseline_year
        ]

    def get_all_metric_values(self) -> list[dict]:
        return [
            {
                "initiative_id": "i1",
                "metric_definition_id": "m_rev",
                "scenario_id": "s_base",
                "year": 2028,
                "month": 1,
                "value": "100.0000",
            },
            {
                "initiative_id": "i1",
                "metric_definition_id": "m_gm",
                "scenario_id": "s_base",
                "year": 2028,
                "month": 1,
                "value": "40.0000",
            },
            {
                "initiative_id": "i2",
                "metric_definition_id": "m_gm",
                "scenario_id": "s_base",
                "year": 2028,
                "month": 1,
                "value": "60.0000",
            },
        ]

    def get_all_cost_lines(self) -> list[dict]:
        return [
            {
                "initiative_id": "i1",
                "year": 2028,
                "amount_plan": "10.0000",
                "amount_actual": None,
                "is_recurring": True,
            },
            {
                "initiative_id": "i2",
                "year": 2028,
                "amount_plan": "25.0000",
                "amount_actual": None,
                "is_recurring": False,
            },
        ]


class _CumulativeInvestmentPaybackRepo(_InitiativePortfolioRepo):
    def get_all_cost_lines(self) -> list[dict]:
        return [
            {
                "initiative_id": "i1",
                "year": 2028,
                "amount_plan": "10.0000",
                "amount_actual": None,
                "is_recurring": True,
            },
            {
                "initiative_id": "i2",
                "year": 2027,
                "amount_plan": "25.0000",
                "amount_actual": None,
                "is_recurring": False,
            },
        ]


def test_initiative_portfolio_reconciles_baseline_and_value_year() -> None:
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = _InitiativePortfolioRepo()

    response = service.get_portfolio_initiative_portfolio(
        baseline_year=2026,
        value_year=2028,
        scenario="plan_base",
    )

    assert [metric.key for metric in response.baseline_metrics] == [
        "annual_revenue_baseline",
        "annual_gross_margin_baseline",
    ]
    assert [metric.key for metric in response.value_metrics] == ["revenue_uplift", "gm_uplift"]
    assert len(response.rows) == 2
    assert response.totals.baseline_values["annual_revenue_baseline"] == "1000.0000"
    assert response.totals.baseline_values["annual_gross_margin_baseline"] == "500.0000"
    assert response.totals.value_metric_values["gm_uplift"] == "100.0000"
    assert response.totals.benefits_total == "100.0000"
    assert response.totals.recurring_costs == "10.0000"
    assert response.totals.one_off_costs == "25.0000"
    assert response.totals.net_run_rate_value == "90.0000"
    assert all(item.reconciled for item in response.baseline_reconciliation)


def test_investments_payback_reuses_initiative_portfolio_math() -> None:
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = _CumulativeInvestmentPaybackRepo()

    response = service.get_portfolio_investments_payback(
        value_year=2028,
        scenario="plan_base",
    )

    assert response.summary.one_off_investment == "25.0000"
    assert response.summary.net_run_rate_value == "90.0000"
    assert response.summary.payback_months == "3.3333"
    assert response.summary.payback_label == "3.3 months"
    assert response.summary.initiatives_with_payback == 2
    assert [row.initiative_id for row in response.rows] == ["i1", "i2"]
    assert response.rows[0].payback_status == "immediate"
    assert response.rows[0].payback_label == "Immediate"
    assert response.rows[1].payback_status == "payback"
    assert response.rows[1].payback_months == "5.0000"
    assert response.rows[1].payback_label == "5.0 months"


class _ValueBridgeBasisRepo:
    def get_all_entries(self) -> list[dict]:
        return []

    def get_all_metric_values(self) -> list[dict]:
        return [
            {
                "initiative_id": "i1",
                "metric_definition_id": "m_gm",
                "scenario_id": "s_plan",
                "year": 2027,
                "month": 1,
                "value": "100.0000",
            },
            {
                "initiative_id": "i1",
                "metric_definition_id": "m_gm",
                "scenario_id": "s_plan",
                "year": 2028,
                "month": 1,
                "value": "200.0000",
            },
        ]

    def list_all_initiative_annual_baselines(self) -> list[dict]:
        return []

    def get_all_cost_lines(self) -> list[dict]:
        return [
            {
                "initiative_id": "i1",
                "year": 2028,
                "month": 1,
                "amount_plan": "50.0000",
                "is_recurring": True,
            }
        ]

    def list_metric_definitions(self) -> list[dict]:
        return [
            {
                "id": "m_gm",
                "key": "gm_uplift",
                "label": "Gross Margin Uplift",
                "aggregation": "sum",
                "is_benefit": True,
                "benefit_class": "margin",
            }
        ]

    def list_financial_scenarios(self) -> list[dict]:
        return [{"id": "s_plan", "key": "plan_base"}]

    def list_financial_bridge_rows(self) -> list[dict]:
        return []


def test_portfolio_value_bridge_basis_filters_selected_year() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _ValueBridgeBasisRepo()

    in_year = service.get_portfolio_value_bridge(basis="in_year", year=2028)
    cumulative = service.get_portfolio_value_bridge(basis="cumulative", year=2028)

    assert in_year.base_case.benefits_total == "200.0000"
    assert in_year.base_case.net == "150.0000"
    assert cumulative.base_case.benefits_total == "300.0000"
