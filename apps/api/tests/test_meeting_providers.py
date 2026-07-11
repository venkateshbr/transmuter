from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import UUID

import pytest

from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.microsoft_graph import build_microsoft_graph_context, normalize_scope_set
from app.repositories.meeting import MeetingRepository
from app.services.meeting_providers import (
    MeetingInviteRequest,
    MeetingProviderConfigurationError,
    MeetingProviderTemporaryError,
    MicrosoftGraphMeetingProvider,
    normalize_vtt_transcript,
)

APP_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
CONNECTED_BY_ID = "00000000-0000-0000-0000-000000000002"
ENTRA_TENANT_ID = "11111111-1111-1111-1111-111111111111"
CLIENT_ID = "22222222-2222-2222-2222-222222222222"
ACCOUNT_ID = "33333333-3333-3333-3333-333333333333"
API_SCOPES = "User.Read Calendars.ReadWrite OnlineMeetings.Read OnlineMeetingTranscript.Read.All"
REQUEST_SCOPES = f"openid profile offline_access {API_SCOPES}"


class FakeResponse:
    def __init__(
        self,
        body: dict | None = None,
        text: str = "",
        status_code: int = 200,
    ) -> None:
        self._body = body or {}
        self.text = text
        self.status_code = status_code

    def json(self) -> dict:
        return self._body


class FakeRepo:
    def __init__(self) -> None:
        self.updates: list[dict] = []
        self.connection: dict | None = None
        self.cas_winner: dict | None = None

    def compare_and_swap_integration_connection_tokens(
        self,
        connection_id: str,
        expected_oauth_generation: int,
        expected_token_generation: int,
        data: dict,
    ) -> dict | None:
        if self.cas_winner is not None:
            self.connection = dict(self.cas_winner)
            self.cas_winner = None
            return None
        if (
            self.connection is None
            or self.connection.get("oauth_generation") != expected_oauth_generation
            or self.connection.get("token_generation") != expected_token_generation
        ):
            return None
        update = {
            "id": connection_id,
            **data,
            "token_generation": expected_token_generation + 1,
        }
        self.updates.append(update)
        self.connection = {**self.connection, **update}
        return update

    def get_integration_connection_by_id(self, _connection_id: str) -> dict | None:
        return dict(self.connection) if self.connection else None


class FakeHttp:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.queued: dict[tuple[str, str], list[FakeResponse]] = {}

    def queue(self, method: str, url_fragment: str, *responses: FakeResponse) -> None:
        self.queued[(method.casefold(), url_fragment)] = list(responses)

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        return self._send("post", url, kwargs)

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        return self._send("get", url, kwargs)

    def delete(self, url: str, **kwargs: object) -> FakeResponse:
        return self._send("delete", url, kwargs)

    def _send(self, method: str, url: str, kwargs: dict) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        for (queued_method, fragment), responses in self.queued.items():
            if queued_method == method and fragment in url and responses:
                return responses.pop(0)
        if "login.microsoftonline.com" in url:
            return FakeResponse(
                {
                    "access_token": "fresh-token",
                    "refresh_token": "rotated-refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": API_SCOPES,
                }
            )
        if url.endswith("/me"):
            return FakeResponse({"id": ACCOUNT_ID})
        if url.endswith("/transcripts"):
            return FakeResponse({"value": [{"id": "transcript-1"}]})
        if url.endswith("/content"):
            return FakeResponse(
                text="WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\n<v Vishwa>Welcome team</v>"
            )
        if method == "post":
            return FakeResponse(
                {
                    "id": "event-1",
                    "onlineMeeting": {
                        "id": "online-1",
                        "joinUrl": "https://teams.example/join",
                    },
                }
            )
        return FakeResponse()


