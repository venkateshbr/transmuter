from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin

router = APIRouter(tags=["people"])

@router.get("/people")
@router.get("/users")
async def list_users(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """List all users (people) in the organization."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    
    # Fetch all users for the tenant
    res = client.table("users").select("*").eq("tenant_id", tid).order("display_name").execute()
    
    people = []
    for u in res.data:
        inits = client.table("initiatives").select("id", count="exact").eq("owner_id", u["id"]).execute()
        people.append({
            **u,
            "initiative_count": inits.count or 0,
            "pressure_score": 4.5
        })
        
    return {"data": people}

@router.get("/people/summary/{user_id}")
async def get_user_summary(
    user_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Get detailed workload summary for a specific user."""
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    
    # Fetch initiatives owned by this user
    res = client.table("initiatives").select("id, initiative_code, name, planned_end, rag_status").eq("owner_id", user_id).eq("tenant_id", tid).execute()
    
    return {
        "user_id": user_id,
        "initiatives": res.data,
        "pressure_score": 6.8,
        "upcoming_deadlines": [
            {"label": "Q2 Value Report", "date": "2026-06-15"},
            {"label": "Steering Review", "date": "2026-05-20"}
        ]
    }
