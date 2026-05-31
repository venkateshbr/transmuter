from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.domain.search import SearchResponse
from app.repositories.search import SearchRepository
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> SearchService:
    return SearchService(SearchRepository(client, current_user.tenant_id), current_user)


@router.get("", response_model=SearchResponse)
async def search(
    svc: Annotated[SearchService, Depends(_svc)],
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(25, ge=1, le=50),
) -> SearchResponse:
    return svc.search(q, limit=limit)