@pytest.fixture(autouse=True)
def configured_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "supabase_schema", "transmuter_dev")
    monkeypatch.setattr(settings, "app_public_url", "https://transmuter-dev.example.com")
    monkeypatch.setattr(settings, "microsoft_graph_tenant_id", ENTRA_TENANT_ID)
    monkeypatch.setattr(settings, "microsoft_graph_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "microsoft_graph_client_secret", "client-secret")
    monkeypatch.setattr(settings, "microsoft_graph_redirect_uri", "")
    monkeypatch.setattr(settings, "microsoft_graph_scopes", REQUEST_SCOPES)
    monkeypatch.setattr(settings, "encryption_key", "test-encryption-key-with-enough-entropy")


def valid_connection(*, expired: bool = False, **overrides: object) -> dict:
    context = build_microsoft_graph_context(settings, "transmuter_dev")
    expires_at = datetime.now(UTC) + timedelta(minutes=-5 if expired else 30)
    row = {
        "id": "44444444-4444-4444-4444-444444444444",
        "tenant_id": str(APP_TENANT_ID),
        "provider": "microsoft_graph",
        "organizer_email": "organizer@example.com",
        "external_account_id": ACCOUNT_ID,
        "connected_by_user_id": CONNECTED_BY_ID,
        "access_token_encrypted": encrypt_secret("expired-token" if expired else "valid-token"),
        "refresh_token_encrypted": encrypt_secret("refresh-token"),
        "token_expires_at": expires_at.isoformat(),
        "scopes": list(normalize_scope_set(API_SCOPES)),
        "sync_status": "connected",
        "deployment_environment": context.environment,
        "deployment_schema": context.deployment_schema,
        "entra_tenant_id": context.tenant_id,
        "oauth_client_id": context.client_id,
        "oauth_redirect_uri": context.redirect_uri,
        "encryption_key_fingerprint": context.encryption_key_fingerprint,
        "context_fingerprint": context.context_fingerprint,
        "oauth_generation": 1,
        "token_generation": 0,
    }
    row.update(overrides)
    return row


def invite_request(organizer_email: str | None = "organizer@example.com") -> MeetingInviteRequest:
    return MeetingInviteRequest(
        organizer_email=organizer_email,
        start_date_time="2026-06-10T09:00:00",
        end_date_time="2026-06-10T10:00:00",
        time_zone="UTC",
        attendee_user_ids=["user-1"],
    )


def create_provider(
    connection: dict,
    repo: FakeRepo | None = None,
    http: FakeHttp | None = None,
) -> tuple[MicrosoftGraphMeetingProvider, FakeRepo, FakeHttp]:
    resolved_repo = repo or FakeRepo()
    resolved_http = http or FakeHttp()
    resolved_repo.connection = dict(connection)
    return (
        MicrosoftGraphMeetingProvider(
            connection,
            resolved_repo,  # type: ignore[arg-type]
            APP_TENANT_ID,
            resolved_http,
        ),
        resolved_repo,
        resolved_http,
    )


def test_graph_provider_refreshes_token_and_uses_consented_account() -> None:
    provider, repo, http = create_provider(valid_connection(expired=True))

    result = provider.create_invite(
        {"id": "meeting-1", "name": "Weekly review", "description": "Review"},
        [
            {
                "user_id": "user-1",
                "users": {"email": "attendee@example.com", "display_name": "Attendee"},
            }
        ],
        invite_request(),
    )

    assert result.join_url == "https://teams.example/join"
    event_call = [call for call in http.calls if call["url"].endswith("/events")][-1]
    assert f"/users/{ACCOUNT_ID}/events" in event_call["url"]
    assert event_call["json"]["attendees"][0]["emailAddress"]["address"] == ("attendee@example.com")
    assert event_call["headers"]["Authorization"] == "Bearer fresh-token"
    assert repo.updates[-1]["refresh_token_encrypted"] != encrypt_secret("refresh-token")
    assert repo.updates[-1]["scopes"] == list(normalize_scope_set(API_SCOPES))


def test_graph_provider_sends_recurring_series_payload() -> None:
    provider, _, http = create_provider(valid_connection())
    request = invite_request()
    request = MeetingInviteRequest(
        **{
            **request.__dict__,
            "recurrence": {
                "pattern": {"type": "weekly", "interval": 2, "daysOfWeek": ["wednesday"]},
                "range": {
                    "type": "endDate",
                    "startDate": "2026-06-10",
                    "endDate": "2026-09-30",
                    "recurrenceTimeZone": "UTC",
                },
            },
        }
    )

    provider.create_invite(
        {"id": "meeting-1", "name": "Biweekly review", "description": "Review"},
        [],
        request,
    )

    event_call = [call for call in http.calls if call["url"].endswith("/events")][-1]
    assert event_call["json"]["recurrence"]["pattern"]["interval"] == 2


def test_graph_provider_syncs_and_normalizes_vtt() -> None:
    provider, _, _ = create_provider(valid_connection())

    result = provider.sync_transcript(
        {"online_meeting_id": "online-1", "organizer_email": "organizer@example.com"}
    )

    assert result.status == "synced"
    assert result.transcript_text == "Vishwa: Welcome team"


def test_graph_provider_cancel_uses_only_persisted_account_id() -> None:
    provider, _, http = create_provider(valid_connection())

    provider.cancel_invite(
        {"external_event_id": "event-1", "organizer_email": "organizer@example.com"}
    )

    delete_call = next(call for call in http.calls if call["method"] == "delete")
    assert delete_call["url"].endswith(f"/users/{ACCOUNT_ID}/events/event-1")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("context_fingerprint", "v1:wrong"),
        ("deployment_schema", "transmuter"),
        ("encryption_key_fingerprint", "v1:wrong"),
        ("scopes", ["User.Read"]),
        ("external_account_id", "me"),
        ("sync_status", "reconnect_required"),
        ("oauth_generation", 0),
        ("token_generation", -1),
    ],
)
def test_graph_provider_rejects_stale_connection_before_decrypt_or_http(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    connection = valid_connection(**{field: value})
    provider, _, http = create_provider(connection)
    decrypt_calls = 0

    def fail_if_decrypted(_value: object) -> None:
        nonlocal decrypt_calls
        decrypt_calls += 1
        raise AssertionError("credential must not be decrypted")

    monkeypatch.setattr("app.services.meeting_providers.decrypt_secret", fail_if_decrypted)

    with pytest.raises(MeetingProviderConfigurationError, match="reconnection is required"):
        provider.create_invite({"name": "Review"}, [], invite_request())

    assert decrypt_calls == 0
    assert http.calls == []


def test_graph_provider_rejects_organizer_mismatch_before_decrypt_or_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, _, http = create_provider(valid_connection())
    monkeypatch.setattr(
        "app.services.meeting_providers.decrypt_secret",
        lambda _value: pytest.fail("credential must not be decrypted"),
    )

    with pytest.raises(MeetingProviderConfigurationError, match="does not match"):
        provider.create_invite({"name": "Review"}, [], invite_request("other@example.com"))

    assert http.calls == []


def test_refresh_invalid_grant_clears_all_token_material() -> None:
    http = FakeHttp()
    http.queue(
        "post",
        "login.microsoftonline.com",
        FakeResponse({"error": "invalid_grant", "error_description": "secret"}, status_code=400),
    )
    provider, repo, _ = create_provider(valid_connection(expired=True), http=http)

    with pytest.raises(MeetingProviderConfigurationError, match="reconnection is required"):
        provider.create_invite({"name": "Review"}, [], invite_request())

    assert repo.updates[-1]["access_token_encrypted"] is None
    assert repo.updates[-1]["refresh_token_encrypted"] is None
    assert repo.updates[-1]["token_expires_at"] is None
    assert repo.updates[-1]["sync_status"] == "reconnect_required"
    assert "secret" not in str(repo.updates[-1])


def test_refresh_scope_narrowing_clears_credentials() -> None:
    http = FakeHttp()
    http.queue(
        "post",
        "login.microsoftonline.com",
        FakeResponse(
            {
                "access_token": "fresh-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "User.Read",
            }
        ),
    )
    provider, repo, _ = create_provider(valid_connection(expired=True), http=http)

    with pytest.raises(MeetingProviderConfigurationError, match="reconnection is required"):
        provider.create_invite({"name": "Review"}, [], invite_request())

    assert repo.updates[-1]["refresh_token_encrypted"] is None


def test_refresh_scope_and_token_omission_retain_verified_values() -> None:
    http = FakeHttp()
    http.queue(
        "post",
        "login.microsoftonline.com",
        FakeResponse(
            {
                "access_token": "fresh-token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        ),
    )
    provider, repo, _ = create_provider(valid_connection(expired=True), http=http)

    provider.create_invite({"name": "Review"}, [], invite_request())

    assert repo.updates[-1]["scopes"] == list(normalize_scope_set(API_SCOPES))
    assert "refresh_token_encrypted" not in repo.updates[-1]


def test_refresh_rejects_present_invalid_refresh_token_without_persistence() -> None:
    http = FakeHttp()
    http.queue(
        "post",
        "login.microsoftonline.com",
        FakeResponse(
            {
                "access_token": "fresh-token",
                "refresh_token": "",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": API_SCOPES,
            }
        ),
    )
    provider, repo, _ = create_provider(valid_connection(expired=True), http=http)

    with pytest.raises(MeetingProviderTemporaryError, match="invalid token response"):
        provider.create_invite({"name": "Review"}, [], invite_request())

    assert repo.updates == []


def test_stale_refresh_cas_cannot_overwrite_new_oauth_generation() -> None:
    old_connection = valid_connection(expired=True, oauth_generation=1, token_generation=0)
    winner = valid_connection(
        oauth_generation=2,
        token_generation=0,
        access_token_encrypted=encrypt_secret("winner-access-token"),
        refresh_token_encrypted=encrypt_secret("winner-refresh-token"),
    )
    repo = FakeRepo()
    repo.cas_winner = winner
    provider, repo, http = create_provider(old_connection, repo=repo)

    provider.create_invite({"name": "Review"}, [], invite_request())

    assert repo.updates == []
    assert repo.connection is not None
    assert repo.connection["oauth_generation"] == 2
    assert decrypt_secret(repo.connection["refresh_token_encrypted"]) == "winner-refresh-token"
    event_call = [call for call in http.calls if call["url"].endswith("/events")][-1]
    assert event_call["headers"]["Authorization"] == "Bearer winner-access-token"


def test_stale_invalid_grant_cannot_clear_new_oauth_generation() -> None:
    old_connection = valid_connection(expired=True, oauth_generation=1, token_generation=0)
    winner = valid_connection(
        oauth_generation=2,
        token_generation=0,
        access_token_encrypted=encrypt_secret("winner-access-token"),
        refresh_token_encrypted=encrypt_secret("winner-refresh-token"),
    )
    repo = FakeRepo()
    repo.cas_winner = winner
    http = FakeHttp()
    http.queue(
        "post",
        "login.microsoftonline.com",
        FakeResponse({"error": "invalid_grant"}, status_code=400),
    )
    provider, repo, _ = create_provider(old_connection, repo=repo, http=http)

    provider.create_invite({"name": "Review"}, [], invite_request())

    assert repo.updates == []
    assert repo.connection is not None
    assert repo.connection["sync_status"] == "connected"
    assert decrypt_secret(repo.connection["refresh_token_encrypted"]) == "winner-refresh-token"


def test_refresh_and_graph_redirects_are_never_followed() -> None:
    refresh_http = FakeHttp()
    refresh_http.queue(
        "post",
        "login.microsoftonline.com",
        FakeResponse(status_code=302),
    )
    refresh_provider, _, _ = create_provider(valid_connection(expired=True), http=refresh_http)

    with pytest.raises(MeetingProviderTemporaryError, match="redirected"):
        refresh_provider.create_invite({"name": "Review"}, [], invite_request())
    assert refresh_http.calls[0]["follow_redirects"] is False

    graph_http = FakeHttp()
    graph_http.queue("post", "/events", FakeResponse(status_code=302))
    graph_provider, _, _ = create_provider(valid_connection(), http=graph_http)

    with pytest.raises(MeetingProviderTemporaryError, match="redirected"):
        graph_provider.create_invite({"name": "Review"}, [], invite_request())
    event_call = [call for call in graph_http.calls if call["url"].endswith("/events")][-1]
    assert event_call["follow_redirects"] is False


def test_token_cas_is_tenant_provider_and_both_generation_scoped() -> None:
    client = MagicMock()
    query = MagicMock()
    client.table.return_value = query
    for operation in (query.update, query.eq):
        operation.return_value = query
    query.execute.return_value = SimpleNamespace(
        data=[{"id": "connection-id", "oauth_generation": 3, "token_generation": 5}]
    )
    repo = MeetingRepository(client, APP_TENANT_ID)

    updated = repo.compare_and_swap_integration_connection_tokens(
        "connection-id",
        expected_oauth_generation=3,
        expected_token_generation=4,
        data={"access_token_encrypted": "ciphertext", "sync_status": "connected"},
    )

    assert updated is not None and updated["token_generation"] == 5
    assert query.eq.call_args_list == [
        call("tenant_id", str(APP_TENANT_ID)),
        call("provider", "microsoft_graph"),
        call("id", "connection-id"),
        call("oauth_generation", 3),
        call("token_generation", 4),
    ]
    payload = query.update.call_args.args[0]
    assert payload["token_generation"] == 5
    assert "tenant_id" not in payload and "provider" not in payload

    with pytest.raises(ValueError, match="Unsupported integration token update"):
        repo.compare_and_swap_integration_connection_tokens(
            "connection-id",
            expected_oauth_generation=3,
            expected_token_generation=4,
            data={"tenant_id": str(UUID(int=0))},
        )


def test_cached_get_401_refreshes_and_retries_once() -> None:
    http = FakeHttp()
    http.queue(
        "get",
        "/transcripts",
        FakeResponse(status_code=401),
        FakeResponse({"value": [{"id": "transcript-1"}]}),
    )
    provider, _, _ = create_provider(valid_connection(), http=http)

    result = provider.sync_transcript(
        {"online_meeting_id": "online-1", "organizer_email": "organizer@example.com"}
    )

    assert result.status == "synced"
    transcript_calls = [call for call in http.calls if call["url"].endswith("/transcripts")]
    assert len(transcript_calls) == 2


def test_cached_post_401_refreshes_but_does_not_replay_event_creation() -> None:
    http = FakeHttp()
    http.queue("post", "/events", FakeResponse(status_code=401))
    provider, _, _ = create_provider(valid_connection(), http=http)

    with pytest.raises(MeetingProviderTemporaryError, match="retry the operation"):
        provider.create_invite({"name": "Review"}, [], invite_request())

    event_calls = [call for call in http.calls if call["url"].endswith("/events")]
    assert len(event_calls) == 1


def test_graph_403_clears_credentials_without_retry() -> None:
    http = FakeHttp()
    http.queue("delete", "/events/event-1", FakeResponse(status_code=403))
    provider, repo, _ = create_provider(valid_connection(), http=http)

    with pytest.raises(MeetingProviderConfigurationError, match="reconnection is required"):
        provider.cancel_invite(
            {"external_event_id": "event-1", "organizer_email": "organizer@example.com"}
        )

    assert repo.updates[-1]["sync_status"] == "reconnect_required"
    delete_calls = [call for call in http.calls if call["method"] == "delete"]
    assert len(delete_calls) == 1


def test_normalize_vtt_transcript_strips_cues_and_duplicates() -> None:
    content = """WEBVTT

1
00:00:00.000 --> 00:00:01.000
<v Speaker>Approve the plan</v>
<v Speaker>Approve the plan</v>
"""

    assert normalize_vtt_transcript(content) == "Speaker: Approve the plan"
