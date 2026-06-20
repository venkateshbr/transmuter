from __future__ import annotations

from types import SimpleNamespace

from app.services.admin import AdminService


class _OrgRepo:
    def get_organization(self) -> dict[str, str]:
        return {"id": "tenant-1", "name": "Blank Tenant"}


class _Query:
    def __init__(
        self,
        table_name: str,
        counts: dict[str, int],
        rows: dict[str, list[dict[str, object]]] | None = None,
    ) -> None:
        self._table_name = table_name
        self._counts = counts
        self._rows = rows or {}

    def select(self, *_args: str, **_kwargs: object) -> _Query:
        return self

    def eq(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def neq(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(
            count=self._counts.get(self._table_name, 0),
            data=self._rows.get(self._table_name, []),
        )


class _Client:
    def __init__(
        self,
        counts: dict[str, int],
        rows: dict[str, list[dict[str, object]]] | None = None,
    ) -> None:
        self._counts = counts
        self._rows = rows or {}

    def table(self, table_name: str) -> _Query:
        return _Query(table_name, self._counts, self._rows)


def test_setup_status_reports_blank_tenant_prerequisites_incomplete() -> None:
    service = object.__new__(AdminService)
    service._org_repo = _OrgRepo()
    service._c = _Client(
        {
            "users": 1,
            "business_units": 0,
            "workstreams": 0,
            "stage_gate_definitions": 0,
            "financial_metric_definitions": 0,
            "financial_scenarios": 0,
            "financial_cost_categories": 0,
            "gate_criteria": 0,
            "initiatives": 0,
        }
    )
    service._tid = "tenant-1"

    status = service.get_setup_status()

    assert status["complete"] is False
    assert status["counts"]["initiatives"] == 0
    checks = {check["key"]: check["complete"] for check in status["checks"]}
    assert checks == {
        "organization": True,
        "business_units": False,
        "workstreams": False,
        "financial_config": False,
        "stage_gates": False,
        "gate_criteria": False,
        "users": True,
    }
    gate_check = next(check for check in status["checks"] if check["key"] == "gate_criteria")
    assert gate_check["details"] == {
        "complete": False,
        "active_stage_gates": 0,
        "active_gate_criteria": 0,
        "gates_with_criteria": 0,
        "gates_missing_criteria": 0,
        "missing_gate_numbers": [],
    }


def test_setup_status_reports_missing_gate_criteria_by_gate() -> None:
    service = object.__new__(AdminService)
    service._org_repo = _OrgRepo()
    service._c = _Client(
        {
            "users": 1,
            "business_units": 2,
            "workstreams": 2,
            "stage_gate_definitions": 3,
            "financial_metric_definitions": 2,
            "financial_scenarios": 2,
            "financial_cost_categories": 2,
            "gate_criteria": 2,
            "initiatives": 0,
        },
        {
            "stage_gate_definitions": [
                {"gate_number": 1, "is_active": True},
                {"gate_number": 2, "is_active": True},
                {"gate_number": 3, "is_active": True},
            ],
            "gate_criteria": [
                {"gate_number": 1, "is_active": True},
                {"gate_number": 3, "is_active": True},
            ],
        },
    )
    service._tid = "tenant-1"

    status = service.get_setup_status()

    assert status["counts"]["active_stage_gates"] == 3
    assert status["counts"]["active_gate_criteria"] == 2
    assert status["counts"]["gates_with_criteria"] == 2
    assert status["counts"]["gates_missing_criteria"] == 1
    gate_check = next(check for check in status["checks"] if check["key"] == "gate_criteria")
    assert gate_check["complete"] is False
    assert gate_check["details"]["missing_gate_numbers"] == [2]
