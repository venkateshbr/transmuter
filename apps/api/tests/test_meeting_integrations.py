from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, call
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.repositories.meeting_integrations import MeetingIntegrationRepository
from app.routers import meeting_integrations as integration_router
from app.services import meeting_integrations as integration_service
from app.services.meeting_integrations import (
    MICROSOFT_GRAPH_ME_URL,
    OAUTH_BINDING_COOKIE_MAX_AGE_SECONDS,
    OAUTH_BINDING_COOKIE_PATH,
    OAUTH_BINDING_COOKIE_PREFIX,
    MeetingIntegrationService,
    OAuthCallbackForm,
    OAuthCallbackResult,
    OAuthCallbackTransport,
    OAuthStartResult,
    oauth_binding_cookie_name,
    parse_oauth_state,
)

TENANT_ID = UUID("10000000-0000-0000-0000-000000000001")
OTHER_TENANT_ID = UUID("10000000-0000-0000-0000-000000000002")
ACTOR_ID = UUID("20000000-0000-0000-0000-000000000001")
ACCOUNT_ID = "30000000-0000-0000-0000-000000000001"
CONNECTION_ID = "40000000-0000-0000-0000-000000000001"
CLIENT_ID = "50000000-0000-0000-0000-000000000001"
ENTRA_TENANT_ID = "60000000-0000-0000-0000-000000000001"
ENCRYPTION_KEY = "integration-test-encryption-key-with-more-than-32-bytes"


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        environment="development",
        app_public_url="https://app.example.com",
        microsoft_graph_tenant_id=ENTRA_TENANT_ID,
        microsoft_graph_client_id=CLIENT_ID,
        microsoft_graph_client_secret="client-secret-never-persisted",
        microsoft_graph_redirect_uri=(
            "https://app.example.com/api/meeting-integrations/microsoft/oauth/callback"
        ),
        microsoft_graph_scopes=(
            "openid profile offline_access User.Read Calendars.ReadWrite "
            "OnlineMeetings.Read OnlineMeetingTranscript.Read.All"
        ),
        encryption_key=ENCRYPTION_KEY,
        recall_meeting_bot_enabled=False,
        fireflies_meeting_bot_enabled=False,
    )


def _actor(*, role: str = "transformation_office", tenant_id: UUID = TENANT_ID) -> CurrentUser:
    return CurrentUser(
        id=ACTOR_ID,
        tenant_id=tenant_id,
        role=role,
        status="active",
        must_change_password=False,
    )


class FakeAdmin:
    def __init__(self, app_metadata: dict[str, Any] | None = None) -> None:
        self.app_metadata = app_metadata or {
            "transmuter_authorization_transmuter_dev": {
                "tenant_id": str(TENANT_ID),
                "role": "transformation_office",
            }
        }

    def get_user_by_id(self, _user_id: str) -> SimpleNamespace:
        return SimpleNamespace(user=SimpleNamespace(app_metadata=self.app_metadata))


class FakeClient:
    def __init__(self, app_metadata: dict[str, Any] | None = None) -> None:
        self.auth = SimpleNamespace(admin=FakeAdmin(app_metadata))


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def log(self, **data: Any) -> dict[str, Any]:
        self.events.append(data)
        return data


