from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.financial import FinancialService, FormulaValidationError
from app.services.financial_metric_catalog import CANONICAL_FINANCIAL_METRICS


class _Repo:
    def __init__(self, definitions: list[dict]) -> None:  # type: ignore[type-arg]
        self.definitions = definitions

    def list_metric_definitions(self) -> list[dict]:  # type: ignore[type-arg]
        return self.definitions


def _service(definitions: list[dict]) -> FinancialService:  # type: ignore[type-arg]
    svc = object.__new__(FinancialService)
    svc._repo = _Repo(definitions)  # type: ignore[attr-defined]
    return svc


def test_formula_metric_values_are_computed_from_decimal_inputs() -> None:
    definitions = [
        {
            "id": "metric-revenue",
            "key": "revenue_uplift",
            "aggregation": "sum",
            "is_active": True,
        },
        {
            "id": "metric-gm",
            "key": "gross_margin",
            "aggregation": "sum",
            "is_active": True,
        },
        {
            "id": "metric-gm-pct",
            "key": "gm_pct",
            "aggregation": "formula",
            "formula": "gross_margin / revenue_uplift * 100",
            "is_active": True,
        },
    ]
    svc = _service(definitions)

    values = svc._values_with_formula_metrics(
        [
            {
                "id": "value-revenue",
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-1",
                "metric_definition_id": "metric-revenue",
                "scenario_id": "scenario-base",
                "year": 2026,
                "month": 1,
                "value": "200.0000",
            },
            {
                "id": "value-gm",
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-1",
                "metric_definition_id": "metric-gm",
                "scenario_id": "scenario-base",
                "year": 2026,
                "month": 1,
                "value": "50.0000",
            },
        ]
    )

    formula_rows = [row for row in values if row.get("_computed_formula")]
    assert len(formula_rows) == 1
    assert formula_rows[0]["metric_definition_id"] == "metric-gm-pct"
    assert formula_rows[0]["value"] == "25.0000"
    assert formula_rows[0]["status"] == "approved"


def test_formula_metric_values_can_reference_annual_baseline_inputs() -> None:
    definitions = [
        {
            "id": "metric-revenue-uplift",
            "key": "revenue_uplift",
            "aggregation": "sum",
            "is_active": True,
        },
        {
            "id": "metric-baseline-revenue",
            "key": "baseline_revenue",
            "aggregation": "last",
            "is_active": True,
        },
        {
            "id": "metric-revenue-uplift-pct",
            "key": "revenue_uplift_pct",
            "aggregation": "formula",
            "formula": "revenue_uplift / baseline_revenue * 100",
            "is_active": True,
        },
    ]
    svc = _service(definitions)

    values = svc._values_with_formula_metrics(
        [
            {
                "id": "value-revenue",
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-1",
                "metric_definition_id": "metric-revenue-uplift",
                "scenario_id": "scenario-base",
                "year": 2027,
                "month": 1,
                "value": "200000.0000",
            },
        ],
        [
            {
                "id": "baseline-revenue",
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-1",
                "metric_definition_id": "metric-baseline-revenue",
                "baseline_year": 2026,
                "value": "20000000.0000",
            },
        ],
    )

    formula_rows = [row for row in values if row.get("_computed_formula")]
    assert len(formula_rows) == 1
    assert formula_rows[0]["metric_definition_id"] == "metric-revenue-uplift-pct"
    assert formula_rows[0]["value"] == "1.0000"


def test_formula_validation_accepts_baseline_metric_aliases() -> None:
    svc = _service(
        [
            {
                "id": "metric-revenue-uplift",
                "key": "revenue_uplift",
                "aggregation": "sum",
                "is_active": True,
            }
        ]
    )

    svc._validate_metric_definition_payload(
        {
            "id": "metric-improvement-pct",
            "key": "improvement_pct",
            "aggregation": "formula",
            "formula": "revenue_uplift / baseline_revenue_uplift * 100",
            "formula_inputs": ["revenue_uplift", "baseline_revenue_uplift"],
            "is_active": True,
        }
    )


