from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/workstreams", tags=["workstreams"])

@router.get("")
async def list_workstreams(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """List all workstreams for the tenant."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    res = client.table("workstreams").select("*").eq("tenant_id", tid).order("name").execute()
    return {"data": res.data}

@router.post("", status_code=201)
async def create_workstream(
    body: dict,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Create a new workstream."""
    client = get_supabase_admin()
    payload = {**body, "tenant_id": str(current_user.tenant_id)}
    res = client.table("workstreams").insert(payload).execute()
    return res.data[0]

@router.put("/{workstream_id}")
async def update_workstream(
    workstream_id: str,
    body: dict,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Update an existing workstream."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    res = client.table("workstreams").update(body).eq("id", workstream_id).eq("tenant_id", tid).execute()
    return res.data[0]

@router.delete("/{workstream_id}", status_code=204)
async def delete_workstream(
    workstream_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Delete a workstream."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    client.table("workstreams").delete().eq("id", workstream_id).eq("tenant_id", tid).execute()
    return None
