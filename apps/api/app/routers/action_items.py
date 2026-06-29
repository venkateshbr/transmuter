from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import assert_can_manage_program_cadence, assert_can_view_portfolio
from app.domain.meetings import ActionItemListResponse, ActionItemUpdate
from app.services.meeting import MeetingService

router = APIRouter(tags=["action-items"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> MeetingService:
    return MeetingService(client, current_user.tenant_id)


@router.get("/action-items", response_model=ActionItemListResponse)
async def list_action_items(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> ActionItemListResponse:
    """List all action items for the tenant."""
    assert_can_view_portfolio(current_user)
    return svc.list_action_items()


@router.get("/portfolio/action-items", response_model=ActionItemListResponse)
async def list_portfolio_action_items(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> ActionItemListResponse:
    """List portfolio action items for the tenant."""
    assert_can_view_portfolio(current_user)
    return svc.list_action_items()


@router.put("/action-items/{action_item_id}")
async def update_action_item(
    action_item_id: str,
    body: ActionItemUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_program_cadence(current_user)
    return svc.update_action_item(action_item_id, body)


@router.delete("/action-items/{action_item_id}", status_code=204)
async def delete_action_item(
    action_item_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_program_cadence(current_user)
    svc.delete_action_item(action_item_id)
