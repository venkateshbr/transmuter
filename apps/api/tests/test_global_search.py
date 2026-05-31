from __future__ import annotations

from uuid import UUID

from app.core.auth import CurrentUser
from app.services.search import SearchService

TENANT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-2222-2222-222222222222"


class FakeSearchRepository:
    def __init__(self) -> None:
        self.owner_user_id: str | None = None

    def list_initiative_search_rows(
        self, owner_user_id: str | None = None
    ) -> list[dict[str, object]]:
        self.owner_user_id = owner_user_id
        return [
            {
                "id": "init-1",
                "name": "AP Automation",
                "initiative_code": "AP-001",
                "summary": "Reduce invoice cycle time",
                "rag_status": "green",
                "stage": "in_progress",
                "workstreams": {"name": "Operations"},
            },
            {
                "id": "init-2",
                "name": "Commercial Lift",
                "initiative_code": "COM-001",
                "summary": "Pricing analytics rollout",
                "rag_status": "amber",
                "stage": "scoping",
                "workstreams": {"name": "Growth"},
            },
            {
                "id": "init-3",
                "name": "Working Capital",
                "initiative_code": "FIN-001",
                "summary": "Supplier terms reset",
                "rag_status": "red",
                "stage": "in_progress",
                "workstreams": None,
            },
        ]


def _current_user(role: str = "transformation_office") -> CurrentUser:
    return CurrentUser(id=UUID(USER_ID), tenant_id=UUID(TENANT_ID), role=role)


def test_global_search_matches_code_name_and_summary_case_insensitive() -> None:
    service = SearchService(FakeSearchRepository(), _current_user())

    by_code = service.search("ap-")
    by_name = service.search("commercial")
    by_summary = service.search("supplier")

    assert by_code.total == 1
    assert by_code.items[0].initiative_code == "AP-001"
    assert by_name.items[0].name == "Commercial Lift"
    assert by_summary.items[0].rag_status == "red"


def test_global_search_returns_contract_fields_and_honors_limit() -> None:
    service = SearchService(FakeSearchRepository(), _current_user())

    response = service.search("i", limit=1)

    assert response.total == 0

    response = service.search("in", limit=1)

    assert response.total > 1
    assert len(response.items) == 1
    assert response.items[0].workstream == "Operations"


def test_global_search_scopes_initiative_owner_results() -> None:
    repo = FakeSearchRepository()
    service = SearchService(repo, _current_user("initiative_owner"))

    service.search("ap")

    assert repo.owner_user_id == USER_ID
