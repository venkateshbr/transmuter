from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.domain.financials import (
    AnnualBaselineMetricValueRow,
    BankablePlanResponse,
    BankablePlanSnapshot,
    BenefitLedgerEntryCreate,
    CostLineItem,
    FinancialEntryRow,
    FinancialMetricValueRow,
    FinancialSummary,
    InitiativeFinancialSelections,
    TenantAnnualBaselineResponse,
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
REBASELINE_SUBMISSION_ID = "submission-rebaseline-1"


class FakePlanRepo:
    def __init__(self) -> None:
        self.plans: list[dict[str, object]] = []
        self.ledger_rows: list[dict[str, object]] = []
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

    def initiatives_by_code(self) -> dict[str, dict]:
        return {
            "ENT-001": {
                "id": INITIATIVE_ID,
                "initiative_code": "ENT-001",
                "name": "Test initiative",
            }
        }

    def list_benefit_ledger_entries(self, initiative_id: str) -> list[dict]:
        return [row for row in self.ledger_rows if row.get("initiative_id") == initiative_id]

    def create_benefit_ledger_entry(self, initiative_id: str, data: dict) -> dict:
        row = {
            **data,
            "id": data.get("id") or f"ledger-{len(self.ledger_rows) + 1}",
            "initiative_id": initiative_id,
            "created_at": data.get("created_at") or "2026-06-18T00:00:00Z",
            "updated_at": data.get("updated_at") or "2026-06-18T00:00:00Z",
        }
        self.ledger_rows.append(row)
        return row

    def update_benefit_ledger_entry(self, initiative_id: str, entry_id: str, data: dict) -> dict:
        for row in self.ledger_rows:
            if row.get("initiative_id") == initiative_id and row.get("id") == entry_id:
                row.update(data)
                row["updated_at"] = "2026-06-18T00:00:00Z"
                return row
        return {}

    def upsert_benefit_ledger_entry(self, initiative_id: str, data: dict) -> tuple[dict, bool]:
        for row in self.ledger_rows:
            if (
                row.get("initiative_id") == initiative_id
                and row.get("period_granularity") == data.get("period_granularity")
                and row.get("period_start") == data.get("period_start")
            ):
                row.update(data)
                row["updated_at"] = "2026-06-18T00:00:00Z"
                return row, False
        return self.create_benefit_ledger_entry(initiative_id, data), True

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
                "submission_type": "stage_gate",
                "decided_by_id": None,
                "decided_at": None,
                "commentary": None,
                "criteria_snapshot": [{"id": "c1", "label": "Plan"}],
                "requested_bankable_plan_version": None,
                "requested_snapshot": None,
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

    def create_submission(self, data: dict) -> dict:
        row = {
            **data,
            "id": data.get("id") or f"submission-{len(self.submissions) + 1}",
            "tenant_id": str(TENANT_ID),
            "submitter": {"display_name": "Requester"},
            "decider": None,
        }
        self.submissions[row["id"]] = row
        return self.get_submission(row["id"]) or row

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

    def get_gate_definition(self, gate_number: int) -> dict | None:
        if gate_number == 1:
            return {
                "id": "gate-definition-1",
                "gate_number": 1,
                "approver_roles": ["transformation_office"],
                "is_active": True,
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
    rebaseline_calls: list[dict[str, object]] = []

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

    def rebaseline_bankable_plan(
        self,
        initiative_id: str,
        locked_by_id: str,
        reason: str | None = None,
        trigger_submission_id: str | None = None,
    ) -> None:
        self.rebaseline_calls.append(
            {
                "initiative_id": initiative_id,
                "locked_by_id": locked_by_id,
                "reason": reason,
                "trigger_submission_id": trigger_submission_id,
                "tenant_id": self.tenant_id,
            }
        )


class FakeGovernedRebaselineService:
    def submit_bankable_plan_rebaseline(self, initiative_id: str, reason: str) -> dict[str, object]:
        return {
            "id": REBASELINE_SUBMISSION_ID,
            "initiative_id": initiative_id,
            "gate_number": 1,
            "submission_type": "bankable_plan_rebaseline",
            "submitted_by_id": str(USER_ID),
            "submitted_by_name": "Requester",
            "submitted_at": "2026-06-22T00:00:00Z",
            "decision": "pending",
            "decided_by_id": None,
            "decided_by_name": None,
            "decided_at": None,
            "commentary": reason,
            "criteria_snapshot": [{"criterion_id": "rebaseline-reason", "label": "Reason"}],
            "requested_bankable_plan_version": 2,
            "requested_snapshot": {"summary": {"net_value_plan": "42.0000"}},
        }


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
    service._user_role = "transformation_office"
    return service


def test_approval_locks_bankable_plan_and_rebaseline_versions_history(
    bankable_service: FinancialService,
) -> None:
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


def test_governance_approval_creates_bankable_plan_lock(
    monkeypatch: pytest.MonkeyPatch, governance_service: GovernanceService
) -> None:
    FakeFinancialLockService.calls = []
    FakeFinancialLockService.rebaseline_calls = []
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
    assert FakeFinancialLockService.rebaseline_calls == []


def test_governance_approval_creates_rebaseline_without_stage_transition(
    monkeypatch: pytest.MonkeyPatch, governance_service: GovernanceService
) -> None:
    FakeFinancialLockService.calls = []
    FakeFinancialLockService.rebaseline_calls = []
    monkeypatch.setattr("app.services.governance.FinancialService", FakeFinancialLockService)
    repo = cast(Any, governance_service._repo)
    repo.submissions[REBASELINE_SUBMISSION_ID] = {
        "id": REBASELINE_SUBMISSION_ID,
        "tenant_id": str(TENANT_ID),
        "initiative_id": INITIATIVE_ID,
        "gate_number": 1,
        "submission_type": "bankable_plan_rebaseline",
        "submitted_by_id": str(USER_ID),
        "submitted_at": "2026-06-22T00:00:00Z",
        "decision": "pending",
        "decided_by_id": None,
        "decided_at": None,
        "commentary": "Annual baseline refresh",
        "criteria_snapshot": [{"id": "rebaseline-reason", "label": "Reason"}],
        "requested_bankable_plan_version": 2,
        "requested_snapshot": {"summary": {"net_value_plan": "42.0000"}},
    }

    submission = governance_service.record_decision(
        REBASELINE_SUBMISSION_ID,
        GateDecisionPatch(decision="approved", commentary="Approved rebaseline"),
    )

    assert submission.decision == "approved"
    assert submission.submission_type == "bankable_plan_rebaseline"
    assert repo.stage == "scoping"
    assert FakeFinancialLockService.calls == []
    assert FakeFinancialLockService.rebaseline_calls == [
        {
            "initiative_id": INITIATIVE_ID,
            "locked_by_id": str(USER_ID),
            "reason": "Approved rebaseline",
            "trigger_submission_id": REBASELINE_SUBMISSION_ID,
            "tenant_id": TENANT_ID,
        }
    ]


def test_benefit_ledger_create_derives_bankable_amount(
    bankable_service: FinancialService,
) -> None:
    bankable_service.lock_bankable_plan_from_approval(
        INITIATIVE_ID,
        SUBMISSION_ID,
        str(USER_ID),
        locked_reason="Approved",
    )

    row = bankable_service.create_benefit_ledger_entry(
        INITIATIVE_ID,
        BenefitLedgerEntryCreate(
            period_granularity="yearly",
            period_start="2026-01-01",
            period_end="2026-12-31",
            actual_amount="40.0000",
            description="Actual benefit",
        ),
    )

    assert row.bankable_plan_amount == "68.0000"
    assert row.actual_amount == "40.0000"
    assert row.variance == "-28.0000"


def test_benefit_ledger_csv_import_maps_code_and_upserts(
    bankable_service: FinancialService,
) -> None:
    bankable_service.lock_bankable_plan_from_approval(
        INITIATIVE_ID,
        SUBMISSION_ID,
        str(USER_ID),
        locked_reason="Approved",
    )

    first = bankable_service.import_benefit_ledger_csv(
        b"initiative_code,period_granularity,period_start,period_end,actual_amount,description\n"
        b"ENT-001,monthly,2026-01-01,2026-01-31,3.0000,January actual\n"
    )
    second = bankable_service.import_benefit_ledger_csv(
        b"initiative_code,period_granularity,period_start,period_end,actual_amount,description\n"
        b"ENT-001,monthly,2026-01-01,2026-01-31,4.0000,January revised\n"
    )

    rows = cast(Any, bankable_service._repo).ledger_rows
    assert first.created == 1
    assert first.updated == 0
    assert second.created == 0
    assert second.updated == 1
    assert second.errors == []
    assert len(rows) == 1
    assert rows[0]["bankable_plan_amount"] == "3.5000"
    assert rows[0]["actual_amount"] == "4.0000"
    assert rows[0]["description"] == "January revised"


def test_bankable_plan_routes_expose_current_history_and_rebaseline_request(
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
    app.dependency_overrides[financials_router._governance_svc] = (
        lambda: FakeGovernedRebaselineService()
    )
    monkeypatch.setattr(
        financials_router, "assert_can_view_initiative", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        financials_router, "assert_can_manage_initiatives", lambda *args, **kwargs: None
    )

    try:
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
            json={"reason": "Refresh annual baseline assumptions"},
        )
        assert rebaseline_resp.status_code == 200
        rebaseline_data = rebaseline_resp.json()
        assert rebaseline_data["submission_type"] == "bankable_plan_rebaseline"
        assert rebaseline_data["decision"] == "pending"
        assert rebaseline_data["requested_bankable_plan_version"] == 2

        current_after_resp = client.get(f"/initiatives/{INITIATIVE_ID}/bankable-plan")
        assert current_after_resp.status_code == 200
        assert current_after_resp.json()["current"]["version"] == 1
        assert [row["version"] for row in current_after_resp.json()["history"]] == [1]
    finally:
        app.dependency_overrides.clear()


def test_readonly_annual_baseline_route_allows_portfolio_viewers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_user = CurrentUser(
        id=USER_ID,
        tenant_id=TENANT_ID,
        role="viewer",
        status="active",
    )

    class FakeBaselineService:
        def get_tenant_annual_baselines(
            self,
            baseline_year: int | None = None,
        ) -> TenantAnnualBaselineResponse:
            assert baseline_year == 2026
            return TenantAnnualBaselineResponse(
                values=[
                    AnnualBaselineMetricValueRow(
                        id="baseline-revenue",
                        metric_definition_id="metric-revenue",
                        metric_key="annual_revenue_baseline",
                        metric_label="Annual Revenue Baseline",
                        baseline_year=2026,
                        value="20000000.0000",
                    )
                ]
            )

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: tenant_user
    app.dependency_overrides[financials_router._svc] = lambda: FakeBaselineService()
    monkeypatch.setattr(
        financials_router, "assert_can_view_portfolio", lambda *args, **kwargs: None
    )

    try:
        response = client.get("/financial-engine/annual-baselines?baseline_year=2026")
        assert response.status_code == 200
        assert response.json()["values"][0]["metric_key"] == "annual_revenue_baseline"
        assert response.json()["values"][0]["value"] == "20000000.0000"
    finally:
        app.dependency_overrides.clear()
