from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.domain.financials import (
    BenefitLedgerSummaryResponse,
)
from app.main import app
from app.routers import financials as financials_router
from app.services.financial import FinancialService

client = TestClient(app, raise_server_exceptions=True)

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
INITIATIVE_ID = "init-1"


@dataclass
class FakeBenefitLedgerRepo:
    entries: list[dict[str, object]]
    initiative_ids: set[str]
    latest_plan: dict[str, object] | None = None

    def initiative_exists(self, initiative_id: str) -> bool:
        return initiative_id in self.initiative_ids

    def list_benefit_ledger_entries(self, initiative_id: str) -> list[dict[str, object]]:
        return [row for row in self.entries if row["initiative_id"] == initiative_id]

    def create_benefit_ledger_entry(self, initiative_id: str, data: dict[str, object]) -> dict[str, object]:
        row = {
            **data,
            "id": f"entry-{len(self.entries) + 1}",
            "initiative_id": initiative_id,
            "created_at": "2026-06-08T00:00:00Z",
            "updated_at": "2026-06-08T00:00:00Z",
        }
        self.entries.append(row)
        return row

    def update_benefit_ledger_entry(
        self,
        initiative_id: str,
        entry_id: str,
        data: dict[str, object],
    ) -> dict[str, object]:
        for row in self.entries:
            if row["initiative_id"] == initiative_id and row["id"] == entry_id:
                row.update(data)
                row["updated_at"] = "2026-06-08T00:00:00Z"
                return row
        return {}

    def delete_benefit_ledger_entry(self, initiative_id: str, entry_id: str) -> None:
        self.entries = [
            row for row in self.entries if not (row["initiative_id"] == initiative_id and row["id"] == entry_id)
        ]

    def get_latest_bankable_plan(self, initiative_id: str) -> dict[str, object] | None:
        if initiative_id not in self.initiative_ids:
            return None
        return self.latest_plan


@pytest.fixture()
def benefit_service() -> FinancialService:
    repo = FakeBenefitLedgerRepo(
        initiative_ids={INITIATIVE_ID},
        latest_plan={
            "id": "plan-3",
            "initiative_id": INITIATIVE_ID,
            "version": 3,
            "trigger_type": "approval",
            "trigger_submission_id": "submission-1",
            "locked_by_id": str(USER_ID),
            "locked_at": "2026-06-08T00:00:00Z",
            "locked_reason": "Approved",
            "snapshot": {"entries": [], "cost_lines": [], "metric_values": [], "selections": {"metric_keys": [], "cost_category_keys": []}, "summary": {"net_value_plan": "0.0000", "net_value_actual": None}},
        },
        entries=[
            {
                "id": "entry-1",
                "initiative_id": INITIATIVE_ID,
                "period_granularity": "weekly",
                "period_start": date(2026, 1, 5),
                "period_end": date(2026, 1, 11),
                "bankable_plan_amount": "100.0000",
                "actual_amount": "120.0000",
                "description": "Week 1",
                "created_at": "2026-06-08T00:00:00Z",
                "updated_at": "2026-06-08T00:00:00Z",
            },
            {
                "id": "entry-2",
                "initiative_id": INITIATIVE_ID,
                "period_granularity": "weekly",
                "period_start": date(2026, 1, 12),
                "period_end": date(2026, 1, 18),
                "bankable_plan_amount": "50.0000",
                "actual_amount": "25.0000",
                "description": "Week 2",
                "created_at": "2026-06-08T00:00:00Z",
                "updated_at": "2026-06-08T00:00:00Z",
            },
            {
                "id": "entry-3",
                "initiative_id": INITIATIVE_ID,
                "period_granularity": "weekly",
                "period_start": date(2026, 2, 2),
                "period_end": date(2026, 2, 8),
                "bankable_plan_amount": "75.0000",
                "actual_amount": "90.0000",
                "description": "Week 3",
                "created_at": "2026-06-08T00:00:00Z",
                "updated_at": "2026-06-08T00:00:00Z",
            },
        ],
    )
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = repo
    service._tenant_id = TENANT_ID
    service._ensure_tenant_initiative = lambda initiative_id: None
    return service


