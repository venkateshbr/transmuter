from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.services import ai as ai_module
from app.services.ai import AIService

TENANT_ID = str(uuid4())
USER_ID = str(uuid4())
INITIATIVE_ID = str(uuid4())


@dataclass
class FakeResult:
    data: object


class FakeQuery:
    def __init__(self, client: FakeSupabaseClient, table: str) -> None:
        self.client = client
        self.table = table
        self.filters: list[tuple[str, object]] = []
        self.insert_payload: dict | None = None
        self.update_payload: dict | None = None
        self.expect_maybe_single = False
        self.expect_single = False

    def select(self, *_args: object, **_kwargs: object) -> FakeQuery:
        return self

    def eq(self, key: str, value: object) -> FakeQuery:
        self.filters.append((key, value))
        return self

    def limit(self, *_args: object, **_kwargs: object) -> FakeQuery:
        return self

    def single(self) -> FakeQuery:
        self.expect_single = True
        return self

    def maybe_single(self) -> FakeQuery:
        self.expect_maybe_single = True
        return self

    def insert(self, payload: dict) -> FakeQuery:
        self.insert_payload = payload
        return self

    def update(self, payload: dict) -> FakeQuery:
        self.update_payload = payload
        return self

    def execute(self) -> FakeResult:
        if self.table in self.client.fail_tables:
            raise RuntimeError(f"{self.table} unavailable")
        rows = self.client.tables.setdefault(self.table, [])
        if self.insert_payload is not None:
            rows.append(dict(self.insert_payload))
            return FakeResult(dict(self.insert_payload))
        if self.update_payload is not None:
            matched = self._matching(rows)
            for row in matched:
                row.update(self.update_payload)
            return FakeResult(matched)
        matched = [dict(row) for row in self._matching(rows)]
        if self.expect_single:
            if not matched:
                raise RuntimeError(f"Missing row in {self.table}")
            return FakeResult(matched[0])
        if self.expect_maybe_single:
            return FakeResult(matched[0] if matched else None)
        return FakeResult(matched)

    def _matching(self, rows: list[dict]) -> list[dict]:
        matched = rows
        for key, value in self.filters:
            matched = [row for row in matched if row.get(key) == value]
        return matched


class FakeSupabaseClient:
    def __init__(self, fail_tables: set[str] | None = None) -> None:
        self.tables = _seed_tables()
        self.fail_tables = fail_tables or set()

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)


def _current_user(role: str = "transformation_office") -> CurrentUser:
    return CurrentUser(id=UUID(USER_ID), tenant_id=UUID(TENANT_ID), role=role)


def _service(role: str = "transformation_office") -> tuple[AIService, FakeSupabaseClient]:
    client = FakeSupabaseClient()
    return AIService(client, _current_user(role), client), client


def _seed_tables() -> dict[str, list[dict]]:
    return {
        "initiatives": [
            {
                "id": INITIATIVE_ID,
                "tenant_id": TENANT_ID,
                "initiative_code": "ALQ-001",
                "name": "Account Lifecycle Quality",
                "owner_id": USER_ID,
                "group_owner_id": None,
                "workstream_id": None,
                "type": "cost_reduction",
                "impact_type": "recurring",
                "country": "US",
                "tag": "Automation",
                "priority": "high",
                "rag_status": "amber",
                "stage": "in_progress",
                "summary": "Improve onboarding quality.",
                "value_logic": None,
                "dependencies_text": None,
                "planned_start": "2026-01-01",
                "planned_end": "2026-12-31",
                "actual_end": None,
                "pressure_score": "42.0000",
                "benefit_confidence": "70.0000",
                "realization_status": "forecasted",
                "archived_at": None,
            }
        ],
        "users": [
            {
                "id": USER_ID,
                "tenant_id": TENANT_ID,
                "display_name": "Avery Stone",
                "role": "transformation_office",
                "title": "Director",
                "department": "PMO",
                "market": "US",
                "status": "active",
            }
        ],
        "milestones": [
            {
                "id": str(uuid4()),
                "tenant_id": TENANT_ID,
                "initiative_id": INITIATIVE_ID,
                "name": "Benefits checkpoint",
                "description": None,
                "owner_id": USER_ID,
                "priority": "high",
                "status": "not_started",
                "planned_start": None,
                "planned_end": "2026-06-30",
                "actual_end": None,
                "pressure_score": "10.0000",
            }
        ],
        "risks": [
            {
                "id": str(uuid4()),
                "tenant_id": TENANT_ID,
                "initiative_id": INITIATIVE_ID,
                "description": "Adoption resistance",
                "type": "people",
                "impact": "high",
                "likelihood": "medium",
                "rating": "high",
                "status": "open",
                "owner_id": USER_ID,
                "mitigation": "Weekly enablement",
                "escalated": True,
                "created_at": "2026-01-15T00:00:00Z",
            }
        ],
        "kpis": [],
        "kpi_entries": [],
        "financial_entries": [
            {
                "id": str(uuid4()),
                "tenant_id": TENANT_ID,
                "initiative_id": INITIATIVE_ID,
                "year": 2026,
                "quarter": 2,
                "gm_uplift_base": "1000.0000",
                "gm_uplift_actual": "200.0000",
            }
        ],
        "financial_cost_lines": [
            {
                "id": str(uuid4()),
                "tenant_id": TENANT_ID,
                "initiative_id": INITIATIVE_ID,
                "year": 2026,
                "quarter": 2,
                "amount_plan": "100.0000",
                "is_recurring": True,
            }
        ],
        "status_updates": [],
        "meetings": [],
        "action_items": [],
        "milestone_dependencies": [],
        "initiative_dependencies": [],
        "ai_copilot_actions": [],
    }


