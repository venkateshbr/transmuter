from types import SimpleNamespace

import pytest

from app.core.auth_metadata import (
    AUTHORIZATION_SCOPES,
    authorization_metadata_key,
    build_auth_metadata_payload,
    verify_scoped_authorization,
)


def test_auth_metadata_keeps_authorization_admin_only_and_preserves_provider_fields() -> None:
    app_metadata = {
        "provider": "email",
        "providers": ["email"],
        "tenant_id": "stale-global-tenant",
        "role": "platform_admin",
        "platform_admin": True,
        "transmuter_authorization_transmuter_dev": {
            "tenant_id": "dev-tenant",
            "role": "viewer",
        },
    }
    user_metadata = {
        "tenant_id": "legacy-tenant",
        "role": "viewer",
        "display_name": "Previous Name",
        "locale": "en",
    }

    payload = build_auth_metadata_payload(
        object(),
        authorization={"tenant_id": "tenant-1", "role": "initiative_owner"},
        profile={"display_name": "Updated Name"},
        scope="public",
    )

    assert payload["app_metadata"] == {
        "transmuter_authorization_public": {
            "tenant_id": "tenant-1",
            "role": "initiative_owner",
        },
        "tenant_id": None,
        "role": None,
        "platform_admin": None,
    }
    assert payload["user_metadata"] == {"display_name": "Updated Name"}

    merged_app_metadata = _merge_metadata(app_metadata, payload["app_metadata"])
    assert merged_app_metadata == {
        "provider": "email",
        "providers": ["email"],
        "transmuter_authorization_public": {
            "tenant_id": "tenant-1",
            "role": "initiative_owner",
        },
        "transmuter_authorization_transmuter_dev": {
            "tenant_id": "dev-tenant",
            "role": "viewer",
        },
    }
    assert _merge_metadata(user_metadata, payload["user_metadata"]) == {
        "tenant_id": "legacy-tenant",
        "role": "viewer",
        "display_name": "Updated Name",
        "locale": "en",
    }


def test_auth_metadata_omits_null_authorization_fields_for_new_user() -> None:
    payload = build_auth_metadata_payload(
        None,
        authorization={
            "tenant_id": None,
            "role": "platform_admin",
            "platform_admin": True,
        },
    )

    assert payload["app_metadata"] == {
        "role": "platform_admin",
        "platform_admin": True,
    }
    assert payload["user_metadata"] == {}


def test_authorization_metadata_key_uses_fixed_scope_allowlist() -> None:
    assert frozenset({"public", "transmuter_dev", "transmuter"}) == AUTHORIZATION_SCOPES
    assert authorization_metadata_key("public") == "transmuter_authorization_public"
    assert authorization_metadata_key("transmuter_dev") == "transmuter_authorization_transmuter_dev"
    assert authorization_metadata_key("transmuter") == "transmuter_authorization_transmuter"

    with pytest.raises(ValueError, match="Unsupported authorization scope"):
        authorization_metadata_key("public.attacker")


def test_verify_scoped_authorization_rejects_mismatch_and_global_markers() -> None:
    admin = SimpleNamespace(
        get_user_by_id=lambda _user_id: SimpleNamespace(
            user=SimpleNamespace(
                app_metadata={
                    "transmuter_authorization_public": {
                        "tenant_id": "wrong-tenant",
                        "role": "viewer",
                    },
                    "platform_admin": True,
                }
            )
        )
    )

    with pytest.raises(RuntimeError, match="authorization metadata verification failed"):
        verify_scoped_authorization(
            admin,
            "user-1",
            scope="public",
            authorization={"tenant_id": "tenant-1", "role": "viewer"},
        )


def test_verify_scoped_authorization_requires_global_marker_absence() -> None:
    app_metadata = {
        "transmuter_authorization_public": {
            "tenant_id": "tenant-1",
            "role": "viewer",
        },
        "platform_admin": None,
    }
    admin = SimpleNamespace(
        get_user_by_id=lambda _user_id: SimpleNamespace(
            user=SimpleNamespace(app_metadata=app_metadata)
        )
    )

    with pytest.raises(RuntimeError, match="authorization metadata verification failed"):
        verify_scoped_authorization(
            admin,
            "user-1",
            scope="public",
            authorization={"tenant_id": "tenant-1", "role": "viewer"},
        )

    app_metadata.pop("platform_admin")
    verify_scoped_authorization(
        admin,
        "user-1",
        scope="public",
        authorization={"tenant_id": "tenant-1", "role": "viewer"},
    )


def _merge_metadata(current: dict[str, object], patch: dict[str, object]) -> dict[str, object]:
    merged = {**current}
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged
