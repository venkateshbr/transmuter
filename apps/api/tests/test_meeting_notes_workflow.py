from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.core.config import settings
from app.domain.meeting_notes import MeetingTranscriptUpload
from app.domain.workflows import WorkflowApproveRequest
from app.services import workflow as workflow_module
from app.services.workflow import WorkflowService

TENANT_ID = uuid4()
USER_ID = uuid4()


@pytest.fixture(autouse=True)
def disable_langfuse_for_workflow_unit_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_enabled", False)


class FakeWorkflowRepository:
    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.runs: dict[str, dict] = {}
        self.audit_logs: list[dict] = []
        self.corrections: list[dict] = []

    def create_meeting_notes_run(
        self,
        *,
        meeting_id: str,
        session_id: str,
        submitter_user_id: UUID,
        transcript_text: str,
    ) -> dict:
        run_id = str(uuid4())
        row = {
            "id": run_id,
            "tenant_id": str(TENANT_ID),
            "meeting_id": meeting_id,
            "session_id": session_id,
            "submitter_user_id": str(submitter_user_id),
            "transcript_text": transcript_text,
            "status": "chunking",
            "chunks": [],
            "action_items": [],
            "decisions": [],
            "initiative_updates": [],
            "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        }
        self.runs[run_id] = row
        return row

    def get_run(self, run_id: UUID | str) -> dict | None:
        return None

    def get_meeting_notes_run(self, run_id: UUID | str) -> dict | None:
        return self.runs.get(str(run_id))

    def update_meeting_notes_run(self, run_id: UUID | str, patch: dict) -> dict:
        self.runs[str(run_id)].update(patch)
        return self.runs[str(run_id)]

    def insert_audit_log(self, **payload: object) -> None:
        self.audit_logs.append(payload)

    def insert_correction(self, **payload: object) -> None:
        self.corrections.append(payload)


class FakeMeetingService:
    sessions: dict[str, dict] = {}
    action_items: list[dict] = []

    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.client = client
        self.tenant_id = tenant_id

    def get_session_for_meeting(self, meeting_id: str, session_id: str) -> dict:
        return self.sessions[session_id]

    def get_session_detail(self, session_id: str) -> dict:
        return self.sessions[session_id]

    def update_session(self, session_id: str, data: object) -> dict:
        patch = data.model_dump(exclude_none=True)
        self.sessions[session_id].update(patch)
        return self.sessions[session_id]

    def create_action_item(self, session_id: str, data: object) -> dict:
        payload = data.model_dump(exclude_none=True)
        item = {"id": str(uuid4()), "session_id": session_id, **payload}
        self.action_items.append(item)
        return item


class FakeStatusUpdateService:
    updates: list[dict] = []

    def __init__(self, client: object, tenant_id: UUID, user_id: UUID) -> None:
        self.user_id = user_id

    def create_update(self, initiative_id: str, data: object) -> dict:
        payload = data.model_dump()
        item = {"initiative_id": initiative_id, **payload}
        self.updates.append(item)
        return item


def test_meeting_notes_workflow_upload_review_and_approve(monkeypatch) -> None:
    repo = FakeWorkflowRepository(None, TENANT_ID)
    session_id = str(uuid4())
    meeting_id = str(uuid4())
    FakeMeetingService.sessions = {
        session_id: {
            "id": session_id,
            "meeting_id": meeting_id,
            "notes": "Opening notes.",
            "attendees": [
                {"user_id": "user-aksha", "users": {"display_name": "Aksha Raman"}},
            ],
            "initiatives": [
                {
                    "initiatives": {
                        "id": "init-1",
                        "name": "AP automation",
                        "initiative_code": "INIT-001",
                    }
                }
            ],
        }
    }
    FakeMeetingService.action_items = []
    FakeStatusUpdateService.updates = []
    monkeypatch.setattr(workflow_module, "WorkflowRepository", lambda client, tenant_id: repo)
    monkeypatch.setattr(workflow_module, "MeetingService", FakeMeetingService)
    monkeypatch.setattr(workflow_module, "StatusUpdateService", FakeStatusUpdateService)

    service = WorkflowService(SimpleNamespace(), TENANT_ID)
    created = service.start_meeting_notes_extraction(
        meeting_id=meeting_id,
        session_id=session_id,
        body=MeetingTranscriptUpload(
            transcript_text=(
                "Vishwa: Decision: approve AP automation pilot.\n\n"
                "Aksha: I will validate invoice baseline by 2026-06-14.\n\n"
                "Priya: AP automation is blocked and should move red until ERP is ready."
            )
        ),
        submitter_user_id=USER_ID,
    )

    assert created.status == "awaiting_review"
    review = service.get_review(created.workflow_run_id)
    assert review.workflow_type == "meeting_notes_extraction"
    assert len(review.action_items) >= 1
    assert len(review.decisions) == 1
    assert len(review.initiative_updates) == 1

    approved = service.approve(
        created.workflow_run_id,
        WorkflowApproveRequest(
            action_items=review.action_items,
            decisions=review.decisions,
            initiative_updates=review.initiative_updates,
        ),
        USER_ID,
    )

    assert approved["status"] == "approved"
    assert FakeMeetingService.sessions[session_id]["has_transcript"] is True
    assert FakeMeetingService.sessions[session_id]["ai_optimised"] is True
    assert any("AI extracted decisions" in FakeMeetingService.sessions[session_id]["notes"] for _ in [0])
    assert any(item.get("assignee_id") == "user-aksha" for item in FakeMeetingService.action_items)
    assert FakeStatusUpdateService.updates[0]["initiative_id"] == "init-1"
