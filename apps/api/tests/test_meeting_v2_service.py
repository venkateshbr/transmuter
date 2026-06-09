"""Focused Meetings v2 service coverage."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException

from app.domain.meetings import (
    MeetingCreate,
    MeetingMinutesGenerateRequest,
    MeetingUpdate,
    SessionStartRequest,
)
from app.services.meeting import MeetingService


class FakeMeetingV2Repository:
    def __init__(self) -> None:
        self.meeting = {
            "id": "meeting-1",
            "name": "Weekly review",
            "workstream_id": "ws-1",
            "workstreams": [{"id": "ws-1", "name": "Operations"}],
        }
        self.created_payload: dict | None = None
        self.updated_payload: dict | None = None
        self.workstream_sets: list[list[str]] = []
        self.created_sessions: list[tuple[str, str]] = []
        self.sessions_by_date: dict[str, dict] = {
            "2026-06-09": {
                "id": "session-existing",
                "meeting_id": "meeting-1",
                "session_date": "2026-06-09",
                "status": "in_progress",
            }
        }
        self.session_detail = {
            "id": "session-empty",
            "meeting_id": "meeting-1",
            "session_date": "2026-06-09",
            "meetings": {"name": "Weekly review"},
        }

    def create(self, data: dict) -> dict:
        self.created_payload = data
        return {"id": "meeting-1", **data}

    def update(self, meeting_id: str, data: dict) -> dict:
        assert meeting_id == "meeting-1"
        self.updated_payload = data
        self.meeting = {**self.meeting, **data}
        return self.meeting

    def get(self, meeting_id: str) -> dict | None:
        assert meeting_id == "meeting-1"
        return self.meeting

    def set_workstreams(self, meeting_id: str, workstream_ids: list[str]) -> None:
        assert meeting_id == "meeting-1"
        self.workstream_sets.append(workstream_ids)
        self.meeting["workstreams"] = [{"id": item, "name": item} for item in workstream_ids]

    def get_sessions(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return list(self.sessions_by_date.values())

    def get_agenda(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return []

    def get_attendees(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return []

    def get_external_events(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return []

    def get_initiatives(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return [
            {
                "initiative_id": "init-linked",
                "initiatives": {
                    "id": "init-linked",
                    "initiative_code": "TRN-010",
                    "name": "Linked Value Work",
                    "rag_status": "green",
                    "stage": "in_progress",
                },
            }
        ]

    def get_session_by_date(self, meeting_id: str, session_date: str) -> dict | None:
        assert meeting_id == "meeting-1"
        return self.sessions_by_date.get(session_date)

    def create_session(self, meeting_id: str, session_date: str) -> dict:
        self.created_sessions.append((meeting_id, session_date))
        row = {
            "id": f"session-{session_date}",
            "meeting_id": meeting_id,
            "session_date": session_date,
            "status": "in_progress",
        }
        self.sessions_by_date[session_date] = row
        return row

    def list_initiatives_for_workstreams(self, workstream_ids: list[str]) -> list[dict]:
        assert workstream_ids == ["ws-1"]
        return [
            {
                "id": "init-red",
                "initiative_code": "TRN-011",
                "name": "Margin Recovery",
                "rag_status": "red",
                "stage": "in_progress",
            }
        ]

    def list_open_actions_for_meeting(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return [
            {
                "id": "action-1",
                "description": "Email owner@example.com with the revised plan",
                "initiative_id": "init-linked",
                "status": "open",
                "initiatives": {"initiative_code": "TRN-010"},
            }
        ]

    def list_recent_risks_for_initiatives(self, initiative_ids: list[str]) -> list[dict]:
        assert "init-red" in initiative_ids
        return []

    def list_recent_milestones_for_initiatives(self, initiative_ids: list[str]) -> list[dict]:
        assert "init-linked" in initiative_ids
        return []

    def get_session(self, session_id: str) -> dict | None:
        assert session_id == "session-empty"
        return self.session_detail

    def get_session_action_items(self, session_id: str) -> list[dict]:
        assert session_id == "session-empty"
        return []

    def list_session_artifacts(self, session_id: str) -> list[dict]:
        assert session_id == "session-empty"
        return []

    def get_carry_forward_action_items(self, meeting_id: str, current_session_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        assert current_session_id == "session-empty"
        return []


def build_service(repo: FakeMeetingV2Repository) -> MeetingService:
    service = MeetingService.__new__(MeetingService)
    service._repo = repo
    service._tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    service._client = None
    return service


def test_create_meeting_sets_join_workstreams_and_legacy_first_id() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    service.create_meeting(
        MeetingCreate(
            name="Weekly review",
            scope="workstream",
            workstream_ids=["ws-1", "ws-2", "ws-1"],
        )
    )

    assert repo.created_payload is not None
    assert repo.created_payload["workstream_id"] == "ws-1"
    assert repo.workstream_sets == [["ws-1", "ws-2"]]


def test_update_meeting_can_clear_join_workstreams() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    service.update_meeting("meeting-1", MeetingUpdate(workstream_ids=[]))

    assert repo.updated_payload == {"workstream_id": None}
    assert repo.workstream_sets == [[]]


def test_start_session_is_date_specific_and_idempotent() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    existing = service.start_session(
        "meeting-1",
        SessionStartRequest(session_date="2026-06-09"),
    )
    created = service.start_session(
        "meeting-1",
        SessionStartRequest(session_date="2026-06-10"),
    )

    assert existing["id"] == "session-existing"
    assert created["id"] == "session-2026-06-10"
    assert repo.created_sessions == [("meeting-1", "2026-06-10")]


def test_agenda_suggestions_use_actions_workstreams_and_mask_pii() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    response = service.suggest_agenda_items("meeting-1")

    texts = [item.text for item in response.items]
    assert any("Close carry-forward action" in text for text in texts)
    assert any("Resolve red status" in text for text in texts)
    assert all("owner@example.com" not in text for text in texts)
    assert response.trace_id is not None


def test_generate_minutes_requires_real_source_material() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    with pytest.raises(HTTPException) as exc:
        service.generate_minutes(
            "session-empty",
            MeetingMinutesGenerateRequest(force=True),
        )

    assert exc.value.status_code == 400
