"""Status Update router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user, require_role
from app.core.database import get_supabase_admin
from app.domain.status_updates import (
    NudgeCreate,
    NudgeItem,
    NudgeResponse,
    StatusComplianceResponse,
    StatusUpdateDraftSuggestion,
    StatusUpdateCreate,
    StatusUpdateItem,
    StatusUpdateListResponse,
    StatusUpdatePatch,
)
from app.services.status_update import StatusUpdateService

router = APIRouter(tags=["status_updates"])


@router.get(
    "/status-updates/portfolio",
    response_model=list[StatusUpdateItem],
)
async def list_portfolio_updates(
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> list[StatusUpdateItem]:
    return svc.list_recent_updates()


@router.get(
    "/status-updates/compliance",
    response_model=StatusComplianceResponse,
)
async def get_compliance_stats(
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusComplianceResponse:
    return svc.get_compliance_stats()


@router.get(
    "/portfolio/status-updates/compliance",
    response_model=StatusComplianceResponse,
)
async def get_portfolio_compliance_stats(
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusComplianceResponse:
    return svc.get_compliance_stats()


@router.post(
    "/initiatives/{initiative_id}/nudge",
    response_model=NudgeResponse,
)
async def nudge_initiative(
    initiative_id: str,
    body: NudgeCreate,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> NudgeResponse:
    return svc.nudge_owner(initiative_id, body)


@router.get(
    "/status-updates/nudges",
    response_model=list[NudgeItem],
)
async def list_nudges(
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> list[NudgeItem]:
    return svc.list_nudges()


@router.post(
    "/status-updates/nudges/run-daily",
    response_model=list[NudgeResponse],
)
async def run_daily_nudges(
    _current_user: Annotated[
        CurrentUser, Depends(require_role("transformation_office"))
    ],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> list[NudgeResponse]:
    return svc.nudge_non_compliant_initiatives()


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StatusUpdateService:
    return StatusUpdateService(
        get_supabase_admin(), current_user.tenant_id, current_user.id
    )


@router.get(
    "/initiatives/{initiative_id}/status-updates",
    response_model=StatusUpdateListResponse,
)
async def list_status_updates(
    initiative_id: str,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusUpdateListResponse:
    return svc.list_history(initiative_id)


@router.get(
    "/initiatives/{initiative_id}/status-updates/draft",
    response_model=StatusUpdateItem | None,
)
async def get_status_update_draft(
    initiative_id: str,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusUpdateItem | None:
    return svc.get_draft(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/status-updates/generate-draft",
    response_model=StatusUpdateDraftSuggestion,
)
async def generate_status_update_draft(
    initiative_id: str,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusUpdateDraftSuggestion:
    return svc.generate_draft(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/status-updates",
    response_model=StatusUpdateItem,
    status_code=201,
)
async def create_status_update(
    initiative_id: str,
    body: StatusUpdateCreate,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusUpdateItem:
    return svc.create_update(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/status-updates/{update_id}",
    response_model=StatusUpdateItem,
)
async def patch_status_update(
    initiative_id: str,
    update_id: str,
    body: StatusUpdatePatch,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusUpdateItem:
    return svc.patch_update(update_id, body)


@router.post(
    "/initiatives/{initiative_id}/status-updates/{update_id}/submit",
    response_model=StatusUpdateItem,
)
async def submit_status_update(
    initiative_id: str,
    update_id: str,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusUpdateItem:
    return svc.submit_update(update_id)


@router.delete(
    "/initiatives/{initiative_id}/status-updates/{update_id}",
    status_code=204,
)
async def delete_status_update(
    update_id: str,
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> None:
    svc.delete_update(update_id)
