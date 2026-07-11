from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode, urlsplit
from uuid import UUID

import httpx

from app.core.auth import CurrentUser
from app.core.auth_metadata import verify_scoped_authorization
from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.database import get_supabase_schema
from app.core.microsoft_graph import (
    MICROSOFT_GRAPH_CALLBACK_PATH,
    REQUIRED_MICROSOFT_GRAPH_API_SCOPES,
    MicrosoftGraphConfigurationError,
    MicrosoftGraphContext,
    build_microsoft_graph_context,
    normalize_scope_set,
    validate_microsoft_id_token,
)
from app.core.rbac import CAP_MANAGE_PROGRAM_CADENCE, has_capability
from app.repositories.meeting_integrations import MeetingIntegrationRepository

MICROSOFT_GRAPH_PROVIDER = "microsoft_graph"
MICROSOFT_LOGIN_ORIGIN = "https://login.microsoftonline.com"
MICROSOFT_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me?$select=id,mail,userPrincipalName"

OAUTH_RESPONSE_MODE = "form_post"
OAUTH_BINDING_COOKIE_PREFIX = "__Secure-transmuter-msgraph-oauth-"
OAUTH_BINDING_COOKIE_PATH = MICROSOFT_GRAPH_CALLBACK_PATH
OAUTH_BINDING_COOKIE_MAX_AGE_SECONDS = 600
OAUTH_STATE_ENCODED_LENGTH = 64
OAUTH_BINDING_ENCODED_LENGTH = 43
OAUTH_HTTP_TIMEOUT_SECONDS = 10.0
OAUTH_MAX_CODE_LENGTH = 8_192
OAUTH_MAX_TOKEN_LENGTH = 32_768
OAUTH_MAX_SCOPE_LENGTH = 4_096
OAUTH_MAX_TOKEN_EXPIRY_SECONDS = 86_400

_BASE64URL_64_PATTERN = re.compile(r"^[A-Za-z0-9_-]{64}$")
_BASE64URL_43_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
_STATE_DIGEST_DOMAIN = b"transmuter:microsoft_graph:oauth-state:v1\0"
_BINDING_DIGEST_DOMAIN = b"transmuter:microsoft_graph:browser-binding:v1\0"


@dataclass(frozen=True, slots=True)
class OAuthStartResult:
    authorization_url: str
    configured: bool
    detail: str | None = None
    cookie_name: str | None = None
    cookie_value: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthCallbackForm:
    state: str
    code: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthCallbackTransport:
    origin: str | None
    host: str | None
    scheme: str | None
    fetch_site: str | None = None
    fetch_mode: str | None = None
    fetch_dest: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthCallbackResult:
    status: Literal["connected", "cancelled", "failed"]
    reason: str | None = None


