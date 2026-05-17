"""Portfolio RAG document repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from supabase import Client


class PortfolioRAGRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list_source_rows(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "initiatives": self._c.table("initiatives")
            .select("id, initiative_code, name, rag_status, stage, summary, value_logic")
            .eq("tenant_id", self._tid)
            .is_("archived_at", "null")
            .execute()
            .data
            or [],
            "milestones": self._c.table("milestones")
            .select("id, initiative_id, name, status, planned_end")
            .eq("tenant_id", self._tid)
            .execute()
            .data
            or [],
            "kpis": self._c.table("kpis")
            .select("id, initiative_id, name, category")
            .eq("tenant_id", self._tid)
            .execute()
            .data
            or [],
            "risks": self._c.table("risks")
            .select("id, initiative_id, description, status, rating, impact")
            .eq("tenant_id", self._tid)
            .execute()
            .data
            or [],
        }

    def upsert_documents(self, documents: list[dict[str, Any]]) -> int:
        if not documents:
            return 0
        now = datetime.now(UTC).isoformat()
        payload = [
            {
                "tenant_id": self._tid,
                "updated_at": now,
                **document,
            }
            for document in documents
        ]
        self._c.table("portfolio_rag_documents").upsert(
            payload,
            on_conflict="tenant_id,source_type,source_id",
        ).execute()
        return len(payload)

    def list_documents(self) -> list[dict[str, Any]]:
        result = (
            self._c.table("portfolio_rag_documents")
            .select("source_type, source_id, title, content, search_text, metadata")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []
