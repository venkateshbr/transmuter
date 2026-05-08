from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user
from app.services.ai import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    query: str


class ChatCitation(BaseModel):
    label: str
    source_type: str


class ChatResponse(BaseModel):
    response: str
    sources: list[ChatCitation] = Field(default_factory=list)


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> AIService:
    return AIService(current_user.tenant_id)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, svc: Annotated[AIService, Depends(_svc)]) -> ChatResponse:
    """Chat with Transmuter AI about the portfolio."""
    data = await svc.chat(body.query)
    return ChatResponse(**data)
