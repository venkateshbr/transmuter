from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.meetings import ActionItemListResponse, ActionItemUpdate
from app.services.meeting import MeetingService

router = APIRouter(tags=["action-items"])

@router.get("/action-items")
async def list_action_items(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ActionItemListResponse:
    """List all action items for the tenant."""
    svc = MeetingService(get_supabase_admin(), current_user.tenant_id)
    return {"items": svc.list_action_items()}


@router.get("/portfolio/action-items")
async def list_portfolio_action_items(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ActionItemListResponse:
    """List portfolio action items for the tenant."""
    svc = MeetingService(get_supabase_admin(), current_user.tenant_id)
    return {"items": svc.list_action_items()}


@router.put("/action-items/{action_item_id}")
async def update_action_item(
    action_item_id: str,
    body: ActionItemUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    svc = MeetingService(get_supabase_admin(), current_user.tenant_id)
    return svc.update_action_item(action_item_id, body)


@router.delete("/action-items/{action_item_id}", status_code=204)
async def delete_action_item(
    action_item_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> None:
    svc = MeetingService(get_supabase_admin(), current_user.tenant_id)
    svc.delete_action_item(action_item_id)
