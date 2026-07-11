from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from joserfc import jwt
from joserfc.errors import InvalidKeyIdError, JoseError
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from pydantic import SecretStr

MICROSOFT_GRAPH_CALLBACK_PATH = "/api/meeting-integrations/microsoft/oauth/callback"
MICROSOFT_GRAPH_FINGERPRINT_VERSION = "v1"
MICROSOFT_OIDC_HTTP_TIMEOUT_SECONDS = 10.0

REQUIRED_MICROSOFT_GRAPH_API_SCOPES = frozenset(
    {
        "User.Read",
        "Calendars.ReadWrite",
        "OnlineMeetings.Read",
        "OnlineMeetingTranscript.Read.All",
    }
)
REQUIRED_MICROSOFT_OIDC_SCOPES = frozenset({"openid", "profile", "offline_access"})
REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES = (
    REQUIRED_MICROSOFT_GRAPH_API_SCOPES | REQUIRED_MICROSOFT_OIDC_SCOPES
)
# Retain the original public name for callers that need the complete authorization request.
REQUIRED_MICROSOFT_GRAPH_SCOPES = REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES

_CANONICAL_SCOPE_BY_CASEFOLD = {
    scope.casefold(): scope for scope in REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES
}
_CANONICAL_SCOPE_BY_CASEFOLD.update(
    {
        f"https://graph.microsoft.com/{scope}".casefold(): scope
        for scope in REQUIRED_MICROSOFT_GRAPH_API_SCOPES
    }
)

