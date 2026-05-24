from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, require_role
from app.core.database import get_supabase_admin
from app.services.billing import stripe_price_configuration

router = APIRouter(
    prefix="/platform",
    tags=["platform"],
    dependencies=[Depends(require_role("platform_admin"))],
)

TENANT_DELETE_TABLES = [
    "audit_log",
    "agent_corrections",
    "agent_metrics",
    "agent_audit_log",
    "action_items",
    "meeting_artifacts",
    "meeting_external_events",
    "agenda_items",
    "meeting_sessions",
    "meeting_initiatives",
    "meeting_attendees",
    "meetings",
    "gate_submissions",
    "stage_gates",
    "gate_criteria",
    "nudge_log",
    "status_updates",
    "financial_cost_lines",
    "financial_entries",
    "financial_cell_assumptions",
    "risks",
    "kpi_entries",
    "kpis",
    "milestone_dependencies",
    "milestone_checklist",
    "milestones",
    "initiative_team",
    "initiatives",
    "user_workstreams",
    "workstreams",
    "business_units",
    "tenant_subscriptions",
    "signup_intents",
    "subscription_plans",
]


class DeleteTenantRequest(BaseModel):
    confirm_slug: str = Field(..., min_length=2, max_length=80)


@router.get("/overview")
async def platform_overview(
    _current_user: Annotated[CurrentUser, Depends(require_role("platform_admin"))],
) -> dict[str, Any]:
    client = get_supabase_admin()

    orgs = (
        client.table("organizations")
        .select("id, name, slug, created_at, updated_at, settings")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    subscriptions = client.table("tenant_subscriptions").select("*").execute()
    signup_intents = (
        client.table("signup_intents")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    users = client.table("users").select("tenant_id, status").execute()

    subscription_by_tenant = {item["tenant_id"]: item for item in subscriptions.data or []}
    users_by_tenant: dict[str, dict[str, int]] = {}
    for user in users.data or []:
        tenant_id = user.get("tenant_id")
        if not tenant_id:
            continue
        counts = users_by_tenant.setdefault(tenant_id, {"active": 0, "total": 0})
        counts["total"] += 1
        if user.get("status") == "active":
            counts["active"] += 1

    tenants = []
    for org in orgs.data or []:
        tenant_id = org["id"]
        billing_settings = (org.get("settings") or {}).get("billing") or {}
        subscription = subscription_by_tenant.get(tenant_id) or {}
        user_counts = users_by_tenant.get(tenant_id, {"active": 0, "total": 0})
        tenants.append(
            {
                "tenant_id": tenant_id,
                "name": org["name"],
                "slug": org["slug"],
                "created_at": org.get("created_at"),
                "updated_at": org.get("updated_at"),
                "subscription_status": subscription.get("status")
                or billing_settings.get("subscription_status")
                or "not_configured",
                "payment_status": subscription.get("payment_status")
                or billing_settings.get("payment_status"),
                "planned_user_count": subscription.get("planned_user_count")
                or billing_settings.get("planned_user_count"),
                "active_user_count": user_counts["active"],
                "total_user_count": user_counts["total"],
                "stripe_customer_id": subscription.get("stripe_customer_id")
                or billing_settings.get("customer_id"),
                "stripe_subscription_id": subscription.get("stripe_subscription_id")
                or billing_settings.get("subscription_id"),
            }
        )

    intents = []
    for intent in signup_intents.data or []:
        intents.append(
            {
                "id": intent["id"],
                "tenant_id": intent["tenant_id"],
                "organization_name": intent["organization_name"],
                "organization_slug": intent["organization_slug"],
                "admin_email": intent["admin_email"],
                "admin_display_name": intent["admin_display_name"],
                "planned_user_count": intent["planned_user_count"],
                "plan_code": intent["plan_code"],
                "billing_interval": intent["billing_interval"],
                "status": intent["status"],
                "has_checkout_session": bool(intent.get("stripe_checkout_session_id")),
                "stripe_customer_id": intent.get("stripe_customer_id"),
                "stripe_subscription_id": intent.get("stripe_subscription_id"),
                "created_at": intent.get("created_at"),
                "updated_at": intent.get("updated_at"),
            }
        )

    active_tenants = len(
        [tenant for tenant in tenants if tenant["subscription_status"] == "active"]
    )
    pending_signups = len(
        [
            intent
            for intent in intents
            if intent["status"] in {"pending_checkout", "checkout_created"}
        ]
    )
    configured_prices = len(
        [price for price in stripe_price_configuration() if price["configured"]]
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "tenant_count": len(tenants),
            "active_tenant_count": active_tenants,
            "pending_signup_count": pending_signups,
            "configured_price_count": configured_prices,
            "required_price_count": len(stripe_price_configuration()),
        },
        "stripe_price_configuration": stripe_price_configuration(),
        "tenants": tenants,
        "signup_intents": intents,
    }


@router.get("/tenants/{tenant_id}/delete-preview")
async def tenant_delete_preview(
    tenant_id: UUID,
    _current_user: Annotated[CurrentUser, Depends(require_role("platform_admin"))],
) -> dict[str, Any]:
    client = get_supabase_admin()
    org = _get_tenant_or_404(client, tenant_id)
    tenant_id_str = str(tenant_id)
    table_counts = {
        table: _count_tenant_rows(client, table, tenant_id_str) for table in TENANT_DELETE_TABLES
    }
    table_counts["users"] = _count_tenant_rows(client, "users", tenant_id_str)
    return {
        "tenant_id": tenant_id_str,
        "tenant_slug": org["slug"],
        "tenant_name": org["name"],
        "object_counts": _object_counts(table_counts),
        "table_counts": table_counts,
    }


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    body: DeleteTenantRequest,
    _current_user: Annotated[CurrentUser, Depends(require_role("platform_admin"))],
) -> dict[str, Any]:
    if str(tenant_id) == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform pseudo-tenant cannot be deleted",
        )

    client = get_supabase_admin()
    org = _get_tenant_or_404(client, tenant_id)
    if org["slug"] != body.confirm_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation slug does not match tenant slug",
        )

    user_response = (
        client.table("users").select("id, email").eq("tenant_id", str(tenant_id)).execute()
    )
    tenant_users = user_response.data or []

    deletion_counts: dict[str, int] = {}
    for table in TENANT_DELETE_TABLES:
        deletion_counts[table] = _delete_tenant_rows(client, table, str(tenant_id))

    deletion_counts["users"] = _delete_tenant_rows(client, "users", str(tenant_id))

    auth_deleted = 0
    auth_errors: list[dict[str, str]] = []
    for user in tenant_users:
        try:
            client.auth.admin.delete_user(user["id"])
            auth_deleted += 1
        except Exception as exc:  # noqa: BLE001 - report and continue cleanup summary.
            auth_errors.append(
                {"id": user["id"], "email": user.get("email") or "", "error": str(exc)}
            )

    org_delete = client.table("organizations").delete().eq("id", str(tenant_id)).execute()
    organization_deleted = len(org_delete.data or [])

    return {
        "deleted": True,
        "tenant_id": str(tenant_id),
        "tenant_slug": org["slug"],
        "tenant_name": org["name"],
        "deleted_rows": deletion_counts,
        "object_counts": _object_counts(deletion_counts),
        "auth_users_deleted": auth_deleted,
        "auth_user_errors": auth_errors,
        "organization_deleted": organization_deleted,
    }


