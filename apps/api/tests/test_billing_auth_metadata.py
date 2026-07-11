from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from app.services.billing import BillingProvisioningService

TENANT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-2222-2222-222222222222"


class FakeAuthAdmin:
    def __init__(self, user: SimpleNamespace | None = None) -> None:
        self.user = user
        self.created_payload: dict[str, Any] | None = None
        self.updated_payload: dict[str, Any] | None = None

    def list_users(self, page: int, per_page: int) -> list[SimpleNamespace]:
        return [self.user] if self.user is not None else []

    def get_user_by_id(self, user_id: str) -> SimpleNamespace:
        assert self.user is not None
        assert str(self.user.id) == user_id
        return SimpleNamespace(user=self.user)

    def create_user(self, payload: dict[str, Any]) -> SimpleNamespace:
        self.created_payload = payload
        return SimpleNamespace(user=SimpleNamespace(id=USER_ID))

    def update_user_by_id(self, user_id: str, payload: dict[str, Any]) -> SimpleNamespace:
        assert user_id == USER_ID
        self.updated_payload = payload
        assert self.user is not None
        app_metadata = {**self.user.app_metadata}
        for key, value in payload["app_metadata"].items():
            if value is None:
                app_metadata.pop(key, None)
            else:
                app_metadata[key] = value
        self.user.app_metadata = app_metadata
        return SimpleNamespace(user=self.user)


def test_billing_creates_initial_admin_with_admin_owned_authorization(monkeypatch) -> None:
    monkeypatch.setattr("app.services.billing.get_supabase_schema", lambda: "public")
    auth_admin = FakeAuthAdmin()
    client = SimpleNamespace(auth=SimpleNamespace(admin=auth_admin))
    service = BillingProvisioningService(client)  # type: ignore[arg-type]

    user_id = service._ensure_auth_user_with_password(
        tenant_id=TENANT_ID,
        email="admin@example.com",
        display_name="Tenant Admin",
        password="Transmuter2026!",
    )

    assert user_id == USER_ID
    assert auth_admin.created_payload is not None
    assert auth_admin.created_payload["app_metadata"] == {
        "transmuter_authorization_public": {
            "tenant_id": TENANT_ID,
            "role": "transformation_office",
        },
    }
    assert auth_admin.created_payload["user_metadata"] == {"display_name": "Tenant Admin"}


def test_billing_existing_admin_preserves_provider_metadata_and_legacy_claims(monkeypatch) -> None:
    monkeypatch.setattr("app.services.billing.get_supabase_schema", lambda: "public")
    auth_admin = FakeAuthAdmin(
        SimpleNamespace(
            id=USER_ID,
            email="admin@example.com",
            app_metadata={
                "provider": "email",
                "providers": ["email"],
                "transmuter_authorization_transmuter_dev": {
                    "tenant_id": "dev-tenant",
                    "role": "viewer",
                },
            },
            user_metadata={
                "tenant_id": "legacy",
                "role": "viewer",
                "display_name": "Old Name",
                "locale": "en",
            },
        )
    )
    client = SimpleNamespace(auth=SimpleNamespace(admin=auth_admin))
    service = BillingProvisioningService(client)  # type: ignore[arg-type]

    user_id = service._ensure_auth_user_with_password(
        tenant_id=TENANT_ID,
        email="admin@example.com",
        display_name="Tenant Admin",
        password="Transmuter2026!",
    )

    assert user_id == USER_ID
    assert auth_admin.updated_payload is not None
    assert auth_admin.updated_payload["app_metadata"] == {
        "transmuter_authorization_public": {
            "tenant_id": TENANT_ID,
            "role": "transformation_office",
        },
        "tenant_id": None,
        "role": None,
        "platform_admin": None,
    }
    assert auth_admin.updated_payload["user_metadata"] == {
        "display_name": "Tenant Admin",
    }


def test_billing_existing_admin_rolls_back_database_when_auth_sync_fails(monkeypatch) -> None:
    previous = {
        "id": USER_ID,
        "tenant_id": TENANT_ID,
        "email": "admin@example.com",
        "display_name": "Original Admin",
        "role": "viewer",
        "status": "pending",
        "must_change_password": True,
        "onboarding_completed": True,
        "updated_at": "2026-07-01T00:00:00+00:00",
    }
    client = FakeBillingUserClient(previous)
    service = BillingProvisioningService(client)  # type: ignore[arg-type]

    def fail_sync(**_kwargs: str) -> None:
        raise HTTPException(status_code=502, detail="Auth sync failed")

    monkeypatch.setattr(service, "_sync_initial_admin_auth", fail_sync)

    with pytest.raises(HTTPException) as exc:
        service._ensure_initial_admin(
            tenant_id=TENANT_ID,
            email="admin@example.com",
            display_name="Updated Admin",
            password="Transmuter2026!",
        )

    assert exc.value.status_code == 502
    assert client.user["display_name"] == "Original Admin"
    assert client.user["role"] == "viewer"
    assert client.user["status"] == "pending"
    assert client.user["must_change_password"] is True
    assert client.user["onboarding_completed"] is True


class FakeBillingUserClient:
    def __init__(self, user: dict[str, Any]) -> None:
        self.user = {**user}

    def table(self, name: str) -> FakeBillingUserQuery:
        assert name == "users"
        return FakeBillingUserQuery(self)


class FakeBillingUserQuery:
    def __init__(self, client: FakeBillingUserClient) -> None:
        self._client = client
        self._operation = "select"
        self._filters: dict[str, Any] = {}
        self._payload: dict[str, Any] = {}

    def select(self, _columns: str) -> FakeBillingUserQuery:
        return self

    def update(self, payload: dict[str, Any]) -> FakeBillingUserQuery:
        self._operation = "update"
        self._payload = payload
        return self

    def eq(self, key: str, value: Any) -> FakeBillingUserQuery:
        self._filters[key] = value
        return self

    def maybe_single(self) -> FakeBillingUserQuery:
        return self

    def execute(self) -> SimpleNamespace:
        matches = all(self._client.user.get(key) == value for key, value in self._filters.items())
        if not matches:
            return SimpleNamespace(data=None if self._operation == "select" else [])
        if self._operation == "update":
            self._client.user.update(self._payload)
            return SimpleNamespace(data=[self._client.user])
        return SimpleNamespace(data={**self._client.user})
