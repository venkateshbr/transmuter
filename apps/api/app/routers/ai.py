from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from supabase import Client

from app.core.agent_security import validate_agent_text
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.services.ai import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return validate_agent_text(value, "query")


class ChatCitation(BaseModel):
    label: str
    source_type: str


class ChatResponse(BaseModel):
    response: str
    sources: list[ChatCitation] = Field(default_factory=list)


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> AIService:
    return AIService(client, current_user.tenant_id)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, svc: Annotated[AIService, Depends(_svc)]) -> ChatResponse:
    """Chat with Transmuter AI about the portfolio."""
    data = await svc.chat(body.query)
    return ChatResponse(**data)
