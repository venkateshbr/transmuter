from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, asdict
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from joserfc import jwt
from joserfc.jwk import OctKey, RSAKey

from app.core.microsoft_graph import (
    MICROSOFT_GRAPH_CALLBACK_PATH,
    REQUIRED_MICROSOFT_GRAPH_API_SCOPES,
    REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES,
    REQUIRED_MICROSOFT_GRAPH_SCOPES,
    MicrosoftGraphConfigurationError,
    MicrosoftGraphContext,
    MicrosoftGraphIdentityTokenError,
    build_microsoft_graph_context,
    has_required_graph_scopes,
    normalize_scope_set,
    validate_microsoft_id_token,
)

TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT_ID = "11111111-2222-3333-4444-555555555555"
OBJECT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SCOPES = (
    "OnlineMeetings.Read profile User.Read offline_access openid "
    "Calendars.ReadWrite OnlineMeetingTranscript.Read.All"
)


class FakeResponse:
    def __init__(
        self,
        document: Any,
        *,
        is_redirect: bool = False,
        error: httpx.HTTPError | None = None,
    ) -> None:
        self._document = document
        self.is_redirect = is_redirect
        self._error = error

    def raise_for_status(self) -> FakeResponse:
        if self._error:
            raise self._error
        return self

    def json(self) -> Any:
        return self._document


class FakeHttp:
    def __init__(self, responses: dict[str, list[FakeResponse]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        timeout: float,
        follow_redirects: bool,
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "timeout": timeout,
                "follow_redirects": follow_redirects,
            }
        )
        responses = self.responses[url]
        return responses.pop(0) if len(responses) > 1 else responses[0]


def _settings(**overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "environment": "production",
        "app_public_url": "https://transmuter.example",
        "microsoft_graph_redirect_uri": (
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}"
        ),
        "microsoft_graph_tenant_id": TENANT_ID,
        "microsoft_graph_client_id": CLIENT_ID,
        "microsoft_graph_client_secret": "client-secret-value",
        "microsoft_graph_scopes": SCOPES,
        "encryption_key": "encryption-key-value-that-is-at-least-32-characters",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _context(**overrides: Any) -> MicrosoftGraphContext:
    return build_microsoft_graph_context(_settings(**overrides), "transmuter")


def _rsa_key() -> RSAKey:
    return RSAKey.generate_key(
        2048,
        parameters={"use": "sig"},
        private=True,
        auto_kid=True,
    )


def _public_jwk(
    key: RSAKey,
    context: MicrosoftGraphContext,
    **overrides: Any,
) -> dict[str, Any]:
    document = key.as_dict(private=False)
    document["issuer"] = context.issuer
    document.update(overrides)
    return document


def _metadata(context: MicrosoftGraphContext, **overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "issuer": context.issuer,
        "jwks_uri": context.jwks_url,
        "id_token_signing_alg_values_supported": ["RS256"],
    }
    document.update(overrides)
    return document


def _fake_http(
    context: MicrosoftGraphContext,
    jwks_documents: list[dict[str, Any]],
    *,
    metadata_documents: list[dict[str, Any]] | None = None,
) -> FakeHttp:
    metadata_values = metadata_documents or [_metadata(context)]
    return FakeHttp(
        {
            context.discovery_url: [FakeResponse(value) for value in metadata_values],
            context.jwks_url: [FakeResponse(value) for value in jwks_documents],
        }
    )


def _claims(
    context: MicrosoftGraphContext,
    nonce: str,
    **overrides: Any,
) -> dict[str, Any]:
    now = int(datetime.now(UTC).timestamp())
    claims: dict[str, Any] = {
        "iss": context.issuer,
        "aud": context.client_id,
        "exp": now + 300,
        "iat": now,
        "nbf": now - 1,
        "nonce": nonce,
        "tid": context.tenant_id,
        "oid": OBJECT_ID,
        "sub": "pairwise-subject",
        "ver": "2.0",
    }
    claims.update(overrides)
    return claims


