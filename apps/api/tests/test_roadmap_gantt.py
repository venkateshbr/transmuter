"""Roadmap Gantt service and contract tests."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.domain.milestones import DependencyCreate
from app.services.milestone import MilestoneService


class RoadmapRepositoryStub:
    def list_roadmap(self) -> list[dict]:  # type: ignore[type-arg]
        return [
            {
                "id": "m-1",
                "initiative_id": "i-1",
                "name": "Design approval",
                "priority": "high",
                "status": "complete",
                "sort_order": 1,
                "planned_start": "2026-01-10",
                "planned_end": "2026-02-20",
                "pressure_score": "0.0",
                "initiatives": {
                    "id": "i-1",
                    "name": "ERP modernisation",
                    "initiative_code": "ERP-01",
                    "workstream_id": "w-1",
                    "workstreams": {"id": "w-1", "name": "Technology"},
                },
                "users": {"display_name": "Delivery Lead"},
            },
            {
                "id": "m-2",
                "initiative_id": "i-1",
                "name": "Pilot launch",
                "priority": "medium",
                "status": "in_progress",
                "sort_order": 2,
                "planned_start": "2026-03-01",
                "planned_end": "2026-06-30",
                "pressure_score": "4.0",
                "initiatives": {
                    "id": "i-1",
                    "name": "ERP modernisation",
                    "initiative_code": "ERP-01",
                    "workstream_id": "w-1",
                    "workstreams": {"id": "w-1", "name": "Technology"},
                },
                "users": None,
            },
        ]

    def list_all_dependencies(self) -> list[dict]:  # type: ignore[type-arg]
        return [
            {
                "id": "d-1",
                "dependency_type": "finish_to_start",
                "lag_days": 5,
                "upstream": {
                    "id": "m-1",
                    "name": "Design approval",
                    "status": "complete",
                    "planned_end": "2026-02-20",
                    "pressure_score": "0.0",
                    "initiatives": {"initiative_code": "ERP-01"},
                },
                "downstream": {
                    "id": "m-2",
                    "name": "Pilot launch",
                    "status": "in_progress",
                    "initiatives": {"initiative_code": "ERP-01"},
                },
            }
        ]


def roadmap_service() -> MilestoneService:
    service = MilestoneService.__new__(MilestoneService)
    service._repo = RoadmapRepositoryStub()  # type: ignore[assignment]
    service._tenant_id = uuid4()
    service._user_id = None
    return service


def test_portfolio_roadmap_has_full_range_and_typed_dependency() -> None:
    response = roadmap_service().get_portfolio_roadmap()

    assert response.range.earliest_start == "2026-01-10"
    assert response.range.latest_end == "2026-06-30"
    assert response.stats.milestones == 2
    assert response.stats.initiatives == 1
    assert response.dependencies[0].dependency_type == "finish_to_start"
    assert response.dependencies[0].lag_days == 5
    assert response.milestones[0].workstream_name == "Technology"
    assert response.milestones[0].dependency_count == 1


def test_dependency_contract_defaults_and_bounds() -> None:
    dependency = DependencyCreate(upstream_milestone_id="m-1")
    assert dependency.dependency_type == "finish_to_start"
    assert dependency.lag_days == 0

    with pytest.raises(ValidationError):
        DependencyCreate(upstream_milestone_id="m-1", lag_days=3651)


def test_dependency_creation_rejects_an_upstream_outside_tenant_scope() -> None:
    class TenantBoundaryRepository:
        def get(self, milestone_id: str) -> dict | None:  # type: ignore[type-arg]
            if milestone_id == "downstream-in-tenant":
                return {"id": milestone_id, "initiative_id": "i-1"}
            return None

    service = MilestoneService.__new__(MilestoneService)
    service._repo = TenantBoundaryRepository()  # type: ignore[assignment]
    service._tenant_id = uuid4()
    service._user_id = None

    with pytest.raises(HTTPException) as error:
        service.add_dependency(
            "downstream-in-tenant",
            DependencyCreate(upstream_milestone_id="milestone-in-another-tenant"),
        )

    assert error.value.status_code == 404
