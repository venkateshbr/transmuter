from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.services import ai as ai_module
from app.services import portfolio_rag as rag_module
from app.services.ai import _mask_pii
from app.services.ai import AIService
from app.services.portfolio_rag import PortfolioRAGService

TENANT_ID = uuid4()
OTHER_TENANT_ID = uuid4()


class FakePortfolioRAGRepository:
    saved: list[dict] = []

    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id

    def list_source_rows(self) -> dict[str, list[dict]]:
        return {
            "initiatives": [
                {
                    "id": "init-1",
                    "initiative_code": "AP-001",
                    "name": "AP automation",
                    "rag_status": "amber",
                    "stage": "in_progress",
                    "summary": "Invoice cycle time reduction",
                    "value_logic": "Reduce manual effort",
                }
            ],
            "milestones": [
                {
                    "id": "ms-1",
                    "initiative_id": "init-1",
                    "name": "ERP integration",
                    "status": "at_risk",
                    "planned_end": "2026-05-22",
                }
            ],
            "kpis": [
                {
                    "id": "kpi-1",
                    "initiative_id": "init-1",
                    "name": "Cycle time reduction",
                    "category": "operational",
                }
            ],
            "risks": [
                {
                    "id": "risk-1",
                    "initiative_id": "init-1",
                    "description": "ERP dependency may slip",
                    "status": "open",
                    "rating": "high",
                    "impact": "medium",
                }
            ],
        }

    def upsert_documents(self, documents: list[dict]) -> int:
        self.saved = documents
        FakePortfolioRAGRepository.saved = documents
        return len(documents)

    def list_documents(self) -> list[dict]:
        if self.tenant_id == OTHER_TENANT_ID:
            return [
                {
                    "source_type": "initiative",
                    "source_id": "other-init",
                    "title": "Other tenant secret",
                    "content": "Should not be visible",
                    "search_text": "other tenant secret",
                    "metadata": {},
                }
            ]
        return [
            {
                "source_type": "initiative",
                "source_id": "init-1",
                "title": "AP-001 AP automation",
                "content": "AP automation amber in_progress invoice cycle time",
                "search_text": "ap-001 ap automation amber in_progress invoice cycle time",
                "metadata": {"initiative_id": "init-1"},
            },
            {
                "source_type": "risk",
                "source_id": "risk-1",
                "title": "ERP dependency may slip",
                "content": "ERP dependency may slip open high medium",
                "search_text": "erp dependency may slip open high medium",
                "metadata": {"initiative_id": "init-1"},
            },
        ]


def test_portfolio_rag_rebuild_indexes_initiatives_milestones_kpis_and_risks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rag_module, "PortfolioRAGRepository", FakePortfolioRAGRepository)

    count = PortfolioRAGService(SimpleNamespace(), TENANT_ID).rebuild_index()

    assert count == 4
    source_types = {document["source_type"] for document in FakePortfolioRAGRepository.saved}
    assert source_types == {"initiative", "milestone", "kpi", "risk"}
    risk = next(document for document in FakePortfolioRAGRepository.saved if document["source_type"] == "risk")
    assert risk["metadata"]["initiative_name"] == "AP automation"


def test_portfolio_rag_search_returns_only_repository_scoped_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rag_module, "PortfolioRAGRepository", FakePortfolioRAGRepository)

    tenant_results = PortfolioRAGService(SimpleNamespace(), TENANT_ID).search("ERP risk")
    other_results = PortfolioRAGService(SimpleNamespace(), OTHER_TENANT_ID).search("ERP risk")

    assert [result["source_id"] for result in tenant_results] == ["risk-1"]
    assert other_results == []


class FakeChatRAGService:
    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.rebuilt = False

    def search(self, query: str, limit: int = 5) -> list[dict]:
        return [
            {
                "source_type": "initiative",
                "source_id": "init-1",
                "title": "AP-001 AP automation",
                "content": "AP automation is amber",
                "search_text": "ap automation amber",
                "metadata": {},
            }
        ]

    def rebuild_index(self) -> int:
        self.rebuilt = True
        return 1

    @staticmethod
    def citations(documents: list[dict]) -> list:
        return PortfolioRAGService.citations(documents)


class FakeObservation:
    def __init__(self) -> None:
        self.input = None
        self.output = None

    def __enter__(self) -> "FakeObservation":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def update(self, output: dict) -> None:
        self.output = output


class FakeLangfuse:
    def __init__(self) -> None:
        self.observation = FakeObservation()

    def start_as_current_observation(self, **kwargs) -> FakeObservation:
        self.observation.input = kwargs["input"]
        return self.observation


@pytest.mark.asyncio
async def test_ai_chat_returns_specific_citations_and_masks_trace_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_langfuse = FakeLangfuse()
    monkeypatch.setattr(ai_module, "PortfolioRAGService", FakeChatRAGService)
    monkeypatch.setattr(ai_module, "get_supabase_admin", lambda: SimpleNamespace())
    monkeypatch.setattr(
        "app.core.observability.get_langfuse",
        lambda: fake_langfuse,
    )

    response = await AIService(TENANT_ID).chat("Summarize AP automation for vishwa@example.com")

    assert response.sources[0].source_id == "init-1"
    assert response.sources[0].source_type == "initiative"
    assert "AP-001 AP automation" in response.response
    assert fake_langfuse.observation.input["query"] == "Summarize AP automation for [email]"


def test_ai_masks_email_and_phone_before_external_observability_or_llm() -> None:
    assert _mask_pii("Email vishwa@example.com or +1 (555) 123-4567") == (
        "Email [email] or [phone]"
    )
