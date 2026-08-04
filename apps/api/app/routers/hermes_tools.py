"""Private bearer-protected tool broker used only by the Hermes MCP bridge."""

from __future__ import annotations

import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from supabase import Client

from app.core.config import settings
from app.core.database import get_supabase_admin
from app.services.hermes_context import HermesContextError, verify_hermes_context_ref
from app.services.hermes_tool_broker import HermesToolBrokerService

router = APIRouter(prefix="/ai-tools", tags=["internal-ai-tools"])
_bearer = HTTPBearer(auto_error=False)


class HermesToolExecuteRequest(BaseModel):
    context_ref: str = Field(min_length=1, max_length=2048)
    tool_name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


class HermesToolExecuteResponse(BaseModel):
    tool_name: str
    result: Any


def require_hermes_tool_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    expected = settings.hermes_tool_token.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hermes tool broker is not configured",
        )
    if credentials is None or not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Hermes tool broker token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/execute", response_model=HermesToolExecuteResponse)
async def execute_hermes_tool(
    payload: HermesToolExecuteRequest,
    _auth: Annotated[None, Depends(require_hermes_tool_auth)],
    client: Annotated[Client, Depends(get_supabase_admin)],
) -> HermesToolExecuteResponse:
    try:
        context = verify_hermes_context_ref(payload.context_ref)
    except HermesContextError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Hermes tool context",
        ) from exc
    result = HermesToolBrokerService(client).execute(
        context=context,
        tool_name=payload.tool_name,
        arguments=payload.arguments,
    )
    return HermesToolExecuteResponse(tool_name=payload.tool_name, result=result)
