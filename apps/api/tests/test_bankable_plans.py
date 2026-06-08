from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.domain.financials import (
    BankablePlanResponse,
    BankablePlanSnapshot,
    CostLineItem,
    FinancialEntryRow,
    FinancialMetricValueRow,
    FinancialSummary,
    InitiativeFinancialSelections,
)
from app.domain.governance import GateDecisionPatch
from app.main import app
from app.routers import financials as financials_router
from app.services.financial import FinancialService
from app.services.governance import GovernanceService

client = TestClient(app, raise_server_exceptions=True)

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
INITIATIVE_ID = "init-1"
SUBMISSION_ID = "submission-1"


class FakePlanRepo:
    def __init__(self) -> None:
        self.plans: list[dict[str, object]] = []
        self.initiative_ids = {INITIATIVE_ID}

    def initiative_exists(self, initiative_id: str) -> bool:
        return initiative_id in self.initiative_ids

    def get_latest_bankable_plan(self, initiative_id: str) -> dict | None:
        plans = [plan for plan in self.plans if plan["initiative_id"] == initiative_id]
        return sorted(plans, key=lambda row: int(row["version"]))[-1] if plans else None

    def list_bankable_plans(self, initiative_id: str) -> list[dict]:
        return sorted(
            [plan for plan in self.plans if plan["initiative_id"] == initiative_id],
            key=lambda row: int(row["version"]),
        )

    def create_bankable_plan(self, data: dict) -> dict:
        row = {**data, "id": data.get("id", f"plan-{len(self.plans) + 1}")}
        self.plans.append(row)
        return row

    # Unused by the tests, but present so FinancialService helpers can be attached safely.
    def get_entries(self, _initiative_id: str) -> list[dict]:
        return []

    def list_cost_lines(self, _initiative_id: str) -> list[dict]:
        return []

    def list_metric_values(self, _initiative_id: str) -> list[dict]:
        return []

    def list_financial_selections(self, _initiative_id: str) -> list[dict]:
        return []

    def list_config_groups(self) -> list[dict]:
        return []

    def list_config_items(self) -> list[dict]:
        return []


class FakeGovernanceRepo:
    def __init__(self) -> None:
        self.stage = "scoping"
        self.submissions = {
            SUBMISSION_ID: {
                "id": SUBMISSION_ID,
                "tenant_id": str(TENANT_ID),
                "initiative_id": INITIATIVE_ID,
                "gate_number": 1,
                "submitted_by_id": str(USER_ID),
                "submitted_at": "2026-06-08T00:00:00Z",
                "decision": "pending",
                "decided_by_id": None,
                "decided_at": None,
                "commentary": None,
                "criteria_snapshot": [{"id": "c1", "label": "Plan"}],
                "submitter": {"display_name": "Requester"},
                "decider": None,
            }
        }

    def list_submissions(self, _initiative_id: str) -> list[dict]:
        return list(self.submissions.values())

    def get_submission(self, submission_id: str) -> dict | None:
        row = self.submissions.get(submission_id)
        if not row:
            return None
        return {
            **row,
            "submitter": {"display_name": "Requester"},
            "decider": {"display_name": "Approver"} if row.get("decided_by_id") else None,
        }

    def update_submission(self, submission_id: str, data: dict) -> dict:
        row = self.submissions[submission_id]
        row.update(data)
        row["decided_by_id"] = data.get("decided_by_id")
        row["decided_at"] = data.get("decided_at")
        row["decision"] = data.get("decision", row["decision"])
        row["commentary"] = data.get("commentary")
        return self.get_submission(submission_id) or row

    def get_gate(self, initiative_id: str, gate_number: int) -> dict | None:
        if initiative_id == INITIATIVE_ID and gate_number == 1:
            return {
                "id": "gate-1",
                "initiative_id": INITIATIVE_ID,
                "gate_number": 1,
                "label": "Plan approval",
                "from_stage": "scoping",
                "to_stage": "in_progress",
            }
        return None

    def update_initiative_stage(self, _initiative_id: str, stage: str) -> None:
        self.stage = stage


class FakeAuditRepo:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def log_change(self, **kwargs: object) -> None:
        self.events.append(kwargs)


class FakeFinancialLockService:
    calls: list[dict[str, object]] = []

    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.client = client
        self.tenant_id = tenant_id

    def lock_bankable_plan_from_approval(
        self,
        initiative_id: str,
        submission_id: str,
        locked_by_id: str,
        locked_reason: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "initiative_id": initiative_id,
                "submission_id": submission_id,
                "locked_by_id": locked_by_id,
                "locked_reason": locked_reason,
                "tenant_id": self.tenant_id,
            }
        )


@pytest.fixture()
def bankable_snapshot() -> BankablePlanSnapshot:
    return BankablePlanSnapshot(
        entries=[
            FinancialEntryRow(
                year=2026,
                quarter=1,
                revenue_uplift_base="100.0000",
                revenue_uplift_high="120.0000",
                gross_margin_base="80.0000",
                gross_margin_high="90.0000",
                gm_uplift_base="80.0000",
                gm_uplift_high="90.0000",
                cogs_base="20.0000",
                cogs_high="30.0000",
            )
        ],
        cost_lines=[
            CostLineItem(
                id="cost-1",
                initiative_id=INITIATIVE_ID,
                name="Software",
                category_key="software",
                year=2026,
                quarter=1,
                amount_plan="12.0000",
                amount_actual=None,
                is_recurring=True,
            )
        ],
        metric_values=[
            FinancialMetricValueRow(
                metric_key="cost_savings",
                year=2026,
                quarter=1,
                value_base="5.0000",
                value_high="7.0000",
                value_actual=None,
            )
        ],
        selections=InitiativeFinancialSelections(
            metric_keys=["cost_savings"],
            cost_category_keys=["software"],
        ),
        summary=FinancialSummary(net_value_plan="42.0000", net_value_actual=None),
    )


