"""Meeting minutes email delivery coverage."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from app.services.email_delivery import EmailDeliveryResult
from app.services.meeting import MeetingService

SESSION_ID = "session-1"
MEETING_ID = "meeting-1"


class FakeMeetingRepository:
    def __init__(self, *, attendees: list[dict] | None = None) -> None:
        self.session = {
            "id": SESSION_ID,
            "meeting_id": MEETING_ID,
            "minutes_markdown": "# Minutes\n\n## Actions\n- Confirm owner",
            "session_date": "2026-06-01",
            "meetings": {"name": "Weekly transformation review"},
        }
        self.attendees = attendees if attendees is not None else []
        self.updated_payload: dict | None = None

    def get_session(self, session_id: str) -> dict | None:
        assert session_id == SESSION_ID
        return self.session

    def get_attendees(self, meeting_id: str) -> list[dict]:
        assert meeting_id == MEETING_ID
        return self.attendees

    def update_session(self, session_id: str, data: dict) -> dict:
        assert session_id == SESSION_ID
        self.updated_payload = data
        return {**self.session, **data}


@dataclass
class FakeEmailDeliveryService:
    result: EmailDeliveryResult
    call: dict | None = None

    def deliver(
        self,
        *,
        to: list[str],
        subject: str,
        text: str,
        html: str | None = None,
    ) -> EmailDeliveryResult:
        self.call = {"to": to, "subject": subject, "text": text, "html": html}
        return self.result


def build_service(
    repo: FakeMeetingRepository,
    email: FakeEmailDeliveryService,
) -> MeetingService:
    service = MeetingService.__new__(MeetingService)
    service._repo = repo
    service._email = email
    return service


def test_send_minutes_emails_attendees_before_marking_sent() -> None:
    repo = FakeMeetingRepository(
        attendees=[
            {"users": {"email": "owner@example.com"}},
            {"users": {"email": "pm@example.com"}},
            {"users": {"display_name": "No email"}},
        ]
    )
    email = FakeEmailDeliveryService(EmailDeliveryResult(status="sent", detail="email"))
    service = build_service(repo, email)

    result = service.send_minutes(SESSION_ID)

    assert result["minutes_status"] == "sent"
    assert repo.updated_payload is not None
    assert repo.updated_payload["minutes_status"] == "sent"
    assert email.call is not None
    assert email.call["to"] == ["owner@example.com", "pm@example.com"]
    assert email.call["subject"] == "Minutes: Weekly transformation review"
    assert "## Actions" in str(email.call["text"])


def test_send_minutes_requires_attendee_email() -> None:
    repo = FakeMeetingRepository(attendees=[{"users": {"display_name": "No email"}}])
    email = FakeEmailDeliveryService(EmailDeliveryResult(status="sent", detail="email"))
    service = build_service(repo, email)

    with pytest.raises(HTTPException) as exc:
        service.send_minutes(SESSION_ID)

    assert exc.value.status_code == 400
    assert repo.updated_payload is None
    assert email.call is None


def test_send_minutes_does_not_mark_sent_when_resend_fails() -> None:
    repo = FakeMeetingRepository(attendees=[{"users": {"email": "owner@example.com"}}])
    email = FakeEmailDeliveryService(
        EmailDeliveryResult(status="failed", detail="provider unavailable")
    )
    service = build_service(repo, email)

    with pytest.raises(HTTPException) as exc:
        service.send_minutes(SESSION_ID)

    assert exc.value.status_code == 502
    assert repo.updated_payload is None
