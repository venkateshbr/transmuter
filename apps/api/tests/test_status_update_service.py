from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from app.domain.status_updates import StatusUpdateCreate
from app.services import status_update as status_update_module
from app.services.status_update import StatusUpdateService


class _FakeStatusUpdateRepository:
    instance: _FakeStatusUpdateRepository | None = None

    def __init__(self, _client: object, _tenant_id: UUID) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.rag_updates: list[tuple[str, str]] = []
        self.client = _client
        _FakeStatusUpdateRepository.instance = self

    def get_draft(self, _initiative_id: str) -> dict[str, Any] | None:
        return None

    def create(
        self,
        initiative_id: str,
        author_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        row = {
            "id": f"status-{len(self.rows) + 1}",
            "tenant_id": "tenant-1",
            "initiative_id": initiative_id,
            "author_id": author_id,
            "rag_status": data["rag_status"],
            "summary": data["summary"],
            "is_draft": data.get("is_draft", True),
            "submitted_at": "2026-06-25T00:00:00+00:00" if data.get("is_draft") is False else None,
        }
        self.rows[row["id"]] = row
        return row

    def get(self, update_id: str) -> dict[str, Any] | None:
        return self.rows.get(update_id)

    def update(self, update_id: str, data: dict[str, Any]) -> dict[str, Any]:
        row = {**self.rows[update_id], **data}
        self.rows[update_id] = row
        return row

    def update_initiative_rag(self, initiative_id: str, rag_status: str) -> None:
        self.rag_updates.append((initiative_id, rag_status))


def test_submitted_status_updates_sync_initiative_headline_rag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        status_update_module,
        "StatusUpdateRepository",
        _FakeStatusUpdateRepository,
    )
    service = StatusUpdateService(
        object(),  # type: ignore[arg-type]
        UUID("11111111-1111-1111-1111-111111111111"),
        UUID("22222222-2222-2222-2222-222222222222"),
    )
    repo = _FakeStatusUpdateRepository.instance
    assert repo is not None

    service.create_update(
        "initiative-1",
        StatusUpdateCreate(
            rag_status="red",
            summary="Submitted directly.",
            is_draft=False,
        ),
    )
    assert repo.rag_updates == [("initiative-1", "red")]

    draft = service.create_update(
        "initiative-1",
        StatusUpdateCreate(
            rag_status="amber",
            summary="Draft update.",
            is_draft=True,
        ),
    )
    assert repo.rag_updates == [("initiative-1", "red")]

    service.submit_update(draft.id)
    assert repo.rag_updates == [("initiative-1", "red"), ("initiative-1", "amber")]
