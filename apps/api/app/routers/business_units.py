from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/business-units", tags=["business-units"])

@router.get("")
async def list_business_units(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """List all business units for the tenant."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    res = client.table("business_units").select("*").eq("tenant_id", tid).order("name").execute()
    return {"data": res.data}

@router.post("", status_code=201)
async def create_business_unit(
    body: dict,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Create a new business unit."""
    client = get_supabase_admin()
    payload = {**body, "tenant_id": str(current_user.tenant_id)}
    res = client.table("business_units").insert(payload).execute()
    return res.data[0]

@router.put("/{bu_id}")
async def update_business_unit(
    bu_id: str,
    body: dict,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Update an existing business unit."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    res = client.table("business_units").update(body).eq("id", bu_id).eq("tenant_id", tid).execute()
    return res.data[0]

@router.delete("/{bu_id}", status_code=204)
async def delete_business_unit(
    bu_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Delete a business unit."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    client.table("business_units").delete().eq("id", bu_id).eq("tenant_id", tid).execute()
    return None
