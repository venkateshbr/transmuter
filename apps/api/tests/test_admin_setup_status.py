from __future__ import annotations

from types import SimpleNamespace

from app.services.admin import AdminService


class _OrgRepo:
    def get_organization(self) -> dict[str, str]:
        return {"id": "tenant-1", "name": "Blank Tenant"}


class _Query:
    def __init__(self, table_name: str, counts: dict[str, int]) -> None:
        self._table_name = table_name
        self._counts = counts

    def select(self, *_args: str, **_kwargs: object) -> _Query:
        return self

    def eq(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def neq(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(count=self._counts.get(self._table_name, 0), data=[])


class _Client:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts

    def table(self, table_name: str) -> _Query:
        return _Query(table_name, self._counts)


def test_setup_status_reports_blank_tenant_prerequisites_incomplete() -> None:
    service = object.__new__(AdminService)
    service._org_repo = _OrgRepo()
    service._c = _Client(
        {
            "users": 1,
            "business_units": 0,
            "workstreams": 0,
            "stage_gate_definitions": 0,
            "financial_config_groups": 0,
            "financial_config_items": 0,
            "financial_metric_definitions": 0,
            "financial_scenarios": 0,
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
        "financial_engine": False,
        "stage_gates": False,
        "gate_criteria": False,
        "users": True,
    }
