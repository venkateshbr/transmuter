"""Initiative router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.auth import AnyRole, CurrentUser, RequireAdmin, get_current_user
from app.core.database import get_supabase_admin
from app.domain.initiatives import (
    InitiativeCreate,
    InitiativeDetail,
    InitiativeListResponse,
    InitiativeUpdate,
)
from app.services.initiative import InitiativeService

router = APIRouter(prefix="/initiatives", tags=["initiatives"])


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> InitiativeService:
    return InitiativeService(get_supabase_admin(), current_user.tenant_id)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=InitiativeListResponse)
async def list_initiatives(
    svc: Annotated[InitiativeService, Depends(_svc)],
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
    stage: str | None = Query(None),
    priority: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("initiative_code"),
    sort_desc: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> InitiativeListResponse:
    return svc.list_initiatives(
        workstream_id=workstream_id,
        rag_status=rag_status,
        stage=stage,
        priority=priority,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc,
        page=page,
        page_size=page_size,
    )


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export", response_class=StreamingResponse)
async def export_csv(svc: Annotated[InitiativeService, Depends(_svc)]) -> StreamingResponse:
    csv_data = svc.export_csv()
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=initiatives.csv"},
    )


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=InitiativeDetail, status_code=201)
async def create_initiative(
    body: InitiativeCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> InitiativeDetail:
    return svc.create_initiative(body, current_user.id)


# ── Get one ───────────────────────────────────────────────────────────────────

@router.get("/{initiative_id}", response_model=InitiativeDetail)
async def get_initiative(
    initiative_id: str,
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> InitiativeDetail:
    return svc.get_initiative(initiative_id)


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/{initiative_id}", response_model=InitiativeDetail)
async def update_initiative(
    initiative_id: str,
    body: InitiativeUpdate,
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> InitiativeDetail:
    return svc.update_initiative(initiative_id, body)


# ── Archive ───────────────────────────────────────────────────────────────────

@router.post("/{initiative_id}/archive", response_model=InitiativeDetail)
async def archive_initiative(
    initiative_id: str,
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> InitiativeDetail:
    return svc.archive_initiative(initiative_id)


# ── Delete (TO only) ──────────────────────────────────────────────────────────

@router.delete("/{initiative_id}", status_code=204, dependencies=[RequireAdmin])
async def delete_initiative(
    initiative_id: str,
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> None:
    svc.delete_initiative(initiative_id)