class FakeRepository:
    def __init__(self) -> None:
        self.created_state: dict[str, Any] | None = None
        self.consumed = False
        self.consume_calls: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []
        self.completed: list[dict[str, Any]] = []
        self.purged: list[dict[str, Any]] = []
        self.connections: list[dict[str, Any]] = []
        self.disconnect_result = True
        self.disconnect_calls: list[UUID] = []
        self.actor: dict[str, Any] | None = {
            "id": str(ACTOR_ID),
            "tenant_id": str(TENANT_ID),
            "role": "transformation_office",
            "status": "active",
            "must_change_password": False,
        }

    def list_connections(self) -> list[dict[str, Any]]:
        return self.connections

    def purge_expired_oauth_states(self, **data: Any) -> None:
        self.purged.append(data)

    def create_oauth_state(self, data: dict[str, Any]) -> dict[str, Any]:
        created_at = datetime.now(UTC)
        self.created_state = {
            "id": "70000000-0000-0000-0000-000000000001",
            "oauth_generation": 1,
            "tenant_id": str(TENANT_ID),
            "provider": "microsoft_graph",
            **data,
            "created_at": created_at.isoformat(),
            "expires_at": (created_at + integration_service.timedelta(minutes=10)).isoformat(),
        }
        return dict(self.created_state)

    def consume_oauth_state(self, **data: Any) -> dict[str, Any] | None:
        self.consume_calls.append(data)
        if self.consumed or self.created_state is None:
            return None
        if data["state_digest"] != self.created_state["state_digest"]:
            return None
        if data["browser_binding_digest"] != self.created_state["browser_binding_digest"]:
            return None
        if data["context_fingerprint"] != self.created_state["context_fingerprint"]:
            return None
        self.consumed = True
        state = dict(self.created_state)
        state["consumed_at"] = data["consumed_at"].isoformat()
        if data.get("terminal"):
            state[f"{data['terminal']}_at"] = state["consumed_at"]
            state["pkce_verifier_encrypted"] = None
        return state

    def fail_oauth_state(self, **data: Any) -> bool:
        self.failed.append(data)
        return True

    def get_actor(self, _user_id: str) -> dict[str, Any] | None:
        return self.actor

    def complete_microsoft_graph_oauth(self, **data: Any) -> str:
        self.completed.append(data)
        return CONNECTION_ID

    def disconnect_microsoft_graph_connection(
        self,
        connection_id: UUID,
        _actor_id: UUID,
    ) -> bool:
        self.disconnect_calls.append(connection_id)
        return self.disconnect_result


class FakeResponse:
    def __init__(self, body: dict[str, Any], *, status_error: bool = False) -> None:
        self._body = body
        self._status_error = status_error
        self.is_redirect = False

    def raise_for_status(self) -> None:
        if self._status_error:
            raise RuntimeError("sentinel-provider-body-must-not-escape")

    def json(self) -> dict[str, Any]:
        return self._body


class FakeHttp:
    def __init__(self, token_body: dict[str, Any] | None = None) -> None:
        self.token_body = token_body or _valid_token_body()
        self.posts: list[dict[str, Any]] = []
        self.gets: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.posts.append({"url": url, **kwargs})
        return FakeResponse(self.token_body)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.gets.append({"url": url, **kwargs})
        if url == MICROSOFT_GRAPH_ME_URL:
            return FakeResponse(
                {
                    "id": ACCOUNT_ID,
                    "mail": "organizer@example.com",
                    "userPrincipalName": "organizer@example.com",
                }
            )
        raise AssertionError(f"unexpected HTTP GET: {url}")


def _valid_token_body() -> dict[str, Any]:
    return {
        "token_type": "Bearer",
        "access_token": "sentinel-access-token",
        "refresh_token": "sentinel-refresh-token",
        "expires_in": 3600,
        "scope": (
            "User.Read Calendars.ReadWrite OnlineMeetings.Read OnlineMeetingTranscript.Read.All"
        ),
        "id_token": "sentinel-id-token",
    }


def _service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tenant_id: UUID = TENANT_ID,
    http: FakeHttp | None = None,
    client: FakeClient | None = None,
) -> tuple[MeetingIntegrationService, FakeRepository, FakeAudit, FakeHttp]:
    monkeypatch.setattr(settings, "encryption_key", ENCRYPTION_KEY)
    repo = FakeRepository()
    audit = FakeAudit()
    http_client = http or FakeHttp()
    service = MeetingIntegrationService(
        client or FakeClient(),
        tenant_id,
        settings_obj=_settings(),
        deployment_schema="transmuter_dev",
        http_client=http_client,
    )
    service._repo = repo  # type: ignore[assignment]
    return service, repo, audit, http_client


def _started_callback(
    service: MeetingIntegrationService,
) -> tuple[OAuthCallbackForm, str, str]:
    start = service.start_oauth(_actor())
    query = parse_qs(urlsplit(start.authorization_url).query)
    state = query["state"][0]
    assert start.cookie_name == oauth_binding_cookie_name(state)
    assert start.cookie_value is not None
    return (
        OAuthCallbackForm(state=state, code="sentinel-authorization-code"),
        start.cookie_value,
        state,
    )


def _transport(**overrides: str | None) -> OAuthCallbackTransport:
    values: dict[str, str | None] = {
        "origin": "https://login.microsoftonline.com",
        "host": "app.example.com",
        "scheme": "https",
        "fetch_site": "cross-site",
        "fetch_mode": "navigate",
        "fetch_dest": "document",
    }
    values.update(overrides)
    return OAuthCallbackTransport(**values)  # type: ignore[arg-type]


