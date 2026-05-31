from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from supabase import Client

from app.core.agent_security import validate_agent_text
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin, get_supabase_request_client
from app.services.ai import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    context: dict[str, Any] | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return validate_agent_text(value, "query")


class ChatCitation(BaseModel):
    label: str
    source_type: str
    record_id: str | None = None
    url: str | None = None
    claim: str | None = None


class ToolTrace(BaseModel):
    tool_name: str
    status: str
    summary: str
    source_type: str


class ProposedAction(BaseModel):
    id: str
    action_type: str
    title: str
    description: str
    payload: dict[str, Any]
    requires_confirmation: bool = True
    status: str = "draft"
    expires_at: str | None = None
    payload_hash: str | None = None
    plan: dict[str, Any] | None = None
    guardrails: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    sources: list[ChatCitation] = Field(default_factory=list)
    tool_trace: list[ToolTrace] = Field(default_factory=list)
    confidence: float = 0.0
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    plan: dict[str, Any] | None = None


class ToolCatalogItem(BaseModel):
    name: str
    domain: str
    description: str
    operation: str
    permission: str
    source: str
    input_schema: dict[str, Any]
    examples: list[str] = Field(default_factory=list)


class ToolCatalogResponse(BaseModel):
    items: list[ToolCatalogItem]


class ActionConfirmResponse(BaseModel):
    action_id: str
    status: str
    message: str
    result: dict[str, Any] | None = None


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
    ledger_client: Annotated[Client, Depends(get_supabase_admin)],
) -> AIService:
    return AIService(client, current_user, ledger_client)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, svc: Annotated[AIService, Depends(_svc)]) -> ChatResponse:
    """Chat with Transmuter AI about the portfolio."""
    data = await svc.chat(body.query, body.conversation_id, body.context)
    return ChatResponse(**data)


@router.get("/tools", response_model=ToolCatalogResponse)
async def tools(svc: Annotated[AIService, Depends(_svc)]) -> ToolCatalogResponse:
    """Return the curated AI tool knowledge base."""
    return ToolCatalogResponse(items=svc.tools())


@router.post("/actions/{action_id}/confirm", response_model=ActionConfirmResponse)
async def confirm_action(
    action_id: str,
    svc: Annotated[AIService, Depends(_svc)],
) -> ActionConfirmResponse:
    """Confirm and execute a previously drafted copilot action."""
    return ActionConfirmResponse(**svc.confirm_action(action_id))
