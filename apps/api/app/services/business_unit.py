"""Business Unit service — business unit management."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client

from app.repositories.business_unit import BusinessUnitRepository


class BusinessUnitService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = BusinessUnitRepository(client, tenant_id)

    def list_business_units(self) -> dict[str, Any]:
        items = self._repo.list()
        return {"items": items, "data": items, "total": len(items)}

    def create_business_unit(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._repo.create(data)

    def update_business_unit(self, bu_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self._repo.update(bu_id, data)

    def delete_business_unit(self, bu_id: str) -> None:
        self._repo.delete(bu_id)
