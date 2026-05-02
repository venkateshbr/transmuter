from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.repositories.initiative import InitiativeRepository
from app.repositories.milestone import MilestoneRepository
from app.repositories.risk import RiskRepository
from app.core.database import get_supabase_admin
from app.domain.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    """Get aggregated dashboard data for the current user."""
    # Note: In a real app, we'd use service layer. 
    # For speed and given the instructions, I'll use repositories directly or simple queries.
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    uid = str(current_user.id)

    # 1. Initiatives Summary
    inits_res = client.table("initiatives").select("id, stage, rag_status, pressure_score").eq("tenant_id", tid).is_("archived_at", "null").execute()
    inits = inits_res.data
    
    total_initiatives = len(inits)
    at_risk = len([i for i in inits if i["rag_status"] == "red"])
    
    # 2. Pipeline by Stage
    pipeline_by_stage = {
        "scoping": len([i for i in inits if i["stage"] == "scoping"]),
        "in_progress": len([i for i in inits if i["stage"] == "in_progress"]),
        "complete": len([i for i in inits if i["stage"] == "complete"]),
    }

    # 3. RAG Breakdown
    rag_breakdown = {
        "red": at_risk,
        "amber": len([i for i in inits if i["rag_status"] == "amber"]),
        "green": len([i for i in inits if i["rag_status"] == "green"]),
    }

    # 4. My Milestones (assigned to user)
    milestones_res = client.table("milestones").select("*, initiative:initiatives(name)").eq("tenant_id", tid).eq("owner_id", uid).neq("status", "complete").order("planned_end").limit(5).execute()
    
    # 5. Pressure Score (average)
    scores = [float(i["pressure_score"]) for i in inits if i["pressure_score"] is not None]
    avg_pressure = sum(scores) / len(scores) if scores else 0

    # 6. Risk Heatmap
    risks_res = client.table("risks").select("impact, likelihood").eq("tenant_id", tid).eq("status", "open").execute()
    risk_heatmap = {} # impact_likelihood -> count
    for r in risks_res.data:
        key = f"{r['impact']}_{r['likelihood']}"
        risk_heatmap[key] = risk_heatmap.get(key, 0) + 1

    # 7. Pending Approvals
    pending_res = client.table("gate_submissions").select("id", count="exact").eq("tenant_id", tid).eq("decision", "pending").execute()
    pending_count = pending_res.count if pending_res.count is not None else 0

    return {
        "summary": {
            "total_initiatives": total_initiatives,
            "at_risk": at_risk,
            "pending_approvals": pending_count,
        },
        "pipeline_by_stage": pipeline_by_stage,
        "rag_breakdown": rag_breakdown,
        "my_milestones": milestones_res.data,
        "portfolio_pressure": {
            "score": avg_pressure,
            "label": "Low" if avg_pressure < 3.4 else "Medium" if avg_pressure < 6.7 else "High"
        },
        "risk_heatmap": risk_heatmap
    }
