from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: str
    result_type: str = "initiative"
    label: str
    name: str
    description: str | None = None
    url: str
    initiative_code: str | None = None
    rag_status: str | None = None
    stage: str | None = None
    workstream: str | None = None
    category: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchResult]
    categories: dict[str, int] = Field(default_factory=dict)
    total: int
