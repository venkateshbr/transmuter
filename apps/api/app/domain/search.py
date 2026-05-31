from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    id: str
    name: str
    initiative_code: str | None = None
    rag_status: str | None = None
    stage: str | None = None
    workstream: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchResult]
    total: int