def test_start_uses_tenant_routable_one_time_state_pkce_nonce_and_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repo, _, _ = _service(monkeypatch)

    result = service.start_oauth(_actor())

    assert result.configured is True
    assert result.cookie_value is not None
    assert len(result.cookie_value) == 43
    query = parse_qs(urlsplit(result.authorization_url).query)
    state = query["state"][0]
    routed_tenant, raw_state = parse_oauth_state(state)
    assert routed_tenant == TENANT_ID
    assert len(raw_state) == 48
    assert len(state) == 64
    assert query["response_mode"] == ["form_post"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == [
        "https://app.example.com/api/meeting-integrations/microsoft/oauth/callback"
    ]
    assert repo.created_state is not None
    stored = repo.created_state
    verifier = decrypt_secret(stored["pkce_verifier_encrypted"])
    assert verifier is not None
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert query["code_challenge"] == [expected_challenge]
    assert stored["nonce_digest"] == hashlib.sha256(query["nonce"][0].encode("ascii")).hexdigest()
    serialized = json.dumps(stored)
    assert state not in serialized
    assert result.cookie_value not in serialized
    assert query["nonce"][0] not in serialized
    assert verifier not in serialized
    assert stored["state_digest"] in str(result.cookie_name)
    assert datetime.fromisoformat(stored["expires_at"]) - datetime.fromisoformat(
        stored["created_at"]
    ) <= integration_service.timedelta(minutes=10)
    assert repo.purged


@pytest.mark.parametrize(
    "state",
    ["", "a" * 63, "a" * 65, "!" * 64, "=" * 64],
)
def test_state_parser_rejects_malformed_or_noncanonical_values(state: str) -> None:
    with pytest.raises(ValueError):
        parse_oauth_state(state)


@pytest.mark.parametrize(
    ("transport_override", "binding_override", "tenant_id"),
    [
        ({"origin": None}, None, TENANT_ID),
        ({"origin": "null"}, None, TENANT_ID),
        ({"origin": "http://login.microsoftonline.com"}, None, TENANT_ID),
        ({"host": "other.example.com"}, None, TENANT_ID),
        ({"scheme": "http"}, None, TENANT_ID),
        ({"fetch_site": "same-site"}, None, TENANT_ID),
        ({}, "wrong-cookie", TENANT_ID),
        ({}, None, OTHER_TENANT_ID),
    ],
)
def test_callback_transport_binding_and_tenant_fail_before_state_or_http(
    monkeypatch: pytest.MonkeyPatch,
    transport_override: dict[str, str | None],
    binding_override: str | None,
    tenant_id: UUID,
) -> None:
    service, repo, _, http = _service(monkeypatch, tenant_id=tenant_id)
    start_service, start_repo, _, _ = _service(monkeypatch)
    form, binding, _ = _started_callback(start_service)
    repo.created_state = start_repo.created_state

    result = service.complete_callback(
        form,
        _transport(**transport_override),
        binding_override if binding_override is not None else binding,
    )

    assert result == OAuthCallbackResult("failed", "invalid_callback")
    assert repo.consume_calls == []
    assert http.posts == []
    assert http.gets == []
    assert repo.completed == []


def test_valid_provider_cancel_is_consumed_once_without_microsoft_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repo, _, http = _service(monkeypatch)
    form, binding, state = _started_callback(service)
    cancelled = OAuthCallbackForm(state=state, error="access_denied")

    first = service.complete_callback(cancelled, _transport(), binding)
    second = service.complete_callback(cancelled, _transport(), binding)

    assert first == OAuthCallbackResult("cancelled", "authorization_cancelled")
    assert second == OAuthCallbackResult("failed", "invalid_callback")
    assert repo.consume_calls[0]["terminal"] == "cancelled"
    assert http.posts == []
    assert http.gets == []
    assert form.code not in json.dumps(repo.consume_calls, default=str)


@pytest.mark.parametrize(
    "actor_update",
    [
        None,
        {"status": "pending"},
        {"status": "ghost"},
        {"status": "deactivated"},
        {"must_change_password": True},
        {"role": "viewer"},
        {"tenant_id": str(OTHER_TENANT_ID)},
    ],
)
def test_actor_drift_fails_before_token_exchange(
    monkeypatch: pytest.MonkeyPatch,
    actor_update: dict[str, Any] | None,
) -> None:
    service, repo, _, http = _service(monkeypatch)
    form, binding, _ = _started_callback(service)
    if actor_update is None:
        repo.actor = None
    else:
        assert repo.actor is not None
        repo.actor.update(actor_update)

    result = service.complete_callback(form, _transport(), binding)

    assert result == OAuthCallbackResult("failed", "consent_invalid")
    assert http.posts == []
    assert http.gets == []
    assert repo.completed == []
    assert repo.failed[-1]["failure_code"] == "consent_invalid"


def test_wrong_scoped_auth_metadata_fails_before_token_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient(
        {
            "transmuter_authorization_transmuter_dev": {
                "tenant_id": str(OTHER_TENANT_ID),
                "role": "transformation_office",
            }
        }
    )
    service, repo, _, http = _service(monkeypatch, client=client)
    form, binding, _ = _started_callback(service)

    result = service.complete_callback(form, _transport(), binding)

    assert result == OAuthCallbackResult("failed", "consent_invalid")
    assert http.posts == []
    assert repo.completed == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("token_type", None),
        ("token_type", "MAC"),
        ("access_token", ""),
        ("refresh_token", ""),
        ("expires_in", 0),
        ("expires_in", 100_000),
        ("scope", "User.Read Calendars.ReadWrite"),
        ("scope", None),
        ("id_token", ""),
    ],
)
def test_partial_or_invalid_initial_consent_never_writes_connection(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
) -> None:
    token_body = _valid_token_body()
    token_body[field] = value
    service, repo, _, http = _service(monkeypatch, http=FakeHttp(token_body))
    form, binding, _ = _started_callback(service)

    result = service.complete_callback(form, _transport(), binding)

    assert result == OAuthCallbackResult("failed", "consent_invalid")
    assert len(http.posts) == 1
    assert http.gets == []
    assert repo.completed == []
    assert repo.failed[-1]["failure_code"] == "consent_invalid"


def test_success_validates_identity_and_persists_only_encrypted_actual_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repo, _, http = _service(monkeypatch)
    form, binding, _ = _started_callback(service)
    monkeypatch.setattr(
        integration_service,
        "validate_microsoft_id_token",
        lambda *_args, **_kwargs: {
            "oid": ACCOUNT_ID,
            "tid": ENTRA_TENANT_ID,
            "sub": "subject-id",
        },
    )

    result = service.complete_callback(form, _transport(), binding)

    assert result == OAuthCallbackResult("connected")
    assert len(http.posts) == 1
    assert http.posts[0]["data"]["code_verifier"]
    assert http.posts[0]["data"]["client_secret"] == "client-secret-never-persisted"
    assert [call["url"] for call in http.gets] == [MICROSOFT_GRAPH_ME_URL]
    assert len(repo.completed) == 1
    completed = repo.completed[0]
    assert completed["external_account_id"] == ACCOUNT_ID
    assert completed["scopes"] == (
        "Calendars.ReadWrite",
        "OnlineMeetings.Read",
        "OnlineMeetingTranscript.Read.All",
        "User.Read",
    )
    assert decrypt_secret(completed["access_token_encrypted"]) == "sentinel-access-token"
    assert decrypt_secret(completed["refresh_token_encrypted"]) == "sentinel-refresh-token"
    persisted = json.dumps(completed, default=str)
    assert "sentinel-access-token" not in persisted
    assert "sentinel-refresh-token" not in persisted
    assert "sentinel-id-token" not in persisted


def test_list_marks_legacy_and_context_mismatch_as_reconnect_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repo, _, _ = _service(monkeypatch)
    context = service._context()
    valid_row = {
        "id": CONNECTION_ID,
        "provider": "microsoft_graph",
        "sync_status": "connected",
        "deployment_environment": context.environment,
        "deployment_schema": context.deployment_schema,
        "entra_tenant_id": context.tenant_id,
        "oauth_client_id": context.client_id,
        "oauth_redirect_uri": context.redirect_uri,
        "context_fingerprint": context.context_fingerprint,
        "oauth_generation": 1,
        "token_generation": 0,
        "external_account_id": ACCOUNT_ID,
        "connected_by_user_id": str(ACTOR_ID),
        "scopes": sorted(integration_service.REQUIRED_MICROSOFT_GRAPH_API_SCOPES),
    }
    repo.connections = [valid_row, {**valid_row, "id": "legacy", "context_fingerprint": None}]

    result = service.list_integrations()

    assert result["items"][0]["effective_status"] == "connected"
    assert result["items"][0]["reconnect_required"] is False
    assert result["items"][1]["effective_status"] == "reconnect_required"
    assert result["items"][1]["reconnect_reason"] == "context_changed"


def test_disconnect_is_local_tenant_command_without_graph_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repo, _, http = _service(monkeypatch)

    assert service.disconnect(_actor(), UUID(CONNECTION_ID)) is True
    assert repo.disconnect_calls == [UUID(CONNECTION_ID)]
    assert http.posts == [] and http.gets == []

    repo.disconnect_result = False
    assert service.disconnect(_actor(), UUID(CONNECTION_ID)) is False


def test_repository_forces_tenant_provider_and_purges_across_rotated_contexts() -> None:
    client = MagicMock()
    query = MagicMock()
    client.table.return_value = query
    for operation in (query.delete, query.update, query.eq, query.lt, query.is_):
        operation.return_value = query
    client.rpc.return_value = query
    query.execute.return_value = SimpleNamespace(data="70000000-0000-0000-0000-000000000001")
    repo = MeetingIntegrationRepository(client, TENANT_ID)

    repo.create_oauth_state(
        {
            "tenant_id": str(OTHER_TENANT_ID),
            "provider": "wrong-provider",
            "state_digest": "a" * 64,
            "browser_binding_digest": "b" * 64,
            "initiated_by_user_id": str(ACTOR_ID),
            "pkce_verifier_encrypted": "encrypted-verifier",
            "nonce_digest": "c" * 64,
            "deployment_environment": "development",
            "deployment_schema": "transmuter_dev",
            "entra_tenant_id": ENTRA_TENANT_ID,
            "oauth_client_id": CLIENT_ID,
            "oauth_redirect_uri": (
                "https://app.example.com/api/meeting-integrations/microsoft/oauth/callback"
            ),
            "encryption_key_fingerprint": "v1:key",
            "context_fingerprint": "v1:context",
            "authorization_scopes": ["openid", "User.Read"],
            "required_api_scopes": ["User.Read"],
        }
    )
    rpc_name, inserted = client.rpc.call_args.args
    assert rpc_name == "create_microsoft_graph_oauth_state"
    assert inserted["p_tenant_id"] == str(TENANT_ID)
    assert inserted["p_provider"] == "microsoft_graph"
    assert "p_expires_at" not in inserted

    query.eq.reset_mock()
    repo.purge_expired_oauth_states(expired_before=datetime.now(UTC))
    assert query.eq.call_args_list == [
        call("tenant_id", str(TENANT_ID)),
        call("provider", "microsoft_graph"),
    ]


def test_repository_state_failure_preserves_original_consumed_timestamp() -> None:
    client = MagicMock()
    query = MagicMock()
    client.table.return_value = query
    for operation in (query.update, query.eq, query.is_):
        operation.return_value = query
    query.execute.return_value = SimpleNamespace(data=[{"id": "state-id"}])
    repo = MeetingIntegrationRepository(client, TENANT_ID)

    repo.fail_oauth_state(
        state_digest="a" * 64,
        context_fingerprint="b" * 64,
        failed_at=datetime.now(UTC),
        failure_code="consent_invalid",
    )

    update = query.update.call_args.args[0]
    assert "consumed_at" not in update
    assert update["pkce_verifier_encrypted"] is None
    assert call("tenant_id", str(TENANT_ID)) in query.eq.call_args_list
    assert call("provider", "microsoft_graph") in query.eq.call_args_list
    assert call("state_digest", "a" * 64) in query.eq.call_args_list
    assert call("context_fingerprint", "b" * 64) in query.eq.call_args_list


