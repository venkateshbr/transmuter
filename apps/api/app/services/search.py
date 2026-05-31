from __future__ import annotations

from typing import Any

from app.core.auth import CurrentUser
from app.core.rbac import can_view_all_initiatives
from app.domain.search import SearchResponse, SearchResult
from app.repositories.search import SearchRepository


class SearchService:
    def __init__(self, repository: SearchRepository, current_user: CurrentUser) -> None:
        self._repo = repository
        self._current_user = current_user

    def search(self, query: str, limit: int = 25) -> SearchResponse:
        needle = query.strip().lower()
        if len(needle) < 2:
            return SearchResponse(items=[], total=0)

        owner_user_id = (
            None
            if can_view_all_initiatives(self._current_user.role)
            else str(self._current_user.id)
        )
        matches = [
            row
            for row in self._repo.list_initiative_search_rows(owner_user_id=owner_user_id)
            if _matches(row, needle)
        ]
        matches.sort(key=lambda row: _rank(row, needle))
        items = [_result(row) for row in matches[:limit]]
        return SearchResponse(items=items, total=len(matches))


def _matches(row: dict[str, Any], needle: str) -> bool:
    return any(
        needle in str(row.get(field) or "").lower()
        for field in ("name", "summary", "initiative_code")
    )


def _rank(row: dict[str, Any], needle: str) -> tuple[int, str]:
    code = str(row.get("initiative_code") or "").lower()
    name = str(row.get("name") or "").lower()
    if code == needle:
        score = 0
    elif code.startswith(needle):
        score = 1
    elif name.startswith(needle):
        score = 2
    else:
        score = 3
    return (score, code or name)


def _result(row: dict[str, Any]) -> SearchResult:
    workstream = row.get("workstreams") or {}
    if isinstance(workstream, list):
        workstream = workstream[0] if workstream else {}
    return SearchResult(
        id=row["id"],
        name=row["name"],
        initiative_code=row.get("initiative_code"),
        rag_status=row.get("rag_status"),
        stage=row.get("stage"),
        workstream=workstream.get("name"),
    )
