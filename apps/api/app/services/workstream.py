"""Workstream service — workstream management."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client

from app.repositories.workstream import WorkstreamRepository


class WorkstreamService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = WorkstreamRepository(client, tenant_id)

    def list_workstreams(self) -> dict[str, Any]:
        items = self._repo.list()
        return {"items": items, "data": items, "total": len(items)}

    def create_workstream(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._repo.create(data)

    def update_workstream(self, ws_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._repo.update(ws_id, data)

    def delete_workstream(self, ws_id: str) -> None:
        self._repo.delete(ws_id)
