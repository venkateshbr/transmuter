from decimal import Decimal
from typing import Annotated, Any
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    business_unit_id: str | None = None,
    workstream_id: str | None = None,
    rag_status: str | None = None,
):
    """Get aggregated dashboard data for the current user."""
    # Note: In a real app, we'd use service layer. 
    # For speed and given the instructions, I'll use repositories directly or simple queries.
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    uid = str(current_user.id)

    # 1. Initiatives Summary
    inits_res = (
        client.table("initiatives")
        .select("id, name, initiative_code, stage, rag_status, pressure_score, workstream_id, workstreams(name, business_unit_id, business_units(name))")
        .eq("tenant_id", tid)
        .is_("archived_at", "null")
        .execute()
    )
    all_inits = inits_res.data or []
    inits = [
        row for row in all_inits
        if _matches_dashboard_filters(row, business_unit_id, workstream_id, rag_status)
    ]
    initiative_ids = {row["id"] for row in inits}
    
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
    milestones_res = (
        client.table("milestones")
        .select("*, initiative:initiatives(name)")
        .eq("tenant_id", tid)
        .eq("owner_id", uid)
        .neq("status", "complete")
        .order("planned_end")
        .limit(20)
        .execute()
    )
    my_milestones = [
        row for row in (milestones_res.data or [])
        if not initiative_ids or row.get("initiative_id") in initiative_ids
    ][:5]
    
    # 5. Pressure Score (average)
    scores = [float(i["pressure_score"]) for i in inits if i["pressure_score"] is not None]
    avg_pressure = sum(scores) / len(scores) if scores else 0

    # 6. Risk Heatmap
    risks_res = (
        client.table("risks")
        .select("id, initiative_id, impact, likelihood")
        .eq("tenant_id", tid)
        .eq("status", "open")
        .execute()
    )
    risk_heatmap = {} # impact_likelihood -> count
    for r in risks_res.data or []:
        if initiative_ids and r.get("initiative_id") not in initiative_ids:
            continue
        key = f"{r['impact']}_{r['likelihood']}"
        risk_heatmap[key] = risk_heatmap.get(key, 0) + 1

    # 7. Pending Approvals
    pending_res = client.table("gate_submissions").select("id", count="exact").eq("tenant_id", tid).eq("decision", "pending").execute()
    pending_count = pending_res.count if pending_res.count is not None else 0
    my_actions = _get_my_actions(client, tid, uid, initiative_ids)
    kpi_pulse = _get_kpi_pulse(client, tid, initiative_ids)
    value_bridge = _get_value_bridge(client, tid, initiative_ids)
    recent_activity = _get_recent_activity(client, tid, initiative_ids)
    available_filters = _get_available_filters(client, tid, all_inits)

    return {
        "summary": {
            "total_initiatives": total_initiatives,
            "at_risk": at_risk,
            "pending_approvals": pending_count,
        },
        "pipeline_by_stage": pipeline_by_stage,
        "rag_breakdown": rag_breakdown,
        "my_milestones": my_milestones,
        "portfolio_pressure": {
            "score": avg_pressure,
            "label": "Low" if avg_pressure < 3.4 else "Medium" if avg_pressure < 6.7 else "High"
        },
        "risk_heatmap": risk_heatmap,
        "my_actions": my_actions,
        "kpi_pulse": kpi_pulse,
        "value_bridge": value_bridge,
        "recent_activity": recent_activity,
        "available_filters": available_filters,
    }


def _matches_dashboard_filters(
    row: dict[str, Any],
    business_unit_id: str | None,
    workstream_id: str | None,
    rag_status: str | None,
) -> bool:
    workstream = row.get("workstreams") or {}
    if business_unit_id and workstream.get("business_unit_id") != business_unit_id:
        return False
    if workstream_id and row.get("workstream_id") != workstream_id:
        return False
    return not rag_status or row.get("rag_status") == rag_status


def _dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001")))


def _get_my_actions(
    client: Any,
    tenant_id: str,
    user_id: str,
    initiative_ids: set[str],
) -> list[dict[str, Any]]:
    result = (
        client.table("action_items")
        .select("id, description, status, due_date, initiative_id, initiatives(name, initiative_code), meeting_sessions(session_date, meetings(name))")
        .eq("tenant_id", tenant_id)
        .eq("assignee_id", user_id)
        .order("due_date")
        .limit(25)
        .execute()
    )
    closed = {"done", "complete", "completed", "closed"}
    return [
        row for row in (result.data or [])
        if row.get("status") not in closed
        and (not initiative_ids or row.get("initiative_id") in initiative_ids)
    ][:5]


