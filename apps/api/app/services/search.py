from __future__ import annotations

from typing import Any

from app.core.auth import CurrentUser
from app.core.rbac import ROLE_WORKSTREAM_LEAD, can_view_all_initiatives
from app.domain.search import SearchResponse, SearchResult
from app.repositories.search import SearchRepository


class SearchService:
    def __init__(self, repository: SearchRepository, current_user: CurrentUser) -> None:
        self._repo = repository
        self._current_user = current_user

    def search(self, query: str, limit: int = 25) -> SearchResponse:
        needle = query.strip().lower()
        if len(needle) < 2:
            return SearchResponse(items=[], categories={}, total=0)

        workstream_ids = (
            self._repo.list_user_workstream_ids(str(self._current_user.id))
            if self._current_user.role == ROLE_WORKSTREAM_LEAD
            else None
        )
        if workstream_ids == []:
            return SearchResponse(items=[], categories={}, total=0)
        owner_user_id = (
            None
            if can_view_all_initiatives(self._current_user.role) or workstream_ids is not None
            else str(self._current_user.id)
        )
        initiative_matches = [
            _initiative_result(row)
            for row in self._repo.list_initiative_search_rows(
                owner_user_id=owner_user_id,
                workstream_ids=workstream_ids,
            )
            if _matches(row, needle, ("name", "summary", "initiative_code"))
        ]
        milestone_matches = [
            _milestone_result(row)
            for row in self._repo.list_milestone_search_rows(
                owner_user_id=owner_user_id,
                workstream_ids=workstream_ids,
            )
            if _visible_related(row, owner_user_id)
            and _matches(row, needle, ("name", "description", "status", "priority"))
        ]
        risk_matches = [
            _risk_result(row)
            for row in self._repo.list_risk_search_rows(
                owner_user_id=owner_user_id,
                workstream_ids=workstream_ids,
            )
            if _visible_related(row, owner_user_id)
            and _matches(
                row, needle, ("description", "type", "impact", "likelihood", "rating", "status")
            )
        ]
        user_matches = (
            [
                _user_result(row)
                for row in self._repo.list_user_search_rows()
                if _matches(row, needle, ("display_name", "title", "department", "market", "role"))
            ]
            if can_view_all_initiatives(self._current_user.role)
            else []
        )
        matches = [*initiative_matches, *milestone_matches, *risk_matches, *user_matches]
        matches.sort(key=lambda row: _rank(row, needle))
        categories: dict[str, int] = {}
        for item in matches:
            categories[item.result_type] = categories.get(item.result_type, 0) + 1
        return SearchResponse(items=matches[:limit], categories=categories, total=len(matches))


def _matches(row: dict[str, Any], needle: str, fields: tuple[str, ...]) -> bool:
    return any(needle in str(row.get(field) or "").lower() for field in fields)


def _rank(row: SearchResult, needle: str) -> tuple[int, str, str]:
    code = str(row.initiative_code or "").lower()
    name = row.name.lower()
    if code == needle:
        score = 0
    elif code.startswith(needle):
        score = 1
    elif name.startswith(needle):
        score = 2
    else:
        score = 3
    return (score, row.result_type, code or name)


def _initiative_result(row: dict[str, Any]) -> SearchResult:
    workstream = row.get("workstreams") or {}
    if isinstance(workstream, list):
        workstream = workstream[0] if workstream else {}
    return SearchResult(
        id=row["id"],
        result_type="initiative",
        label=f"{row.get('initiative_code') or 'Initiative'} · {row['name']}",
        name=row["name"],
        description=row.get("summary"),
        url=f"/initiatives/{row['id']}",
        initiative_code=row.get("initiative_code"),
        rag_status=row.get("rag_status"),
        stage=row.get("stage"),
        workstream=workstream.get("name"),
        category="Initiatives",
    )


def _milestone_result(row: dict[str, Any]) -> SearchResult:
    initiative = _nested(row, "initiatives")
    code = initiative.get("initiative_code")
    return SearchResult(
        id=row["id"],
        result_type="milestone",
        label=f"Milestone · {row['name']}",
        name=row["name"],
        description=row.get("description") or f"{row.get('status', 'tracked')} milestone",
        url=f"/initiatives/{row['initiative_id']}/milestones",
        initiative_code=code,
        stage=row.get("status"),
        category="Milestones",
    )


def _risk_result(row: dict[str, Any]) -> SearchResult:
    initiative = _nested(row, "initiatives")
    return SearchResult(
        id=row["id"],
        result_type="risk",
        label=f"Risk · {str(row['description'])[:80]}",
        name=row["description"],
        description=f"{row.get('impact') or 'unrated'} impact · {row.get('status') or 'open'}",
        url=f"/initiatives/{row['initiative_id']}/risks",
        initiative_code=initiative.get("initiative_code"),
        rag_status=_risk_rag(row.get("rating") or row.get("impact")),
        category="Risks",
    )


def _user_result(row: dict[str, Any]) -> SearchResult:
    label = row.get("display_name") or "User"
    parts = [part for part in (row.get("title"), row.get("department"), row.get("market")) if part]
    return SearchResult(
        id=row["id"],
        result_type="user",
        label=f"User · {label}",
        name=label,
        description=" · ".join(parts) if parts else row.get("role"),
        url=f"/people?user_id={row['id']}",
        category="Users",
    )


def _visible_related(row: dict[str, Any], owner_user_id: str | None) -> bool:
    if owner_user_id is None:
        return True
    initiative = _nested(row, "initiatives")
    return owner_user_id in {
        str(row.get("owner_id") or ""),
        str(initiative.get("owner_id") or ""),
        str(initiative.get("group_owner_id") or ""),
    }


def _nested(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key) or {}
    if isinstance(value, list):
        return value[0] if value else {}
    return value if isinstance(value, dict) else {}


def _risk_rag(value: Any) -> str | None:
    risk_value = str(value or "").lower()
    if risk_value in {"critical", "high", "red"}:
        return "red"
    if risk_value in {"medium", "amber"}:
        return "amber"
    if risk_value in {"low", "green"}:
        return "green"
    return None
