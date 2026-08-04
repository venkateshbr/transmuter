from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_supabase_admin
from app.main import app
from app.services.hermes_client import extract_hermes_text
from app.services.hermes_context import (
    HermesContextError,
    create_hermes_context_ref,
    verify_hermes_context_ref,
)
from app.services.transmuter_ai_runtime import TransmuterAIRuntime

TENANT_ID = str(uuid4())
OTHER_TENANT_ID = str(uuid4())
USER_ID = str(uuid4())
TEST_SECRET = "hermes-test-secret-that-is-at-least-32-characters"
TEST_TOKEN = "hermes-private-broker-token"


@dataclass
class FakeResult:
    data: Any


class FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.filters: list[tuple[str, object]] = []
        self.single = False

    def select(self, *_args: object, **_kwargs: object) -> FakeQuery:
        return self

    def eq(self, key: str, value: object) -> FakeQuery:
        self.filters.append((key, value))
        return self

    def limit(self, *_args: object) -> FakeQuery:
        return self

    def maybe_single(self) -> FakeQuery:
        self.single = True
        return self

    def execute(self) -> FakeResult:
        rows = [dict(row) for row in self.rows]
        for key, value in self.filters:
            rows = [row for row in rows if row.get(key) == value]
        return FakeResult(rows[0] if self.single and rows else None if self.single else rows)


class FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "users": [
                {
                    "id": USER_ID,
                    "tenant_id": TENANT_ID,
                    "display_name": "Avery Stone",
                    "role": "transformation_office",
                    "status": "active",
                    "must_change_password": False,
                }
            ],
            "initiatives": [
                {
                    "id": str(uuid4()),
                    "tenant_id": TENANT_ID,
                    "initiative_code": "TRN-001",
                    "name": "Operating Model",
                    "rag_status": "amber",
                    "stage": "in_progress",
                    "priority": "high",
                }
            ],
            "milestones": [],
            "risks": [],
            "kpis": [],
            "kpi_entries": [],
            "financial_entries": [],
            "financial_cost_lines": [],
            "status_updates": [],
            "meetings": [],
            "action_items": [],
            "milestone_dependencies": [],
            "initiative_dependencies": [],
        }

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self.tables.get(name, []))


@pytest.fixture(autouse=True)
def hermes_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "hermes_context_signing_secret", TEST_SECRET)
    monkeypatch.setattr(settings, "hermes_tool_token", TEST_TOKEN)
    yield
    app.dependency_overrides.clear()


def test_context_reference_is_encrypted_scoped_and_expires() -> None:
    context_ref = create_hermes_context_ref(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        thread_id="thread-1",
        ttl_seconds=60,
        now=1_000,
    )
    assert TENANT_ID not in context_ref
    assert USER_ID not in context_ref
    context = verify_hermes_context_ref(context_ref, now=1_030)
    assert context.tenant_id == TENANT_ID
    assert context.user_id == USER_ID
    with pytest.raises(HermesContextError, match="expired"):
        verify_hermes_context_ref(context_ref, now=1_061)
    with pytest.raises(HermesContextError):
        verify_hermes_context_ref(f"{context_ref}tampered", now=1_030)


def test_extract_hermes_text_ignores_non_message_output() -> None:
    payload = {
        "output": [
            {"type": "function_call", "name": "secret_tool"},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Portfolio is stable."}],
            },
        ]
    }
    assert extract_hermes_text(payload) == "Portfolio is stable."