def test_formula_divide_by_zero_is_explicitly_not_available() -> None:
    definitions = [
        {
            "id": "metric-revenue",
            "key": "revenue_uplift",
            "aggregation": "sum",
            "is_active": True,
        },
        {
            "id": "metric-gm",
            "key": "gross_margin",
            "aggregation": "sum",
            "is_active": True,
        },
        {
            "id": "metric-gm-pct",
            "key": "gm_pct",
            "aggregation": "formula",
            "formula": "gross_margin / revenue_uplift * 100",
            "is_active": True,
        },
    ]
    svc = _service(definitions)

    values = svc._values_with_formula_metrics(
        [
            {
                "id": "value-revenue",
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-1",
                "metric_definition_id": "metric-revenue",
                "scenario_id": "scenario-base",
                "year": 2026,
                "month": 1,
                "value": "0.0000",
            },
            {
                "id": "value-gm",
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-1",
                "metric_definition_id": "metric-gm",
                "scenario_id": "scenario-base",
                "year": 2026,
                "month": 1,
                "value": "50.0000",
            },
        ]
    )

    formula_rows = [row for row in values if row.get("_computed_formula")]
    assert formula_rows[0]["value"] == "0.0000"
    assert formula_rows[0]["calculation_status"] == "not_available"
    assert formula_rows[0]["calculation_reason"] == "zero_denominator"


def test_annual_formula_uses_ratio_of_summed_months_and_baseline_once() -> None:
    definitions = [
        {"id": "baseline", "key": "annual_revenue_baseline", "aggregation": "last"},
        {"id": "uplift", "key": "revenue_uplift", "aggregation": "sum"},
        {
            "id": "growth",
            "key": "revenue_growth_pct",
            "aggregation": "formula",
            "evaluation_grain": "annual",
            "formula": "revenue_uplift / annual_revenue_baseline * 100",
            "validation": {},
            "is_active": True,
        },
    ]
    svc = _service(definitions)
    values = svc._values_with_formula_metrics(
        [
            {
                "id": "jan",
                "tenant_id": "t",
                "initiative_id": "i",
                "scenario_id": "s",
                "metric_definition_id": "uplift",
                "year": 2028,
                "month": 1,
                "value": "100",
            },
            {
                "id": "feb",
                "tenant_id": "t",
                "initiative_id": "i",
                "scenario_id": "s",
                "metric_definition_id": "uplift",
                "year": 2028,
                "month": 2,
                "value": "300",
            },
        ],
        [
            {
                "id": "b",
                "initiative_id": "i",
                "metric_definition_id": "baseline",
                "baseline_year": 2027,
                "value": "2000",
            }
        ],
    )

    formula_rows = [row for row in values if row.get("_computed_formula")]
    assert len(formula_rows) == 1
    assert formula_rows[0]["month"] == 12
    assert formula_rows[0]["value"] == "20.0000"
    assert formula_rows[0]["calculation_status"] == "calculated"


def test_formula_missing_input_and_computed_range_are_distinct() -> None:
    definitions = [
        {"id": "revenue", "key": "target_revenue", "aggregation": "sum"},
        {
            "id": "cogs",
            "key": "target_cogs_pct",
            "aggregation": "formula",
            "formula": "target_cogs / target_revenue * 100",
            "is_active": True,
            "validation": {"min": 0, "max": 100},
        },
    ]
    svc = _service(definitions)
    missing = svc._values_with_formula_metrics(
        [
            {
                "id": "r",
                "tenant_id": "t",
                "initiative_id": "i",
                "scenario_id": "s",
                "metric_definition_id": "revenue",
                "year": 2028,
                "month": 1,
                "value": "100",
            }
        ]
    )
    formula = next(row for row in missing if row.get("_computed_formula"))
    assert formula["calculation_status"] == "not_available"
    assert formula["calculation_reason"] == "missing_input"


