from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.domain.executive_control import (
    AllocationPreviewRequest,
    AllocationRuleCreate,
    AllocationRuleUpdate,
    AllocationRunCreate,
    InitiativeDependencyCreate,
    InitiativeDependencyUpdate,
    ReportFilterParams,
)
from app.services.executive_control import ExecutiveControlService


class _Repo:
    def __init__(self) -> None:
        self.dependencies = [
            {
                "id": "d1",
                "upstream_initiative_id": "i1",
                "downstream_initiative_id": "i2",
                "dependency_type": "blocks",
                "status": "active",
                "severity": "high",
                "upstream": {
                    "id": "i1",
                    "initiative_code": "TRN-001",
                    "name": "Platform",
                    "owner_id": "u1",
                    "rag_status": "green",
                    "stage": "in_progress",
                },
                "downstream": {
                    "id": "i2",
                    "initiative_code": "TRN-002",
                    "name": "Commercial rollout",
                    "owner_id": "u2",
                    "rag_status": "amber",
                    "stage": "in_progress",
                },
            }
        ]
        self.created_allocations: list[dict] = []
        self.rule_targets: dict[str, list[dict]] = {}
        self.rule_weights: dict[str, list[dict]] = {}
        self.rules = [
            {
                "id": "r1",
                "pool_id": "p1",
                "name": "Benefit rule",
                "allocation_method": "benefit_weighted",
                "filters": {},
                "weights": {},
                "is_active": True,
                "version": 1,
                "policy_status": "active",
                "missing_basis_behavior": "fail",
            }
        ]

    def list_dependencies(self) -> list[dict]:
        return self.dependencies

    def create_dependency(self, data: dict) -> dict:
        row = {"id": "d2", **data}
        self.dependencies.append(row)
        return row

    def get_dependency(self, dependency_id: str) -> dict | None:
        return next((row for row in self.dependencies if row["id"] == dependency_id), None)

    def update_dependency(self, dependency_id: str, data: dict) -> dict:
        row = self.get_dependency(dependency_id)
        assert row is not None
        row.update(data)
        return row

    def list_initiatives(self) -> list[dict]:
        return [
            {
                "id": "i1",
                "initiative_code": "TRN-001",
                "name": "Platform",
                "owner_id": "u1",
                "workstream_id": "w1",
                "tag": "automation",
                "country": "Group",
                "rag_status": "green",
                "stage": "in_progress",
                "benefit_confidence": "80",
                "realization_status": "forecasted",
            },
            {
                "id": "i2",
                "initiative_code": "TRN-002",
                "name": "Commercial rollout",
                "owner_id": "u2",
                "workstream_id": "w1",
                "tag": "commercial",
                "country": "Singapore",
                "rag_status": "amber",
                "stage": "in_progress",
                "benefit_confidence": "40",
                "realization_status": "at_risk",
            },
        ]

    def list_workstreams(self) -> list[dict]:
        return [{"id": "w1", "name": "Transformation"}]

    def list_business_units(self) -> list[dict]:
        return []

    def list_financial_scenarios(self) -> list[dict]:
        return [
            {
                "id": "s-plan",
                "key": "plan",
                "label": "Plan",
                "kind": "plan",
                "is_primary": True,
                "is_active": True,
            }
        ]

    def list_metric_definitions(self) -> list[dict]:
        return []

    def list_metric_values(self) -> list[dict]:
        return []

    def list_cost_categories(self) -> list[dict]:
        return []

    def list_financial_entries(self) -> list[dict]:
        return [
            {
                "initiative_id": "i1",
                "year": 2026,
                "gm_uplift_base": "100.0000",
                "gm_uplift_actual": "80.0000",
                "revenue_uplift_base": "500.0000",
            },
            {
                "initiative_id": "i2",
                "year": 2026,
                "gm_uplift_base": "300.0000",
                "gm_uplift_actual": None,
                "revenue_uplift_base": "1500.0000",
            },
        ]

    def list_direct_cost_lines(self) -> list[dict]:
        return [{"initiative_id": "i1", "year": 2026, "amount_plan": "10.0000"}]

    def list_allocations(self) -> list[dict]:
        return [
            {
                **row,
                "pool_id": row.get("pool_id", "p1"),
                "shared_cost_pools": {"year": 2026},
                "shared_cost_allocation_runs": {
                    "status": "locked",
                    "period_start": row.get("period_start") or "2026-01-01",
                    "period_end": row.get("period_end") or "2026-12-31",
                },
            }
            for row in self.created_allocations
        ]

    def get_pool(self, pool_id: str) -> dict | None:
        if pool_id != "p1":
            return None
        return {
            "id": pool_id,
            "name": "Shared platform",
            "category_key": "technology",
            "amount_plan": "400.0000",
            "amount_actual": "300.0000",
            "year": 2026,
            "status": "active",
            "reporting_treatment": "report_only",
            "period_grain": "annual",
        }

    def get_rule(self, rule_id: str) -> dict | None:
        return next((row for row in self.rules if row["id"] == rule_id), None)

    def create_rule(self, pool_id: str, data: dict) -> dict:
        row = {"id": "r2", "pool_id": pool_id, **data}
        self.rules.append(row)
        return row

    def update_rule(self, rule_id: str, data: dict) -> dict:
        row = self.get_rule(rule_id)
        assert row is not None
        row.update(data)
        return row

    def list_rule_targets(self, rule_id: str) -> list[dict]:
        return self.rule_targets.get(rule_id, [])

    def replace_rule_targets(self, rule_id: str, targets: list[dict]) -> list[dict]:
        rows = [{"id": f"target-{index}", **target} for index, target in enumerate(targets, 1)]
        self.rule_targets[rule_id] = rows
        return rows

    def list_rule_weights(self, rule_id: str) -> list[dict]:
        return self.rule_weights.get(rule_id, [])

    def replace_rule_weights(self, rule_id: str, weights: list[dict]) -> list[dict]:
        rows = [{"id": f"weight-{index}", **weight} for index, weight in enumerate(weights, 1)]
        self.rule_weights[rule_id] = rows
        return rows

    def create_run(self, data: dict, allocations: list[dict]) -> dict:
        self.created_allocations = [
            {
                **allocation,
                "pool_id": data["pool_id"],
                "rule_id": data["rule_id"],
            }
            for allocation in allocations
        ]
        return {"id": "run1", "created_at": "2026-05-10T00:00:00Z", **data}

    def create_exceptions(self, rows: list[dict]) -> None:
        return None

    def create_audit_event(self, data: dict) -> None:
        return None

    def get_reporting_settings(self) -> dict:
        return {
            "include_in_executive_control_tower": True,
            "include_in_dashboard_executive_brief": True,
            "include_in_portfolio_financials": False,
            "include_in_initiative_financials": True,
            "include_in_bankable_plan": False,
            "posting_mode": "report_only",
        }


