from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.repositories.meeting import MeetingRepository


class MeetingProviderError(Exception):
    """Base error for meeting provider failures."""


class MeetingProviderConfigurationError(MeetingProviderError):
    """Provider is not configured for the current tenant."""


@dataclass(frozen=True)
class MeetingInviteRequest:
    organizer_email: str | None
    start_date_time: str
    end_date_time: str
    time_zone: str
    attendee_user_ids: list[str]
    recurrence: dict | None = None


@dataclass(frozen=True)
class MeetingInviteResult:
    external_event_id: str | None
    online_meeting_id: str | None
    join_url: str | None
    organizer_email: str | None


@dataclass(frozen=True)
class TranscriptSyncResult:
    status: str
    transcript_text: str = ""
    detail: str | None = None
    transcript_id: str | None = None


class MeetingProvider(Protocol):
    def create_invite(
        self,
        meeting: dict,
        attendees: list[dict],
        request: MeetingInviteRequest,
    ) -> MeetingInviteResult: ...

    def get_join_url(self, external_event: dict) -> str | None: ...

    def sync_transcript(self, external_event: dict) -> TranscriptSyncResult: ...


class MicrosoftGraphMeetingProvider:
    def __init__(
        self,
        connection: dict,
        repo: MeetingRepository,
        http_client: object = httpx,
    ) -> None:
        self._connection = connection
        self._repo = repo
        self._http = http_client

    def create_invite(
        self,
        meeting: dict,
        attendees: list[dict],
        request: MeetingInviteRequest,
    ) -> MeetingInviteResult:
        access_token = self._access_token()
        user_id = self._graph_user_id(request.organizer_email)
        event_payload = {
            "subject": meeting["name"],
            "body": {
                "contentType": "HTML",
                "content": meeting.get("description") or "Transmuter meeting",
            },
            "start": {"dateTime": request.start_date_time, "timeZone": request.time_zone},
            "end": {"dateTime": request.end_date_time, "timeZone": request.time_zone},
            "attendees": self._graph_attendees(attendees, request.attendee_user_ids),
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }
        if request.recurrence:
            event_payload["recurrence"] = request.recurrence
        response = self._http.post(
            f"https://graph.microsoft.com/v1.0/{user_id}/events",
            headers=self._headers(access_token),
            json=event_payload,
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
        online = body.get("onlineMeeting") or {}
        return MeetingInviteResult(
            external_event_id=body.get("id"),
            online_meeting_id=online.get("id"),
            join_url=online.get("joinUrl"),
            organizer_email=request.organizer_email or self._connection.get("organizer_email"),
        )

    def get_join_url(self, external_event: dict) -> str | None:
        return external_event.get("join_url")

    def sync_transcript(self, external_event: dict) -> TranscriptSyncResult:
        access_token = self._access_token()
        user_id = self._graph_user_id(external_event.get("organizer_email"))
        online_meeting_id = external_event.get("online_meeting_id")
        if not online_meeting_id and external_event.get("join_url"):
            online_meeting_id = self._find_online_meeting_id(
                access_token,
                user_id,
                external_event["join_url"],
            )
        if not online_meeting_id:
            return TranscriptSyncResult(
                status="unavailable",
                detail="The synced Teams event does not include an online meeting id yet.",
            )

        transcripts_response = self._http.get(
            f"https://graph.microsoft.com/v1.0/{user_id}/onlineMeetings/{quote(online_meeting_id, safe='')}/transcripts",
            headers=self._headers(access_token),
            timeout=10,
        )
        transcripts_response.raise_for_status()
        transcripts = transcripts_response.json().get("value") or []
        if not transcripts:
            return TranscriptSyncResult(
                status="pending",
                detail="No Microsoft Teams transcript is available for this meeting yet.",
            )

        transcript = transcripts[-1]
        transcript_id = transcript.get("id")
        if not transcript_id:
            return TranscriptSyncResult(
                status="unavailable",
                detail="Microsoft returned transcript metadata without a transcript id.",
            )

        content_response = self._http.get(
            f"https://graph.microsoft.com/v1.0/{user_id}/onlineMeetings/{quote(online_meeting_id, safe='')}/transcripts/{quote(transcript_id, safe='')}/content",
            headers={**self._headers(access_token), "Accept": "text/vtt"},
            timeout=15,
        )
        content_response.raise_for_status()
        transcript_text = normalize_vtt_transcript(content_response.text)
        if not transcript_text:
            return TranscriptSyncResult(
                status="unavailable",
                detail="Microsoft returned an empty transcript.",
                transcript_id=transcript_id,
            )
        return TranscriptSyncResult(
            status="synced",
            transcript_text=transcript_text,
            transcript_id=transcript_id,
        )

    def _access_token(self) -> str:
        token = decrypt_secret(self._connection.get("access_token_encrypted"))
        expires_at = _parse_datetime(self._connection.get("token_expires_at"))
        if token and expires_at and expires_at > datetime.now(UTC) + timedelta(minutes=5):
            return token
        refresh_token = decrypt_secret(self._connection.get("refresh_token_encrypted"))
        if not refresh_token:
            raise MeetingProviderConfigurationError(
                "Microsoft Graph is not connected. Connect a Microsoft organizer account first."
            )
        if not settings.microsoft_graph_client_id or not settings.microsoft_graph_client_secret:
            raise MeetingProviderConfigurationError(
                "Microsoft OAuth client id and secret are not configured."
            )
        response = self._http.post(
            _token_url(),
            data={
                "client_id": settings.microsoft_graph_client_id,
                "client_secret": settings.microsoft_graph_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": settings.microsoft_graph_scopes,
            },
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
        token = body["access_token"]
        expires_in = int(body.get("expires_in") or 3600)
        update = {
            "access_token_encrypted": encrypt_secret(token),
            "token_expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
            "sync_status": "connected",
            "sync_error": None,
            "last_synced_at": datetime.now(UTC).isoformat(),
        }
        if body.get("refresh_token"):
            update["refresh_token_encrypted"] = encrypt_secret(body["refresh_token"])
        self._connection = self._repo.update_integration_connection(self._connection["id"], update)
        return token

    def _find_online_meeting_id(
        self,
        access_token: str,
        user_id: str,
        join_url: str,
    ) -> str | None:
        response = self._http.get(
            f"https://graph.microsoft.com/v1.0/{user_id}/onlineMeetings",
            headers=self._headers(access_token),
            params={"$filter": f"JoinWebUrl eq '{join_url}'"},
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json().get("value") or []
        return rows[0].get("id") if rows else None

    def _graph_user_id(self, organizer_email: str | None) -> str:
        raw_user_id = (
            self._connection.get("external_account_id")
            or settings.microsoft_graph_user_id
            or organizer_email
            or self._connection.get("organizer_email")
            or "me"
        )
        return "me" if raw_user_id == "me" else f"users/{quote(str(raw_user_id), safe='')}"

    @staticmethod
    def _headers(access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _graph_attendees(attendees: list[dict], attendee_user_ids: list[str]) -> list[dict]:
        selected = set(attendee_user_ids)
        rows = [
            attendee
            for attendee in attendees
            if not selected or str(attendee.get("user_id")) in selected
        ]
        graph_rows: list[dict] = []
        for attendee in rows:
            user = attendee.get("users") if isinstance(attendee.get("users"), dict) else {}
            email = user.get("email")
            if not email:
                continue
            graph_rows.append(
                {
                    "emailAddress": {
                        "address": email,
                        "name": user.get("display_name") or email,
                    },
                    "type": "required",
                }
            )
        return graph_rows


class DisabledMeetingBotProvider:
    def __init__(self, provider_name: str) -> None:
        self._provider_name = provider_name

    def create_invite(
        self,
        meeting: dict,
        attendees: list[dict],
        request: MeetingInviteRequest,
    ) -> MeetingInviteResult:
        raise MeetingProviderConfigurationError(
            f"{self._provider_name} meeting bot provider is disabled."
        )

    def get_join_url(self, external_event: dict) -> str | None:
        return None

    def sync_transcript(self, external_event: dict) -> TranscriptSyncResult:
        return TranscriptSyncResult(
            status="unavailable",
            detail=f"{self._provider_name} meeting bot provider is disabled.",
        )


def normalize_vtt_transcript(content: str) -> str:
    lines: list[str] = []
    previous = ""
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "WEBVTT" or line.startswith(("NOTE", "STYLE", "REGION")):
            continue
        if "-->" in line or re.fullmatch(r"\d+", line):
            continue
        line = re.sub(r"<v\s+([^>]+)>", r"\1: ", line)
        line = re.sub(r"</v>", "", line)
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line and line != previous:
            lines.append(line)
            previous = line
    return "\n".join(lines)


def _token_url() -> str:
    tenant = settings.microsoft_graph_tenant_id or "common"
    return f"https://login.microsoftonline.com/{quote(tenant, safe='')}/oauth2/v2.0/token"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