def _token(
    context: MicrosoftGraphContext,
    key: RSAKey,
    nonce: str,
    *,
    header: dict[str, Any] | None = None,
    claims: dict[str, Any] | None = None,
) -> str:
    return jwt.encode(
        header or {"alg": "RS256", "kid": key.kid},
        claims or _claims(context, nonce),
        key,
        algorithms=["RS256"],
    )


def _nonce_digest(nonce: str) -> str:
    return hashlib.sha256(nonce.encode()).hexdigest()


def test_context_is_canonical_immutable_and_uses_fixed_endpoints() -> None:
    settings = _settings(
        environment=" Production ",
        microsoft_graph_redirect_uri="",
    )

    context = build_microsoft_graph_context(settings, "TRANSMUTER")

    assert context.environment == "production"
    assert context.deployment_schema == "transmuter"
    assert context.deployment_key == "production:transmuter"
    assert context.tenant_id == TENANT_ID
    assert context.client_id == CLIENT_ID
    assert context.redirect_uri == (f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}")
    assert context.authority_url == f"https://login.microsoftonline.com/{TENANT_ID}"
    assert context.issuer == f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
    assert context.discovery_url == (
        f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration"
    )
    assert context.jwks_url == (
        f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
    )
    assert context.encryption_key_fingerprint.startswith("v1:")
    assert context.context_fingerprint.startswith("v1:")
    assert "client-secret-value" not in repr(context)
    assert str(context.client_secret) == "**********"
    serialized_context = json.dumps(asdict(context), default=str)
    assert "client-secret-value" not in serialized_context
    assert "**********" in serialized_context
    assert context.reveal_client_secret_for_token_exchange() == "client-secret-value"
    with pytest.raises(FrozenInstanceError):
        context.environment = "development"  # type: ignore[misc]


def test_scope_helpers_normalize_order_whitespace_and_duplicates() -> None:
    input_scopes = f"  {SCOPES}   openid  "

    normalized = normalize_scope_set(input_scopes)

    assert normalized == tuple(sorted(REQUIRED_MICROSOFT_GRAPH_SCOPES))
    assert REQUIRED_MICROSOFT_GRAPH_SCOPES == REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES
    assert has_required_graph_scopes(normalized)
    assert has_required_graph_scopes(REQUIRED_MICROSOFT_GRAPH_API_SCOPES)
    assert has_required_graph_scopes(
        [scope for scope in normalized if scope not in {"openid", "profile", "offline_access"}]
    )
    assert not has_required_graph_scopes([scope for scope in normalized if scope != "User.Read"])
    assert has_required_graph_scopes(
        ["user.read", *[scope for scope in normalized if scope != "User.Read"]]
    )
    assert not has_required_graph_scopes(["openid", 1])  # type: ignore[list-item]
    assert not has_required_graph_scopes(None)  # type: ignore[arg-type]

    with pytest.raises(MicrosoftGraphConfigurationError) as exc_info:
        normalize_scope_set(None)  # type: ignore[arg-type]
    assert exc_info.value.code == "invalid_scopes"


def test_context_turns_missing_scope_configuration_into_safe_error() -> None:
    with pytest.raises(MicrosoftGraphConfigurationError) as exc_info:
        _context(microsoft_graph_scopes=None)

    assert exc_info.value.code == "invalid_scopes"
    assert str(exc_info.value) == "Microsoft Graph integration configuration is invalid."


def test_scope_helpers_canonicalize_known_case_uri_forms_and_duplicates() -> None:
    value = [
        "OPENID Profile OFFLINE_ACCESS user.read",
        "https://graph.microsoft.com/calendars.readwrite",
        "https://GRAPH.microsoft.com/OnlineMeetings.Read",
        "onlineMeetingTranscript.read.all USER.READ",
        "Custom.Scope custom.scope",
    ]

    normalized = normalize_scope_set(value)

    assert REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES.issubset(normalized)
    assert normalized.count("User.Read") == 1
    assert "https://graph.microsoft.com/calendars.readwrite" not in normalized
    assert "Custom.Scope" in normalized
    assert "custom.scope" in normalized
    assert has_required_graph_scopes(normalized)


