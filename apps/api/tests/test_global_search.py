from __future__ import annotations

from app.services.search import SearchService


class FakeSearchRepository:
    def list_initiative_search_rows(self) -> list[dict]:
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


def test_global_search_matches_code_name_and_summary_case_insensitive() -> None:
    service = SearchService(FakeSearchRepository())  # type: ignore[arg-type]

    by_code = service.search("ap-")
    by_name = service.search("commercial")
    by_summary = service.search("supplier")

    assert by_code.total == 1
    assert by_code.items[0].initiative_code == "AP-001"
    assert by_name.items[0].name == "Commercial Lift"
    assert by_summary.items[0].rag_status == "red"


def test_global_search_returns_contract_fields_and_honors_limit() -> None:
    service = SearchService(FakeSearchRepository())  # type: ignore[arg-type]

    response = service.search("i", limit=1)

    assert response.total == 0

    response = service.search("in", limit=1)

    assert response.total > 1
    assert len(response.items) == 1
    assert response.items[0].workstream == "Operations"
