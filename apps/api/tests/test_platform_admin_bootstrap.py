from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.bootstrap.platform_admin import ensure_platform_admin_user, rotate_platform_admin_email


class FakeAuthAdmin:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.created_payloads: list[dict[str, Any]] = []
        self.updated_payloads: list[tuple[str, dict[str, Any]]] = []
        self.list_calls = 0

    def seed_user(
        self,
        email: str,
        *,
        app_metadata: dict[str, Any] | None = None,
        user_metadata: dict[str, Any] | None = None,
    ) -> str:
        user_id = f"auth-{len(self.users) + 1}"
        self.users[email.lower()] = {
            "id": user_id,
            "email": email.lower(),
            "app_metadata": app_metadata or {},
            "user_metadata": user_metadata or {},
        }
        return user_id

    def list_users(self, page: int, per_page: int) -> list[SimpleNamespace]:
        assert page >= 1
        assert per_page > 0
        self.list_calls += 1
        return [SimpleNamespace(**user) for user in sorted(self.users.values(), key=str)]

    def create_user(self, payload: dict[str, Any]) -> SimpleNamespace:
        self.created_payloads.append(payload)
        user_id = self.seed_user(
            payload["email"],
            app_metadata=payload.get("app_metadata") or {},
            user_metadata=payload.get("user_metadata") or {},
        )
        self.users[payload["email"].lower()].update(payload)
        return SimpleNamespace(user=SimpleNamespace(id=user_id))

    def update_user_by_id(self, user_id: str, payload: dict[str, Any]) -> None:
        self.updated_payloads.append((user_id, payload))
        for email, user in list(self.users.items()):
            if user["id"] == user_id:
                user.update(payload)
                if "email" in payload:
                    self.users.pop(email)
                    user["email"] = str(payload["email"]).lower()
                    self.users[user["email"]] = user
                return
        raise AssertionError(f"missing auth user {user_id}")


class FakeClient:
    def __init__(self) -> None:
        self.auth = SimpleNamespace(admin=FakeAuthAdmin())

    def table(self, name: str) -> None:
        raise AssertionError(f"platform admin bootstrap must not touch table {name}")


def test_platform_admin_bootstrap_skips_existing_user_with_complete_metadata() -> None:
    client = FakeClient()
    user_id = client.auth.admin.seed_user(
        "venkatesh@ishirock.com",
        app_metadata={"role": "platform_admin", "platform_admin": True},
        user_metadata={"role": "platform_admin"},
    )

    result = ensure_platform_admin_user(
        client,
        allowed_emails="venkatesh@ishirock.com",
    )

    assert result.status == "skipped"
    assert result.email == "venkatesh@ishirock.com"
    assert result.user_id == user_id
    assert client.auth.admin.created_payloads == []
    assert client.auth.admin.updated_payloads == []


def test_platform_admin_bootstrap_updates_existing_user_metadata_only() -> None:
    client = FakeClient()
    user_id = client.auth.admin.seed_user(
        "venkatesh@ishirock.com",
        app_metadata={"provider": "email"},
        user_metadata={"display_name": "Venkatesh"},
    )

    result = ensure_platform_admin_user(
        client,
        allowed_emails="venkatesh@ishirock.com",
    )

    assert result.status == "metadata_updated"
    assert result.user_id == user_id
    user = client.auth.admin.users["venkatesh@ishirock.com"]
    assert user["app_metadata"] == {
        "provider": "email",
        "role": "platform_admin",
        "platform_admin": True,
    }
    assert user["user_metadata"] == {
        "display_name": "Venkatesh",
        "role": "platform_admin",
    }
    assert client.auth.admin.created_payloads == []


def test_platform_admin_bootstrap_creates_missing_user_with_password() -> None:
    client = FakeClient()

    result = ensure_platform_admin_user(
        client,
        allowed_emails="ops@example.com, venkatesh@ishirock.com",
        bootstrap_email="venkatesh@ishirock.com",
        bootstrap_password="TemporaryPassword2026!",
    )

    assert result.status == "created"
    assert result.email == "venkatesh@ishirock.com"
    payload = client.auth.admin.created_payloads[0]
    assert payload["email"] == "venkatesh@ishirock.com"
    assert payload["email_confirm"] is True
    assert payload["password"] == "TemporaryPassword2026!"
    assert payload["app_metadata"] == {"role": "platform_admin", "platform_admin": True}
    assert payload["user_metadata"] == {"role": "platform_admin"}


def test_platform_admin_bootstrap_missing_user_requires_explicit_password() -> None:
    client = FakeClient()

    result = ensure_platform_admin_user(
        client,
        allowed_emails="venkatesh@ishirock.com",
    )

    assert result.status == "missing_password"
    assert result.email == "venkatesh@ishirock.com"
    assert client.auth.admin.users == {}
    assert client.auth.admin.created_payloads == []


def test_platform_admin_bootstrap_disabled_skips_auth_lookup() -> None:
    client = FakeClient()

    result = ensure_platform_admin_user(
        client,
        allowed_emails="venkatesh@ishirock.com",
        enabled=False,
    )

    assert result.status == "disabled"
    assert client.auth.admin.list_calls == 0


def test_platform_admin_bootstrap_email_must_be_allowlisted() -> None:
    client = FakeClient()

    result = ensure_platform_admin_user(
        client,
        allowed_emails="operator@example.com",
        bootstrap_email="venkatesh@ishirock.com",
        bootstrap_password="TemporaryPassword2026!",
    )

    assert result.status == "misconfigured"
    assert result.email == "venkatesh@ishirock.com"
    assert client.auth.admin.list_calls == 0
    assert client.auth.admin.created_payloads == []


def test_platform_admin_rotation_renames_previous_auth_user() -> None:
    client = FakeClient()
    user_id = client.auth.admin.seed_user(
        "admin@ishirock.com",
        app_metadata={"provider": "email"},
        user_metadata={"display_name": "Operator"},
    )

    result = rotate_platform_admin_email(
        client,
        previous_email="admin@ishirock.com",
        allowed_emails="venkatesh@ishirock.com",
        target_email="venkatesh@ishirock.com",
    )

    assert result.status == "renamed"
    assert result.user_id == user_id
    assert "admin@ishirock.com" not in client.auth.admin.users
    user = client.auth.admin.users["venkatesh@ishirock.com"]
    assert user["id"] == user_id
    assert user["email_confirm"] is True
    assert user["app_metadata"] == {
        "provider": "email",
        "role": "platform_admin",
        "platform_admin": True,
    }
    assert user["user_metadata"] == {
        "display_name": "Operator",
        "role": "platform_admin",
    }


def test_platform_admin_rotation_normalizes_target_and_revokes_previous_metadata() -> None:
    client = FakeClient()
    previous_id = client.auth.admin.seed_user(
        "admin@ishirock.com",
        app_metadata={"provider": "email", "role": "platform_admin", "platform_admin": True},
        user_metadata={"role": "platform_admin"},
    )
    target_id = client.auth.admin.seed_user(
        "venkatesh@ishirock.com",
        app_metadata={"provider": "email"},
        user_metadata={"display_name": "Venkatesh"},
    )

    result = rotate_platform_admin_email(
        client,
        previous_email="admin@ishirock.com",
        allowed_emails="venkatesh@ishirock.com",
        target_email="venkatesh@ishirock.com",
    )

    assert result.status == "target_exists"
    assert result.user_id == target_id
    target = client.auth.admin.users["venkatesh@ishirock.com"]
    assert target["app_metadata"] == {
        "provider": "email",
        "role": "platform_admin",
        "platform_admin": True,
    }
    previous = client.auth.admin.users["admin@ishirock.com"]
    assert previous["id"] == previous_id
    assert previous["app_metadata"] == {"provider": "email"}
    assert previous["user_metadata"] == {}
