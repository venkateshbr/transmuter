"""Workstream service — workstream management."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.repositories.workstream import WorkstreamRepository


class WorkstreamService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = WorkstreamRepository(client, tenant_id)

    def list_workstreams(self) -> dict[str, Any]:
        items = self._repo.list()
        return {"items": items, "data": items, "total": len(items)}

    def create_workstream(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._repo.create(self._clean_payload(data))

    def update_workstream(self, ws_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._repo.update(ws_id, self._clean_payload(data))

    def delete_workstream(self, ws_id: str) -> None:
        self._repo.delete(ws_id)

    @staticmethod
    def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name is required"
            )
        return {"name": name}