def test_benefit_ledger_summary_rolls_up_weekly_monthly_and_yearly(benefit_service: FinancialService) -> None:
    weekly = benefit_service.get_benefit_ledger_summary(INITIATIVE_ID, "weekly")
    assert isinstance(weekly, BenefitLedgerSummaryResponse)
    assert [period.period for period in weekly.periods] == ["2026-W02", "2026-W03", "2026-W06"]
    assert weekly.bankable_plan_amount == "225.0000"
    assert weekly.actual_amount == "235.0000"
    assert weekly.variance == "10.0000"
    assert weekly.periods[0].variance == "20.0000"

    monthly = benefit_service.get_benefit_ledger_summary(INITIATIVE_ID, "monthly")
    assert [period.period for period in monthly.periods] == ["2026-M01", "2026-M02"]
    assert monthly.periods[0].bankable_plan_amount == "150.0000"
    assert monthly.periods[0].actual_amount == "145.0000"
    assert monthly.periods[0].variance == "-5.0000"

    yearly = benefit_service.get_benefit_ledger_summary(INITIATIVE_ID, "yearly")
    assert len(yearly.periods) == 1
    assert yearly.periods[0].period == "2026"
    assert yearly.periods[0].bankable_plan_amount == "225.0000"
    assert yearly.periods[0].actual_amount == "235.0000"
    assert yearly.periods[0].variance == "10.0000"
    assert yearly.locked_bankable_plan_version == 3


def test_benefit_ledger_empty_summary_returns_zeroed_response() -> None:
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._tenant_id = TENANT_ID
    service._repo = FakeBenefitLedgerRepo(initiative_ids={INITIATIVE_ID}, latest_plan=None, entries=[])
    service._ensure_tenant_initiative = lambda initiative_id: None

    summary = service.get_benefit_ledger_summary(INITIATIVE_ID, "monthly")
    assert isinstance(summary, BenefitLedgerSummaryResponse)
    assert summary.periods == []
    assert summary.bankable_plan_amount == "0.0000"
    assert summary.actual_amount == "0.0000"
    assert summary.variance == "0.0000"
    assert summary.locked_bankable_plan_version is None


def test_benefit_ledger_entry_crud_routes(monkeypatch: pytest.MonkeyPatch, benefit_service: FinancialService) -> None:
    tenant_user = CurrentUser(
        id=USER_ID,
        tenant_id=TENANT_ID,
        role="transformation_office",
        status="active",
    )

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: tenant_user
    app.dependency_overrides[get_supabase_request_client] = lambda: object()
    app.dependency_overrides[financials_router._svc] = lambda: benefit_service
    monkeypatch.setattr(financials_router, "assert_can_view_initiative", lambda *args, **kwargs: None)
    monkeypatch.setattr(financials_router, "assert_can_manage_initiatives", lambda *args, **kwargs: None)

    try:
        create_resp = client.post(
            f"/initiatives/{INITIATIVE_ID}/benefit-ledger",
            json={
                "period_granularity": "monthly",
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
                "bankable_plan_amount": "200.0000",
                "actual_amount": "250.0000",
                "description": "March realization",
            },
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["variance"] == "50.0000"

        list_resp = client.get(f"/initiatives/{INITIATIVE_ID}/benefit-ledger")
        assert list_resp.status_code == 200
        assert any(row["id"] == created["id"] for row in list_resp.json())

        update_resp = client.put(
            f"/initiatives/{INITIATIVE_ID}/benefit-ledger/{created['id']}",
            json={"actual_amount": "260.0000"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["variance"] == "60.0000"

        summary_resp = client.get(
            f"/initiatives/{INITIATIVE_ID}/benefit-ledger/summary?granularity=monthly",
        )
        assert summary_resp.status_code == 200
        assert summary_resp.json()["locked_bankable_plan_version"] == 3

        delete_resp = client.delete(
            f"/initiatives/{INITIATIVE_ID}/benefit-ledger/{created['id']}",
        )
        assert delete_resp.status_code == 204
    finally:
        app.dependency_overrides.clear()