def _get_tenant_or_404(client: Any, tenant_id: UUID) -> dict[str, Any]:
    org_response = (
        client.table("organizations")
        .select("id, name, slug")
        .eq("id", str(tenant_id))
        .maybe_single()
        .execute()
    )
    org = org_response.data if org_response else None
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return org


def _count_tenant_rows(client: Any, table: str, tenant_id: str) -> int:
    response = client.table(table).select("id", count="exact").eq("tenant_id", tenant_id).execute()
    return response.count or 0


def _delete_tenant_rows(client: Any, table: str, tenant_id: str) -> int:
    count = _count_tenant_rows(client, table, tenant_id)
    if count == 0:
        return 0
    client.table(table).delete().eq("tenant_id", tenant_id).execute()
    return count


def _object_counts(table_counts: dict[str, int]) -> dict[str, int]:
    groups = {
        "users": ["users"],
        "initiatives": ["initiatives", "initiative_team"],
        "financials": ["financial_entries", "financial_cost_lines", "financial_cell_assumptions"],
        "kpis": ["kpis", "kpi_entries"],
        "risks": ["risks"],
        "milestones": ["milestones", "milestone_checklist", "milestone_dependencies"],
        "meetings": [
            "meetings",
            "meeting_attendees",
            "meeting_initiatives",
            "meeting_external_events",
            "meeting_artifacts",
            "meeting_sessions",
            "agenda_items",
        ],
        "action_items": ["action_items"],
        "governance": ["gate_criteria", "gate_submissions", "stage_gates"],
        "billing": ["tenant_subscriptions", "signup_intents", "subscription_plans"],
        "status_updates": ["status_updates", "nudge_log"],
        "audit_and_ai": ["audit_log", "agent_audit_log", "agent_corrections", "agent_metrics"],
        "master_data": ["business_units", "workstreams", "user_workstreams"],
    }
    return {
        key: sum(table_counts.get(table, 0) for table in tables) for key, tables in groups.items()
    }
