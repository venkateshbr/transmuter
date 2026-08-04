"""Encrypted, short-lived authority references for Hermes tool calls."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

HERMES_READ_SCOPE = "transmuter_tools:read"
_CONTEXT_PREFIX = "ctx_"


class HermesContextError(ValueError):
    """Raised when a Hermes context reference is invalid, expired, or mis-scoped."""


@dataclass(frozen=True)
class HermesToolContext:
    tenant_id: str
    user_id: str
    thread_id: str
    scope: str
    expires_at: int


def create_hermes_context_ref(
    *,
    tenant_id: str,
    user_id: str,
    thread_id: str,
    scope: str = HERMES_READ_SCOPE,
    ttl_seconds: int | None = None,
    now: int | None = None,
) -> str:
    """Create an encrypted reference; Hermes cannot inspect or alter its authority."""
    issued_at = int(time.time()) if now is None else now
    ttl = ttl_seconds or settings.hermes_context_ttl_seconds
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "thread_id": thread_id,
        "scope": scope,
        "iat": issued_at,
        "exp": issued_at + ttl,
    }
    token = _fernet().encrypt(_canonical_json(payload)).decode("ascii")
    return f"{_CONTEXT_PREFIX}{token}"


def verify_hermes_context_ref(
    context_ref: str,
    *,
    required_scope: str = HERMES_READ_SCOPE,
    now: int | None = None,
) -> HermesToolContext:
    """Decrypt and validate a context reference supplied to the private broker."""
    if not context_ref.startswith(_CONTEXT_PREFIX):
        raise HermesContextError("Invalid context reference")
    current_time = int(time.time()) if now is None else now
    token = context_ref[len(_CONTEXT_PREFIX) :]
    try:
        token_bytes = token.encode("ascii")
        decoded = base64.b64decode(token_bytes, altchars=b"-_", validate=True)
        canonical_token = base64.urlsafe_b64encode(decoded).decode("ascii")
        if not hmac.compare_digest(token, canonical_token):
            raise ValueError("Non-canonical context token")
        payload = json.loads(_fernet().decrypt(token_bytes).decode("utf-8"))
    except (
        InvalidToken,
        ValueError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        json.JSONDecodeError,
    ) as exc:
        raise HermesContextError("Invalid context reference") from exc
    if not isinstance(payload, dict):
        raise HermesContextError("Invalid context payload")

    expires_at = _required_int(payload, "exp")
    if expires_at < current_time:
        raise HermesContextError("Context reference expired")
    scope = _required_str(payload, "scope")
    if scope != required_scope:
        raise HermesContextError("Context reference scope is not allowed")
    return HermesToolContext(
        tenant_id=_required_str(payload, "tenant_id"),
        user_id=_required_str(payload, "user_id"),
        thread_id=_required_str(payload, "thread_id"),
        scope=scope,
        expires_at=expires_at,
    )


def _fernet() -> Fernet:
    secret = (
        settings.hermes_context_signing_secret.strip()
        or settings.hermes_tool_token.strip()
        or settings.jwt_secret.strip()
    )
    if len(secret) < 32:
        raise HermesContextError("Hermes context signing secret must be at least 32 characters")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise HermesContextError(f"Context payload missing {key}")
    return value


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise HermesContextError(f"Context payload missing {key}")
    return value
