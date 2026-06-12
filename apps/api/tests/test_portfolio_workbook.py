from __future__ import annotations

from pathlib import Path

from app.services.portfolio_workbook import PortfolioWorkbookReloadService

WORKBOOK_PATH = Path(__file__).resolve().parents[3] / "Initiative_Portfolio_Anonymised.xlsx"


def test_anonymised_portfolio_workbook_summary_is_deterministic() -> None:
    service = PortfolioWorkbookReloadService.__new__(PortfolioWorkbookReloadService)
    parsed = service.parse(WORKBOOK_PATH.read_bytes())

    summary = PortfolioWorkbookReloadService.workbook_summary(parsed)

    assert summary["initiatives"] == 21
    assert summary["business_units"] == 9
    assert summary["workstreams"] == 4
    assert summary["benefit_lines"] == 63
    assert summary["metric_values"] == 4694
    assert summary["cost_lines"] == 867
    assert summary["kpis"] == 83
    assert summary["kpi_entries"] == 313
    assert summary["milestones"] == 292
    assert summary["risks"] == 33
    assert summary["status_updates"] == 4
    assert summary["required_metric_keys"] == [
        "gm_uplift",
        "gm_uplift_pct",
        "gross_margin",
        "revenue_uplift",
    ]
    assert summary["required_scenario_keys"] == ["actual", "plan_base", "plan_high"]
    assert summary["required_stage_gate_numbers"] == [3]