def _service() -> ExecutiveControlService:
    service = ExecutiveControlService.__new__(ExecutiveControlService)
    service._repo = _Repo()
    return service


def test_dependency_cycle_detection_blocks_reverse_edge() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc:
        service.create_dependency(
            InitiativeDependencyCreate(
                upstream_initiative_id="i2",
                downstream_initiative_id="i1",
                dependency_type="blocks",
            )
        )

    assert exc.value.status_code == 400
    assert "cycle" in exc.value.detail


def test_dependency_create_rejects_unknown_initiative() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc:
        service.create_dependency(
            InitiativeDependencyCreate(
                upstream_initiative_id="i1",
                downstream_initiative_id="missing",
                dependency_type="blocks",
            )
        )

    assert exc.value.status_code == 404


def test_dependency_update_blocks_viewer_mutation() -> None:
    service = _service()
    viewer = type("User", (), {"id": "viewer", "role": "viewer"})()

    with pytest.raises(HTTPException) as exc:
        service.update_dependency(
            "d1",
            InitiativeDependencyUpdate(status="resolved"),
            viewer,
        )

    assert exc.value.status_code == 403


def test_dependency_owner_update_is_limited_to_visible_status_fields() -> None:
    service = _service()
    owner = type("User", (), {"id": "u1", "role": "initiative_owner"})()

    updated = service.update_dependency(
        "d1",
        InitiativeDependencyUpdate(status="resolved", resolution_notes="Done"),
        owner,
    )
    assert updated.status == "resolved"

    with pytest.raises(HTTPException) as exc:
        service.update_dependency(
            "d1",
            InitiativeDependencyUpdate(severity="low"),
            owner,
        )

    assert exc.value.status_code == 403


def test_allocation_rule_update_requires_matching_pool() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc:
        service.update_rule("wrong-pool", "r1", AllocationRuleUpdate(name="Renamed"))

    assert exc.value.status_code == 404


def test_allocation_rule_create_requires_existing_pool() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc:
        service.create_rule(
            "missing-pool",
            AllocationRuleCreate(name="Missing", allocation_method="equal_split"),
        )

    assert exc.value.status_code == 404


def test_benefit_weighted_allocation_reconciles_to_pool_total() -> None:
    service = _service()
    run = service.create_allocation_run(
        "p1",
        AllocationRunCreate(rule_id="r1", scenario="plan"),
        current_user=type("User", (), {"id": "u1"})(),
    )

    assert run.total_amount_plan == "400.0000"
    assert sum(float(row.allocated_plan) for row in run.allocations) == 400.0
    by_initiative = {row.initiative_id: row.allocated_plan for row in run.allocations}
    assert by_initiative["i1"] == "100.0000"
    assert by_initiative["i2"] == "300.0000"


