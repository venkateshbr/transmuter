from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.services import initiative_context as context_module
from app.services.initiative_context import InitiativeContextService

TENANT_ID = uuid4()


class FakeInitiativeContextRepository:
    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.client = client
        self.tenant_id = tenant_id

    def get_initiative(self, initiative_id: str) -> dict:
        return {"id": initiative_id, "name": "AP automation", "rag_status": "amber"}

    def list_milestones(self, initiative_id: str) -> list[dict]:
        return [
            {
                "name": "Baseline complete",
                "status": "complete",
                "actual_end": "2026-05-10",
                "planned_end": "2026-05-11",
            },
            {
                "name": "ERP integration",
                "status": "in_progress",
                "planned_end": "2026-05-12",
            },
            {
                "name": "Future rollout",
                "status": "not_started",
                "planned_end": "2026-08-01",
            },
        ]

    def list_kpis(self, initiative_id: str) -> list[dict]:
        return [{"id": "kpi-1", "name": "Cycle time reduction"}]

    def list_kpi_entries(self, kpi_ids: list[str]) -> list[dict]:
        return [
            {
                "kpi_id": "kpi-1",
                "year": 2026,
                "quarter": 1,
                "value_base": "10.0000",
                "value_actual": "8.0000",
            },
            {
                "kpi_id": "kpi-1",
                "year": 2026,
                "quarter": 2,
                "value_base": "12.0000",
                "value_actual": "13.0000",
            },
        ]

    def list_risks(self, initiative_id: str) -> list[dict]:
        return [
            {
                "description": "ERP dependency may slip",
                "status": "open",
                "rating": "high",
                "created_at": "2026-05-14T00:00:00+00:00",
            },
            {
                "description": "Change fatigue",
                "status": "open",
                "impact": "medium",
                "created_at": "2026-04-01T00:00:00+00:00",
            },
            {
                "description": "Closed legacy risk",
                "status": "closed",
                "rating": "high",
                "created_at": "2026-05-15T00:00:00+00:00",
            },
        ]

    def list_financial_entries(self, initiative_id: str) -> list[dict]:
        return [
            {
                "year": 2026,
                "quarter": 2,
                "revenue_uplift_base": "100.1250",
                "revenue_uplift_actual": "90.5000",
            },
            {
                "year": 2026,
                "quarter": 3,
                "revenue_uplift_base": "999.0000",
                "revenue_uplift_actual": "999.0000",
            },
        ]

    def list_cost_lines(self, initiative_id: str) -> list[dict]:
        return [
            {"year": 2026, "quarter": 2, "amount_plan": "10.1250", "amount_actual": "8.0000"},
            {"year": 2026, "quarter": 1, "amount_plan": "999.0000", "amount_actual": "999.0000"},
        ]

    def get_last_status_update(self, initiative_id: str) -> dict:
        return {
            "rag_status": "amber",
            "submitted_at": "2026-05-16T01:00:00+00:00",
            "summary": "ERP integration is delayed.",
        }


def test_initiative_context_pull_summarises_period_and_money(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        context_module,
        "InitiativeContextRepository",
        FakeInitiativeContextRepository,
    )

    result = InitiativeContextService(SimpleNamespace(), TENANT_ID).pull_context(
        "init-1",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
    )

    assert result.milestones_summary.total == 3
    assert result.milestones_summary.complete == 1
    assert result.milestones_summary.at_risk == 1
    assert result.milestones_summary.completed_this_period[0].name == "Baseline complete"
    assert result.kpis_summary.kpis[0].target_base == "12.0000"
    assert result.kpis_summary.kpis[0].latest_actual == "13.0000"
    assert result.kpis_summary.kpis[0].on_track is True
    assert result.risks_summary.open_high == 1
    assert result.risks_summary.open_medium == 1
    assert [item.description for item in result.risks_summary.new_this_period] == [
        "ERP dependency may slip",
        "Closed legacy risk",
    ]
    assert result.financials_summary.revenue_plan == "100.1250"
    assert result.financials_summary.revenue_actual == "90.5000"
    assert result.financials_summary.costs_plan == "10.1250"
    assert result.financials_summary.costs_actual == "8.0000"
    assert result.last_update and result.last_update.rag_status == "amber"


def test_initiative_context_pull_rejects_invalid_period(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        context_module,
        "InitiativeContextRepository",
        FakeInitiativeContextRepository,
    )

    with pytest.raises(HTTPException):
        InitiativeContextService(SimpleNamespace(), TENANT_ID).pull_context(
            "init-1",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 5, 31),
        )
