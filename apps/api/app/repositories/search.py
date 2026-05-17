from __future__ import annotations

from typing import Any
from uuid import UUID


class SearchRepository:
    def __init__(self, client: Any, tenant_id: UUID) -> None:
        self._client = client
        self._tenant_id = str(tenant_id)

    def list_initiative_search_rows(self) -> list[dict[str, Any]]:
        result = (
            self._client.table("initiatives")
            .select("id, name, initiative_code, summary, rag_status, stage, workstreams(name)")
            .eq("tenant_id", self._tenant_id)
            .is_("archived_at", "null")
            .order("initiative_code")
            .limit(1000)
            .execute()
        )
        return result.data or []