@pytest.mark.parametrize("extra_scope", ["Mail.Read", "Mail.ReadWrite", "Custom.Scope"])
def test_context_rejects_unreviewed_requested_scopes(extra_scope: str) -> None:
    with pytest.raises(MicrosoftGraphConfigurationError) as exc_info:
        _context(microsoft_graph_scopes=f"{SCOPES} {extra_scope}")

    assert exc_info.value.code == "unreviewed_scopes"


@pytest.mark.parametrize("missing_scope", sorted(REQUIRED_MICROSOFT_GRAPH_SCOPES))
def test_context_rejects_each_missing_required_scope(missing_scope: str) -> None:
    scopes = " ".join(REQUIRED_MICROSOFT_GRAPH_SCOPES - {missing_scope})

    with pytest.raises(MicrosoftGraphConfigurationError) as exc_info:
        _context(microsoft_graph_scopes=scopes)

    assert exc_info.value.code == "missing_required_scopes"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("microsoft_graph_tenant_id", "common", "invalid_tenant_id"),
        ("microsoft_graph_tenant_id", "organizations", "invalid_tenant_id"),
        ("microsoft_graph_tenant_id", "consumers", "invalid_tenant_id"),
        ("microsoft_graph_tenant_id", "not-a-guid", "invalid_tenant_id"),
        ("microsoft_graph_tenant_id", TENANT_ID.upper(), "invalid_tenant_id"),
        ("microsoft_graph_tenant_id", f" {TENANT_ID}", "invalid_tenant_id"),
        (
            "microsoft_graph_tenant_id",
            "00000000-0000-0000-0000-000000000000",
            "invalid_tenant_id",
        ),
        ("microsoft_graph_client_id", "not-a-guid", "invalid_client_id"),
        (
            "microsoft_graph_client_id",
            "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
            "invalid_client_id",
        ),
        ("microsoft_graph_client_secret", "", "missing_client_secret"),
        ("encryption_key", "", "missing_encryption_key"),
        ("encryption_key", "short-encryption-key", "weak_encryption_key"),
        ("environment", "production/east", "invalid_environment"),
    ],
)
def test_context_rejects_invalid_identity_and_deployment_values(
    field: str,
    value: str,
    code: str,
) -> None:
    with pytest.raises(MicrosoftGraphConfigurationError) as exc_info:
        _context(**{field: value})

    assert exc_info.value.code == code
    assert str(exc_info.value) == "Microsoft Graph integration configuration is invalid."
    if value:
        assert value not in str(exc_info.value)


@pytest.mark.parametrize(
    ("app_public_url", "redirect_uri", "code"),
    [
        (
            "http://transmuter.example",
            f"http://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "insecure_app_public_url",
        ),
        (
            "https://user@transmuter.example",
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_app_public_url",
        ),
        (
            "https://transmuter.example/app",
            f"https://transmuter.example/app{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_app_public_url",
        ),
        (
            "https://transmuter.example?environment=dev",
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_app_public_url",
        ),
        (
            "https://transmuter.example?",
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_app_public_url",
        ),
        (
            "https://transmuter.example#",
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_app_public_url",
        ),
        (
            "https://transmuter.example/?",
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_app_public_url",
        ),
        (
            "https://transmuter.example/#",
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_app_public_url",
        ),
        (
            "https://transmuter.example",
            f"https://other.example{MICROSOFT_GRAPH_CALLBACK_PATH}",
            "invalid_redirect_uri",
        ),
        (
            "https://transmuter.example",
            "https://transmuter.example/api/meeting-integrations/microsoft/oauth/wrong",
            "invalid_redirect_uri",
        ),
        (
            "https://transmuter.example",
            f"https://transmuter.example{MICROSOFT_GRAPH_CALLBACK_PATH}?x=1",
            "invalid_redirect_uri",
        ),
    ],
)
def test_context_rejects_callback_origin_path_and_transport_swaps(
    app_public_url: str,
    redirect_uri: str,
    code: str,
) -> None:
    with pytest.raises(MicrosoftGraphConfigurationError) as exc_info:
        _context(
            app_public_url=app_public_url,
            microsoft_graph_redirect_uri=redirect_uri,
        )

    assert exc_info.value.code == code