class FakeRouterService:
    callback_calls: list[dict[str, Any]] = []

    def __init__(self, _client: Any, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id

    def start_oauth(self, _actor: CurrentUser) -> OAuthStartResult:
        return OAuthStartResult(
            authorization_url="https://login.microsoftonline.com/authorize?state=safe",
            configured=True,
            cookie_name=f"{OAUTH_BINDING_COOKIE_PREFIX}{'a' * 64}",
            cookie_value="b" * 43,
        )

    def complete_callback(
        self,
        form: OAuthCallbackForm,
        transport: OAuthCallbackTransport,
        browser_binding: str | None,
    ) -> OAuthCallbackResult:
        self.callback_calls.append(
            {"form": form, "transport": transport, "browser_binding": browser_binding}
        )
        return OAuthCallbackResult("connected")


def _router_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(integration_router, "MeetingIntegrationService", FakeRouterService)
    monkeypatch.setattr(integration_router, "get_supabase_admin", lambda: object())
    monkeypatch.setattr(settings, "app_public_url", "https://app.example.com")
    FakeRouterService.callback_calls = []
    app = FastAPI()
    app.include_router(integration_router.router)
    app.dependency_overrides[get_current_user] = _actor
    return TestClient(app, base_url="https://app.example.com")


def _canonical_state() -> str:
    raw = TENANT_ID.bytes + b"s" * 32
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def test_start_cookie_contract_is_host_only_secure_none_and_callback_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _router_client(monkeypatch)

    response = client.post("/meeting-integrations/microsoft/oauth/start")

    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(OAUTH_BINDING_COOKIE_PREFIX)
    assert "Domain=" not in cookie
    assert f"Path={OAUTH_BINDING_COOKIE_PATH}" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=none" in cookie
    assert f"Max-Age={OAUTH_BINDING_COOKIE_MAX_AGE_SECONDS}" in cookie
    assert "b" * 43 not in response.text


def test_form_post_callback_parses_once_clears_cookie_and_sanitizes_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _router_client(monkeypatch)
    state = _canonical_state()
    cookie_name = oauth_binding_cookie_name(state)
    binding = "c" * 43

    response = client.post(
        "/meeting-integrations/microsoft/oauth/callback",
        content=f"state={state}&code=sentinel-authorization-code",
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://login.microsoftonline.com",
            "x-forwarded-host": "app.example.com",
            "x-forwarded-proto": "https",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "navigate",
            "sec-fetch-dest": "document",
            "cookie": f"{cookie_name}={binding}",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "https://app.example.com/meetings?microsoft_graph=connected"
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"
    cleared = response.headers["set-cookie"]
    assert cookie_name in cleared and "Max-Age=0" in cleared
    assert "sentinel-authorization-code" not in response.text
    assert state not in response.headers["location"]
    call = FakeRouterService.callback_calls[0]
    assert call["browser_binding"] == binding
    assert call["transport"] == _transport()


@pytest.mark.parametrize(
    ("target", "content", "content_type"),
    [
        (
            "/meeting-integrations/microsoft/oauth/callback?state=query-secret",
            "state=ignored&code=ignored",
            "application/x-www-form-urlencoded",
        ),
        (
            "/meeting-integrations/microsoft/oauth/callback",
            f"state={_canonical_state()}&state={_canonical_state()}&code=duplicate",
            "application/x-www-form-urlencoded",
        ),
        (
            "/meeting-integrations/microsoft/oauth/callback",
            f"state={_canonical_state()}&code=wrong-type",
            "application/json",
        ),
        (
            "/meeting-integrations/microsoft/oauth/callback",
            f"state={_canonical_state()}&code=one&error=two",
            "application/x-www-form-urlencoded",
        ),
    ],
)
def test_malformed_callback_transport_is_generic_and_never_invokes_service(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    content: str,
    content_type: str,
) -> None:
    client = _router_client(monkeypatch)

    response = client.post(
        target,
        content=content,
        headers={"content-type": content_type},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("microsoft_graph=failed&reason=invalid_callback")
    assert FakeRouterService.callback_calls == []
    assert "duplicate" not in response.text
    assert "wrong-type" not in response.text


def test_get_callback_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _router_client(monkeypatch)
    response = client.get(
        "/meeting-integrations/microsoft/oauth/callback",
        follow_redirects=False,
    )
    assert response.status_code == 405
    assert FakeRouterService.callback_calls == []


def _streaming_callback_request(
    chunks: list[bytes],
    *,
    declared_length: int | None = None,
) -> Request:
    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]

    async def receive() -> dict[str, object]:
        if messages:
            return messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    headers = [(b"content-type", b"application/x-www-form-urlencoded")]
    if declared_length is not None:
        headers.append((b"content-length", str(declared_length).encode("ascii")))
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/meeting-integrations/microsoft/oauth/callback",
            "raw_path": b"/meeting-integrations/microsoft/oauth/callback",
            "query_string": b"",
            "headers": headers,
            "server": ("app.example.com", 443),
            "client": ("127.0.0.1", 12345),
        },
        receive,
    )