def test_copilot_tools_catalog_documents_curated_registry() -> None:
    service, _client = _service()

    tools = service.tools()
    names = {tool["name"] for tool in tools}

    assert {"portfolio_snapshot", "financial_rollup", "draft_initiative"} <= names
    assert all(tool["operation"] in {"read", "write"} for tool in tools)
    assert any(tool["permission"] == "transformation_office" for tool in tools)


@pytest.mark.asyncio
async def test_copilot_answers_portfolio_financial_milestone_and_risk_queries() -> None:
    service, _client = _service()

    for query, expected_source in (
        ("Summarize the portfolio with citations", "initiatives"),
        ("What is the portfolio net value?", "financials"),
        ("What milestones are due this month?", "milestones"),
        ("Show high risks", "risks"),
    ):
        data = await service.chat(query)
        assert data["response"]
        assert data["confidence"] > 0
        assert data["plan"]["operation"] == "read"
        assert any(source["source_type"] == expected_source for source in data["sources"])
        assert all(source.get("claim") for source in data["sources"])
        assert any(trace["status"] == "completed" for trace in data["tool_trace"])


@pytest.mark.asyncio
async def test_copilot_drafts_and_confirms_initiative_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, client = _service()
    name = f"Copilot Initiative {uuid4().hex[:8]}"

    class FakeInitiativeService:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def create_initiative(self, data: object, _created_by: object) -> dict:
            return {"id": str(uuid4()), "name": data.name}

    monkeypatch.setattr(ai_module, "InitiativeService", FakeInitiativeService)

    draft = await service.chat(f"Create a new initiative called {name}")
    action = draft["proposed_actions"][0]
    assert action["action_type"] == "create_initiative"
    assert action["status"] == "draft"
    assert action["payload_hash"]
    assert action["plan"]["operation"] == "draft_confirm"
    assert all(item["passed"] for item in action["guardrails"])
    assert client.tables["ai_copilot_actions"][0]["payload"]["name"] == name

    confirmed = service.confirm_action(action["id"])

    assert confirmed["status"] == "confirmed"
    assert confirmed["result"]["name"] == name
    assert client.tables["ai_copilot_actions"][0]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_copilot_drafts_milestone_against_context_initiative() -> None:
    service, _client = _service()

    draft = await service.chat(
        "Add milestone called Benefits checkpoint by 2026-06-30",
        context={"initiative_id": INITIATIVE_ID},
    )
    action = draft["proposed_actions"][0]

    assert action["action_type"] == "create_milestone"
    assert action["payload"]["initiative_id"] == INITIATIVE_ID
    assert action["payload"]["data"]["planned_end"] == "2026-06-30"
    assert action["plan"]["tools"] == ["ai_tools", "draft_milestone"]
    assert any(item["name"] == "target_initiative" for item in action["guardrails"])


@pytest.mark.asyncio
async def test_copilot_write_guardrail_requires_target_initiative() -> None:
    service, _client = _service()

    data = await service.chat("Add risk called adoption risk")

    assert data["proposed_actions"] == []
    assert data["plan"]["is_write"] is True
    assert any(trace["status"] == "rejected" for trace in data["tool_trace"])


@pytest.mark.asyncio
async def test_copilot_confirmation_rejects_tampered_payload_hash() -> None:
    service, client = _service()
    draft = await service.chat("Create a new initiative called Original Initiative")
    action = draft["proposed_actions"][0]
    client.tables["ai_copilot_actions"][0]["payload"]["name"] = "Tampered Initiative"

    with pytest.raises(HTTPException) as exc:
        service.confirm_action(action["id"])

    assert exc.value.status_code == 409
    assert client.tables["ai_copilot_actions"][0]["status"] == "failed"


@pytest.mark.asyncio
async def test_copilot_fails_closed_when_source_query_fails() -> None:
    client = FakeSupabaseClient(fail_tables={"risks"})
    service = AIService(client, _current_user(), client)

    with pytest.raises(HTTPException) as exc:
        await service.chat("Show high risks")

    assert exc.value.status_code == 503
