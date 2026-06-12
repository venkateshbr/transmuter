from __future__ import annotations

from app.services.financial import FinancialService


class _Repo:
    def list_financial_bridge_rows(self) -> list[dict]:  # type: ignore[type-arg]
        return [
            {
                "key": "revenue",
                "label": "Revenue",
                "row_kind": "metric_set",
                "metric_definition_ids": ["metric-revenue"],
                "cost_category_keys": [],
                "sign": 1,
                "display_order": 10,
                "is_active": True,
            },
            {
                "key": "implementation",
                "label": "Implementation Costs",
                "row_kind": "cost_set",
                "metric_definition_ids": [],
                "cost_category_keys": ["implementation"],
                "sign": -1,
                "display_order": 20,
                "is_active": True,
            },
            {
                "key": "net_value",
                "label": "Net Value",
                "row_kind": "net",
                "metric_definition_ids": [],
                "cost_category_keys": [],
                "sign": 1,
                "display_order": 30,
                "is_active": True,
            },
        ]

    def list_financial_scenarios(self) -> list[dict]:  # type: ignore[type-arg]
        return [
            {"id": "scenario-base", "key": "plan_base"},
            {"id": "scenario-high", "key": "plan_high"},
            {"id": "scenario-actual", "key": "actual"},
        ]

    def list_metric_definitions(self) -> list[dict]:  # type: ignore[type-arg]
        return [
            {
                "id": "metric-revenue",
                "key": "revenue_uplift",
                "aggregation": "sum",
                "benefit_class": "revenue",
                "is_benefit": True,
            }
        ]


def test_dynamic_value_bridge_rows_follow_tenant_configuration() -> None:
    svc = object.__new__(FinancialService)
    svc._repo = _Repo()  # type: ignore[attr-defined]

    values = [
        {
            "metric_definition_id": "metric-revenue",
            "scenario_id": "scenario-base",
            "year": 2026,
            "month": 1,
            "value": "100.0000",
        },
        {
            "metric_definition_id": "metric-revenue",
            "scenario_id": "scenario-high",
            "year": 2026,
            "month": 1,
            "value": "150.0000",
        },
        {
            "metric_definition_id": "metric-revenue",
            "scenario_id": "scenario-actual",
            "year": 2026,
            "month": 1,
            "value": "80.0000",
        },
    ]
    costs = [
        {
            "category_key": "implementation",
            "amount_plan": "25.0000",
            "amount_actual": "30.0000",
            "is_recurring": True,
        }
    ]

    rows = svc._clean_dynamic_bridge_rows(values, costs)

    assert [(row.key, row.base_case, row.high_case, row.actual) for row in rows] == [
        ("revenue", "100.0000", "150.0000", "80.0000"),
        ("implementation", "-25.0000", "-25.0000", "-30.0000"),
        ("net_value", "75.0000", "125.0000", "50.0000"),
    ]