def test_canonical_catalogue_reconciles_gross_margin_and_cogs_percentages() -> None:
    definitions = [{"id": str(metric["key"]), **metric} for metric in CANONICAL_FINANCIAL_METRICS]
    svc = _service(definitions)
    common = {
        "tenant_id": "tenant-1",
        "initiative_id": "initiative-1",
        "scenario_id": "plan-base",
        "year": 2028,
    }
    values = svc._values_with_formula_metrics(
        [
            {
                "id": "revenue",
                **common,
                "metric_definition_id": "revenue_uplift",
                "month": 1,
                "value": "200",
            },
            {
                "id": "profit",
                **common,
                "metric_definition_id": "gross_profit_uplift",
                "month": 1,
                "value": "110",
            },
        ],
        [
            {
                "id": "revenue-baseline",
                "initiative_id": "initiative-1",
                "metric_definition_id": "annual_revenue_baseline",
                "baseline_year": 2027,
                "value": "1000",
            },
            {
                "id": "profit-baseline",
                "initiative_id": "initiative-1",
                "metric_definition_id": "annual_gross_profit_baseline",
                "baseline_year": 2027,
                "value": "400",
            },
        ],
    )
    by_key = {row["metric_definition_id"]: row for row in values if row.get("_computed_formula")}

    assert by_key["target_revenue"]["value"] == "1200.0000"
    assert by_key["target_gross_profit"]["value"] == "510.0000"
    assert by_key["target_cogs"]["value"] == "690.0000"
    assert by_key["revenue_growth_pct"]["value"] == "20.0000"
    assert by_key["baseline_gross_margin_pct"]["value"] == "40.0000"
    assert by_key["target_gross_margin_pct"]["value"] == "42.5000"
    assert by_key["gross_margin_change_pp"]["value"] == "2.5000"
    assert by_key["target_cogs_pct"]["value"] == "57.5000"
    assert Decimal(by_key["target_gross_margin_pct"]["value"]) + Decimal(
        by_key["target_cogs_pct"]["value"]
    ) == Decimal("100.0000")


def test_formula_metrics_are_computed_in_dependency_order() -> None:
    definitions = [
        {
            "id": "metric-revenue",
            "key": "revenue_uplift",
            "aggregation": "sum",
            "is_active": True,
        },
        {
            "id": "metric-double-with-bonus",
            "key": "double_with_bonus",
            "aggregation": "formula",
            "formula": "double_revenue + 5",
            "is_active": True,
        },
        {
            "id": "metric-double-revenue",
            "key": "double_revenue",
            "aggregation": "formula",
            "formula": "revenue_uplift * 2",
            "is_active": True,
        },
    ]
    svc = _service(definitions)

    values = svc._values_with_formula_metrics(
        [
            {
                "id": "value-revenue",
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-1",
                "metric_definition_id": "metric-revenue",
                "scenario_id": "scenario-base",
                "year": 2026,
                "month": 1,
                "value": "10.0000",
            },
        ]
    )

    formula_values = {
        row["metric_definition_id"]: row["value"] for row in values if row.get("_computed_formula")
    }
    assert formula_values == {
        "metric-double-revenue": "20.0000",
        "metric-double-with-bonus": "25.0000",
    }


def test_formula_metric_writes_are_rejected() -> None:
    svc = _service(
        [
            {
                "id": "metric-gm-pct",
                "key": "gm_pct",
                "aggregation": "formula",
                "is_active": True,
            }
        ]
    )

    with pytest.raises(HTTPException) as exc:
        svc._assert_no_formula_metric_values(
            [SimpleNamespace(metric_definition_id="metric-gm-pct")]
        )

    assert exc.value.status_code == 400


def test_formula_validation_rejects_unsafe_syntax_and_cycles() -> None:
    svc = _service(
        [
            {
                "id": "metric-revenue",
                "key": "revenue_uplift",
                "aggregation": "sum",
                "is_active": True,
            }
        ]
    )

    with pytest.raises(FormulaValidationError):
        svc._validate_formula_expression("__import__('os').system('echo no')", {"revenue_uplift"})

    cycle_service = _service(
        [
            {
                "id": "metric-a",
                "key": "a",
                "aggregation": "formula",
                "formula": "b + 1",
                "formula_inputs": ["b"],
                "is_active": True,
            }
        ]
    )
    with pytest.raises(HTTPException) as exc:
        cycle_service._validate_metric_definition_payload(
            {
                "id": "metric-b",
                "key": "b",
                "aggregation": "formula",
                "formula": "a + 1",
                "formula_inputs": ["a"],
                "is_active": True,
            }
        )

    assert exc.value.status_code == 400
    assert "cycles" in str(exc.value.detail)
