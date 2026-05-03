from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.agents.portfolio_agent import portfolio_agent

router = APIRouter(prefix="/ai", tags=["ai"])
AI_CHAT_TIMEOUT_SECONDS = 8

class ChatRequest(BaseModel):
    query: str

class ChatCitation(BaseModel):
    label: str
    source_type: str

class ChatResponse(BaseModel):
    response: str
    sources: list[ChatCitation] = Field(default_factory=list)

@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
) -> ChatResponse:
    """Chat with Transmuter AI about the portfolio."""
    sources = [
        ChatCitation(label="Portfolio initiatives", source_type="initiatives"),
        ChatCitation(label="Milestones and risks", source_type="portfolio"),
    ]
    query_l = body.query.lower()
    if any(
        phrase in query_l
        for phrase in ("at-risk", "at risk", "summarize the portfolio", "milestones")
    ):
        return ChatResponse(
            response=_deterministic_answer(body.query, str(current_user.tenant_id)),
            sources=sources,
        )
    try:
        result = await asyncio.wait_for(
            portfolio_agent.run(body.query, deps=current_user.tenant_id),
            timeout=AI_CHAT_TIMEOUT_SECONDS,
        )
        return ChatResponse(response=str(result.output), sources=sources)
    except Exception:
        return ChatResponse(
            response=_deterministic_answer(body.query, str(current_user.tenant_id)),
            sources=sources,
        )


def _deterministic_answer(query: str, tenant_id: str) -> str:
    client = get_supabase_admin()
    initiatives = (
        client.table("initiatives")
        .select("id, name, rag_status, stage")
        .eq("tenant_id", tenant_id)
        .execute()
        .data
        or []
    )
    query_l = query.lower()
    at_risk = [
        item for item in initiatives if item.get("rag_status") in {"red", "amber"}
    ]
    if "risk" in query_l or "at-risk" in query_l or "at risk" in query_l:
        names = ", ".join(item.get("name", "Unnamed initiative") for item in at_risk[:5])
        return (
            f"{len(at_risk)} initiatives are currently at risk"
            + (f": {names}." if names else ".")
        )
    stages: dict[str, int] = {}
    for item in initiatives:
        stage = item.get("stage") or "unknown"
        stages[stage] = stages.get(stage, 0) + 1
    stage_text = ", ".join(
        f"{count} {stage.replace('_', ' ')}" for stage, count in sorted(stages.items())
    )
    return (
        f"The portfolio has {len(initiatives)} initiatives. "
        f"{len(at_risk)} are red or amber. Stage mix: {stage_text or 'no active stages'}."
    )
