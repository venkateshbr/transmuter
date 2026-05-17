"""Tenant-scoped portfolio RAG indexing and retrieval."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from supabase import Client

from app.domain.ai import ChatCitation
from app.repositories.portfolio_rag import PortfolioRAGRepository


class PortfolioRAGService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = PortfolioRAGRepository(client, tenant_id)

    def rebuild_index(self) -> int:
        source_rows = self._repo.list_source_rows()
        documents: list[dict[str, Any]] = []
        for row in source_rows["initiatives"]:
            documents.append(
                _document(
                    source_type="initiative",
                    source_id=row["id"],
                    title=f"{row.get('initiative_code') or ''} {row['name']}".strip(),
                    content=" ".join(
                        str(value)
                        for value in (
                            row.get("name"),
                            row.get("rag_status"),
                            row.get("stage"),
                            row.get("summary"),
                            row.get("value_logic"),
                        )
                        if value
                    ),
                    metadata={"initiative_id": row["id"], "rag_status": row.get("rag_status")},
                )
            )
        initiative_names = {row["id"]: row["name"] for row in source_rows["initiatives"]}
        for row in source_rows["milestones"]:
            documents.append(
                _document(
                    source_type="milestone",
                    source_id=row["id"],
                    title=row["name"],
                    content=f"{row['name']} {row.get('status') or ''} {row.get('planned_end') or ''}",
                    metadata={
                        "initiative_id": row.get("initiative_id"),
                        "initiative_name": initiative_names.get(row.get("initiative_id")),
                    },
                )
            )
        for row in source_rows["kpis"]:
            documents.append(
                _document(
                    source_type="kpi",
                    source_id=row["id"],
                    title=row["name"],
                    content=f"{row['name']} {row.get('category') or ''}",
                    metadata={
                        "initiative_id": row.get("initiative_id"),
                        "initiative_name": initiative_names.get(row.get("initiative_id")),
                    },
                )
            )
        for row in source_rows["risks"]:
            documents.append(
                _document(
                    source_type="risk",
                    source_id=row["id"],
                    title=row["description"][:120],
                    content=" ".join(
                        str(value)
                        for value in (
                            row.get("description"),
                            row.get("status"),
                            row.get("rating"),
                            row.get("impact"),
                        )
                        if value
                    ),
                    metadata={
                        "initiative_id": row.get("initiative_id"),
                        "initiative_name": initiative_names.get(row.get("initiative_id")),
                    },
                )
            )
        return self._repo.upsert_documents(documents)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        terms = _terms(query)
        documents = self._repo.list_documents()
        scored = [
            (score, document)
            for document in documents
            if (score := _score(document.get("search_text") or "", terms)) > 0
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored[:limit]]

    @staticmethod
    def citations(documents: list[dict[str, Any]]) -> list[ChatCitation]:
        return [
            ChatCitation(
                label=document["title"],
                source_type=document["source_type"],
                source_id=document.get("source_id"),
                source_title=document["title"],
                snippet=(document.get("content") or "")[:220],
            )
            for document in documents
        ]


def _document(
    *,
    source_type: str,
    source_id: str,
    title: str,
    content: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "title": title,
        "content": content,
        "search_text": f"{title} {content}".lower(),
        "metadata": metadata,
    }


def _terms(query: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2}


def _score(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)
