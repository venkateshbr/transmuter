from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.domain.people import InviteAccept, InviteCreate, UserCreate, UserTemporaryPassword
from app.services.people import PeopleInviteAcceptanceService, PeopleService

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = "22222222-2222-2222-2222-222222222222"


class FakePeopleRepository:
    def __init__(self) -> None:
        self.saved_user: dict[str, object] | None = None
        self.workstream_ids: list[str] = []
        self.saved_invite: dict[str, object] | None = None
        self.saved_invites: list[dict[str, object]] = []
        self.updated_user: dict[str, object] | None = None

    def get_user_by_email(self, email: str) -> dict[str, object] | None:
        return None

    def get_pending_invite_by_email(self, email: str) -> dict[str, object] | None:
        return None

    def upsert_user(self, row: dict[str, object]) -> dict[str, object]:
        self.saved_user = row
        return {**row, "id": str(row["id"])}

    def replace_user_workstreams(
        self,
        user_id: str,
        workstream_ids: list[str],
    ) -> list[dict[str, object]]:
        self.workstream_ids = workstream_ids
        return [
            {"id": f"uw-{index}", "workstream_id": workstream_id}
            for index, workstream_id in enumerate(workstream_ids)
        ]

    def get_user(self, user_id: str) -> dict[str, object] | None:
        assert self.saved_user is not None
        return {**self.saved_user, "id": user_id}

    def list_user_workstreams(self, user_id: str) -> list[dict[str, object]]:
        return [
            {"id": "uw-1", "workstream_id": workstream_id} for workstream_id in self.workstream_ids
        ]

    def list_owned_initiatives(self, user_id: str) -> list[dict[str, object]]:
        return []

    def list_owned_milestones(self, user_id: str) -> list[dict[str, object]]:
        return []

    def list_assigned_actions(self, user_id: str) -> list[dict[str, object]]:
        return []

    def insert_invite(self, row: dict[str, object]) -> dict[str, object]:
        self.saved_invite = {
            "id": f"invite-{len(self.saved_invites) + 1}",
            **row,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.saved_invites.append(self.saved_invite)
        return self.saved_invite

    def update_invite(self, invite_id: str, patch: dict[str, object]) -> dict[str, object]:
        for index, invite in enumerate(self.saved_invites):
            if invite["id"] == invite_id:
                updated = {**invite, **patch}
                self.saved_invites[index] = updated
                self.saved_invite = updated
                return updated
        assert self.saved_invite is not None
        self.saved_invite = {**self.saved_invite, **patch}
        return self.saved_invite

    def get_invite(self, invite_id: str) -> dict[str, object] | None:
        return self.saved_invite

    def list_pending_invites_by_email(self, email: str) -> list[dict[str, object]]:
        return [
            invite
            for invite in self.saved_invites
            if invite.get("email") == email and invite.get("status") == "pending"
        ]

    def list_invites(self) -> list[dict[str, object]]:
        return self.saved_invites

    def update_user(self, user_id: str, patch: dict[str, object]) -> dict[str, object]:
        assert self.saved_user is not None
        self.saved_user = {**self.saved_user, **patch}
        self.updated_user = self.saved_user
        return self.saved_user


def test_create_user_marks_account_pending_with_forced_password_change(monkeypatch) -> None:
    service = PeopleService(client=object(), tenant_id=TENANT_ID)  # type: ignore[arg-type]
    repo = FakePeopleRepository()
    service._repo = repo
    monkeypatch.setattr(service, "_ensure_auth_password_user", lambda data: USER_ID)

    result = service.create_user(
        UserCreate(
            email="new.user@example.com",
            display_name="New User",
            role="initiative_owner",
            temporary_password="Transmuter2026!",
            workstream_ids=["ws-1"],
        )
    )

    assert repo.saved_user is not None
    assert repo.saved_user["status"] == "pending"
    assert repo.saved_user["must_change_password"] is True
    assert repo.saved_user["onboarding_completed"] is False
    assert repo.workstream_ids == ["ws-1"]
    assert result["status"] == "pending"


def test_create_user_rejects_weak_temporary_password(monkeypatch) -> None:
    service = PeopleService(client=object(), tenant_id=TENANT_ID)  # type: ignore[arg-type]
    service._repo = FakePeopleRepository()
    monkeypatch.setattr(service, "_ensure_auth_password_user", lambda data: USER_ID)

    with pytest.raises(HTTPException) as exc:
        service.create_user(
            UserCreate(
                email="new.user@example.com",
                display_name="New User",
                role="initiative_owner",
                temporary_password="weakpassword",
            )
        )

    assert exc.value.status_code == 400
    assert "uppercase" in exc.value.detail


def test_create_user_rejects_existing_orphan_auth_account(monkeypatch) -> None:
    service = PeopleService(client=object(), tenant_id=TENANT_ID)  # type: ignore[arg-type]
    service._repo = FakePeopleRepository()
    monkeypatch.setattr(service, "_find_auth_user_id", lambda email: USER_ID)

    with pytest.raises(HTTPException) as exc:
        service.create_user(
            UserCreate(
                email="orphan@example.com",
                display_name="Orphan User",
                role="viewer",
                temporary_password="Transmuter2026!",
            )
        )

    assert exc.value.status_code == 409
    assert "auth account already exists" in exc.value.detail


def test_invite_user_rejects_existing_orphan_auth_account(monkeypatch) -> None:
    service = PeopleService(client=object(), tenant_id=TENANT_ID)  # type: ignore[arg-type]
    service._repo = FakePeopleRepository()
    monkeypatch.setattr(service, "_find_auth_user_id", lambda email: USER_ID)

    with pytest.raises(HTTPException) as exc:
        service.invite_user(
            InviteCreate(
                email="orphan@example.com",
                display_name="Orphan User",
                role="viewer",
            ),
            created_by_id=USER_ID,
        )

    assert exc.value.status_code == 409
    assert "auth account already exists" in exc.value.detail


def test_invite_user_creates_hashed_app_owned_invite(monkeypatch) -> None:
    service = PeopleService(client=object(), tenant_id=TENANT_ID)  # type: ignore[arg-type]
    repo = FakePeopleRepository()
    service._repo = repo
    service._email = SimpleNamespace(
        deliver=lambda **kwargs: SimpleNamespace(
            status="queued",
            detail="email_not_configured",
            recipient_count=1,
        )
    )
    monkeypatch.setattr(service, "_find_auth_user_id", lambda email: None)
    monkeypatch.setattr("app.services.people.settings.app_public_url", "https://transmuter.test")

    result = service.invite_user(
        InviteCreate(
            email="Invited.User@Example.com",
            display_name="Invited User",
            role="viewer",
            workstream_ids=["33333333-3333-3333-3333-333333333333"],
        ),
        created_by_id=USER_ID,
    )

    assert repo.saved_invite is not None
    assert repo.saved_invite["email"] == "invited.user@example.com"
    assert repo.saved_invite["status"] == "pending"
    assert repo.saved_invite["token_hash"] != result.get("invite_url")
    assert "token_hash" not in result
    assert "invite_url" in result
    assert str(result["invite_url"]).startswith("https://transmuter.test/auth/accept-invite?")
    assert result["delivery_status"] == "queued"


def test_send_password_setup_link_creates_reset_token(monkeypatch) -> None:
    service = PeopleService(client=object(), tenant_id=TENANT_ID)  # type: ignore[arg-type]
    repo = FakePeopleRepository()
    repo.saved_user = {
        "id": USER_ID,
        "tenant_id": str(TENANT_ID),
        "email": "pending.user@example.com",
        "display_name": "Pending User",
        "role": "viewer",
        "status": "pending",
        "must_change_password": True,
    }
    repo.insert_invite(
        {
            "tenant_id": str(TENANT_ID),
            "email": "pending.user@example.com",
            "display_name": "Old Token",
            "role": "viewer",
            "token_hash": "old-token-hash",
            "purpose": "password_setup",
            "status": "pending",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        }
    )
    service._repo = repo
    service._email = SimpleNamespace(
        deliver=lambda **kwargs: SimpleNamespace(
            status="queued",
            detail="email_not_configured",
            recipient_count=1,
        )
    )
    monkeypatch.setattr("app.services.people.settings.app_public_url", "https://transmuter.test")

    result = service.send_password_setup_link(USER_ID, created_by_id=USER_ID)

    assert repo.saved_invites[0]["status"] == "revoked"
    assert repo.saved_invite is not None
    assert repo.saved_invite["purpose"] == "password_setup"
    assert repo.saved_invite["email"] == "pending.user@example.com"
    assert "token_hash" not in result
    assert str(result["invite_url"]).startswith("https://transmuter.test/auth/accept-invite?")


def test_set_temporary_password_activates_user_and_forces_change(monkeypatch) -> None:
    service = PeopleService(client=object(), tenant_id=TENANT_ID)  # type: ignore[arg-type]
    repo = FakePeopleRepository()
    repo.saved_user = {
        "id": USER_ID,
        "tenant_id": str(TENANT_ID),
        "email": "pending.user@example.com",
        "display_name": "Pending User",
        "role": "viewer",
        "status": "pending",
        "must_change_password": True,
    }
    service._repo = repo
    password_updates: list[tuple[dict[str, object], str, bool]] = []
    monkeypatch.setattr(
        service,
        "_set_auth_password_for_user",
        lambda user, password, must_change_password: password_updates.append(
            (user, password, must_change_password)
        ),
    )

    result = service.set_temporary_password(
        USER_ID,
        UserTemporaryPassword(temporary_password="Transmuter2026!"),
    )

    assert password_updates[0][1] == "Transmuter2026!"
    assert password_updates[0][2] is True
    assert repo.updated_user is not None
    assert repo.updated_user["status"] == "active"
    assert repo.updated_user["must_change_password"] is True
    assert result["status"] == "active"


def test_accept_invite_creates_active_user_and_marks_token_used() -> None:
    token = "secure-token-for-acceptance-value-123456"
    token_hash = PeopleInviteAcceptanceService.hash_token(token)
    client = FakeInviteClient(
        invite={
            "id": "invite-1",
            "tenant_id": str(TENANT_ID),
            "email": "invitee@example.com",
            "display_name": "Invitee User",
            "role": "initiative_owner",
            "title": "Owner",
            "department": None,
            "market": None,
            "workstream_ids": ["33333333-3333-3333-3333-333333333333"],
            "token_hash": token_hash,
            "status": "pending",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        }
    )

    result = PeopleInviteAcceptanceService(client).accept_invite(
        InviteAccept(
            token=token,
            password="Transmuter2026!",
            confirm_password="Transmuter2026!",
        )
    )

    assert result["email"] == "invitee@example.com"
    assert client.created_auth_user["email"] == "invitee@example.com"
    assert client.inserted_user["status"] == "active"
    assert client.inserted_user["must_change_password"] is False
    assert client.invite["status"] == "accepted"
    assert str(client.invite["token_hash"]).startswith("accepted:invite-1:")
    assert client.workstream_rows[0]["workstream_id"] == "33333333-3333-3333-3333-333333333333"


def test_accept_password_setup_updates_existing_user_password() -> None:
    token = "secure-token-for-reset-value-123456789"
    token_hash = PeopleInviteAcceptanceService.hash_token(token)
    client = FakeInviteClient(
        invite={
            "id": "reset-1",
            "tenant_id": str(TENANT_ID),
            "email": "pending.user@example.com",
            "display_name": "Pending User",
            "role": "viewer",
            "token_hash": token_hash,
            "purpose": "password_setup",
            "status": "pending",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "auth_user_id": USER_ID,
        },
        existing_user={
            "id": USER_ID,
            "tenant_id": str(TENANT_ID),
            "email": "pending.user@example.com",
            "display_name": "Pending User",
            "role": "viewer",
            "status": "pending",
            "must_change_password": True,
        },
    )

    result = PeopleInviteAcceptanceService(client).accept_invite(
        InviteAccept(
            token=token,
            password="Transmuter2026!",
            confirm_password="Transmuter2026!",
        )
    )

    assert result["email"] == "pending.user@example.com"
    assert client.updated_auth_user["id"] == USER_ID
    assert client.updated_auth_user["payload"]["password"] == "Transmuter2026!"
    assert client.existing_user["status"] == "active"
    assert client.existing_user["must_change_password"] is False
    assert client.invite["status"] == "accepted"
    assert str(client.invite["token_hash"]).startswith("accepted:reset-1:")


class FakeInviteClient:
    def __init__(
        self,
        *,
        invite: dict[str, object],
        existing_user: dict[str, object] | None = None,
    ) -> None:
        self.invite = invite
        self.existing_user = existing_user
        self.created_auth_user: dict[str, object] = {}
        self.updated_auth_user: dict[str, object] = {}
        self.inserted_user: dict[str, object] = {}
        self.workstream_rows: list[dict[str, object]] = []
        self.auth = SimpleNamespace(admin=FakeInviteAuthAdmin(self))

    def table(self, name: str) -> "FakeInviteQuery":
        return FakeInviteQuery(self, name)


class FakeInviteAuthAdmin:
    def __init__(self, client: FakeInviteClient) -> None:
        self._client = client

    def list_users(self, page: int, per_page: int) -> list[object]:
        return []

    def create_user(self, payload: dict[str, object]) -> SimpleNamespace:
        self._client.created_auth_user = payload
        return SimpleNamespace(user=SimpleNamespace(id=USER_ID))

    def update_user_by_id(self, user_id: str, payload: dict[str, object]) -> SimpleNamespace:
        self._client.updated_auth_user = {"id": user_id, "payload": payload}
        return SimpleNamespace(user=SimpleNamespace(id=user_id))


class FakeInviteQuery:
    def __init__(self, client: FakeInviteClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._operation = "select"
        self._patch: dict[str, object] = {}
        self._insert: dict[str, object] | list[dict[str, object]] | None = None
        self._filters: dict[str, object] = {}

    def select(self, *args: object, **kwargs: object) -> "FakeInviteQuery":
        self._operation = "select"
        return self

    def insert(self, payload: dict[str, object] | list[dict[str, object]]) -> "FakeInviteQuery":
        self._operation = "insert"
        self._insert = payload
        return self

    def update(self, patch: dict[str, object]) -> "FakeInviteQuery":
        self._operation = "update"
        self._patch = patch
        return self

    def delete(self) -> "FakeInviteQuery":
        self._operation = "delete"
        return self

    def eq(self, key: str, value: object) -> "FakeInviteQuery":
        self._filters[key] = value
        return self

    def maybe_single(self) -> "FakeInviteQuery":
        return self

    def execute(self) -> SimpleNamespace:
        if self._table_name == "user_invites":
            return self._execute_invites()
        if self._table_name == "users":
            return self._execute_users()
        if self._table_name == "user_workstreams":
            return self._execute_workstreams()
        return SimpleNamespace(data=None)

    def _execute_invites(self) -> SimpleNamespace:
        if self._operation == "select":
            if self._filters.get("token_hash") == self._client.invite["token_hash"]:
                return SimpleNamespace(data=self._client.invite)
            return SimpleNamespace(data=None)
        self._client.invite = {**self._client.invite, **self._patch}
        return SimpleNamespace(data=[self._client.invite])

    def _execute_users(self) -> SimpleNamespace:
        if self._operation == "select":
            return SimpleNamespace(data=self._client.existing_user)
        if self._operation == "update":
            assert self._client.existing_user is not None
            self._client.existing_user = {**self._client.existing_user, **self._patch}
            return SimpleNamespace(data=[self._client.existing_user])
        assert isinstance(self._insert, dict)
        self._client.inserted_user = self._insert
        return SimpleNamespace(data=[self._insert])

    def _execute_workstreams(self) -> SimpleNamespace:
        if self._operation == "insert":
            assert isinstance(self._insert, list)
            self._client.workstream_rows = self._insert
            return SimpleNamespace(data=self._insert)
        return SimpleNamespace(data=[])