@pytest.mark.parametrize("origin", ["http://localhost:4300", "http://127.0.0.1:4300"])
def test_context_rejects_http_even_for_loopback(origin: str) -> None:
    with pytest.raises(MicrosoftGraphConfigurationError) as exc_info:
        _context(
            app_public_url=origin,
            microsoft_graph_redirect_uri=f"{origin}{MICROSOFT_GRAPH_CALLBACK_PATH}",
        )

    assert exc_info.value.code == "insecure_app_public_url"


def test_fingerprints_are_stable_for_scope_order_and_change_on_boundaries() -> None:
    base = _context()
    reordered = _context(microsoft_graph_scopes=" ".join(reversed(SCOPES.split())))

    assert reordered.context_fingerprint == base.context_fingerprint
    assert reordered.encryption_key_fingerprint == base.encryption_key_fingerprint

    changed_contexts = [
        build_microsoft_graph_context(_settings(environment="development"), "transmuter"),
        build_microsoft_graph_context(_settings(), "transmuter_dev"),
        _context(microsoft_graph_client_id="22222222-2222-2222-2222-222222222222"),
        _context(microsoft_graph_tenant_id="33333333-3333-3333-3333-333333333333"),
        _context(
            app_public_url="https://other.example",
            microsoft_graph_redirect_uri=(f"https://other.example{MICROSOFT_GRAPH_CALLBACK_PATH}"),
        ),
        _context(encryption_key="rotated-" + ("test-key-" * 4)),
    ]

    assert all(value.context_fingerprint != base.context_fingerprint for value in changed_contexts)
    assert changed_contexts[-1].encryption_key_fingerprint != base.encryption_key_fingerprint


def test_validate_id_token_accepts_valid_rs256_token_and_returns_identifiers_only() -> None:
    context = _context()
    key = _rsa_key()
    nonce = "one-time-high-entropy-nonce"
    token = _token(context, key, nonce)
    client = _fake_http(context, [{"keys": [_public_jwk(key, context)]}])

    result = validate_microsoft_id_token(token, context, _nonce_digest(nonce), client)

    assert result == {"oid": OBJECT_ID, "tid": TENANT_ID, "sub": "pairwise-subject"}
    assert [call["url"] for call in client.calls] == [context.discovery_url, context.jwks_url]
    assert all(call["follow_redirects"] is False for call in client.calls)
    assert all(call["timeout"] == 10.0 for call in client.calls)


def test_validate_id_token_refreshes_jwks_once_for_unknown_kid() -> None:
    context = _context()
    old_key = _rsa_key()
    current_key = _rsa_key()
    nonce = "nonce-for-key-rollover"
    token = _token(context, current_key, nonce)
    client = _fake_http(
        context,
        [
            {"keys": [_public_jwk(old_key, context)]},
            {"keys": [_public_jwk(current_key, context)]},
        ],
        metadata_documents=[_metadata(context), _metadata(context)],
    )

    result = validate_microsoft_id_token(token, context, _nonce_digest(nonce), client)

    assert result["oid"] == OBJECT_ID
    assert [call["url"] for call in client.calls] == [
        context.discovery_url,
        context.jwks_url,
        context.discovery_url,
        context.jwks_url,
    ]


def test_validate_id_token_rejects_unknown_kid_after_one_refresh() -> None:
    context = _context()
    known_key = _rsa_key()
    unknown_key = _rsa_key()
    nonce = "nonce-for-unknown-key"
    token = _token(context, unknown_key, nonce)
    client = _fake_http(
        context,
        [
            {"keys": [_public_jwk(known_key, context)]},
            {"keys": [_public_jwk(known_key, context)]},
        ],
        metadata_documents=[_metadata(context), _metadata(context)],
    )

    with pytest.raises(MicrosoftGraphIdentityTokenError):
        validate_microsoft_id_token(token, context, _nonce_digest(nonce), client)

    assert len(client.calls) == 4


