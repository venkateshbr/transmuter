from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class SearchRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._client = client
        self._tenant_id = str(tenant_id)

    def list_initiative_search_rows(self, owner_user_id: str | None = None) -> list[dict[str, Any]]:
        query = (
            self._client.table("initiatives")
            .select(
                "id, name, initiative_code, summary, rag_status, stage, "
                "owner_id, group_owner_id, workstreams(name)"
            )
            .eq("tenant_id", self._tenant_id)
            .is_("archived_at", "null")
            .order("initiative_code")
            .limit(1000)
        )
        if owner_user_id:
            query = query.or_(f"owner_id.eq.{owner_user_id},group_owner_id.eq.{owner_user_id}")
        result = query.execute()
        return result.data or []
