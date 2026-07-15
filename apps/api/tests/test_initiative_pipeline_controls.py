from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services.initiative import InitiativeService

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def build_service() -> InitiativeService:
    service = InitiativeService(MagicMock(), TENANT_ID)
    service._repo = MagicMock()
    service._fin = MagicMock()
    return service


def test_list_rejects_unknown_sort_field_before_repository_query() -> None:
    service = build_service()

    with pytest.raises(HTTPException) as exc:
        service.list_initiatives(sort_by="tenant_id")

    assert exc.value.status_code == 422
    service._repo.list.assert_not_called()


def test_list_passes_paging_sort_and_archive_controls_to_repository() -> None:
    service = build_service()
    service._repo.list.return_value = ([], 0)

    result = service.list_initiatives(
        sort_by="updated_at",
        sort_desc=True,
        include_archived=True,
        page=3,
        page_size=25,
    )

    assert result.total == 0
    service._repo.list.assert_called_once_with(
        business_unit_ids=None,
        workstream_ids=None,
        rag_statuses=None,
        stages=None,
        priorities=None,
        tags=None,
        search=None,
        sort_by="updated_at",
        sort_desc=True,
        include_archived=True,
        page=3,
        page_size=25,
        owner_user_id=None,
    )


def test_restore_is_audited_and_returns_refreshed_initiative() -> None:
    service = build_service()
    existing = {"id": "initiative-1", "archived_at": "2026-07-15T00:00:00Z"}
    restored = MagicMock()
    service._assert_exists = MagicMock(return_value=existing)
    service.get_initiative = MagicMock(return_value=restored)
    service._audit_change = MagicMock()

    result = service.restore_initiative("initiative-1")

    assert result is restored
    service._repo.restore.assert_called_once_with("initiative-1")
    service._audit_change.assert_called_once_with(
        "restore",
        "initiative",
        "initiative-1",
        before_data=existing,
        after_data=restored.model_dump(mode="json"),
    )
