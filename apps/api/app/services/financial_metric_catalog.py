"""Versioned, tenant-owned starter catalogue for the configurable financial engine."""

from __future__ import annotations

from typing import Any, Final

from supabase import Client

FINANCIAL_METRIC_CATALOG_VERSION: Final = "financial-v2"


def _metric(
    key: str,
    label: str,
    semantic_role: str,
    group_key: str,
    value_type: str,
    aggregation: str,
    display_order: int,
    *,
    direction: str = "increase_good",
    rollup_type: str | None = None,
    is_benefit: bool = False,
    benefit_class: str | None = None,
    formula: str | None = None,
    formula_inputs: list[str] | None = None,
    validation: dict[str, object] | None = None,
    unit: str | None = None,
) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "semantic_role": semantic_role,
        "group_key": group_key,
        "value_type": value_type,
        "unit": unit,
        "direction": direction,
        "aggregation": aggregation,
        "rollup_type": rollup_type,
        "is_benefit": is_benefit,
        "benefit_class": benefit_class,
        "formula": formula,
        "formula_inputs": formula_inputs or [],
        "evaluation_grain": "annual" if aggregation == "formula" else "period",
        "precision": 4,
        "display_order": display_order,
        "applies_to": "all",
        "validation": validation or {},
    }


CANONICAL_FINANCIAL_METRICS: Final[list[dict[str, object]]] = [
    _metric(
        "annual_revenue_baseline",
        "Annual Revenue Baseline",
        "revenue_baseline",
        "baseline",
        "currency",
        "last",
        10,
        direction="neutral",
    ),
    _metric(
        "annual_gross_profit_baseline",
        "Annual Gross Profit Baseline",
        "gross_profit_baseline",
        "baseline",
        "currency",
        "last",
        20,
        direction="neutral",
    ),
    _metric(
        "revenue_uplift",
        "Revenue Uplift",
        "revenue_uplift",
        "revenue",
        "currency",
        "sum",
        30,
        rollup_type="benefit",
        is_benefit=True,
        benefit_class="revenue",
    ),
    _metric(
        "gross_profit_uplift",
        "Gross Profit Uplift",
        "gross_profit_uplift",
        "margin",
        "currency",
        "sum",
        40,
        rollup_type="benefit",
        is_benefit=True,
        benefit_class="margin",
    ),
    _metric(
        "cost_savings",
        "Cost Savings",
        "cost_savings",
        "savings",
        "currency",
        "sum",
        50,
        rollup_type="benefit",
        is_benefit=True,
        benefit_class="savings",
    ),
    _metric(
        "target_revenue",
        "Target Revenue",
        "target_revenue",
        "revenue",
        "currency",
        "formula",
        60,
        formula="annual_revenue_baseline + revenue_uplift",
        formula_inputs=["annual_revenue_baseline", "revenue_uplift"],
    ),
    _metric(
        "target_gross_profit",
        "Target Gross Profit",
        "target_gross_profit",
        "margin",
        "currency",
        "formula",
        70,
        formula="annual_gross_profit_baseline + gross_profit_uplift",
        formula_inputs=["annual_gross_profit_baseline", "gross_profit_uplift"],
    ),
    _metric(
        "target_cogs",
        "Target COGS",
        "target_cogs",
        "costs",
        "currency",
        "formula",
        80,
        direction="decrease_good",
        formula="target_revenue - target_gross_profit",
        formula_inputs=["target_revenue", "target_gross_profit"],
    ),
    _metric(
        "revenue_growth_pct",
        "Revenue Growth %",
        "revenue_growth_pct",
        "revenue",
        "percent",
        "formula",
        90,
        formula="revenue_uplift / annual_revenue_baseline * 100",
        formula_inputs=["revenue_uplift", "annual_revenue_baseline"],
    ),
    _metric(
        "baseline_gross_margin_pct",
        "Baseline Gross Margin %",
        "baseline_gross_margin_pct",
        "margin",
        "percent",
        "formula",
        100,
        formula="annual_gross_profit_baseline / annual_revenue_baseline * 100",
        formula_inputs=["annual_gross_profit_baseline", "annual_revenue_baseline"],
        validation={"min": 0, "max": 100},
    ),
    _metric(
        "target_gross_margin_pct",
        "Target Gross Margin %",
        "target_gross_margin_pct",
        "margin",
        "percent",
        "formula",
        110,
        formula="target_gross_profit / target_revenue * 100",
        formula_inputs=["target_gross_profit", "target_revenue"],
        validation={"min": 0, "max": 100},
    ),
    _metric(
        "gross_margin_change_pp",
        "Gross Margin Change (pp)",
        "gross_margin_change_pp",
        "margin",
        "number",
        "formula",
        120,
        formula="target_gross_margin_pct - baseline_gross_margin_pct",
        formula_inputs=["target_gross_margin_pct", "baseline_gross_margin_pct"],
        unit="pp",
    ),
    _metric(
        "target_cogs_pct",
        "Target COGS %",
        "target_cogs_pct",
        "costs",
        "percent",
        "formula",
        130,
        direction="decrease_good",
        formula="target_cogs / target_revenue * 100",
        formula_inputs=["target_cogs", "target_revenue"],
        validation={"min": 0, "max": 100},
    ),
]