class MeetingIntegrationService:
    def __init__(
        self,
        client: Any,
        tenant_id: UUID,
        *,
        settings_obj: object = settings,
        deployment_schema: str | None = None,
        http_client: object = httpx,
    ) -> None:
        self._client = client
        self._tenant_id = tenant_id
        self._repo = MeetingIntegrationRepository(client, tenant_id)
        self._settings = settings_obj
        self._deployment_schema = deployment_schema or get_supabase_schema()
        self._http = http_client

    def list_integrations(self) -> dict[str, Any]:
        context = self._context_or_none()
        items = [
            self._effective_connection_status(row, context) for row in self._repo.list_connections()
        ]
        return {
            "items": items,
            "providers": [
                {
                    "provider": MICROSOFT_GRAPH_PROVIDER,
                    "configured": context is not None,
                },
                {
                    "provider": "recall_ai",
                    "enabled": bool(getattr(self._settings, "recall_meeting_bot_enabled", False)),
                },
                {
                    "provider": "fireflies",
                    "enabled": bool(
                        getattr(self._settings, "fireflies_meeting_bot_enabled", False)
                    ),
                },
            ],
        }

    def start_oauth(self, actor: CurrentUser) -> OAuthStartResult:
        self._assert_actor_matches_tenant(actor)
        if not has_capability(actor.role, CAP_MANAGE_PROGRAM_CADENCE):
            raise PermissionError("program_cadence.manage is required")
        try:
            context = self._context()
        except MicrosoftGraphConfigurationError:
            return OAuthStartResult(
                authorization_url="",
                configured=False,
                detail="Microsoft Graph integration is not configured.",
            )

        now = datetime.now(UTC)
        raw_state = actor.tenant_id.bytes + secrets.token_bytes(32)
        state = _base64url_encode(raw_state)
        state_digest = _domain_digest(_STATE_DIGEST_DOMAIN, raw_state)
        binding_raw = secrets.token_bytes(32)
        binding_value = _base64url_encode(binding_raw)
        binding_digest = _domain_digest(_BINDING_DIGEST_DOMAIN, binding_raw)
        verifier = _base64url_encode(secrets.token_bytes(32))
        challenge = _base64url_encode(hashlib.sha256(verifier.encode("ascii")).digest())
        nonce = _base64url_encode(secrets.token_bytes(32))
        nonce_digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()
        encrypted_verifier = encrypt_secret(verifier)
        if not encrypted_verifier:
            return OAuthStartResult(
                authorization_url="",
                configured=False,
                detail="Microsoft Graph integration is not configured.",
            )

        self._repo.purge_expired_oauth_states(
            expired_before=now - timedelta(days=1),
        )
        self._repo.create_oauth_state(
            {
                "state_digest": state_digest,
                "browser_binding_digest": binding_digest,
                "initiated_by_user_id": str(actor.id),
                "pkce_verifier_encrypted": encrypted_verifier,
                "nonce_digest": nonce_digest,
                "deployment_environment": context.environment,
                "deployment_schema": context.deployment_schema,
                "entra_tenant_id": context.tenant_id,
                "oauth_client_id": context.client_id,
                "oauth_redirect_uri": context.redirect_uri,
                "encryption_key_fingerprint": context.encryption_key_fingerprint,
                "context_fingerprint": context.context_fingerprint,
                "authorization_scopes": list(context.scopes),
                "required_api_scopes": sorted(REQUIRED_MICROSOFT_GRAPH_API_SCOPES),
            }
        )

        params = {
            "client_id": context.client_id,
            "response_type": "code",
            "redirect_uri": context.redirect_uri,
            "response_mode": OAUTH_RESPONSE_MODE,
            "scope": context.scope_value,
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return OAuthStartResult(
            authorization_url=f"{context.authorization_url}?{urlencode(params)}",
            configured=True,
            cookie_name=f"{OAUTH_BINDING_COOKIE_PREFIX}{state_digest}",
            cookie_value=binding_value,
        )

    def complete_callback(
        self,
        form: OAuthCallbackForm,
        transport: OAuthCallbackTransport,
        browser_binding: str | None,
    ) -> OAuthCallbackResult:
        try:
            context = self._context()
            self._validate_callback_transport(transport, context)
            routed_tenant_id, raw_state = parse_oauth_state(form.state)
            if routed_tenant_id != self._tenant_id:
                return OAuthCallbackResult("failed", "invalid_callback")
            binding_raw = parse_browser_binding(browser_binding)
        except (MicrosoftGraphConfigurationError, ValueError):
            return OAuthCallbackResult("failed", "invalid_callback")

        state_digest = _domain_digest(_STATE_DIGEST_DOMAIN, raw_state)
        binding_digest = _domain_digest(_BINDING_DIGEST_DOMAIN, binding_raw)
        now = datetime.now(UTC)
        if form.error is not None:
            cancelled = form.error == "access_denied"
            state = self._repo.consume_oauth_state(
                state_digest=state_digest,
                browser_binding_digest=binding_digest,
                context_fingerprint=context.context_fingerprint,
                consumed_at=now,
                terminal="cancelled" if cancelled else "failed",
                failure_code="authorization_cancelled" if cancelled else "provider_error",
            )
            if state is None:
                return OAuthCallbackResult("failed", "invalid_callback")
            return OAuthCallbackResult(
                "cancelled" if cancelled else "failed",
                "authorization_cancelled" if cancelled else "provider_error",
            )

        if not form.code or len(form.code) > OAUTH_MAX_CODE_LENGTH:
            return OAuthCallbackResult("failed", "invalid_callback")

        state = self._repo.consume_oauth_state(
            state_digest=state_digest,
            browser_binding_digest=binding_digest,
            context_fingerprint=context.context_fingerprint,
            consumed_at=now,
        )
        if state is None:
            return OAuthCallbackResult("failed", "invalid_callback")

        failure_code = "consent_invalid"
        try:
            self._validate_consumed_state(state, context, state_digest)
            self._revalidate_actor(state, context)
            encrypted_verifier = state.get("pkce_verifier_encrypted")
            verifier = decrypt_secret(
                encrypted_verifier if isinstance(encrypted_verifier, str) else None
            )
            if not verifier or not _BASE64URL_43_PATTERN.fullmatch(verifier):
                raise ValueError("invalid encrypted PKCE verifier")

            token_body = self._exchange_authorization_code(form.code, verifier, context)
            access_token, refresh_token, expires_at, granted_scopes, id_token = (
                self._validate_initial_token_response(token_body, now)
            )
            identity = validate_microsoft_id_token(
                id_token,
                context,
                str(state["nonce_digest"]),
                http_client=self._http,
            )
            external_account_id, organizer_email = self._fetch_graph_identity(
                access_token,
                str(identity["oid"]),
            )
            access_token_encrypted = encrypt_secret(access_token)
            refresh_token_encrypted = encrypt_secret(refresh_token)
            if not access_token_encrypted or not refresh_token_encrypted:
                raise ValueError("token encryption failed")

            failure_code = "connection_failed"
            self._repo.complete_microsoft_graph_oauth(
                state_digest=state_digest,
                context_fingerprint=context.context_fingerprint,
                external_account_id=external_account_id,
                organizer_email=organizer_email,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=expires_at,
                scopes=granted_scopes,
            )
        except Exception:
            with suppress(Exception):
                self._repo.fail_oauth_state(
                    state_digest=state_digest,
                    context_fingerprint=context.context_fingerprint,
                    failed_at=datetime.now(UTC),
                    failure_code=failure_code,
                )
            return OAuthCallbackResult("failed", failure_code)
        return OAuthCallbackResult("connected")

    def disconnect(self, actor: CurrentUser, connection_id: UUID) -> bool:
        self._assert_actor_matches_tenant(actor)
        if not has_capability(actor.role, CAP_MANAGE_PROGRAM_CADENCE):
            raise PermissionError("program_cadence.manage is required")
        return self._repo.disconnect_microsoft_graph_connection(connection_id, actor.id)

    def _context(self) -> MicrosoftGraphContext:
        return build_microsoft_graph_context(self._settings, self._deployment_schema)

    def _context_or_none(self) -> MicrosoftGraphContext | None:
        try:
            return self._context()
        except MicrosoftGraphConfigurationError:
            return None

    def _effective_connection_status(
        self,
        row: dict[str, Any],
        context: MicrosoftGraphContext | None,
    ) -> dict[str, Any]:
        item = dict(row)
        if item.get("provider") != MICROSOFT_GRAPH_PROVIDER:
            return item
        reason = self._reconnect_reason(item, context)
        if reason:
            item["sync_status"] = "reconnect_required"
        item["effective_status"] = "reconnect_required" if reason else "connected"
        item["reconnect_required"] = reason is not None
        item["reconnect_reason"] = reason
        for internal_key in (
            "deployment_environment",
            "deployment_schema",
            "entra_tenant_id",
            "oauth_client_id",
            "oauth_redirect_uri",
            "context_fingerprint",
            "oauth_generation",
            "token_generation",
            "connected_by_user_id",
        ):
            item.pop(internal_key, None)
        return item

    @staticmethod
    def _reconnect_reason(
        row: Mapping[str, Any],
        context: MicrosoftGraphContext | None,
    ) -> str | None:
        if context is None:
            return "configuration_error"
        if row.get("sync_status") != "connected":
            return "connection_stale"
        expected = {
            "deployment_environment": context.environment,
            "deployment_schema": context.deployment_schema,
            "entra_tenant_id": context.tenant_id,
            "oauth_client_id": context.client_id,
            "oauth_redirect_uri": context.redirect_uri,
            "context_fingerprint": context.context_fingerprint,
        }
        if any(str(row.get(key) or "") != value for key, value in expected.items()):
            return "context_changed"
        if not _has_required_api_scopes(row.get("scopes")):
            return "scope_changed"
        try:
            _canonical_uuid_text(row.get("external_account_id"))
            UUID(str(row.get("connected_by_user_id") or ""))
            generation = row.get("oauth_generation")
            if isinstance(generation, bool) or not isinstance(generation, int) or generation <= 0:
                raise ValueError("invalid OAuth generation")
            token_generation = row.get("token_generation")
            if (
                isinstance(token_generation, bool)
                or not isinstance(token_generation, int)
                or token_generation < 0
            ):
                raise ValueError("invalid token generation")
        except (TypeError, ValueError):
            return "connection_stale"
        return None

    def _validate_callback_transport(
        self,
        transport: OAuthCallbackTransport,
        context: MicrosoftGraphContext,
    ) -> None:
        expected_host = urlsplit(context.redirect_uri).netloc
        if (
            transport.origin != MICROSOFT_LOGIN_ORIGIN
            or transport.host != expected_host
            or transport.scheme != "https"
        ):
            raise ValueError("invalid callback transport")
        fetch_values = (transport.fetch_site, transport.fetch_mode, transport.fetch_dest)
        if any(value is not None for value in fetch_values) and fetch_values != (
            "cross-site",
            "navigate",
            "document",
        ):
            raise ValueError("invalid callback fetch metadata")

    def _validate_consumed_state(
        self,
        state: Mapping[str, Any],
        context: MicrosoftGraphContext,
        state_digest: str,
    ) -> None:
        expected = {
            "tenant_id": str(self._tenant_id),
            "provider": MICROSOFT_GRAPH_PROVIDER,
            "state_digest": state_digest,
            "deployment_environment": context.environment,
            "deployment_schema": context.deployment_schema,
            "entra_tenant_id": context.tenant_id,
            "oauth_client_id": context.client_id,
            "oauth_redirect_uri": context.redirect_uri,
            "encryption_key_fingerprint": context.encryption_key_fingerprint,
            "context_fingerprint": context.context_fingerprint,
        }
        if any(str(state.get(key) or "") != value for key, value in expected.items()):
            raise ValueError("OAuth state context changed")
        if tuple(state.get("authorization_scopes") or ()) != context.scopes:
            raise ValueError("OAuth authorization scopes changed")
        if not _has_required_api_scopes(state.get("required_api_scopes")):
            raise ValueError("OAuth required scopes changed")

    def _revalidate_actor(
        self,
        state: Mapping[str, Any],
        context: MicrosoftGraphContext,
    ) -> CurrentUser:
        actor_id = _canonical_uuid_text(state.get("initiated_by_user_id"))
        row = self._repo.get_actor(actor_id)
        if (
            row is None
            or str(row.get("id")) != actor_id
            or str(row.get("tenant_id")) != str(self._tenant_id)
            or row.get("status") != "active"
            or bool(row.get("must_change_password"))
            or not isinstance(row.get("role"), str)
            or not has_capability(str(row["role"]), CAP_MANAGE_PROGRAM_CADENCE)
        ):
            raise PermissionError("OAuth actor is no longer authorized")
        verify_scoped_authorization(
            self._client.auth.admin,
            actor_id,
            scope=context.deployment_schema,
            authorization={
                "tenant_id": str(self._tenant_id),
                "role": str(row["role"]),
            },
        )
        return CurrentUser(
            id=UUID(actor_id),
            tenant_id=self._tenant_id,
            role=str(row["role"]),
            status="active",
            must_change_password=False,
        )

    def _exchange_authorization_code(
        self,
        code: str,
        verifier: str,
        context: MicrosoftGraphContext,
    ) -> dict[str, Any]:
        post = getattr(self._http, "post", None)
        if not callable(post):
            raise ValueError("OAuth token endpoint unavailable")
        response = post(
            context.token_url,
            data={
                "client_id": context.client_id,
                "client_secret": context.reveal_client_secret_for_token_exchange(),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": context.redirect_uri,
                "code_verifier": verifier,
                "scope": context.scope_value,
            },
            timeout=OAUTH_HTTP_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
        if bool(getattr(response, "is_redirect", False)):
            raise ValueError("OAuth token endpoint redirected")
        raise_for_status = getattr(response, "raise_for_status", None)
        read_json = getattr(response, "json", None)
        if not callable(raise_for_status) or not callable(read_json):
            raise ValueError("OAuth token response invalid")
        raise_for_status()
        body = read_json()
        if not isinstance(body, dict):
            raise ValueError("OAuth token response invalid")
        return body

    def _validate_initial_token_response(
        self,
        token_body: Mapping[str, Any],
        issued_at: datetime,
    ) -> tuple[str, str, datetime, tuple[str, ...], str]:
        token_type = token_body.get("token_type")
        access_token = _bounded_nonempty_string(
            token_body.get("access_token"), OAUTH_MAX_TOKEN_LENGTH
        )
        refresh_token = _bounded_nonempty_string(
            token_body.get("refresh_token"), OAUTH_MAX_TOKEN_LENGTH
        )
        id_token = _bounded_nonempty_string(token_body.get("id_token"), OAUTH_MAX_TOKEN_LENGTH)
        raw_scope = _bounded_nonempty_string(token_body.get("scope"), OAUTH_MAX_SCOPE_LENGTH)
        expires_in = token_body.get("expires_in")
        if not isinstance(token_type, str) or token_type.lower() != "bearer":
            raise ValueError("OAuth token type invalid")
        if (
            isinstance(expires_in, bool)
            or not isinstance(expires_in, int)
            or expires_in <= 0
            or expires_in > OAUTH_MAX_TOKEN_EXPIRY_SECONDS
        ):
            raise ValueError("OAuth token expiry invalid")
        granted_scopes = _normalize_granted_scopes(raw_scope)
        if not _has_required_api_scopes(granted_scopes):
            raise ValueError("OAuth consent incomplete")
        return (
            access_token,
            refresh_token,
            issued_at + timedelta(seconds=expires_in),
            granted_scopes,
            id_token,
        )

    def _fetch_graph_identity(
        self,
        access_token: str,
        expected_object_id: str,
    ) -> tuple[str, str]:
        get = getattr(self._http, "get", None)
        if not callable(get):
            raise ValueError("Microsoft Graph unavailable")
        response = get(
            MICROSOFT_GRAPH_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=OAUTH_HTTP_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
        if bool(getattr(response, "is_redirect", False)):
            raise ValueError("Microsoft Graph redirected")
        raise_for_status = getattr(response, "raise_for_status", None)
        read_json = getattr(response, "json", None)
        if not callable(raise_for_status) or not callable(read_json):
            raise ValueError("Microsoft Graph response invalid")
        raise_for_status()
        profile = read_json()
        if not isinstance(profile, dict):
            raise ValueError("Microsoft Graph response invalid")
        external_account_id = _canonical_uuid_text(profile.get("id"))
        if not hmac.compare_digest(external_account_id, _canonical_uuid_text(expected_object_id)):
            raise ValueError("Microsoft Graph identity changed")
        organizer = profile.get("mail") or profile.get("userPrincipalName")
        organizer_email = _bounded_nonempty_string(organizer, 320).strip()
        if not organizer_email:
            raise ValueError("Microsoft Graph organizer identity missing")
        return external_account_id, organizer_email

    def _assert_actor_matches_tenant(self, actor: CurrentUser) -> None:
        if actor.tenant_id != self._tenant_id:
            raise PermissionError("tenant mismatch")


def parse_oauth_state(state: str | None) -> tuple[UUID, bytes]:
    if not isinstance(state, str) or not _BASE64URL_64_PATTERN.fullmatch(state):
        raise ValueError("invalid OAuth state")
    raw = _base64url_decode(state, OAUTH_STATE_ENCODED_LENGTH, _BASE64URL_64_PATTERN)
    if len(raw) != 48 or not hmac.compare_digest(_base64url_encode(raw), state):
        raise ValueError("invalid OAuth state")
    return UUID(bytes=raw[:16]), raw


def oauth_binding_cookie_name(state: str) -> str:
    _, raw_state = parse_oauth_state(state)
    return f"{OAUTH_BINDING_COOKIE_PREFIX}{_domain_digest(_STATE_DIGEST_DOMAIN, raw_state)}"


def parse_browser_binding(binding: str | None) -> bytes:
    if not isinstance(binding, str) or not _BASE64URL_43_PATTERN.fullmatch(binding):
        raise ValueError("invalid browser binding")
    raw = _base64url_decode(
        binding,
        OAUTH_BINDING_ENCODED_LENGTH,
        _BASE64URL_43_PATTERN,
    )
    if len(raw) != 32 or not hmac.compare_digest(_base64url_encode(raw), binding):
        raise ValueError("invalid browser binding")
    return raw


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str, expected_length: int, pattern: re.Pattern[str]) -> bytes:
    if len(value) != expected_length or not pattern.fullmatch(value):
        raise ValueError("invalid base64url value")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(
            f"{value}{padding}",
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError):
        raise ValueError("invalid base64url value") from None


def _domain_digest(domain: bytes, value: bytes) -> str:
    return hashlib.sha256(domain + value).hexdigest()


def _bounded_nonempty_string(value: Any, maximum_length: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum_length:
        raise ValueError("invalid bounded string")
    return value


def _normalize_granted_scopes(value: str) -> tuple[str, ...]:
    normalized = normalize_scope_set(value)
    by_casefold: dict[str, str] = {}
    for scope in normalized:
        by_casefold.setdefault(scope.casefold(), scope)
    return tuple(sorted(by_casefold.values(), key=str.casefold))


def _has_required_api_scopes(value: Any) -> bool:
    if isinstance(value, str):
        scopes = value.split()
    elif isinstance(value, (list, tuple, set, frozenset)):
        scopes = value
    else:
        return False
    granted = {str(scope).casefold() for scope in scopes if isinstance(scope, str)}
    return all(scope.casefold() in granted for scope in REQUIRED_MICROSOFT_GRAPH_API_SCOPES)


def _canonical_uuid_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid UUID")
    parsed = UUID(value)
    canonical = str(parsed)
    if value.lower() != canonical:
        raise ValueError("noncanonical UUID")
    return canonical