def _get_kpi_pulse(client: Any, tenant_id: str, initiative_ids: set[str]) -> dict[str, Any]:
    kpis_result = (
        client.table("kpis")
        .select("id, name, unit, initiative_id, initiatives(name, initiative_code)")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    kpis = [
        row for row in (kpis_result.data or [])
        if not initiative_ids or row.get("initiative_id") in initiative_ids
    ]
    kpi_ids = [row["id"] for row in kpis]
    entries: list[dict[str, Any]] = []
    if kpi_ids:
        entries = (
            client.table("kpi_entries")
            .select("kpi_id, year, quarter, value_base, value_high, value_actual")
            .eq("tenant_id", tenant_id)
            .in_("kpi_id", kpi_ids)
            .execute()
            .data or []
        )

    entries_by_kpi: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        entries_by_kpi.setdefault(entry["kpi_id"], []).append(entry)

    hitting = 0
    missing = 0
    no_actuals = 0
    items: list[dict[str, Any]] = []
    for kpi in kpis:
        actual_entries = [
            row for row in entries_by_kpi.get(kpi["id"], [])
            if row.get("value_actual") is not None
        ]
        latest = sorted(
            actual_entries,
            key=lambda row: (row.get("year") or 0, row.get("quarter") or 5),
            reverse=True,
        )[0] if actual_entries else None
        if latest is None:
            no_actuals += 1
            status = "no_data"
        elif _dec(latest.get("value_actual")) >= _dec(latest.get("value_base")):
            hitting += 1
            status = "on_track"
        else:
            missing += 1
            status = "at_risk"
        items.append({
            "id": kpi["id"],
            "name": kpi["name"],
            "unit": kpi.get("unit"),
            "initiative": kpi.get("initiatives"),
            "status": status,
            "actual": str(latest.get("value_actual")) if latest else None,
            "base": str(latest.get("value_base")) if latest else None,
        })

    tracked = hitting + missing
    health = Decimal("0") if tracked == 0 else (Decimal(hitting) / Decimal(tracked)) * Decimal("100")
    return {
        "total_kpis": len(kpis),
        "hitting_base": hitting,
        "missing_base": missing,
        "no_actuals": no_actuals,
        "health_score": str(health.quantize(Decimal("0.1"))),
        "items": items[:5],
    }


def _get_value_bridge(client: Any, tenant_id: str, initiative_ids: set[str]) -> dict[str, str]:
    entries = (
        client.table("financial_entries")
        .select("initiative_id, revenue_uplift_base, revenue_uplift_high, revenue_uplift_actual, gm_uplift_base, gm_uplift_high, gm_uplift_actual")
        .eq("tenant_id", tenant_id)
        .execute()
        .data or []
    )
    cost_lines = (
        client.table("financial_cost_lines")
        .select("initiative_id, amount_plan, amount_actual")
        .eq("tenant_id", tenant_id)
        .execute()
        .data or []
    )
    scoped_entries = [row for row in entries if not initiative_ids or row.get("initiative_id") in initiative_ids]
    scoped_costs = [row for row in cost_lines if not initiative_ids or row.get("initiative_id") in initiative_ids]
    benefits_base = sum((_dec(row.get("gm_uplift_base")) for row in scoped_entries), Decimal("0"))
    benefits_high = sum((_dec(row.get("gm_uplift_high")) for row in scoped_entries), Decimal("0"))
    benefits_actual = sum((_dec(row.get("gm_uplift_actual")) for row in scoped_entries), Decimal("0"))
    costs_plan = sum((_dec(row.get("amount_plan")) for row in scoped_costs), Decimal("0"))
    costs_actual = sum((_dec(row.get("amount_actual")) for row in scoped_costs), Decimal("0"))
    return {
        "benefits_base": _money(benefits_base),
        "benefits_high": _money(benefits_high),
        "benefits_actual": _money(benefits_actual),
        "costs_plan": _money(costs_plan),
        "costs_actual": _money(costs_actual),
        "net_base": _money(benefits_base - costs_plan),
        "net_high": _money(benefits_high - costs_plan),
        "net_actual": _money(benefits_actual - costs_actual),
    }


def _get_recent_activity(
    client: Any,
    tenant_id: str,
    initiative_ids: set[str],
) -> list[dict[str, Any]]:
    result = (
        client.table("status_updates")
        .select("id, initiative_id, rag_status, summary, submitted_at, initiatives(name, initiative_code), users!status_updates_author_id_fkey(display_name)")
        .eq("tenant_id", tenant_id)
        .eq("is_draft", False)
        .order("submitted_at", desc=True)
        .limit(25)
        .execute()
    )
    return [
        row for row in (result.data or [])
        if not initiative_ids or row.get("initiative_id") in initiative_ids
    ][:5]


def _get_available_filters(
    client: Any,
    tenant_id: str,
    initiatives: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    business_units = (
        client.table("business_units")
        .select("id, name")
        .eq("tenant_id", tenant_id)
        .order("name")
        .execute()
        .data or []
    )
    workstreams = (
        client.table("workstreams")
        .select("id, name, business_unit_id")
        .eq("tenant_id", tenant_id)
        .order("name")
        .execute()
        .data or []
    )
    rag_values = sorted({row.get("rag_status") for row in initiatives if row.get("rag_status")})
    return {
        "business_units": business_units,
        "workstreams": workstreams,
        "rag_statuses": [{"id": value, "name": value.title()} for value in rag_values],
    }
