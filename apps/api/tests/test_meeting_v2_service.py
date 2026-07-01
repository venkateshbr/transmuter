"""Focused Meetings v2 service coverage."""

from __future__ import annotations

from unittest.mock import ANY
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
            "recurrence": "weekly",
            "day_of_week": 1,
            "start_time": "09:00",
            "timezone": "UTC",
            "duration_minutes": 60,
        }
        self.created_payload: dict | None = None
        self.updated_payload: dict | None = None
        self.workstream_sets: list[list[str]] = []
        self.attendee_sets: list[list[str]] = []
        self.created_sessions: list[tuple[str, str, dict]] = []
        self.snapshotted_sessions: list[str] = []
        self.external_event_updates: list[dict] = []
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

    def set_attendees(self, meeting_id: str, user_ids: list[str]) -> None:
        assert meeting_id == "meeting-1"
        self.attendee_sets.append(user_ids)

    def get_sessions(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return list(self.sessions_by_date.values())

    def get_agenda(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return []

    def create_agenda_item(self, meeting_id: str, data: dict) -> dict:
        assert meeting_id == "meeting-1"
        return {"id": f"agenda-{data['sort_order']}", "meeting_id": meeting_id, **data}

    def get_attendees(self, meeting_id: str) -> list[dict]:
        assert meeting_id == "meeting-1"
        return []

    def get_session_attendees(self, session_id: str) -> list[dict]:
        return []

    def snapshot_session_attendees(self, session: dict, attendees: list[dict]) -> None:
        self.snapshotted_sessions.append(session["id"])

    def get_external_events(self, meeting_id: str, session_id: str | None = None) -> list[dict]:
        assert meeting_id == "meeting-1"
        return []

    def update_external_event(self, event_id: str, data: dict) -> dict:
        self.external_event_updates.append({"id": event_id, **data})
        return {"id": event_id, **data}

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

    def create_session(self, meeting_id: str, session_date: str, data: dict | None = None) -> dict:
        payload = data or {}
        self.created_sessions.append((meeting_id, session_date, payload))
        row = {
            "id": f"session-{session_date}",
            "meeting_id": meeting_id,
            "session_date": session_date,
            "status": payload.get("status", "scheduled"),
        }
        self.sessions_by_date[session_date] = row
        return row

    def update_session(self, session_id: str, data: dict) -> dict:
        for session in self.sessions_by_date.values():
            if session["id"] == session_id:
                session.update(data)
                return session
        return {**self.session_detail, **data}

    def cancel_open_sessions(self, meeting_id: str) -> int:
        assert meeting_id == "meeting-1"
        count = 0
        for session in self.sessions_by_date.values():
            if session["status"] in {"scheduled", "in_progress"}:
                session["status"] = "cancelled"
                count += 1
        return count

    def get_integration_connection(
        self, provider: str, organizer_email: str | None = None
    ) -> dict | None:
        return None

    def get_integration_connection_by_id(self, connection_id: str) -> dict | None:
        return None

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

    def get_session_agenda(self, session_id: str) -> list[dict]:
        return []

    def snapshot_session_agenda(self, session: dict, agenda: list[dict]) -> None:
        self.snapshotted_sessions.append(session["id"])

    def get_session_action_items(self, session_id: str) -> list[dict]:
        assert session_id == "session-empty"
        return []

    def list_session_artifacts(self, session_id: str) -> list[dict]:
        assert session_id == "session-empty"
        return []

    def get_carry_forward_action_items(
        self, meeting_id: str, current_session_id: str
    ) -> list[dict]:
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


def test_create_meeting_sets_v3_participants_schedule_and_default_agenda() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    service.create_meeting(
        MeetingCreate(
            name="Biweekly review",
            scope="all",
            recurrence="biweekly",
            day_of_week=2,
            start_time="13:30",
            timezone="America/New_York",
            duration_minutes=45,
            series_start_date="2026-06-10",
            series_end_date="2026-09-30",
            participant_user_ids=["user-1", "user-2", "user-1"],
            default_agenda_items=[{"text": "Review blockers"}],
        )
    )

    assert repo.created_payload is not None
    assert repo.created_payload["recurrence"] == "biweekly"
    assert repo.created_payload["start_time"] == "13:30"
    assert repo.created_payload["timezone"] == "America/New_York"
    assert repo.created_payload["duration_minutes"] == 45
    assert repo.created_payload["series_start_date"] == "2026-06-10"
    assert repo.created_payload["series_end_date"] == "2026-09-30"
    assert repo.attendee_sets == [["user-1", "user-2"]]


def test_timezones_catalog_contains_iana_values() -> None:
    values = {item["value"] for item in MeetingService.list_timezones()}

    assert "UTC" in values
    assert "Asia/Kolkata" in values
    assert "America/New_York" in values


def test_create_meeting_rejects_invalid_timezone() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    with pytest.raises(HTTPException) as exc:
        service.create_meeting(MeetingCreate(name="Bad timezone", timezone="IST"))

    assert exc.value.status_code == 422
    assert exc.value.detail == "timezone must be a valid IANA timezone."
    assert repo.created_payload is None


def test_create_meeting_rejects_series_end_before_start() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    with pytest.raises(HTTPException) as exc:
        service.create_meeting(
            MeetingCreate(
                name="Bad date range",
                day_of_week=2,
                series_start_date="2026-06-10",
                series_end_date="2026-06-09",
            )
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "series_end_date must be on or after series_start_date."
    assert repo.created_payload is None


def test_update_meeting_can_clear_join_workstreams() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    service.update_meeting("meeting-1", MeetingUpdate(workstream_ids=[]))

    assert repo.updated_payload == {"workstream_id": None}
    assert repo.workstream_sets == [[]]


def test_cancel_meeting_series_marks_series_and_open_sessions_cancelled() -> None:
    repo = FakeMeetingV2Repository()
    repo.sessions_by_date["2026-06-16"] = {
        "id": "session-scheduled",
        "meeting_id": "meeting-1",
        "session_date": "2026-06-16",
        "status": "scheduled",
    }
    service = build_service(repo)

    result = service.cancel_meeting_series("meeting-1")

    assert result.meeting["status"] == "cancelled"
    assert result.teams_status == "no_external_event"
    assert result.cancelled_sessions == 2
    assert repo.updated_payload is not None
    assert repo.updated_payload["status"] == "cancelled"
    assert {session["status"] for session in repo.sessions_by_date.values()} == {"cancelled"}


def test_cancelled_meeting_series_cannot_start_session() -> None:
    repo = FakeMeetingV2Repository()
    repo.meeting["status"] = "cancelled"
    service = build_service(repo)

    with pytest.raises(HTTPException) as exc:
        service.start_session("meeting-1", SessionStartRequest(session_date="2026-06-16"))

    assert exc.value.status_code == 409
    assert repo.created_sessions == []


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
    assert repo.created_sessions == [("meeting-1", "2026-06-10", ANY)]
    assert repo.created_sessions[0][2]["status"] == "in_progress"


def test_session_window_materializes_last_three_and_next_three() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    window = service.get_sessions_window("meeting-1", anchor_date="2026-06-10", page_size=3)

    assert window["anchor_date"] == "2026-06-10"
    assert [item["session_date"] for item in window["items"]] == [
        "2026-05-26",
        "2026-06-02",
        "2026-06-09",
        "2026-06-16",
        "2026-06-23",
        "2026-06-30",
    ]
    assert len(repo.created_sessions) == 5
    assert all(row[2]["status"] == "scheduled" for row in repo.created_sessions)


def test_session_window_respects_series_start_and_end_dates() -> None:
    repo = FakeMeetingV2Repository()
    repo.meeting.update(
        {
            "day_of_week": 2,
            "series_start_date": "2026-06-10",
            "series_end_date": "2026-06-24",
        }
    )
    service = build_service(repo)

    window = service.get_sessions_window("meeting-1", anchor_date="2026-06-01", page_size=3)

    assert [item["session_date"] for item in window["items"]] == [
        "2026-06-10",
        "2026-06-17",
        "2026-06-24",
    ]
    assert [row[1] for row in repo.created_sessions] == [
        "2026-06-10",
        "2026-06-17",
        "2026-06-24",
    ]


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


def test_generate_minutes_summarizes_transcript_by_agenda_without_raw_dump() -> None:
    repo = FakeMeetingV2Repository()
    repo.session_detail = {
        **repo.session_detail,
        "id": "session-empty",
        "notes": "The team agreed benefits tracking needs a weekly owner checkpoint.",
        "transcript_text": (
            "Rupa Menon: Benefits tracking is behind because the owner checklist is incomplete. "
            "Vishwa Rao: The migration risk is high until the cutover plan has a rollback owner. "
            "Rupa Menon: Finance validation should be complete by Friday."
        ),
        "meetings": {"name": "Weekly review"},
    }
    repo.get_session_agenda = lambda session_id: [  # type: ignore[method-assign]
        {"id": "agenda-benefits", "text": "Benefits tracking"},
        {"id": "agenda-risk", "text": "Migration risk"},
    ]
    repo.list_session_artifacts = lambda session_id: [  # type: ignore[method-assign]
        {
            "id": "artifact-1",
            "agenda_item_id": "agenda-risk",
            "artifact_type": "risk",
            "title": "Cutover rollback owner missing",
            "status": "open",
        }
    ]

    service = build_service(repo)

    response = service.generate_minutes(
        "session-empty",
        MeetingMinutesGenerateRequest(force=True),
    )

    minutes = response["minutes_markdown"]
    assert "## AI Summary" in minutes
    assert "## Agenda Discussion" in minutes
    assert "### Benefits tracking" in minutes
    assert "### Migration risk" in minutes
    assert "Discussed benefits tracking is behind" in minutes
    assert "Discussed the migration risk is high" in minutes
    assert "Captured items:" in minutes
    assert "Cutover rollback owner missing" in minutes
    assert "## Transcript Summary Source" not in minutes
    assert "Rupa Menon:" not in minutes
    assert "Vishwa Rao:" not in minutes
