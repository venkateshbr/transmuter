from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.financial import FinancialService, FormulaValidationError


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


def test_formula_divide_by_zero_returns_zero_value() -> None:
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
