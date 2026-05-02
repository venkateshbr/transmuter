from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/people", tags=["people"])

@router.get("")
async def list_people(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """List all people in the organization."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    
    # Fetch all users for the tenant
    res = client.table("users").select("*").eq("tenant_id", tid).order("display_name").execute()
    
    # For each user, let's get some stats (e.g. initiative count)
    # This is a bit expensive in a loop, but fine for sample data
    people = []
    for u in res.data:
        inits = client.table("initiatives").select("id", count="exact").eq("owner_id", u["id"]).execute()
        people.append({
            **u,
            "initiative_count": inits.count or 0,
            "pressure_score": 4.5 # Placeholder for now
        })
        
    return {"items": people}