_CANONICAL_GUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_DEPLOYMENT_VALUE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class MicrosoftGraphConfigurationError(ValueError):
    """A safe, integration-scoped Microsoft Graph configuration failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__("Microsoft Graph integration configuration is invalid.")


class MicrosoftGraphIdentityTokenError(ValueError):
    """A safe Microsoft identity-token validation failure."""

    def __init__(self, code: str = "invalid_id_token") -> None:
        self.code = code
        super().__init__("Microsoft identity response could not be verified.")


@dataclass(frozen=True, slots=True)
class MicrosoftGraphContext:
    environment: str
    deployment_schema: str
    deployment_key: str
    tenant_id: str
    client_id: str
    client_secret: SecretStr = field(repr=False, compare=False, hash=False)
    redirect_uri: str
    scopes: tuple[str, ...]
    scope_value: str
    encryption_key_fingerprint: str
    context_fingerprint: str
    authority_url: str
    authorization_url: str
    token_url: str
    issuer: str
    discovery_url: str
    jwks_url: str

    def reveal_client_secret_for_token_exchange(self) -> str:
        """Reveal the credential only while constructing the Entra token request."""
        return self.client_secret.get_secret_value()


def normalize_scope_set(value: str | Iterable[str]) -> tuple[str, ...]:
    """Return a stable, de-duplicated OAuth scope tuple."""
    if isinstance(value, str):
        values = [value]
    else:
        try:
            values = list(value)
        except TypeError:
            raise MicrosoftGraphConfigurationError("invalid_scopes") from None
    scopes: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            raise MicrosoftGraphConfigurationError("invalid_scopes")
        for scope in item.split():
            scopes.add(_CANONICAL_SCOPE_BY_CASEFOLD.get(scope.casefold(), scope))
    return tuple(sorted(scopes))


def has_required_graph_scopes(scopes: str | Iterable[str]) -> bool:
    try:
        normalized = set(normalize_scope_set(scopes))
    except (MicrosoftGraphConfigurationError, TypeError):
        return False
    return REQUIRED_MICROSOFT_GRAPH_API_SCOPES.issubset(normalized)


def build_microsoft_graph_context(
    settings_obj: object,
    deployment_schema: str,
) -> MicrosoftGraphContext:
    """Build one normalized, immutable deployment boundary for Graph access."""
    environment = _canonical_deployment_value(
        _setting(settings_obj, "environment"),
        "invalid_environment",
    )
    schema = _canonical_deployment_value(deployment_schema, "invalid_deployment_schema")
    tenant_id = _canonical_guid(
        _setting(settings_obj, "microsoft_graph_tenant_id"),
        "invalid_tenant_id",
    )
    client_id = _canonical_guid(
        _setting(settings_obj, "microsoft_graph_client_id"),
        "invalid_client_id",
    )
    client_secret = _required_secret(
        _setting(settings_obj, "microsoft_graph_client_secret"),
        "missing_client_secret",
    )
    encryption_key = _required_encryption_key(
        _setting(settings_obj, "encryption_key"),
    )

    app_origin = _canonical_app_origin(_setting(settings_obj, "app_public_url"))
    expected_redirect_uri = f"{app_origin}{MICROSOFT_GRAPH_CALLBACK_PATH}"
    configured_redirect_uri = _optional_string(
        _setting(settings_obj, "microsoft_graph_redirect_uri")
    )
    if configured_redirect_uri and configured_redirect_uri != expected_redirect_uri:
        raise MicrosoftGraphConfigurationError("invalid_redirect_uri")
    redirect_uri = configured_redirect_uri or expected_redirect_uri
    _validate_callback_uri(redirect_uri, expected_redirect_uri)

    scopes = normalize_scope_set(_setting(settings_obj, "microsoft_graph_scopes"))
    if not REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES.issubset(scopes):
        raise MicrosoftGraphConfigurationError("missing_required_scopes")
    if set(scopes) != REQUIRED_MICROSOFT_GRAPH_CONTEXT_SCOPES:
        raise MicrosoftGraphConfigurationError("unreviewed_scopes")

    encryption_key_fingerprint = _fingerprint_secret(
        "encryption-key",
        encryption_key,
    )
    deployment_key = f"{environment}:{schema}"
    context_fingerprint = _fingerprint_json(
        "deployment-context",
        {
            "client_id": client_id,
            "deployment_key": deployment_key,
            "encryption_key_fingerprint": encryption_key_fingerprint,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "tenant_id": tenant_id,
        },
    )

    authority_url = f"https://login.microsoftonline.com/{tenant_id}"
    issuer = f"{authority_url}/v2.0"
    return MicrosoftGraphContext(
        environment=environment,
        deployment_schema=schema,
        deployment_key=deployment_key,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=SecretStr(client_secret),
        redirect_uri=redirect_uri,
        scopes=scopes,
        scope_value=" ".join(scopes),
        encryption_key_fingerprint=encryption_key_fingerprint,
        context_fingerprint=context_fingerprint,
        authority_url=authority_url,
        authorization_url=f"{authority_url}/oauth2/v2.0/authorize",
        token_url=f"{authority_url}/oauth2/v2.0/token",
        issuer=issuer,
        discovery_url=f"{issuer}/.well-known/openid-configuration",
        jwks_url=f"{authority_url}/discovery/v2.0/keys",
    )


def validate_microsoft_id_token(
    id_token: str,
    context: MicrosoftGraphContext,
    nonce_digest: str,
    http_client: object = httpx,
) -> dict[str, str]:
    """Verify a tenant-specific Entra ID token and return non-PII identifiers."""
    if not isinstance(id_token, str) or not id_token:
        raise MicrosoftGraphIdentityTokenError()
    if not isinstance(nonce_digest, str) or not _SHA256_HEX_PATTERN.fullmatch(nonce_digest):
        raise MicrosoftGraphIdentityTokenError("invalid_nonce_digest")

    try:
        key_set = _load_microsoft_oidc_key_set(context, http_client)
        try:
            decoded = jwt.decode(id_token, key_set, algorithms=["RS256"])
        except InvalidKeyIdError:
            refreshed_key_set = _load_microsoft_oidc_key_set(context, http_client)
            decoded = jwt.decode(id_token, refreshed_key_set, algorithms=["RS256"])

        _validate_id_token_header(decoded.header)
        claims = decoded.claims
        JWTClaimsRegistry(
            leeway=60,
            iss={"essential": True, "value": context.issuer},
            aud={"essential": True, "value": context.client_id},
            exp={"essential": True},
            iat={"essential": True},
            nbf={"essential": True},
            nonce={"essential": True},
            tid={"essential": True, "value": context.tenant_id},
            oid={"essential": True},
            sub={"essential": True},
            ver={"essential": True, "value": "2.0"},
        ).validate(claims)

        audience = claims.get("aud")
        if not isinstance(audience, str) or audience != context.client_id:
            raise MicrosoftGraphIdentityTokenError()

        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise MicrosoftGraphIdentityTokenError()
        actual_nonce_digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual_nonce_digest, nonce_digest):
            raise MicrosoftGraphIdentityTokenError()

        tenant_id = _canonical_claim_guid(claims.get("tid"))
        object_id = _canonical_claim_guid(claims.get("oid"))
        if tenant_id != context.tenant_id:
            raise MicrosoftGraphIdentityTokenError()

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise MicrosoftGraphIdentityTokenError()
        _validate_numeric_dates(claims)
    except MicrosoftGraphIdentityTokenError:
        raise
    except (JoseError, KeyError, OverflowError, TypeError, ValueError, httpx.HTTPError):
        raise MicrosoftGraphIdentityTokenError() from None

    return {"oid": object_id, "tid": tenant_id, "sub": subject}


def _load_microsoft_oidc_key_set(
    context: MicrosoftGraphContext,
    http_client: object,
) -> KeySet:
    metadata = _get_json_document(http_client, context.discovery_url)
    if metadata.get("issuer") != context.issuer:
        raise MicrosoftGraphIdentityTokenError("invalid_oidc_metadata")
    if metadata.get("jwks_uri") != context.jwks_url:
        raise MicrosoftGraphIdentityTokenError("invalid_oidc_metadata")
    algorithms = metadata.get("id_token_signing_alg_values_supported")
    if not isinstance(algorithms, list) or "RS256" not in algorithms:
        raise MicrosoftGraphIdentityTokenError("invalid_oidc_metadata")

    document = _get_json_document(http_client, context.jwks_url)
    raw_keys = document.get("keys")
    if not isinstance(raw_keys, list):
        raise MicrosoftGraphIdentityTokenError("invalid_jwks")

    accepted_keys: list[dict[str, Any]] = []
    seen_key_ids: set[str] = set()
    for raw_key in raw_keys:
        if not isinstance(raw_key, dict):
            continue
        key_id = raw_key.get("kid")
        if (
            raw_key.get("kty") != "RSA"
            or raw_key.get("use") != "sig"
            or not isinstance(key_id, str)
            or not key_id
            or raw_key.get("issuer") != context.issuer
            or raw_key.get("alg") not in (None, "RS256")
        ):
            continue
        if key_id in seen_key_ids:
            raise MicrosoftGraphIdentityTokenError("invalid_jwks")
        seen_key_ids.add(key_id)
        accepted_keys.append(raw_key)

    if not accepted_keys:
        raise MicrosoftGraphIdentityTokenError("invalid_jwks")
    try:
        return KeySet.import_key_set({"keys": accepted_keys})
    except (JoseError, KeyError, TypeError, ValueError):
        raise MicrosoftGraphIdentityTokenError("invalid_jwks") from None


def _get_json_document(http_client: object, url: str) -> dict[str, Any]:
    get = getattr(http_client, "get", None)
    if not callable(get):
        raise MicrosoftGraphIdentityTokenError("oidc_unavailable")
    response = get(
        url,
        timeout=MICROSOFT_OIDC_HTTP_TIMEOUT_SECONDS,
        follow_redirects=False,
    )
    if bool(getattr(response, "is_redirect", False)):
        raise MicrosoftGraphIdentityTokenError("oidc_unavailable")
    raise_for_status = getattr(response, "raise_for_status", None)
    read_json = getattr(response, "json", None)
    if not callable(raise_for_status) or not callable(read_json):
        raise MicrosoftGraphIdentityTokenError("oidc_unavailable")
    raise_for_status()
    document = read_json()
    if not isinstance(document, dict):
        raise MicrosoftGraphIdentityTokenError("invalid_oidc_document")
    return document


def _validate_id_token_header(header: Mapping[str, Any]) -> None:
    if header.get("alg") != "RS256" or header.get("typ") != "JWT":
        raise MicrosoftGraphIdentityTokenError()
    key_id = header.get("kid")
    if not isinstance(key_id, str) or not key_id:
        raise MicrosoftGraphIdentityTokenError()


def _validate_numeric_dates(claims: Mapping[str, Any]) -> None:
    numeric_dates: dict[str, float] = {}
    for name in ("exp", "iat", "nbf"):
        value = claims.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MicrosoftGraphIdentityTokenError()
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise MicrosoftGraphIdentityTokenError()
        numeric_dates[name] = numeric_value
    if numeric_dates["iat"] > numeric_dates["exp"]:
        raise MicrosoftGraphIdentityTokenError()
    if numeric_dates["nbf"] > numeric_dates["exp"]:
        raise MicrosoftGraphIdentityTokenError()


def _setting(settings_obj: object, name: str) -> Any:
    if isinstance(settings_obj, Mapping):
        return settings_obj.get(name)
    return getattr(settings_obj, name, None)


def _canonical_deployment_value(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise MicrosoftGraphConfigurationError(code)
    normalized = value.strip().lower()
    if not _DEPLOYMENT_VALUE_PATTERN.fullmatch(normalized):
        raise MicrosoftGraphConfigurationError(code)
    return normalized


def _canonical_guid(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise MicrosoftGraphConfigurationError(code)
    if not _CANONICAL_GUID_PATTERN.fullmatch(value):
        raise MicrosoftGraphConfigurationError(code)
    parsed = UUID(value)
    if parsed.int == 0 or str(parsed) != value:
        raise MicrosoftGraphConfigurationError(code)
    return str(parsed)


def _canonical_claim_guid(value: Any) -> str:
    if not isinstance(value, str) or not _CANONICAL_GUID_PATTERN.fullmatch(value):
        raise MicrosoftGraphIdentityTokenError()
    parsed = UUID(value)
    if parsed.int == 0 or str(parsed) != value:
        raise MicrosoftGraphIdentityTokenError()
    return str(parsed)


def _required_secret(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MicrosoftGraphConfigurationError(code)
    return value


def _required_encryption_key(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MicrosoftGraphConfigurationError("missing_encryption_key")
    if len(value) < 32 or len(value.encode("utf-8")) < 32:
        raise MicrosoftGraphConfigurationError("weak_encryption_key")
    return value


def _optional_string(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise MicrosoftGraphConfigurationError("invalid_redirect_uri")
    return value.strip()


def _canonical_app_origin(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MicrosoftGraphConfigurationError("invalid_app_public_url")
    raw = value.strip()
    if "?" in raw or "#" in raw:
        raise MicrosoftGraphConfigurationError("invalid_app_public_url")
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        raise MicrosoftGraphConfigurationError("invalid_app_public_url") from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise MicrosoftGraphConfigurationError("invalid_app_public_url")

    host = parsed.hostname.lower()
    try:
        host.encode("ascii")
    except UnicodeEncodeError:
        raise MicrosoftGraphConfigurationError("invalid_app_public_url") from None
    scheme = parsed.scheme.lower()
    if scheme != "https":
        raise MicrosoftGraphConfigurationError("insecure_app_public_url")

    display_host = f"[{host}]" if ":" in host else host
    netloc = f"{display_host}:{port}" if port is not None else display_host
    return f"{scheme}://{netloc}"


def _validate_callback_uri(callback_uri: str, expected_redirect_uri: str) -> None:
    if callback_uri != expected_redirect_uri:
        raise MicrosoftGraphConfigurationError("invalid_redirect_uri")
    try:
        parsed = urlsplit(callback_uri)
    except ValueError:
        raise MicrosoftGraphConfigurationError("invalid_redirect_uri") from None
    if (
        parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise MicrosoftGraphConfigurationError("invalid_redirect_uri")


def _fingerprint_secret(label: str, secret: str) -> str:
    material = (
        f"transmuter:microsoft-graph:{label}:{MICROSOFT_GRAPH_FINGERPRINT_VERSION}\0"
    ).encode("ascii") + secret.encode("utf-8")
    return f"{MICROSOFT_GRAPH_FINGERPRINT_VERSION}:{hashlib.sha256(material).hexdigest()}"


def _fingerprint_json(label: str, value: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    material = (
        f"transmuter:microsoft-graph:{label}:{MICROSOFT_GRAPH_FINGERPRINT_VERSION}\0{serialized}"
    ).encode()
    return f"{MICROSOFT_GRAPH_FINGERPRINT_VERSION}:{hashlib.sha256(material).hexdigest()}"
