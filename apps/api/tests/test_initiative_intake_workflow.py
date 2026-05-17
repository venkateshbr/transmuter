from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.domain.initiative_intake import InitiativeDraft, InitiativeFieldExtractionResult
from app.domain.initiatives import InitiativeCounts, InitiativeCreate, InitiativeDetail
from app.domain.workflows import (
    InitiativeIntakeWorkflowStart,
    WorkflowApproveRequest,
    WorkflowRejectRequest,
)
from app.services import workflow as workflow_module
from app.services.workflow import WorkflowService

TENANT_ID = uuid4()
USER_ID = uuid4()


class FakeWorkflowRepository:
    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.runs: dict[str, dict] = {}
        self.audit_logs: list[dict] = []
        self.corrections: list[dict] = []

    def create_initiative_intake_run(self, submitter_user_id: UUID, raw_text: str) -> dict:
        run_id = str(uuid4())
        row = {
            "id": run_id,
            "tenant_id": str(TENANT_ID),
            "submitter_user_id": str(submitter_user_id),
            "raw_text": raw_text,
            "status": "extracting",
            "extracted_draft": {},
            "kpi_suggestions": [],
            "risk_suggestions": [],
            "created_initiative_id": None,
            "error": None,
            "expires_at": (datetime.now(UTC) + timedelta(hours=48)).isoformat(),
        }
        self.runs[run_id] = row
        return row

    def get_run(self, run_id: UUID | str) -> dict | None:
        return self.runs.get(str(run_id))

    def update_run(self, run_id: UUID | str, patch: dict) -> dict:
        self.runs[str(run_id)].update(patch)
        return self.runs[str(run_id)]

    def insert_audit_log(self, **payload: object) -> None:
        self.audit_logs.append(payload)

    def insert_correction(self, **payload: object) -> None:
        self.corrections.append(payload)


def test_initiative_intake_workflow_reaches_review(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeWorkflowRepository(None, TENANT_ID)
    monkeypatch.setattr(workflow_module, "WorkflowRepository", lambda client, tenant_id: repo)

    async def fake_extract(text: str) -> InitiativeFieldExtractionResult:
        return InitiativeFieldExtractionResult(
            trace_id="trace-1",
            confidence=0.82,
            draft=InitiativeDraft(
                name="AP automation",
                type="cost_reduction",
                priority="high",
                country="Singapore",
                value_logic="Reduce invoice cycle time",
                dependencies="ERP integration",
            ),
        )

    monkeypatch.setattr(workflow_module, "extract_initiative_fields", fake_extract)

    service = WorkflowService(SimpleNamespace(), TENANT_ID)
    created = asyncio.run(
        service.start_initiative_intake(
            InitiativeIntakeWorkflowStart(raw_text="Name: AP automation"),
            USER_ID,
        )
    )

    assert created.status == "awaiting_review"
    review = service.get_review(created.workflow_run_id)
    assert review.extracted_draft.name == "AP automation"
    assert review.field_confidence["name"] == "high"
    assert len(review.kpi_suggestions) >= 1
    assert len(review.risk_suggestions) >= 1
    assert {item["action"] for item in repo.audit_logs} == {
        "extract_fields",
        "suggest_kpis",
        "scan_risk_patterns",
    }


def test_workflow_approval_creates_initiative_and_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeWorkflowRepository(None, TENANT_ID)
    monkeypatch.setattr(workflow_module, "WorkflowRepository", lambda client, tenant_id: repo)

    run = repo.create_initiative_intake_run(USER_ID, "Name: AP automation")
    repo.update_run(
        run["id"],
        {
            "status": "awaiting_review",
            "kpi_suggestions": [
                {
                    "name": "Run-rate savings realized",
                    "type": "custom",
                    "frequency": "quarterly",
                    "unit": "USD",
                    "accepted": True,
                    "rationale": "Cost-reduction tracking",
                }
            ],
            "risk_suggestions": [
                {
                    "description": "Savings baseline may not be validated",
                    "type": "financial",
                    "impact": "medium",
                    "likelihood": "medium",
                    "mitigation": "Finance sign-off",
                    "accepted": True,
                    "rationale": "Baseline risk",
                }
            ],
        },
    )
    created_detail = _initiative_detail()

    class FakeInitiativeService:
        def __init__(self, client: object, tenant_id: UUID) -> None:
            self.client = client
            self.tenant_id = tenant_id

        def create_from_intake(self, data: object, created_by: UUID) -> InitiativeDetail:
            assert created_by == USER_ID
            assert data.suggestions.kpis[0].name == "Run-rate savings realized"
            assert data.suggestions.risks[0].description == "Savings baseline may not be validated"
            return created_detail

    monkeypatch.setattr(workflow_module, "InitiativeService", FakeInitiativeService)

    service = WorkflowService(SimpleNamespace(), TENANT_ID)
    response = service.approve(
        UUID(run["id"]),
        WorkflowApproveRequest(initiative=InitiativeCreate(name="AP automation")),
        USER_ID,
    )

    assert response.status == "approved"
    assert response.initiative.id == created_detail.id
    assert repo.runs[run["id"]]["status"] == "approved"
    assert repo.runs[run["id"]]["created_initiative_id"] == str(created_detail.id)
    assert repo.audit_logs[-1]["human_action"] == "approved"
    assert repo.corrections[-1]["correction_type"] == "field_edit"


def test_workflow_reject_marks_run_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeWorkflowRepository(None, TENANT_ID)
    monkeypatch.setattr(workflow_module, "WorkflowRepository", lambda client, tenant_id: repo)
    run = repo.create_initiative_intake_run(USER_ID, "Name: AP automation")
    repo.update_run(run["id"], {"status": "awaiting_review"})

    service = WorkflowService(SimpleNamespace(), TENANT_ID)
    response = service.reject(UUID(run["id"]), WorkflowRejectRequest(reason="Not ready"), USER_ID)

    assert response.status == "rejected"
    assert repo.runs[run["id"]]["status"] == "rejected"
    assert repo.audit_logs[-1]["human_action"] == "rejected"
    assert repo.corrections[-1]["correction_type"] == "full_reject"


def _initiative_detail() -> InitiativeDetail:
    initiative_id = uuid4()
    return InitiativeDetail(
        id=initiative_id,
        initiative_code="INIT-001",
        name="AP automation",
        workstream_id=None,
        workstream_name=None,
        owner_id=None,
        owner_name=None,
        group_owner_id=None,
        group_owner_name=None,
        type="cost_reduction",
        impact_type=None,
        theme=None,
        country=None,
        tag=None,
        priority="medium",
        rag_status="green",
        stage="scoping",
        summary=None,
        value_logic=None,
        dependencies_text=None,
        planned_start=None,
        planned_end=None,
        actual_start=None,
        actual_end=None,
        pressure_score=None,
        pressure_breakdown=None,
        counts=InitiativeCounts(),
        archived_at=None,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )
