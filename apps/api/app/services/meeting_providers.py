from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import quote
from uuid import UUID

import httpx

from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.database import get_supabase_schema
from app.core.microsoft_graph import (
    MicrosoftGraphConfigurationError,
    MicrosoftGraphContext,
    build_microsoft_graph_context,
    has_required_graph_scopes,
    normalize_scope_set,
)
from app.repositories.meeting import MeetingRepository

logger = logging.getLogger(__name__)


class MeetingProviderError(Exception):
    """Base error for meeting provider failures."""


class MeetingProviderConfigurationError(MeetingProviderError):
    """Provider is not configured for the current tenant."""


class MeetingProviderTemporaryError(MeetingProviderError):
    """Provider failed without invalidating the stored connection."""


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

    def cancel_invite(self, external_event: dict) -> None: ...


class MicrosoftGraphMeetingProvider:
    def __init__(
        self,
        connection: dict,
        repo: MeetingRepository,
        tenant_id: UUID,
        http_client: object = httpx,
    ) -> None:
        self._connection = connection
        self._repo = repo
        self._tenant_id = str(tenant_id)
        self._http = http_client
        try:
            self._context: MicrosoftGraphContext | None = build_microsoft_graph_context(
                settings,
                get_supabase_schema(),
            )
        except MicrosoftGraphConfigurationError:
            self._context = None

    def create_invite(
        self,
        meeting: dict,
        attendees: list[dict],
        request: MeetingInviteRequest,
    ) -> MeetingInviteResult:
        user_id = self._graph_user_path(request.organizer_email)
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
        response = self._graph_request(
            "post",
            f"https://graph.microsoft.com/v1.0/{user_id}/events",
            organizer_email=request.organizer_email,
            json=event_payload,
            timeout=10,
        )
        body = self._response_json(response)
        online = body.get("onlineMeeting") or {}
        return MeetingInviteResult(
            external_event_id=body.get("id"),
            online_meeting_id=online.get("id"),
            join_url=online.get("joinUrl"),
            organizer_email=self._connection.get("organizer_email"),
        )

    def get_join_url(self, external_event: dict) -> str | None:
        return external_event.get("join_url")

    def cancel_invite(self, external_event: dict) -> None:
        external_event_id = external_event.get("external_event_id")
        if not external_event_id:
            raise MeetingProviderConfigurationError(
                "The synced Teams event does not include a Microsoft event id."
            )
        organizer_email = external_event.get("organizer_email")
        user_id = self._graph_user_path(organizer_email)
        self._graph_request(
            "delete",
            f"https://graph.microsoft.com/v1.0/{user_id}/events/{quote(str(external_event_id), safe='')}",
            organizer_email=organizer_email,
            timeout=10,
        )

    def sync_transcript(self, external_event: dict) -> TranscriptSyncResult:
        organizer_email = external_event.get("organizer_email")
        user_id = self._graph_user_path(organizer_email)
        online_meeting_id = external_event.get("online_meeting_id")
        if not online_meeting_id and external_event.get("join_url"):
            online_meeting_id = self._find_online_meeting_id(
                user_id,
                external_event["join_url"],
                organizer_email,
            )
        if not online_meeting_id:
            return TranscriptSyncResult(
                status="unavailable",
                detail="The synced Teams event does not include an online meeting id yet.",
            )

        transcripts_response = self._graph_request(
            "get",
            f"https://graph.microsoft.com/v1.0/{user_id}/onlineMeetings/{quote(online_meeting_id, safe='')}/transcripts",
            organizer_email=organizer_email,
            timeout=10,
        )
        transcripts = self._response_json(transcripts_response).get("value") or []
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

        content_response = self._graph_request(
            "get",
            f"https://graph.microsoft.com/v1.0/{user_id}/onlineMeetings/{quote(online_meeting_id, safe='')}/transcripts/{quote(transcript_id, safe='')}/content",
            organizer_email=organizer_email,
            accept="text/vtt",
            timeout=15,
        )
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

    def _access_token(self, organizer_email: str | None = None) -> tuple[str, bool]:
        self._validate_connection(organizer_email)
        token = decrypt_secret(self._connection.get("access_token_encrypted"))
        expires_at = _parse_datetime(self._connection.get("token_expires_at"))
        if token and expires_at and expires_at > datetime.now(UTC) + timedelta(minutes=5):
            return token, True
        return self._refresh_access_token(), False

    def _refresh_access_token(self) -> str:
        context = self._require_context()
        self._validate_connection()
        expected_oauth_generation = self._oauth_generation()
        expected_token_generation = self._token_generation()
        refresh_token = decrypt_secret(self._connection.get("refresh_token_encrypted"))
        if not refresh_token:
            if not self._clear_credentials(
                expected_token_generation,
                expected_oauth_generation,
            ):
                winner_token = self._winner_access_token()
                if winner_token:
                    return winner_token
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        try:
            response = self._http.post(
                context.token_url,
                data={
                    "client_id": context.client_id,
                    "client_secret": context.reveal_client_secret_for_token_exchange(),
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "scope": context.scope_value,
                },
                timeout=10,
                follow_redirects=False,
            )
        except httpx.RequestError as exc:
            raise MeetingProviderTemporaryError(
                "Microsoft Graph is temporarily unavailable."
            ) from exc

        body = self._response_json(response)
        response_status = self._status_code(response)
        if 300 <= response_status < 400:
            raise MeetingProviderTemporaryError("Microsoft Graph token endpoint redirected.")
        if response_status >= 400:
            if body.get("error") == "invalid_grant":
                if not self._clear_credentials(
                    expected_token_generation,
                    expected_oauth_generation,
                ):
                    winner_token = self._winner_access_token()
                    if winner_token:
                        return winner_token
                raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
            if response_status == 429 or response_status >= 500:
                raise MeetingProviderTemporaryError("Microsoft Graph is temporarily unavailable.")
            raise MeetingProviderConfigurationError("Microsoft Graph token refresh failed.")

        token = body.get("access_token")
        if not isinstance(token, str) or not token:
            raise MeetingProviderTemporaryError(
                "Microsoft Graph returned an invalid token response."
            )
        if str(body.get("token_type") or "").casefold() != "bearer":
            raise MeetingProviderTemporaryError(
                "Microsoft Graph returned an invalid token response."
            )
        expires_in = _bounded_expires_in(body.get("expires_in"))
        previous_scopes = normalize_scope_set(self._connection.get("scopes") or [])
        if "scope" in body:
            returned_scope = body.get("scope")
            if not isinstance(returned_scope, str) or not returned_scope.strip():
                raise MeetingProviderTemporaryError(
                    "Microsoft Graph returned an invalid token response."
                )
            granted_scopes = normalize_scope_set(returned_scope)
        else:
            granted_scopes = previous_scopes
        if not has_required_graph_scopes(granted_scopes):
            if not self._clear_credentials(
                expected_token_generation,
                expected_oauth_generation,
            ):
                winner_token = self._winner_access_token()
                if winner_token:
                    return winner_token
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")

        self._validate_refreshed_account(
            token,
            expected_token_generation,
            expected_oauth_generation,
        )
        update = {
            "access_token_encrypted": encrypt_secret(token),
            "token_expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
            "scopes": list(granted_scopes),
            "sync_status": "connected",
            "sync_error": None,
            "last_synced_at": datetime.now(UTC).isoformat(),
        }
        if "refresh_token" in body:
            replacement_refresh = body.get("refresh_token")
            if not isinstance(replacement_refresh, str) or not replacement_refresh:
                raise MeetingProviderTemporaryError(
                    "Microsoft Graph returned an invalid token response."
                )
            update["refresh_token_encrypted"] = encrypt_secret(replacement_refresh)
        if self._compare_and_swap_connection(
            expected_oauth_generation,
            expected_token_generation,
            update,
        ):
            return token
        winner_token = self._winner_access_token()
        if winner_token:
            return winner_token
        raise MeetingProviderTemporaryError(
            "Microsoft Graph authorization changed; retry the operation."
        )

    def _find_online_meeting_id(
        self,
        user_id: str,
        join_url: str,
        organizer_email: str | None,
    ) -> str | None:
        escaped_join_url = join_url.replace("'", "''")
        response = self._graph_request(
            "get",
            f"https://graph.microsoft.com/v1.0/{user_id}/onlineMeetings",
            organizer_email=organizer_email,
            params={"$filter": f"JoinWebUrl eq '{escaped_join_url}'"},
            timeout=10,
        )
        rows = self._response_json(response).get("value") or []
        return rows[0].get("id") if rows else None

    def _graph_request(
        self,
        method: str,
        url: str,
        *,
        organizer_email: str | None,
        accept: str | None = None,
        **kwargs: object,
    ) -> object:
        token, cached = self._access_token(organizer_email)
        response = self._send_graph_request(method, url, token, accept=accept, **kwargs)
        if self._status_code(response) == 401 and cached:
            refreshed_token = self._refresh_access_token()
            if method.casefold() == "post":
                raise MeetingProviderTemporaryError(
                    "Microsoft Graph authorization was refreshed; retry the operation."
                )
            response = self._send_graph_request(
                method,
                url,
                refreshed_token,
                accept=accept,
                **kwargs,
            )

        response_status = self._status_code(response)
        if 300 <= response_status < 400:
            raise MeetingProviderTemporaryError("Microsoft Graph redirected the request.")
        if response_status == 401 or response_status == 403:
            self._clear_credentials()
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        if response_status == 429 or response_status >= 500:
            raise MeetingProviderTemporaryError("Microsoft Graph is temporarily unavailable.")
        if response_status >= 400:
            raise MeetingProviderError("Microsoft Graph rejected the request.")
        return response

    def _send_graph_request(
        self,
        method: str,
        url: str,
        token: str,
        *,
        accept: str | None,
        **kwargs: object,
    ) -> object:
        headers = self._headers(token)
        if accept:
            headers["Accept"] = accept
        try:
            request_method = getattr(self._http, method.casefold())
            return request_method(url, headers=headers, follow_redirects=False, **kwargs)
        except httpx.RequestError as exc:
            raise MeetingProviderTemporaryError(
                "Microsoft Graph is temporarily unavailable."
            ) from exc

    def _validate_refreshed_account(
        self,
        token: str,
        expected_token_generation: int,
        expected_oauth_generation: int,
    ) -> None:
        try:
            response = self._http.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=self._headers(token),
                params={"$select": "id"},
                timeout=10,
                follow_redirects=False,
            )
        except httpx.RequestError as exc:
            raise MeetingProviderTemporaryError(
                "Microsoft Graph is temporarily unavailable."
            ) from exc
        response_status = self._status_code(response)
        if 300 <= response_status < 400:
            raise MeetingProviderTemporaryError("Microsoft Graph redirected the request.")
        if response_status == 401 or response_status == 403:
            self._clear_credentials(expected_token_generation, expected_oauth_generation)
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        if response_status == 429 or response_status >= 500:
            raise MeetingProviderTemporaryError("Microsoft Graph is temporarily unavailable.")
        if response_status >= 400:
            raise MeetingProviderConfigurationError("Microsoft Graph account verification failed.")
        account_id = self._response_json(response).get("id")
        if account_id != self._connection.get("external_account_id"):
            self._clear_credentials(expected_token_generation, expected_oauth_generation)
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")

    def _validate_connection(self, organizer_email: str | None = None) -> None:
        context = self._require_context()
        expected = {
            "provider": "microsoft_graph",
            "tenant_id": self._tenant_id,
            "sync_status": "connected",
            "deployment_environment": context.environment,
            "deployment_schema": context.deployment_schema,
            "entra_tenant_id": context.tenant_id,
            "oauth_client_id": context.client_id,
            "oauth_redirect_uri": context.redirect_uri,
            "encryption_key_fingerprint": context.encryption_key_fingerprint,
            "context_fingerprint": context.context_fingerprint,
        }
        if any(str(self._connection.get(key) or "") != value for key, value in expected.items()):
            mismatched = [
                key
                for key, value in expected.items()
                if str(self._connection.get(key) or "") != value
            ]
            logger.warning(
                "microsoft_graph_connection_invalid connection_id=%s sync_status=%s "
                "oauth_generation=%s mismatched_fields=%s",
                self._connection.get("id"),
                self._connection.get("sync_status"),
                self._connection.get("oauth_generation"),
                mismatched,
            )
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        if not _canonical_uuid(self._connection.get("external_account_id")):
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        if not _canonical_uuid(self._connection.get("connected_by_user_id")):
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        oauth_generation = self._connection.get("oauth_generation")
        if (
            isinstance(oauth_generation, bool)
            or not isinstance(oauth_generation, int)
            or oauth_generation <= 0
        ):
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        token_generation = self._connection.get("token_generation")
        if (
            isinstance(token_generation, bool)
            or not isinstance(token_generation, int)
            or token_generation < 0
        ):
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        if not has_required_graph_scopes(self._connection.get("scopes") or []):
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        if organizer_email:
            connected_email = str(self._connection.get("organizer_email") or "")
            if organizer_email.strip().casefold() != connected_email.strip().casefold():
                raise MeetingProviderConfigurationError(
                    "The selected Microsoft organizer does not match the connected account."
                )

    def _graph_user_path(self, organizer_email: str | None) -> str:
        self._validate_connection(organizer_email)
        return f"users/{quote(str(self._connection['external_account_id']), safe='')}"

    def _require_context(self) -> MicrosoftGraphContext:
        if self._context is None:
            raise MeetingProviderConfigurationError("Microsoft Graph integration is unavailable.")
        return self._context

    def _clear_credentials(
        self,
        expected_token_generation: int | None = None,
        expected_oauth_generation: int | None = None,
    ) -> bool:
        generation = (
            self._token_generation()
            if expected_token_generation is None
            else expected_token_generation
        )
        oauth_generation = (
            self._oauth_generation()
            if expected_oauth_generation is None
            else expected_oauth_generation
        )
        return self._compare_and_swap_connection(
            oauth_generation,
            generation,
            {
                "access_token_encrypted": None,
                "refresh_token_encrypted": None,
                "token_expires_at": None,
                "sync_status": "reconnect_required",
                "sync_error": "Microsoft Graph reconnection is required.",
            },
        )

    def _compare_and_swap_connection(
        self,
        expected_oauth_generation: int,
        expected_token_generation: int,
        update: dict,
    ) -> bool:
        updated = self._repo.compare_and_swap_integration_connection_tokens(
            self._connection["id"],
            expected_oauth_generation,
            expected_token_generation,
            update,
        )
        if updated:
            self._connection = {**self._connection, **updated}
            return True
        reloaded = self._repo.get_integration_connection_by_id(self._connection["id"])
        if reloaded:
            self._connection = reloaded
        return False

    def _winner_access_token(self) -> str | None:
        try:
            self._validate_connection()
        except MeetingProviderConfigurationError:
            return None
        token = decrypt_secret(self._connection.get("access_token_encrypted"))
        expires_at = _parse_datetime(self._connection.get("token_expires_at"))
        if token and expires_at and expires_at > datetime.now(UTC) + timedelta(minutes=5):
            return token
        return None

    def _token_generation(self) -> int:
        value = self._connection.get("token_generation")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        return value

    def _oauth_generation(self) -> int:
        value = self._connection.get("oauth_generation")
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise MeetingProviderConfigurationError("Microsoft Graph reconnection is required.")
        return value

    @staticmethod
    def _status_code(response: object) -> int:
        return int(getattr(response, "status_code", 200))

    @staticmethod
    def _response_json(response: object) -> dict:
        try:
            body = response.json()
        except (TypeError, ValueError):
            return {}
        return body if isinstance(body, dict) else {}

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

    def cancel_invite(self, external_event: dict) -> None:
        raise MeetingProviderConfigurationError(
            f"{self._provider_name} meeting bot provider is disabled."
        )

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


def _bounded_expires_in(value: object) -> int:
    if isinstance(value, bool):
        raise MeetingProviderTemporaryError("Microsoft Graph returned an invalid token response.")
    try:
        expires_in = int(value)
    except (TypeError, ValueError) as exc:
        raise MeetingProviderTemporaryError(
            "Microsoft Graph returned an invalid token response."
        ) from exc
    if expires_in <= 0 or expires_in > 86400:
        raise MeetingProviderTemporaryError("Microsoft Graph returned an invalid token response.")
    return expires_in


def _canonical_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


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
