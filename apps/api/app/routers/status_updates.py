"""Status Update router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import (
    assert_can_manage_initiative_execution,
    assert_can_manage_program_cadence,
    assert_can_view_initiative,
    assert_can_view_portfolio,
)
from app.domain.status_updates import (
    NudgeCreate,
    NudgeItem,
    NudgeResponse,
    StatusComplianceResponse,
    StatusUpdateCreate,
    StatusUpdateDraftSuggestion,
    StatusUpdateItem,
    StatusUpdateListResponse,
    StatusUpdatePatch,
)
from app.services.status_update import StatusUpdateService

router = APIRouter(tags=["status_updates"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> StatusUpdateService:
    return StatusUpdateService(client, current_user.tenant_id, current_user.id)


@router.get(
    "/status-updates/portfolio",
    response_model=list[StatusUpdateItem],
)
async def list_portfolio_updates(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> list[StatusUpdateItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_recent_updates()


@router.get(
    "/status-updates/compliance",
    response_model=StatusComplianceResponse,
)
async def get_compliance_stats(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusComplianceResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_compliance_stats()


@router.get(
    "/portfolio/status-updates/compliance",
    response_model=StatusComplianceResponse,
)
async def get_portfolio_compliance_stats(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> StatusComplianceResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_compliance_stats()


@router.post(
    "/initiatives/{initiative_id}/nudge",
    response_model=NudgeResponse,
)
async def nudge_initiative(
    initiative_id: str,
    body: NudgeCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> NudgeResponse:
    assert_can_manage_program_cadence(current_user)
    return svc.nudge_owner(initiative_id, body)


@router.get(
    "/status-updates/nudges",
    response_model=list[NudgeItem],
)
async def list_nudges(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> list[NudgeItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_nudges()


@router.post(
    "/status-updates/nudges/run-daily",
    response_model=list[NudgeResponse],
)
async def run_daily_nudges(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
) -> list[NudgeResponse]:
    assert_can_manage_program_cadence(current_user)
    return svc.nudge_non_compliant_initiatives()


@router.get(
    "/initiatives/{initiative_id}/status-updates",
    response_model=StatusUpdateListResponse,
)
async def list_status_updates(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> StatusUpdateListResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_history(initiative_id)


@router.get(
    "/initiatives/{initiative_id}/status-updates/draft",
    response_model=StatusUpdateItem | None,
)
async def get_status_update_draft(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> StatusUpdateItem | None:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_draft(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/status-updates/generate-draft",
    response_model=StatusUpdateDraftSuggestion,
)
async def generate_status_update_draft(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> StatusUpdateDraftSuggestion:
    assert_can_manage_initiative_execution(client, current_user, initiative_id)
    return await svc.generate_draft(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/status-updates",
    response_model=StatusUpdateItem,
    status_code=201,
)
async def create_status_update(
    initiative_id: str,
    body: StatusUpdateCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> StatusUpdateItem:
    assert_can_manage_initiative_execution(client, current_user, initiative_id)
    return svc.create_update(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/status-updates/{update_id}",
    response_model=StatusUpdateItem,
)
async def patch_status_update(
    initiative_id: str,
    update_id: str,
    body: StatusUpdatePatch,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> StatusUpdateItem:
    assert_can_manage_initiative_execution(client, current_user, initiative_id)
    return svc.patch_update(update_id, body)


@router.post(
    "/initiatives/{initiative_id}/status-updates/{update_id}/submit",
    response_model=StatusUpdateItem,
)
async def submit_status_update(
    initiative_id: str,
    update_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> StatusUpdateItem:
    assert_can_manage_initiative_execution(client, current_user, initiative_id)
    return svc.submit_update(update_id)


@router.delete(
    "/initiatives/{initiative_id}/status-updates/{update_id}",
    status_code=204,
)
async def delete_status_update(
    initiative_id: str,
    update_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[StatusUpdateService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> None:
    assert_can_manage_initiative_execution(client, current_user, initiative_id)
    svc.delete_update(update_id)
