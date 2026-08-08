from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from app.domain.financials import (
    FinancialMetricDefinitionCreate,
    FinancialMetricDeleteRequest,
)
from app.services.financial import FinancialService


def _impact(*, can_delete: bool, blocker_total: int = 0) -> dict[str, Any]:
    empty = {"count": 0, "references": []}
    blockers = {
        "benefit_lines": dict(empty),
        "metric_values": dict(empty),
        "initiative_scope": dict(empty),
        "initiative_baselines": dict(empty),
        "legacy_selections": dict(empty),
        "legacy_configuration": dict(empty),
        "formula_dependencies": dict(empty),
        "bridge_rows": dict(empty),
        "shared_cost_rules": dict(empty),
        "shared_cost_allocations": dict(empty),
    }
    if blocker_total:
        blockers["formula_dependencies"] = {
            "count": blocker_total,
            "references": [
                {
                    "id": "formula-1",
                    "initiative_id": None,
                    "initiative_name": None,
                    "label": "Margin percentage · metric",
                }
            ],
        }
    return {
        "metric": {
            "id": "metric-1",
            "key": "custom_margin",
            "label": "Custom margin",
            "is_system": False,
            "is_active": True,
        },
        "can_delete": can_delete,
        "blocked_by_system": False,
        "blocker_total": blocker_total,
        "blockers": blockers,
        "cleanup": {"tenant_annual_baselines": dict(empty)},
        "confirmation_key": "custom_margin",
    }


class _Repo:
    def __init__(self) -> None:
        self.created: dict[str, Any] | None = None
        self.impact = _impact(can_delete=True)
        self.delete_result: dict[str, Any] | None = {
            **self.impact,
            "deleted": True,
            "status": "deleted",
        }

    def list_metric_definitions(self) -> list[dict[str, Any]]:
        return []

    def create_metric_definition(
        self,
        data: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        self.created = data
        return {"id": "metric-1", **data, "created_by": user_id, "updated_by": user_id}

    def get_metric_deletion_impact(self, metric_definition_id: str) -> dict[str, Any] | None:
        return self.impact if metric_definition_id == "metric-1" else None

    def delete_metric_definition(
        self,
        metric_definition_id: str,
        confirmation_key: str,
    ) -> dict[str, Any] | None:
        return self.delete_result if metric_definition_id == "metric-1" else None


def _service(repo: _Repo) -> FinancialService:
    service = object.__new__(FinancialService)
    service._repo = repo  # type: ignore[attr-defined]
    return service


def _create_request() -> FinancialMetricDefinitionCreate:
    return FinancialMetricDefinitionCreate(
        key="custom_margin",
        label="Custom margin",
        value_type="currency",
        aggregation="sum",
        is_benefit=True,
        benefit_class="margin",
    )


def test_tenant_metric_creation_forces_custom_classification() -> None:
    repo = _Repo()
    created = _service(repo).create_metric_definition(_create_request(), "user-1")

    assert created.is_system is False
    assert repo.created is not None
    assert repo.created["is_system"] is False


def test_metric_deletion_impact_is_typed() -> None:
    impact = _service(_Repo()).get_metric_deletion_impact("metric-1")

    assert impact.can_delete is True
    assert impact.metric.key == "custom_margin"
    assert impact.blockers.formula_dependencies.count == 0


def test_blocked_metric_delete_returns_structured_conflict() -> None:
    repo = _Repo()
    repo.impact = _impact(can_delete=False, blocker_total=1)
    repo.delete_result = {**repo.impact, "deleted": False, "status": "blocked"}

    with pytest.raises(HTTPException) as exc_info:
        _service(repo).delete_metric_definition(
            "metric-1",
            FinancialMetricDeleteRequest(confirmation_key="custom_margin"),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["impact"]["blocker_total"] == 1
    assert exc_info.value.detail["impact"]["blockers"]["formula_dependencies"]["count"] == 1


def test_metric_delete_rejects_confirmation_mismatch() -> None:
    repo = _Repo()
    repo.delete_result = {
        **repo.impact,
        "deleted": False,
        "status": "confirmation_mismatch",
    }

    with pytest.raises(HTTPException) as exc_info:
        _service(repo).delete_metric_definition(
            "metric-1",
            FinancialMetricDeleteRequest(confirmation_key="wrong_key"),
        )

    assert exc_info.value.status_code == 400


def test_cross_tenant_or_missing_metric_is_not_disclosed() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _service(_Repo()).get_metric_deletion_impact("another-tenant-metric")

    assert exc_info.value.status_code == 404