FINANCIAL_CATALOG: Final[dict[str, Any]] = {
    "scenarios": [
        {
            "key": "baseline",
            "label": "Baseline",
            "kind": "baseline",
            "is_primary": False,
            "display_order": 0,
        },
        {
            "key": "plan_base",
            "label": "Plan Base",
            "kind": "plan",
            "is_primary": True,
            "display_order": 10,
        },
        {
            "key": "plan_high",
            "label": "Plan High",
            "kind": "plan",
            "is_primary": False,
            "display_order": 20,
        },
        {
            "key": "actual",
            "label": "Actual",
            "kind": "actual",
            "is_primary": False,
            "display_order": 30,
        },
    ],
    "metrics": CANONICAL_FINANCIAL_METRICS,
    "cost_categories": [
        {
            "key": key,
            "label": label,
            "group_key": group,
            "rollup_type": rollup,
            "display_order": order,
        }
        for key, label, group, rollup, order in (
            (
                "implementation",
                "Implementation / Project Cost",
                "implementation",
                "one_off_cost",
                10,
            ),
            ("technology_tooling", "Technology / Tooling", "implementation", "one_off_cost", 20),
            ("external_consultants", "External Consultants", "implementation", "one_off_cost", 30),
            (
                "training_change",
                "Training / Change Management",
                "implementation",
                "one_off_cost",
                40,
            ),
            ("software", "Software / Licenses", "operating", "recurring_cost", 50),
            ("maintenance", "Support / Maintenance", "operating", "recurring_cost", 60),
            ("labor", "People Support", "operating", "recurring_cost", 70),
            ("other", "Other", "uncategorized", None, 999),
        )
    ],
    "bridge_rows": [
        {
            "key": "revenue",
            "label": "Revenue Uplift",
            "row_kind": "metric_set",
            "metric_keys": ["revenue_uplift"],
            "cost_category_keys": [],
            "sign": 1,
            "display_order": 10,
        },
        {
            "key": "margin",
            "label": "Gross Profit Uplift",
            "row_kind": "metric_set",
            "metric_keys": ["gross_profit_uplift"],
            "cost_category_keys": [],
            "sign": 1,
            "display_order": 20,
        },
        {
            "key": "savings",
            "label": "Cost Savings",
            "row_kind": "metric_set",
            "metric_keys": ["cost_savings"],
            "cost_category_keys": [],
            "sign": 1,
            "display_order": 30,
        },
        {
            "key": "recurring_costs",
            "label": "Recurring Costs",
            "row_kind": "cost_set",
            "metric_keys": [],
            "cost_category_keys": ["software", "maintenance", "labor"],
            "sign": -1,
            "display_order": 40,
        },
        {
            "key": "net_run_rate_value",
            "label": "Net Run-rate Value",
            "row_kind": "net",
            "metric_keys": [],
            "cost_category_keys": [],
            "sign": 1,
            "display_order": 50,
        },
        {
            "key": "one_off_investment",
            "label": "One-off Investment",
            "row_kind": "cost_set",
            "metric_keys": [],
            "cost_category_keys": [
                "implementation",
                "technology_tooling",
                "external_consultants",
                "training_change",
            ],
            "sign": -1,
            "display_order": 60,
        },
    ],
}


class FinancialMetricCatalogInstaller:
    """Install a catalogue exactly once through one database transaction."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def install(self, tenant_id: str) -> dict[str, int]:
        result = self._client.rpc(
            "install_financial_metric_catalog",
            {
                "p_tenant_id": tenant_id,
                "p_catalog_version": FINANCIAL_METRIC_CATALOG_VERSION,
                "p_catalog": FINANCIAL_CATALOG,
            },
        ).execute()
        data = result.data or {}
        if isinstance(data, list):
            data = data[0] if data else {}
        return {str(key): int(value) for key, value in data.items()}
