"""Initiative router — thin parse + respond layer."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.core.auth import AnyRole, CurrentUser, RequireAdmin, get_current_user
from app.core.database import get_supabase_admin
from app.domain.initiatives import (
    InitiativeCreate,
    InitiativeDetail,
    InitiativeListResponse,
    InitiativeUpdate,
)
from app.domain.initiative_intake import (
    InitiativeIntakeCreate,
    InitiativeIntakeRequest,
    InitiativeIntakeSuggestions,
    InitiativeWorkbookPreview,
)
from app.agents.initiative_intake_agent import generate_intake_suggestions
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


@router.get("/template")
async def export_template(svc: Annotated[InitiativeService, Depends(_svc)]) -> Response:
    workbook = svc.export_template()
    return Response(
        content=workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="transmuter-initiative-template.xlsx"'},
    )


@router.post("/import/preview", response_model=InitiativeWorkbookPreview)
async def preview_import(
    svc: Annotated[InitiativeService, Depends(_svc)],
    file: UploadFile = File(...),
) -> InitiativeWorkbookPreview:
    return svc.preview_import(await file.read())


@router.post("/import", response_model=InitiativeDetail, status_code=201)
async def import_initiative(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[InitiativeService, Depends(_svc)],
    file: UploadFile = File(...),
) -> InitiativeDetail:
    return svc.import_template(await file.read(), current_user.id)


@router.post("/intake/suggestions", response_model=InitiativeIntakeSuggestions)
async def create_intake_suggestions(
    body: InitiativeIntakeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> InitiativeIntakeSuggestions:
    return await generate_intake_suggestions(body)


@router.post("/intake/create", response_model=InitiativeDetail, status_code=201)
async def create_initiative_from_intake(
    body: InitiativeIntakeCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> InitiativeDetail:
    return svc.create_from_intake(body, current_user.id)


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


@router.get("/{initiative_id}/export")
async def export_initiative_workbook(
    initiative_id: str,
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> Response:
    workbook = svc.export_initiative_workbook(initiative_id)
    return Response(
        content=workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="initiative-{initiative_id}-transmuter.xlsx"'
        },
    )


@router.post("/{initiative_id}/import", response_model=InitiativeDetail)
async def import_into_existing_initiative(
    initiative_id: str,
    svc: Annotated[InitiativeService, Depends(_svc)],
    file: UploadFile = File(...),
) -> InitiativeDetail:
    return svc.import_into_existing_initiative(initiative_id, await file.read())


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


# ── Summary & Lessons Learned ────────────────────────────────────────────────
@router.get("/{initiative_id}/summary")
async def get_initiative_summary(
    initiative_id: str,
    svc: Annotated[InitiativeService, Depends(_svc)],
):
    """Fetch persistent closure summary and value-realisation fields."""
    init = svc.get_initiative(initiative_id)
    fin = init.financial_summary
    planned_value = Decimal(fin.net_value_plan) if fin else Decimal("0")
    realized_value = Decimal(fin.net_value_actual) if fin and fin.net_value_actual else Decimal("0")
    return {
        "initiative_id": initiative_id,
        "draft_status": "draft",
        "planned_value": str(planned_value),
        "realized_value": str(realized_value),
        "final_summary": init.summary,
        "lessons_learned": init.lessons_learned,
        "stage": init.stage,
        "completion_date": init.actual_end or init.planned_end,
    }

@router.patch("/{initiative_id}/summary")
async def update_initiative_summary(
    initiative_id: str,
    body: dict,
    svc: Annotated[InitiativeService, Depends(_svc)],
):
    """Persist closure narrative fields on the initiative record."""
    update_data = {}
    if "final_summary" in body:
        update_data["summary"] = body["final_summary"]
    elif "executive_summary" in body:
        update_data["summary"] = body["executive_summary"]
    if "lessons_learned" in body:
        update_data["lessons_learned"] = body["lessons_learned"]
    
    if update_data:
        svc.update_initiative(initiative_id, InitiativeUpdate(**update_data))
    return await get_initiative_summary(initiative_id, svc)

# ── Delete (TO only) ──────────────────────────────────────────────────────────

@router.delete("/{initiative_id}", status_code=204, dependencies=[RequireAdmin])
async def delete_initiative(
    initiative_id: str,
    svc: Annotated[InitiativeService, Depends(_svc)],
) -> None:
    svc.delete_initiative(initiative_id)