@pytest.mark.asyncio
async def test_chunked_callback_stops_stream_at_body_cap_before_service() -> None:
    FakeRouterService.callback_calls = []
    request = _streaming_callback_request([b"a" * 9_000, b"b" * 9_000])

    response = await integration_router.microsoft_oauth_callback(request)

    assert response.status_code == 303
    assert response.headers["location"].endswith("microsoft_graph=failed&reason=invalid_callback")
    assert FakeRouterService.callback_calls == []


@pytest.mark.asyncio
async def test_callback_rejects_declared_length_mismatch_before_service() -> None:
    FakeRouterService.callback_calls = []
    body = f"state={_canonical_state()}&code=sentinel".encode("ascii")
    request = _streaming_callback_request([body], declared_length=len(body) - 1)

    response = await integration_router.microsoft_oauth_callback(request)

    assert response.status_code == 303
    assert response.headers["location"].endswith("microsoft_graph=failed&reason=invalid_callback")
    assert FakeRouterService.callback_calls == []


def test_migration_contains_service_only_rls_context_and_terminal_scrubbing() -> None:
    root = Path(__file__).resolve().parents[3]
    migration = (
        root / "supabase/migrations/20260711000002_harden_microsoft_graph_oauth.sql"
    ).read_text(encoding="utf-8")
    lowered = migration.lower()

    assert "tenant_id                  uuid not null" in lowered
    assert "alter table integration_oauth_states enable row level security" in lowered
    assert 'create policy "integration_oauth_states_service_role_all"' in lowered
    assert "to service_role" in lowered
    assert (
        "to authenticated"
        not in lowered.split('create policy "integration_oauth_states_service_role_all"', 1)[
            1
        ].split("revoke all privileges", 1)[0]
    )
    assert (
        "revoke all privileges on integration_oauth_states from public, anon, authenticated"
        in lowered
    )
    assert "grant select, update, delete on integration_oauth_states to service_role" in lowered
    assert "state_raw" not in lowered
    assert "nonce_raw" not in lowered
    assert "browser_binding_raw" not in lowered
    assert "pkce_verifier_encrypted" in lowered
    assert "sync_status = 'reconnect_required'" in lowered
    assert "oauth_context_missing" in lowered
    for column in (
        "deployment_environment",
        "deployment_schema",
        "entra_tenant_id",
        "oauth_client_id",
        "oauth_redirect_uri",
        "encryption_key_fingerprint",
        "context_fingerprint",
        "connected_by_user_id",
    ):
        assert column in lowered
    authenticated_grant = lowered.split("on integration_connections to authenticated", maxsplit=1)[
        0
    ].rsplit("grant select", maxsplit=1)[1]
    assert "encryption_key_fingerprint" not in authenticated_grant


def test_migration_functions_are_definer_locked_and_tenant_exact() -> None:
    root = Path(__file__).resolve().parents[3]
    migration = (
        root / "supabase/migrations/20260711000002_harden_microsoft_graph_oauth.sql"
    ).read_text(encoding="utf-8")
    lowered = migration.lower()
    creation = lowered.split(
        "create or replace function %1$i.create_microsoft_graph_oauth_state", 1
    )[1]
    completion = lowered.split("create or replace function %1$i.complete_microsoft_graph_oauth", 1)[
        1
    ]
    disconnect = lowered.split(
        "create or replace function %1$i.disconnect_microsoft_graph_connection", 1
    )[1]

    assert creation.index("pg_advisory_xact_lock") < creation.index("for update")
    assert completion.index("pg_advisory_xact_lock") < completion.index("for update")
    assert disconnect.index("pg_advisory_xact_lock") < disconnect.index("for update")
    assert "security definer" in completion
    assert "security definer" in creation
    assert "set search_path = pg_catalog, %1$i" in completion
    assert "oauth.tenant_id = p_tenant_id" in completion
    assert "oauth.provider = p_provider" in completion
    assert "oauth.state_digest = p_state_digest" in completion
    assert "oauth.context_fingerprint = p_context_fingerprint" in completion
    assert "platform_user.id = oauth_state.initiated_by_user_id" in completion
    assert "platform_user.tenant_id = p_tenant_id" in completion
    assert "platform_user.status = 'active'" in completion
    assert "platform_user.role in ('transformation_office', 'pmo_lead')" in completion
    assert "pkce_verifier_encrypted = null" in completion
    assert "p_external_account_id <> canonical_external_account_id::text" in completion
    assert lowered.count("insert into %1$i.audit_log") == 2
    assert disconnect.index("if not found") < disconnect.index(
        "update %1$i.integration_oauth_states"
    )
    assert "connection.tenant_id = p_tenant_id" in disconnect
    assert "connection.provider = p_provider" in disconnect
    assert "connection.id = p_connection_id" in disconnect
    assert "consumed_at = coalesce(oauth.consumed_at, now_at)" in disconnect
    assert "pg_catalog.coalesce" not in disconnect
    assert "from public, anon, authenticated, service_role" in lowered
    assert "to service_role" in lowered

    original = (root / "supabase/migrations/20260610000001_meeting_integrations.sql").read_text(
        encoding="utf-8"
    )
    assert "REFERENCES integration_connections(id) ON DELETE SET NULL" in original


