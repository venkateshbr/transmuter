from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.services.meeting_providers import (
    MeetingInviteRequest,
    MicrosoftGraphMeetingProvider,
    normalize_vtt_transcript,
)


class FakeResponse:
    def __init__(self, body: dict | None = None, text: str = "") -> None:
        self._body = body or {}
        self.text = text

    def json(self) -> dict:
        return self._body

    def raise_for_status(self) -> None:
        return None


class FakeRepo:
    def __init__(self) -> None:
        self.updated_connection: dict | None = None

    def update_integration_connection(self, connection_id: str, data: dict) -> dict:
        self.updated_connection = {"id": connection_id, **data}
        return self.updated_connection


class FakeHttp:
    def __init__(self) -> None:
        self.posts: list[dict] = []
        self.gets: list[dict] = []
        self.deletes: list[dict] = []

    def post(self, url: str, **kwargs) -> FakeResponse:  # noqa: ANN003
        self.posts.append({"url": url, **kwargs})
        if "login.microsoftonline.com" in url:
            return FakeResponse({"access_token": "fresh-token", "expires_in": 3600})
        return FakeResponse(
            {
                "id": "event-1",
                "onlineMeeting": {"id": "online-1", "joinUrl": "https://teams.example/join"},
            }
        )

    def get(self, url: str, **kwargs) -> FakeResponse:  # noqa: ANN003
        self.gets.append({"url": url, **kwargs})
        if url.endswith("/transcripts"):
            return FakeResponse({"value": [{"id": "transcript-1"}]})
        return FakeResponse(
            text="WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\n<v Vishwa>Welcome team</v>"
        )

    def delete(self, url: str, **kwargs) -> FakeResponse:  # noqa: ANN003
        self.deletes.append({"url": url, **kwargs})
        return FakeResponse()


def test_graph_provider_refreshes_token_and_sends_attendees(monkeypatch) -> None:
    monkeypatch.setattr(settings, "encryption_key", "test-encryption-key")
    monkeypatch.setattr(settings, "microsoft_graph_client_id", "client-id")
    monkeypatch.setattr(settings, "microsoft_graph_client_secret", "client-secret")
    repo = FakeRepo()
    http = FakeHttp()
    connection = {
        "id": "connection-1",
        "organizer_email": "organizer@example.com",
        "access_token_encrypted": encrypt_secret("expired-token"),
        "refresh_token_encrypted": encrypt_secret("refresh-token"),
        "token_expires_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
    }

    provider = MicrosoftGraphMeetingProvider(connection, repo, http)
    result = provider.create_invite(
        {"id": "meeting-1", "name": "Weekly review", "description": "Review"},
        [
            {
                "user_id": "user-1",
                "users": {"email": "attendee@example.com", "display_name": "Attendee"},
            }
        ],
        MeetingInviteRequest(
            organizer_email="organizer@example.com",
            start_date_time="2026-06-10T09:00:00",
            end_date_time="2026-06-10T10:00:00",
            time_zone="UTC",
            attendee_user_ids=["user-1"],
        ),
    )

    assert repo.updated_connection is not None
    assert result.join_url == "https://teams.example/join"
    event_payload = http.posts[-1]["json"]
    assert event_payload["isOnlineMeeting"] is True
    assert event_payload["attendees"][0]["emailAddress"]["address"] == "attendee@example.com"
    assert http.posts[-1]["headers"]["Authorization"] == "Bearer fresh-token"


def test_graph_provider_sends_recurring_series_payload(monkeypatch) -> None:
    monkeypatch.setattr(settings, "encryption_key", "test-encryption-key")
    repo = FakeRepo()
    http = FakeHttp()
    connection = {
        "id": "connection-1",
        "organizer_email": "organizer@example.com",
        "access_token_encrypted": encrypt_secret("valid-token"),
        "refresh_token_encrypted": encrypt_secret("refresh-token"),
        "token_expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
    }

    provider = MicrosoftGraphMeetingProvider(connection, repo, http)
    provider.create_invite(
        {"id": "meeting-1", "name": "Biweekly review", "description": "Review"},
        [],
        MeetingInviteRequest(
            organizer_email="organizer@example.com",
            start_date_time="2026-06-10T09:00:00",
            end_date_time="2026-06-10T10:00:00",
            time_zone="UTC",
            attendee_user_ids=[],
            recurrence={
                "pattern": {"type": "weekly", "interval": 2, "daysOfWeek": ["wednesday"]},
                "range": {
                    "type": "endDate",
                    "startDate": "2026-06-10",
                    "endDate": "2026-09-30",
                    "recurrenceTimeZone": "UTC",
                },
            },
        ),
    )

    event_payload = http.posts[-1]["json"]
    assert event_payload["recurrence"]["pattern"]["interval"] == 2
    assert event_payload["recurrence"]["range"]["endDate"] == "2026-09-30"


def test_graph_provider_syncs_and_normalizes_vtt(monkeypatch) -> None:
    monkeypatch.setattr(settings, "encryption_key", "test-encryption-key")
    repo = FakeRepo()
    http = FakeHttp()
    connection = {
        "id": "connection-1",
        "organizer_email": "organizer@example.com",
        "access_token_encrypted": encrypt_secret("valid-token"),
        "refresh_token_encrypted": encrypt_secret("refresh-token"),
        "token_expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
    }

    provider = MicrosoftGraphMeetingProvider(connection, repo, http)
    result = provider.sync_transcript(
        {
            "online_meeting_id": "online-1",
            "organizer_email": "organizer@example.com",
        }
    )

    assert result.status == "synced"
    assert result.transcript_text == "Vishwa: Welcome team"


def test_graph_provider_deletes_event_on_cancel(monkeypatch) -> None:
    monkeypatch.setattr(settings, "encryption_key", "test-encryption-key")
    repo = FakeRepo()
    http = FakeHttp()
    connection = {
        "id": "connection-1",
        "organizer_email": "organizer@example.com",
        "access_token_encrypted": encrypt_secret("valid-token"),
        "refresh_token_encrypted": encrypt_secret("refresh-token"),
        "token_expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
    }

    provider = MicrosoftGraphMeetingProvider(connection, repo, http)
    provider.cancel_invite(
        {
            "external_event_id": "event-1",
            "organizer_email": "organizer@example.com",
        }
    )

    assert http.deletes
    assert http.deletes[0]["url"].endswith("/users/organizer%40example.com/events/event-1")
    assert http.deletes[0]["headers"]["Authorization"] == "Bearer valid-token"


def test_normalize_vtt_transcript_strips_cues_and_duplicates() -> None:
    content = """WEBVTT

1
00:00:00.000 --> 00:00:01.000
<v Speaker>Approve the plan</v>
<v Speaker>Approve the plan</v>
"""

    assert normalize_vtt_transcript(content) == "Speaker: Approve the plan"
