from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.auth import CurrentUser, get_current_user
from app.agents.portfolio_agent import portfolio_agent

router = APIRouter(prefix="/ai", tags=["ai"])

class ChatRequest(BaseModel):
    query: str

@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Chat with Transmuter AI about the portfolio."""
    # Run the agent
    result = await portfolio_agent.run(body.query, deps=current_user.tenant_id)
    return {"response": result.output}