def test_hostinger_proxy_preserves_only_traefik_https_for_callback_validation() -> None:
    root = Path(__file__).resolve().parents[3]
    nginx = (root / "apps/web/nginx.conf").read_text(encoding="utf-8")

    assert "map $http_x_forwarded_proto $transmuter_forwarded_proto" in nginx
    assert "map_hash_bucket_size 128;" in nginx
    assert '"https" https;' in nginx
    assert "default $scheme;" in nginx
    assert "proxy_set_header X-Forwarded-Proto $transmuter_forwarded_proto;" in nginx
    assert "proxy_set_header X-Forwarded-Proto $scheme;" not in nginx
    assert '"/api/meeting-integrations/microsoft/oauth/callback" 0;' in nginx

    production_api = (root / "apps/api/Dockerfile.prod").read_text(encoding="utf-8")
    assert '"--no-access-log"' in production_api


def test_graph_migration_requires_verified_offline_hostinger_rollout() -> None:
    root = Path(__file__).resolve().parents[3]
    migration = (
        root / "supabase/migrations/20260711000002_harden_microsoft_graph_oauth.sql"
    ).read_text(encoding="utf-8")
    assert "Apply with the application stack stopped" in migration
    assert "Rollback category: forward-fix-only" in migration

    for relative_path in (
        "infra/hostinger/deploy-change-to-dev.sh",
        "infra/hostinger/promote-dev-to-prod.sh",
    ):
        script = (root / relative_path).read_text(encoding="utf-8")
        assert "requires --offline-schema" in script
        assert script.index("preflight-offline-schema.sh") < script.index("stop-docker-project.sh")
        assert script.index("stop-docker-project.sh") < script.index("apply-schema-sql.sh")
        assert "CONFIRM_STOP_PROJECT=1" in script
        assert "EXPECTED_HOSTINGER_PROJECT_NAME" in script

    production = (root / "infra/hostinger/promote-dev-to-prod.sh").read_text(encoding="utf-8")
    assert "transmuter transmuter-hostinger" in production
    assert "Offline production rollout must stop" in production
    assert "Offline production rollout stop set must be exactly" in production
    assert 'for project_name in "${stop_projects[@]}"' in production

    stop_helper = (root / "infra/hostinger/stop-docker-project.sh").read_text(encoding="utf-8")
    assert "CONFIRM_STOP_PROJECT" in stop_helper
    assert "is already stopped" in stop_helper
    assert stop_helper.index("active_container_count") < stop_helper.index('"${project_url}/stop"')

    preflight = (root / "infra/hostinger/preflight-offline-schema.sh").read_text(encoding="utf-8")
    assert "git status --porcelain" in preflight
    assert "git ls-remote origin" in preflight
    assert "git cat-file -e" in preflight
    assert "HOSTINGER_SCHEMA_GIT_REF" in preflight
    assert "HOSTINGER_DEPLOY_REF" in preflight
    assert "does not permit HOSTINGER_COMPOSE_URL overrides" in preflight
    assert "does not permit SQL URL overrides" in preflight
    assert "curl -fsSL --max-time 20" in preflight
    assert "VERIFY_STOPPED_ONLY=1" in production

    schema_apply = (root / "infra/hostinger/apply-schema-sql.sh").read_text(encoding="utf-8")
    assert "CALLER_OFFLINE_SCHEMA_PINNED" in schema_apply
    assert "unset HOSTINGER_SCHEMA_SQL_URL HOSTINGER_SCHEMA_SQL_BASE_URL" in schema_apply