def test_allocation_preview_reconciles_without_posting() -> None:
    service = _service()

    preview = service.preview_allocation_run(
        "p1",
        AllocationPreviewRequest(rule_id="r1", scenario="plan"),
    )

    assert preview.candidate_count == 2
    assert preview.reconciliation.reconciled is True
    assert preview.reconciliation.allocated_plan == "400.0000"
    assert sum(float(row.allocated_plan) for row in preview.allocations) == 400.0
    assert service._repo.created_allocations == []


def test_fixed_percentage_allocation_blocks_when_total_is_not_100() -> None:
    service = _service()
    service._repo.rules.append(
        {
            "id": "r_pct",
            "pool_id": "p1",
            "name": "Bad percentages",
            "allocation_method": "fixed_percentage",
            "filters": {},
            "weights": {},
            "is_active": True,
            "version": 1,
            "policy_status": "active",
            "missing_basis_behavior": "fail",
        }
    )
    service._repo.replace_rule_weights(
        "r_pct",
        [
            {"initiative_id": "i1", "percentage": "60.0000"},
            {"initiative_id": "i2", "percentage": "30.0000"},
        ],
    )

    preview = service.preview_allocation_run(
        "p1",
        AllocationPreviewRequest(rule_id="r_pct", scenario="plan"),
    )

    assert preview.reconciliation.reconciled is False
    assert any(
        exc.exception_type == "invalid_percentage_total" and exc.severity == "blocking"
        for exc in preview.exceptions
    )
    with pytest.raises(HTTPException) as exc:
        service.create_allocation_run(
            "p1",
            AllocationRunCreate(rule_id="r_pct", scenario="plan"),
            current_user=type("User", (), {"id": "u1"})(),
        )
    assert exc.value.status_code == 400


def test_manual_amount_allocation_blocks_unreconciled_total() -> None:
    service = _service()
    service._repo.rules.append(
        {
            "id": "r_manual",
            "pool_id": "p1",
            "name": "Manual shortfall",
            "allocation_method": "manual_amount",
            "filters": {},
            "weights": {},
            "is_active": True,
            "version": 1,
            "policy_status": "active",
            "missing_basis_behavior": "fail",
        }
    )
    service._repo.replace_rule_weights(
        "r_manual",
        [
            {"initiative_id": "i1", "manual_amount": "250.0000"},
            {"initiative_id": "i2", "manual_amount": "100.0000"},
        ],
    )

    preview = service.preview_allocation_run(
        "p1",
        AllocationPreviewRequest(rule_id="r_manual", scenario="plan"),
    )

    assert preview.reconciliation.reconciled is False
    assert preview.reconciliation.unallocated_plan == "50.0000"
    assert any(
        exc.exception_type == "unreconciled" and exc.severity == "blocking"
        for exc in preview.exceptions
    )
    with pytest.raises(HTTPException) as exc:
        service.create_allocation_run(
            "p1",
            AllocationRunCreate(rule_id="r_manual", scenario="plan"),
            current_user=type("User", (), {"id": "u1"})(),
        )
    assert exc.value.status_code == 400


def test_management_report_reconciles_allocated_costs() -> None:
    service = _service()
    service.create_allocation_run(
        "p1",
        AllocationRunCreate(rule_id="r1", scenario="plan"),
        current_user=type("User", (), {"id": "u1"})(),
    )
    user = type("User", (), {"id": "u1", "role": "transformation_office"})()

    report = service.management_report(user, ReportFilterParams(target_year=2026))

    assert report.value_bridge["benefits_plan"] == "400.0000"
    assert report.value_bridge["direct_costs_plan"] == "10.0000"
    assert report.value_bridge["allocated_costs_plan"] == "400.0000"
    assert report.value_bridge["net_after_allocation_plan"] == "-10.0000"
    assert report.dependency_risk.critical_path_risk == 1

    default_year_report = service.management_report(user, ReportFilterParams())
    assert default_year_report.selected_year == 2026
    assert default_year_report.available_years == [2026]
    assert any(
        item["initiative_code"] == "TRN-002" and item["initiative_name"] == "Commercial rollout"
        for item in default_year_report.needs_attention
    )


def test_allocation_year_ignores_malformed_period_metadata() -> None:
    assert ExecutiveControlService._allocation_year(
        {"shared_cost_allocation_runs": {"period_start": "not-a-date"}}
    ) is None
    assert ExecutiveControlService._allocation_year(
        {"shared_cost_pools": {"year": "bad-year"}}
    ) is None