@pytest.fixture()
def bankable_service(bankable_snapshot: BankablePlanSnapshot) -> FinancialService:
    repo = FakePlanRepo()
    service = cast(Any, FinancialService.__new__(FinancialService))
    service._repo = repo
    service._tenant_id = TENANT_ID
    service._ensure_tenant_initiative = lambda initiative_id: None
    service._build_bankable_plan_snapshot = lambda initiative_id: bankable_snapshot
    return service


@pytest.fixture()
def governance_service() -> GovernanceService:
    service = cast(Any, GovernanceService.__new__(GovernanceService))
    service._client = object()
    service._repo = FakeGovernanceRepo()
    service._audit = FakeAuditRepo()
    service._tenant_id = TENANT_ID
    service._user_id = str(USER_ID)
    return service


def test_approval_locks_bankable_plan_and_rebaseline_versions_history(bankable_service: FinancialService) -> None:
    first = bankable_service.lock_bankable_plan_from_approval(
        INITIATIVE_ID,
        SUBMISSION_ID,
        str(USER_ID),
        locked_reason="Approved by governance",
    )
    assert first.version == 1
    assert first.trigger_type == "approval"
    assert first.trigger_submission_id == SUBMISSION_ID
    assert first.locked_reason == "Approved by governance"
    assert first.snapshot.summary.net_value_plan == "42.0000"

    duplicate = bankable_service.lock_bankable_plan_from_approval(
        INITIATIVE_ID,
        SUBMISSION_ID,
        str(USER_ID),
        locked_reason="Approved by governance",
    )
    assert duplicate.id == first.id
    assert len(cast(Any, bankable_service._repo).plans) == 1

    second = bankable_service.rebaseline_bankable_plan(
        INITIATIVE_ID,
        str(USER_ID),
        reason="Annual refresh",
    )
    assert second.version == 2
    assert second.trigger_type == "rebaseline"
    assert second.locked_reason == "Annual refresh"

    history_response = bankable_service.get_bankable_plan_history(INITIATIVE_ID)
    assert isinstance(history_response, BankablePlanResponse)
    assert history_response.current is not None
    assert history_response.current.version == 2
    assert [plan.version for plan in history_response.history] == [1, 2]


def test_governance_approval_creates_bankable_plan_lock(monkeypatch: pytest.MonkeyPatch, governance_service: GovernanceService) -> None:
    FakeFinancialLockService.calls = []
    monkeypatch.setattr("app.services.governance.FinancialService", FakeFinancialLockService)

    submission = governance_service.record_decision(
        SUBMISSION_ID,
        GateDecisionPatch(decision="approved", commentary="Looks good"),
    )

    assert submission.decision == "approved"
    assert governance_service._repo.stage == "in_progress"
    assert FakeFinancialLockService.calls == [
        {
            "initiative_id": INITIATIVE_ID,
            "submission_id": SUBMISSION_ID,
            "locked_by_id": str(USER_ID),
            "locked_reason": "Looks good",
            "tenant_id": TENANT_ID,
        }
    ]


def test_bankable_plan_routes_expose_current_history_and_rebaseline(
    monkeypatch: pytest.MonkeyPatch,
    bankable_service: FinancialService,
) -> None:
    tenant_user = CurrentUser(
        id=USER_ID,
        tenant_id=TENANT_ID,
        role="transformation_office",
        status="active",
    )

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: tenant_user
    app.dependency_overrides[get_supabase_request_client] = lambda: object()
    app.dependency_overrides[financials_router._svc] = lambda: bankable_service
    monkeypatch.setattr(financials_router, "assert_can_view_initiative", lambda *args, **kwargs: None)
    monkeypatch.setattr(financials_router, "assert_can_manage_initiatives", lambda *args, **kwargs: None)

    try:
        lock_resp = client.post(
            f"/initiatives/{INITIATIVE_ID}/bankable-plan/rebaseline",
            json={"reason": "Refresh"},
        )
        assert lock_resp.status_code == 404

        bankable_service.lock_bankable_plan_from_approval(
            INITIATIVE_ID,
            SUBMISSION_ID,
            str(USER_ID),
            locked_reason="Approved by governance",
        )

        current_resp = client.get(f"/initiatives/{INITIATIVE_ID}/bankable-plan")
        assert current_resp.status_code == 200
        current_data = current_resp.json()
        assert current_data["current"]["version"] == 1
        assert current_data["history"] == [current_data["current"]]

        history_resp = client.get(f"/initiatives/{INITIATIVE_ID}/bankable-plan/history")
        assert history_resp.status_code == 200
        assert [row["version"] for row in history_resp.json()] == [1]

        rebaseline_resp = client.post(
            f"/initiatives/{INITIATIVE_ID}/bankable-plan/rebaseline",
            json={"reason": "Refresh"},
        )
        assert rebaseline_resp.status_code == 200
        assert rebaseline_resp.json()["version"] == 2

        current_after_resp = client.get(f"/initiatives/{INITIATIVE_ID}/bankable-plan")
        assert current_after_resp.status_code == 200
        assert current_after_resp.json()["current"]["version"] == 2
        assert [row["version"] for row in current_after_resp.json()["history"]] == [1, 2]
    finally:
        app.dependency_overrides.clear()
