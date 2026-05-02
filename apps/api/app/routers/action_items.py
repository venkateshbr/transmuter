from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/action-items", tags=["action-items"])

@router.get("")
async def list_action_items(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """List all action items for the tenant."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    
    res = client.table("action_items").select("*, users!action_items_assignee_id_fkey(display_name), initiatives(name, initiative_code)").eq("tenant_id", tid).execute()
    return {"items": res.data or []}
