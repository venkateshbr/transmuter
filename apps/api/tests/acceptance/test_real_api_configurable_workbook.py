"""Real API acceptance for the configurable workbook-backed platform model.

Run with a live API server after applying migrations and reloading
Initiative_Portfolio_Anonymised.xlsx:

    RUN_REAL_ACCEPTANCE=1 TRANSMUTER_API_BASE_URL=http://localhost:8000 \
      pytest tests/acceptance/test_real_api_configurable_workbook.py -q
"""

from __future__ import annotations

import os
from decimal import Decimal

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REAL_ACCEPTANCE") != "1",
    reason="real API acceptance requires a running API and RUN_REAL_ACCEPTANCE=1",
)

BASE_URL = os.environ.get("TRANSMUTER_API_BASE_URL", "http://localhost:8000")
EMAIL = os.environ.get("TRANSMUTER_E2E_EMAIL", "admin@ishirock.dev")
PASSWORD = os.environ.get("TRANSMUTER_E2E_PASSWORD", "Transmuter2026!")


def _auth_headers(client: httpx.Client) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _money(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def test_real_api_configurable_workbook_financial_model() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        headers = _auth_headers(client)

        config = client.get("/financial-engine-configuration", headers=headers)
        config.raise_for_status()
        config_data = config.json()
        definitions = {row["key"]: row for row in config_data["definitions"]}
        scenarios = {row["key"]: row for row in config_data["scenarios"]}
        bridge_rows = {row["key"]: row for row in config_data["bridge_rows"]}

        assert {"revenue_uplift", "gross_margin", "gm_uplift", "gm_uplift_pct"} <= set(definitions)
        assert {"baseline", "plan_base", "plan_high", "actual"} <= set(scenarios)
        assert {"revenue", "margin", "recurring_costs", "one_off_costs", "net_value"} <= set(
            bridge_rows
        )

        initiatives = client.get("/initiatives?page_size=25", headers=headers)
        initiatives.raise_for_status()
        initiative_items = initiatives.json()["items"]
        assert len(initiative_items) >= 21

        candidate = initiative_items[0]
        financials = client.get(f"/initiatives/{candidate['id']}/financials", headers=headers)
        financials.raise_for_status()
        grid = financials.json()

        assert len(grid["definitions"]) >= 10
        assert len(grid["scenarios"]) >= 4
        assert len(grid["benefit_lines"]) >= 1
        assert len(grid["cost_lines"]) >= 1
        assert len(grid["values"]) >= 1
        assert grid["entries"] == []
        assert grid["metric_values"] == []

        grid_definitions = {row["key"]: row for row in grid["definitions"]}
        value_metric_ids = {row["metric_definition_id"] for row in grid["values"]}
        assert {"revenue_uplift", "gross_margin", "gm_uplift", "gm_uplift_pct"} <= set(
            grid_definitions
        )
        assert value_metric_ids <= {row["id"] for row in grid["definitions"]}

        portfolio = client.get(
            "/portfolio/financials?granularity=quarterly&year=2027",
            headers=headers,
        )
        portfolio.raise_for_status()
        portfolio_data = portfolio.json()
        assert portfolio_data["granularity"] == "quarterly"
        assert len(portfolio_data["periods"]) == 4
        assert _money(portfolio_data["summary"][0]["plan"]) > 0
        assert any(_money(period["benefits_plan"]) > 0 for period in portfolio_data["periods"])

        ramp = client.get(
            "/portfolio/value-ramp?granularity=quarterly&run_rate_year=2027",
            headers=headers,
        )
        ramp.raise_for_status()
        ramp_data = ramp.json()
        assert ramp_data["granularity"] == "quarterly"
        assert ramp_data["run_rate_year"] == 2027
        assert len(ramp_data["periods"]) == 4
        assert len(ramp_data["in_year"]) == 4
        assert ramp_data["financial_mode"]["key"] == "multi_scenario"
        assert any(
            _money(period["cumulative_net_value_plan"]) != 0 for period in ramp_data["periods"]
        )


def test_real_api_configurable_stage_gates_are_tenant_defined() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        headers = _auth_headers(client)

        gates = client.get("/governance/stage-gates", headers=headers)
        gates.raise_for_status()
        gate_numbers = [gate["gate_number"] for gate in gates.json()]

        assert gate_numbers == [1, 2, 3, 4, 5]
