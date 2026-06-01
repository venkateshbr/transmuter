from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException

from app.domain.people import InviteCreate, UserCreate
from app.services.people import PeopleService

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = "22222222-2222-2222-2222-222222222222"


class FakePeopleRepository:
    def __init__(self) -> None:
        self.saved_user: dict[str, object] | None = None
        self.workstream_ids: list[str] = []

    def get_user_by_email(self, email: str) -> dict[str, object] | None:
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
            )
        )

    assert exc.value.status_code == 409
    assert "auth account already exists" in exc.value.detail
