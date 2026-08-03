"""Focused Meetings v2 service coverage."""

from __future__ import annotations

from unittest.mock import ANY
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.agents.meeting_minutes_agent import _ground_with_captured_records
from app.domain.meeting_notes import (
    MeetingMinutesAction,
    MeetingMinutesContent,
    MeetingMinutesDecision,
)
from app.domain.meetings import (
    MeetingCreate,
    MeetingExternalEventCreate,
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
        self.external_event_upserts: list[dict] = []
        self.integration_connection: dict | None = None
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
        assert provider == "microsoft_graph"
        assert organizer_email is None
        return self.integration_connection

    def upsert_external_event(
        self,
        meeting_id: str,
        provider: str,
        data: dict,
        session_id: str | None = None,
    ) -> dict:
        row = {
            "id": "event-1",
            "meeting_id": meeting_id,
            "provider": provider,
            "session_id": session_id,
            **data,
        }
        self.external_event_upserts.append(row)
        return row

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
        assert initiative_ids == ["init-linked"]
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


def test_disconnected_microsoft_event_is_not_relinked_by_organizer_email() -> None:
    service = build_service(FakeMeetingV2Repository())

    connection = service._microsoft_connection_for_event(  # noqa: SLF001
        {
            "integration_connection_id": None,
            "organizer_email": "historical-organizer@example.com",
        }
    )

    assert connection is None


def test_microsoft_invite_uses_tenant_organizer_without_request_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = FakeMeetingV2Repository()
    repo.integration_connection = {
        "id": "connection-1",
        "organizer_email": "tenant-organizer@example.com",
    }
    captured: dict = {}

    class FakeMicrosoftProvider:
        def __init__(self, connection: dict, *_args: object) -> None:
            captured["connection"] = connection

        def create_invite(self, _meeting: dict, _attendees: list[dict], request: object) -> object:
            captured["organizer_email"] = request.organizer_email  # type: ignore[attr-defined]
            return type(
                "InviteResult",
                (),
                {
                    "external_event_id": "graph-event-1",
                    "online_meeting_id": "online-meeting-1",
                    "join_url": "https://teams.example/join",
                    "organizer_email": "tenant-organizer@example.com",
                },
            )()

    monkeypatch.setattr("app.services.meeting.MicrosoftGraphMeetingProvider", FakeMicrosoftProvider)
    service = build_service(repo)

    event = service.create_microsoft_event(
        "meeting-1",
        MeetingExternalEventCreate(
            start_date_time="2026-08-04T09:00:00",
            end_date_time="2026-08-04T10:00:00",
            time_zone="Asia/Singapore",
        ),
    )

    assert captured["connection"] is repo.integration_connection
    assert captured["organizer_email"] == "tenant-organizer@example.com"
    assert event["integration_connection_id"] == "connection-1"
    assert event["organizer_email"] == "tenant-organizer@example.com"


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


@pytest.mark.parametrize("terminal_status", ["completed", "cancelled"])
def test_start_session_does_not_reopen_terminal_session(terminal_status: str) -> None:
    repo = FakeMeetingV2Repository()
    repo.sessions_by_date["2026-06-09"]["status"] = terminal_status
    service = build_service(repo)

    with pytest.raises(HTTPException) as exc:
        service.start_session(
            "meeting-1",
            SessionStartRequest(session_date="2026-06-09"),
        )

    assert exc.value.status_code == 409
    assert repo.sessions_by_date["2026-06-09"]["status"] == terminal_status


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


def test_agenda_suggestions_use_linked_context_and_mask_pii() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    response = service.suggest_agenda_items("meeting-1")

    texts = [item.text for item in response.items]
    assert any("Close carry-forward action" in text for text in texts)
    assert all("Margin Recovery" not in text for text in texts)
    assert all("owner@example.com" not in text for text in texts)
    assert response.trace_id is not None


def test_agenda_suggestions_are_scoped_to_linked_initiatives_and_deduplicated() -> None:
    repo = FakeMeetingV2Repository()
    repo.list_recent_risks_for_initiatives = lambda initiative_ids: [  # type: ignore[method-assign]
        {
            "id": "risk-1",
            "description": "Capability ramp",
            "initiative_id": "init-linked",
            "status": "open",
            "initiatives": {"initiative_code": "TRN-010"},
        },
        {
            "id": "risk-2",
            "description": "Capability ramp",
            "initiative_id": "init-linked",
            "status": "open",
            "initiatives": {"initiative_code": "TRN-010"},
        },
    ]
    repo.list_recent_milestones_for_initiatives = lambda initiative_ids: [  # type: ignore[method-assign]
        {
            "id": "milestone-1",
            "name": "Automation build",
            "initiative_id": "init-linked",
            "status": "in_progress",
            "planned_end": "2026-07-31",
            "initiatives": {"initiative_code": "TRN-010"},
        },
        {
            "id": "milestone-2",
            "name": "Automation build",
            "initiative_id": "init-linked",
            "status": "in_progress",
            "planned_end": "2026-07-31",
            "initiatives": {"initiative_code": "TRN-010"},
        },
    ]
    service = build_service(repo)

    response = service.suggest_agenda_items("meeting-1")

    assert 1 <= len(response.items) <= 5
    assert all(item.initiative_id != "init-red" for item in response.items)
    normalized = [" ".join(item.text.lower().split()) for item in response.items]
    assert len(normalized) == len(set(normalized))


def test_agenda_suggestions_require_a_linked_initiative() -> None:
    repo = FakeMeetingV2Repository()
    repo.get_initiatives = lambda meeting_id: []  # type: ignore[method-assign]
    service = build_service(repo)

    response = service.suggest_agenda_items("meeting-1")

    assert response.items == []


def test_meeting_pii_mask_preserves_iso_dates_while_masking_phone_numbers() -> None:
    text = (
        "ACME Saturday Value Steering - 2026-07-18; target 2028-03-31; "
        "call +65 6123 4567 or (212) 555-0199; owner@example.com"
    )

    masked = MeetingService._mask_pii(text)

    assert "2026-07-18" in masked
    assert "2028-03-31" in masked
    assert "+65 6123 4567" not in masked
    assert "(212) 555-0199" not in masked
    assert masked.count("[phone]") == 2
    assert "owner@example.com" not in masked
    assert "[email]" in masked


def test_minutes_source_masks_attendees_speakers_and_captured_owners() -> None:
    repo = FakeMeetingV2Repository()
    repo.get_attendees = lambda meeting_id: [  # type: ignore[method-assign]
        {
            "user_id": "user-rupa",
            "users": {"display_name": "Rupa Menon"},
        }
    ]
    service = build_service(repo)
    detail = {
        **repo.session_detail,
        "notes": "Rupa Menon confirmed the next step.",
        "transcript_text": "External Guest: Rupa Menon will verify the workflow.",
        "agenda": [],
        "attendees": repo.get_attendees("meeting-1"),
        "artifacts": [
            {
                "artifact_type": "action",
                "title": "Verify the workflow",
                "users": {"display_name": "Vishwa Rao"},
            }
        ],
        "action_items": [],
    }

    source, participant_names = service._professional_minutes_source(detail)

    serialized = str(source)
    assert "Rupa Menon" not in serialized
    assert "Vishwa Rao" not in serialized
    assert "External Guest" not in serialized
    assert "Participant 1" in serialized
    assert "Speaker:" in serialized
    assert set(participant_names.values()) == {"Rupa Menon", "Vishwa Rao"}


def test_minutes_source_excludes_undiscussed_agenda_context() -> None:
    repo = FakeMeetingV2Repository()
    service = build_service(repo)
    repo.get_session_agenda = lambda session_id: [  # type: ignore[method-assign]
        {
            "id": "agenda-discussed",
            "text": "Review Meetings V4 workflow",
            "initiative_id": "init-linked",
        },
        {
            "id": "agenda-undiscussed",
            "text": "Undiscussed budget review",
            "initiative_id": "init-linked",
        },
    ]
    detail = {
        **repo.session_detail,
        "notes": "The team reviewed the Meetings V4 workflow and verified agenda propagation.",
        "transcript_text": "The Meetings V4 workflow is ready for dev acceptance.",
        "agenda": repo.get_session_agenda("session-empty"),
        "attendees": [],
        "artifacts": [],
        "action_items": [],
    }

    source, _participant_names = service._professional_minutes_source(detail)

    assert [item["text"] for item in source["agenda"]] == ["Review Meetings V4 workflow"]


def test_captured_decision_deduplicates_an_ai_paraphrase() -> None:
    content = MeetingMinutesContent(
        executive_summary="The team agreed how unscheduled meetings will be handled.",
        decisions=[
            MeetingMinutesDecision(
                text=(
                    "Ad-hoc meeting series will be used for unscheduled meetings instead "
                    "of changing recurring session dates."
                ),
                evidence="use ad-hoc meeting series for unscheduled meetings",
            )
        ],
    )
    source = {
        "artifacts": [
            {
                "artifact_type": "decision",
                "title": "Use ad-hoc meeting series for unscheduled meetings",
            }
        ],
        "action_items": [],
    }

    grounded = _ground_with_captured_records(content, source)

    assert len(grounded.decisions) == 1


def test_captured_action_enriches_an_ai_paraphrase() -> None:
    content = MeetingMinutesContent(
        executive_summary="The team assigned acceptance documentation.",
        actions=[
            MeetingMinutesAction(
                description="Document the acceptance evidence for issue 425.",
                evidence="document the dev acceptance evidence on issue 425",
            )
        ],
    )
    source = {
        "artifacts": [
            {
                "artifact_type": "action",
                "title": "Document dev acceptance evidence on issue 425",
                "owner": "Participant 1",
                "due_date": "2026-07-24",
                "priority": "high",
                "status": "open",
            }
        ],
        "action_items": [],
    }

    grounded = _ground_with_captured_records(content, source)

    assert len(grounded.actions) == 1
    assert grounded.actions[0].owner == "Participant 1"
    assert grounded.actions[0].due_date == "2026-07-24"
    assert grounded.actions[0].priority == "high"


@pytest.mark.asyncio
async def test_generate_minutes_requires_real_source_material(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.meeting_minutes_agent.settings.ai_enabled", False)
    repo = FakeMeetingV2Repository()
    service = build_service(repo)

    with pytest.raises(HTTPException) as exc:
        await service.generate_minutes(
            "session-empty",
            MeetingMinutesGenerateRequest(force=True),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_generate_minutes_summarizes_transcript_by_agenda_without_raw_dump(
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.agents.meeting_minutes_agent.settings.ai_enabled", False)
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
        {
            "id": "session-agenda-benefits",
            "source_agenda_item_id": "agenda-benefits",
            "text": "Benefits tracking",
        },
        {
            "id": "session-agenda-risk",
            "source_agenda_item_id": "agenda-risk",
            "text": "Migration risk",
        },
    ]
    repo.list_session_artifacts = lambda session_id: [  # type: ignore[method-assign]
        {
            "id": "artifact-1",
            "agenda_item_id": "agenda-risk",
            "artifact_type": "risk",
            "title": "Cutover rollback owner missing",
            "status": "open",
        },
        {
            "id": "artifact-2",
            "agenda_item_id": None,
            "session_agenda_item_id": "session-agenda-risk",
            "artifact_type": "decision",
            "title": "Retain the governed baseline",
            "status": "open",
        },
    ]

    service = build_service(repo)

    response = await service.generate_minutes(
        "session-empty",
        MeetingMinutesGenerateRequest(force=True),
    )

    minutes = response["minutes_markdown"]
    assert "## Executive Summary" in minutes
    assert "## Key Discussion" in minutes
    assert "Benefits tracking is behind" in minutes
    assert "migration risk is high" in minutes
    assert "Cutover rollback owner missing" in minutes
    assert "Retain the governed baseline" in minutes
    assert "## Source Coverage" in minutes
    assert "Discussed " not in minutes
    assert "No specific transcript or note content" not in minutes


@pytest.mark.asyncio
async def test_generate_minutes_deduplicates_agenda_and_excludes_undiscussed_topics(
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.agents.meeting_minutes_agent.settings.ai_enabled", False)
    repo = FakeMeetingV2Repository()
    repo.session_detail = {
        **repo.session_detail,
        "id": "session-empty",
        "notes": "The meeting configuration review found that series agenda changes were not reaching sessions.",
        "transcript_text": (
            "We reviewed the Transmuter meeting workflow. "
            "The team agreed to fix agenda propagation before adding more generated topics. "
            "Action: update the session agenda workflow and verify it in the browser."
        ),
        "meetings": {"name": "Transmuter Weekly"},
    }
    duplicated_milestone = {
        "id": "session-agenda-milestone-1",
        "source_agenda_item_id": "agenda-milestone",
        "initiative_id": "init-linked",
        "text": "Review upcoming milestone for NPK-2: Configure automation due 2026-07-31",
    }
    repo.get_session_agenda = lambda session_id: [  # type: ignore[method-assign]
        {
            "id": "session-agenda-review",
            "source_agenda_item_id": "agenda-review",
            "text": "Review meeting functionality",
        },
        duplicated_milestone,
        {
            **duplicated_milestone,
            "id": "session-agenda-milestone-2",
        },
    ]

    service = build_service(repo)

    response = await service.generate_minutes(
        "session-empty",
        MeetingMinutesGenerateRequest(force=True),
    )

    minutes = response["minutes_markdown"]
    assert "Review upcoming milestone for NPK-2" not in minutes
    assert "The meeting configuration review found" in minutes
    assert "update the session agenda workflow" in minutes
    assert "Discussed " not in minutes
    assert (
        "No specific transcript or note content was captured for this agenda item." not in minutes
    )