@pytest.mark.parametrize(
    ("metadata_override", "code"),
    [
        ({"issuer": "https://login.microsoftonline.com/wrong/v2.0"}, "invalid_oidc_metadata"),
        ({"jwks_uri": "https://attacker.example/keys"}, "invalid_oidc_metadata"),
        ({"id_token_signing_alg_values_supported": ["ES256"]}, "invalid_oidc_metadata"),
        ({"id_token_signing_alg_values_supported": "RS256"}, "invalid_oidc_metadata"),
    ],
)
def test_validate_id_token_rejects_untrusted_metadata(
    metadata_override: dict[str, Any],
    code: str,
) -> None:
    context = _context()
    key = _rsa_key()
    nonce = "nonce-for-metadata"
    client = _fake_http(
        context,
        [{"keys": [_public_jwk(key, context)]}],
        metadata_documents=[_metadata(context, **metadata_override)],
    )

    with pytest.raises(MicrosoftGraphIdentityTokenError) as exc_info:
        validate_microsoft_id_token(
            _token(context, key, nonce),
            context,
            _nonce_digest(nonce),
            client,
        )

    assert exc_info.value.code == code
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "key_override",
    [
        {"kty": "EC"},
        {"use": "enc"},
        {"kid": ""},
        {"issuer": "https://login.microsoftonline.com/wrong/v2.0"},
        {"alg": "RS512"},
    ],
)
def test_validate_id_token_filters_untrusted_jwks_keys(key_override: dict[str, Any]) -> None:
    context = _context()
    key = _rsa_key()
    nonce = "nonce-for-jwks-filter"
    invalid_key = _public_jwk(key, context, **key_override)
    client = _fake_http(context, [{"keys": [invalid_key]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError) as exc_info:
        validate_microsoft_id_token(
            _token(context, key, nonce),
            context,
            _nonce_digest(nonce),
            client,
        )

    assert exc_info.value.code == "invalid_jwks"


def test_validate_id_token_rejects_duplicate_key_ids() -> None:
    context = _context()
    key = _rsa_key()
    nonce = "nonce-for-duplicate-kid"
    public_key = _public_jwk(key, context)
    client = _fake_http(context, [{"keys": [public_key, public_key.copy()]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError) as exc_info:
        validate_microsoft_id_token(
            _token(context, key, nonce),
            context,
            _nonce_digest(nonce),
            client,
        )

    assert exc_info.value.code == "invalid_jwks"


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("iss", "https://login.microsoftonline.com/wrong/v2.0"),
        ("aud", "99999999-9999-9999-9999-999999999999"),
        ("tid", "99999999-9999-9999-9999-999999999999"),
        ("tid", TENANT_ID.upper()),
        ("oid", "not-a-guid"),
        ("oid", OBJECT_ID.upper()),
        ("sub", ""),
        ("ver", "1.0"),
        ("exp", 0),
        ("iat", 4_102_444_800),
        ("nbf", 4_102_444_800),
        ("iat", True),
        ("nbf", float("nan")),
    ],
)
def test_validate_id_token_rejects_invalid_claims(claim: str, value: Any) -> None:
    context = _context()
    key = _rsa_key()
    nonce = "nonce-for-invalid-claims"
    token = _token(context, key, nonce, claims=_claims(context, nonce, **{claim: value}))
    client = _fake_http(context, [{"keys": [_public_jwk(key, context)]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError):
        validate_microsoft_id_token(token, context, _nonce_digest(nonce), client)


@pytest.mark.parametrize(
    "missing_claim", ["iss", "aud", "exp", "iat", "nbf", "nonce", "tid", "oid", "sub", "ver"]
)
def test_validate_id_token_requires_all_security_claims(missing_claim: str) -> None:
    context = _context()
    key = _rsa_key()
    nonce = "nonce-for-missing-claim"
    claims = _claims(context, nonce)
    claims.pop(missing_claim)
    client = _fake_http(context, [{"keys": [_public_jwk(key, context)]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError):
        validate_microsoft_id_token(
            _token(context, key, nonce, claims=claims),
            context,
            _nonce_digest(nonce),
            client,
        )


def test_validate_id_token_rejects_wrong_nonce_digest() -> None:
    context = _context()
    key = _rsa_key()
    nonce = "expected-nonce"
    client = _fake_http(context, [{"keys": [_public_jwk(key, context)]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError):
        validate_microsoft_id_token(
            _token(context, key, "different-nonce"),
            context,
            _nonce_digest(nonce),
            client,
        )


@pytest.mark.parametrize("nonce_digest", ["", "not-a-digest", "A" * 64])
def test_validate_id_token_rejects_noncanonical_nonce_digest(nonce_digest: str) -> None:
    context = _context()

    with pytest.raises(MicrosoftGraphIdentityTokenError) as exc_info:
        validate_microsoft_id_token("token", context, nonce_digest, FakeHttp({}))

    assert exc_info.value.code == "invalid_nonce_digest"


@pytest.mark.parametrize(
    "header",
    [
        {"alg": "RS256"},
        {"alg": "RS256", "kid": "key", "typ": "not-jwt"},
    ],
)
def test_validate_id_token_rejects_missing_kid_and_wrong_type(header: dict[str, Any]) -> None:
    context = _context()
    key = _rsa_key()
    nonce = "nonce-for-header"
    client = _fake_http(context, [{"keys": [_public_jwk(key, context)]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError):
        validate_microsoft_id_token(
            _token(context, key, nonce, header=header),
            context,
            _nonce_digest(nonce),
            client,
        )


def test_validate_id_token_rejects_algorithm_confusion() -> None:
    context = _context()
    rsa_key = _rsa_key()
    nonce = "nonce-for-algorithm"
    hmac_key = OctKey.import_key("hmac-secret-that-is-at-least-32-characters")
    token = jwt.encode(
        {"alg": "HS256", "kid": rsa_key.kid},
        _claims(context, nonce),
        hmac_key,
        algorithms=["HS256"],
    )
    client = _fake_http(context, [{"keys": [_public_jwk(rsa_key, context)]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError):
        validate_microsoft_id_token(token, context, _nonce_digest(nonce), client)


def test_validate_id_token_rejects_bad_signature() -> None:
    context = _context()
    trusted_key = _rsa_key()
    attacker_key = _rsa_key()
    nonce = "nonce-for-signature"
    token = _token(
        context,
        attacker_key,
        nonce,
        header={"alg": "RS256", "kid": trusted_key.kid},
    )
    client = _fake_http(context, [{"keys": [_public_jwk(trusted_key, context)]}])

    with pytest.raises(MicrosoftGraphIdentityTokenError):
        validate_microsoft_id_token(token, context, _nonce_digest(nonce), client)


def test_validate_id_token_rejects_redirected_discovery() -> None:
    context = _context()
    key = _rsa_key()
    nonce = "nonce-for-redirect"
    client = FakeHttp(
        {
            context.discovery_url: [FakeResponse(_metadata(context), is_redirect=True)],
            context.jwks_url: [FakeResponse({"keys": [_public_jwk(key, context)]})],
        }
    )

    with pytest.raises(MicrosoftGraphIdentityTokenError) as exc_info:
        validate_microsoft_id_token(
            _token(context, key, nonce),
            context,
            _nonce_digest(nonce),
            client,
        )

    assert exc_info.value.code == "oidc_unavailable"
    assert len(client.calls) == 1


def test_validate_id_token_sanitizes_oidc_network_failure() -> None:
    context = _context()
    nonce = "nonce-for-network-error"
    request = httpx.Request("GET", context.discovery_url)
    client = FakeHttp(
        {
            context.discovery_url: [
                FakeResponse(
                    {},
                    error=httpx.ConnectError("provider unavailable", request=request),
                )
            ],
            context.jwks_url: [FakeResponse({})],
        }
    )

    with pytest.raises(MicrosoftGraphIdentityTokenError) as exc_info:
        validate_microsoft_id_token("signed-token", context, _nonce_digest(nonce), client)

    assert str(exc_info.value) == "Microsoft identity response could not be verified."
    assert "provider unavailable" not in str(exc_info.value)