def test_private_broker_enforces_token_context_allowlist_and_scope() -> None:
    fake = FakeSupabase()
    app.dependency_overrides[get_supabase_admin] = lambda: fake
    client = TestClient(app)
    context_ref = create_hermes_context_ref(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        thread_id="thread-1",
    )
    payload = {
        "context_ref": context_ref,
        "tool_name": "transmuter.portfolio.overview",
        "arguments": {},
    }

    assert client.post("/ai-tools/execute", json=payload).status_code == 401
    invalid_context = client.post(
        "/ai-tools/execute",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={**payload, "context_ref": "ctx_invalid"},
    )
    assert invalid_context.status_code == 400
    unknown_tool = client.post(
        "/ai-tools/execute",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={**payload, "tool_name": "transmuter.database.raw_query"},
    )
    assert unknown_tool.status_code == 404
    injected_scope = client.post(
        "/ai-tools/execute",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={**payload, "arguments": {"tenant_id": OTHER_TENANT_ID}},
    )
    assert injected_scope.status_code == 422

    response = client.post(
        "/ai-tools/execute",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["result"]["initiative_count"] == 1
    assert "Avery Stone" not in response.text
    assert USER_ID not in response.text


def test_private_broker_rechecks_canonical_tenant_membership() -> None:
    app.dependency_overrides[get_supabase_admin] = lambda: FakeSupabase()
    client = TestClient(app)
    wrong_tenant_context = create_hermes_context_ref(
        tenant_id=OTHER_TENANT_ID,
        user_id=USER_ID,
        thread_id="thread-1",
    )
    response = client.post(
        "/ai-tools/execute",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        json={
            "context_ref": wrong_tenant_context,
            "tool_name": "transmuter.portfolio.overview",
            "arguments": {},
        },
    )
    assert response.status_code == 403


class FakeBasicService:
    tenant_id = TENANT_ID
    user_id = USER_ID

    def __init__(self, *, write: bool = False) -> None:
        self.write = write
        self.calls = 0

    def is_write_request(self, _query: str) -> bool:
        return self.write

    def mask_external_prompt(self, query: str) -> str:
        return query.replace("Avery Stone", "[User 1]")

    async def chat(self, *_args: object, **_kwargs: object) -> dict[str, Any]:
        self.calls += 1
        return {
            "response": "Built-in response",
            "sources": [],
            "tool_trace": [],
            "confidence": 1.0,
            "proposed_actions": [],
            "plan": None,
        }


class FakeHermesClient:
    def __init__(self, *, fail: bool = False, text: str = "Hermes response") -> None:
        self.fail = fail
        self.text = text
        self.input_text = ""
        self.conversation = ""
        self.instructions = ""

    async def create_response(self, **kwargs: Any) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("upstream unavailable")
        self.input_text = kwargs["input_text"]
        self.conversation = kwargs["conversation"]
        self.instructions = kwargs["instructions"]
        return {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": self.text}],
                }
            ]
        }


@pytest.mark.asyncio
async def test_runtime_uses_hermes_for_reads_and_masks_known_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "transmuter_ai_runtime", "hermes_agent")
    basic = FakeBasicService()
    hermes = FakeHermesClient()
    response = await TransmuterAIRuntime(basic, hermes).chat(
        "Show Avery Stone portfolio",
        "thread-1",
    )
    assert response["response"] == "Hermes response"
    assert hermes.input_text == "Show [User 1] portfolio"
    assert TENANT_ID not in hermes.conversation
    assert USER_ID not in hermes.conversation
    assert "ctx_" in hermes.instructions
    assert basic.calls == 0


@pytest.mark.asyncio
async def test_runtime_keeps_writes_on_basic_and_falls_back_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "transmuter_ai_runtime", "hermes_agent")
    write_basic = FakeBasicService(write=True)
    hermes = FakeHermesClient()
    write_response = await TransmuterAIRuntime(write_basic, hermes).chat("Create an initiative")
    assert write_response["response"] == "Built-in response"
    assert write_basic.calls == 1

    read_basic = FakeBasicService()
    failing_hermes = FakeHermesClient(fail=True)
    fallback_response = await TransmuterAIRuntime(read_basic, failing_hermes).chat(
        "Portfolio status"
    )
    assert fallback_response["response"] == "Built-in response"
    assert read_basic.calls == 1

    monkeypatch.setattr(settings, "hermes_fallback_to_basic", False)
    with pytest.raises(HTTPException) as exc_info:
        await TransmuterAIRuntime(FakeBasicService(), failing_hermes).chat("Portfolio status")
    assert exc_info.value.status_code == 503
