"""Build Supabase Auth metadata without exposing authorization claims to users."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

AUTHORIZATION_METADATA_KEYS = ("tenant_id", "role")
AUTHORIZATION_SCOPES = frozenset({"public", "transmuter_dev", "transmuter"})


def authorization_metadata_key(scope: str) -> str:
    """Return the independent top-level Auth metadata key for an allowed schema."""
    if scope not in AUTHORIZATION_SCOPES:
        allowed = ", ".join(sorted(AUTHORIZATION_SCOPES))
        raise ValueError(f"Unsupported authorization scope {scope!r}; expected one of: {allowed}")
    return f"transmuter_authorization_{scope}"


def build_auth_metadata_payload(
    user: Any | None,
    *,
    authorization: Mapping[str, Any],
    profile: Mapping[str, Any] | None = None,
    scope: str | None = None,
    preserve_legacy_user_authorization: bool = True,
) -> dict[str, dict[str, Any]]:
    """Build a top-level merge patch without copying concurrent metadata fields."""
    authorization_patch = dict(authorization)
    if scope is not None:
        authorization_patch = {
            authorization_metadata_key(scope): authorization_patch,
            "tenant_id": None,
            "role": None,
            "platform_admin": None,
        }
    if user is None:
        authorization_patch = {
            key: value for key, value in authorization_patch.items() if value is not None
        }
    user_metadata = dict(profile or {})
    if user is None or not preserve_legacy_user_authorization:
        for key in AUTHORIZATION_METADATA_KEYS:
            if user is None:
                user_metadata.pop(key, None)
            else:
                # GoTrue merges metadata updates; null is the JSON merge-patch deletion marker.
                user_metadata[key] = None
    return {
        "app_metadata": authorization_patch,
        "user_metadata": user_metadata,
    }


def verify_scoped_authorization(
    admin: Any,
    user_id: str,
    *,
    scope: str,
    authorization: Mapping[str, Any],
) -> None:
    """Refetch a tenant Auth user and fail if the scoped authorization did not persist."""
    response = admin.get_user_by_id(user_id)
    user = getattr(response, "user", None)
    app_metadata = getattr(user, "app_metadata", None)
    expected = dict(authorization)
    if (
        not isinstance(app_metadata, dict)
        or app_metadata.get(authorization_metadata_key(scope)) != expected
        or any(key in app_metadata for key in ("tenant_id", "role", "platform_admin"))
    ):
        raise RuntimeError("Supabase Auth authorization metadata verification failed")
