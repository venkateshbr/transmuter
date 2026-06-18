from uuid import UUID

from app.domain.financials import ValueBridgeCase
from app.services.financial import FinancialService


def test_initiative_pnl_bridge_uses_baseline_and_incremental_value() -> None:
    service = FinancialService.__new__(FinancialService)
    service._tenant_id = UUID("11111111-1111-1111-1111-111111111111")

    bridge = service._initiative_pnl_bridge(
        baseline_values=[
            {
                "metric_key": "annual_revenue_baseline",
                "metric_label": "Annual Revenue Baseline",
                "baseline_year": 2026,
                "value": "2200000.0000",
            },
            {
                "metric_key": "annual_gross_margin_baseline",
                "metric_label": "Annual Gross Margin Baseline",
                "baseline_year": 2026,
                "value": "990000.0000",
            },
        ],
        base_case=ValueBridgeCase(
            revenue_uplift="1099999.9992",
            gross_margin="0.0000",
            gm_uplift="760000.0008",
            other_benefits="249999.9996",
            benefits_total="1010000.0004",
            costs_recurring="82500.0000",
            costs_one_off="280000.0000",
            costs_total="362500.0000",
            net="927500.0004",
        ),
        high_case=ValueBridgeCase(
            revenue_uplift="1243999.9992",
            gm_uplift="841200.0000",
            other_benefits="272000.0004",
            benefits_total="1113200.0004",
            costs_recurring="82500.0000",
            costs_one_off="280000.0000",
            costs_total="362500.0000",
            net="1030700.0004",
        ),
        actual_case=ValueBridgeCase(
            revenue_uplift="996000.0000",
            gm_uplift="673599.9996",
            other_benefits="213999.9996",
            benefits_total="887599.9992",
            costs_recurring="80025.0000",
            costs_one_off="266000.0000",
            costs_total="346025.0000",
            net="807574.9992",
        ),
    )

    assert bridge.baseline_year == 2026
    assert bridge.base_case.baseline_revenue == "2200000.0000"
    assert bridge.base_case.target_revenue == "3299999.9992"
    assert bridge.base_case.baseline_gross_margin == "990000.0000"
    assert bridge.base_case.margin_and_benefit_uplift == "1010000.0004"
    assert bridge.base_case.incremental_net_run_rate == "927500.0004"
    assert bridge.base_case.target_run_rate_value == "1917500.0004"
    assert bridge.base_case.one_off_costs == "280000.0000"
    assert [step.key for step in bridge.base_case.steps] == [
        "baseline_revenue",
        "revenue_uplift",
        "target_revenue",
        "baseline_gross_margin",
        "margin_and_benefit_uplift",
        "recurring_opex",
        "target_run_rate_value",
    ]
    assert bridge.base_case.steps[1].value == "1099999.9992"
    assert bridge.base_case.steps[5].value == "-82500.0000"
    assert bridge.high_case.target_run_rate_value == "2020700.0004"
    assert bridge.actual.target_run_rate_value == "1797574.9992"
