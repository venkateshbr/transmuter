"""Tenant-scoped dashboard layout persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from supabase import Client

from app.domain.dashboard_layout import (
    DashboardBreakpoint,
    DashboardKey,
    DashboardLayoutResponse,
    DashboardLayoutUpdate,
    DashboardWidgetLayout,
)

LAYOUT_ADMIN_ROLES = {"transformation_office", "tenant_admin"}
LAYOUT_TARGET_ROLES = {
    "transformation_office",
    "tenant_admin",
    "pmo_lead",
    "finance_lead",
    "workstream_lead",
    "initiative_owner",
    "business_benefit_owner",
    "executive_sponsor",
    "viewer",
}

SYSTEM_LAYOUTS: dict[str, list[DashboardWidgetLayout]] = {
    "operational": [
        DashboardWidgetLayout(widget_key="decision_strip", order=10, size="full"),
        DashboardWidgetLayout(widget_key="needs_attention", order=20, size="wide"),
        DashboardWidgetLayout(widget_key="execution_health", order=30, size="medium"),
        DashboardWidgetLayout(widget_key="stage_progression", order=40, size="wide"),
        DashboardWidgetLayout(widget_key="risk_heatmap", order=50, size="medium"),
        DashboardWidgetLayout(widget_key="kpi_pulse", order=60, size="medium"),
        DashboardWidgetLayout(widget_key="my_work", order=70, size="medium"),
        DashboardWidgetLayout(widget_key="recent_activity", order=80, size="medium"),
    ],
    "financial": [
        DashboardWidgetLayout(widget_key="financial_position", order=10, size="full"),
        DashboardWidgetLayout(widget_key="benefit_realization", order=20, size="wide"),
        DashboardWidgetLayout(widget_key="investment_payback", order=30, size="medium"),
        DashboardWidgetLayout(widget_key="waterline", order=40, size="wide"),
        DashboardWidgetLayout(widget_key="financial_trend", order=50, size="wide"),
        DashboardWidgetLayout(widget_key="value_bridge", order=60, size="medium"),
        DashboardWidgetLayout(widget_key="cost_breakdown", order=70, size="medium"),
        DashboardWidgetLayout(widget_key="value_matrix", order=80, size="full"),
    ],
}

REQUIRED_WIDGETS: dict[str, set[str]] = {
    "operational": {"decision_strip", "needs_attention", "execution_health", "stage_progression"},
    "financial": {
        "financial_position",
        "benefit_realization",
        "investment_payback",
        "waterline",
    },
}
ALLOWED_WIDGETS = {key: {item.widget_key for item in items} for key, items in SYSTEM_LAYOUTS.items()}


class DashboardLayoutService:
    def __init__(self, client: Client, tenant_id: str, user_id: str, role: str) -> None:
        self._client = client
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._role = role

    def get_layout(
        self, dashboard_key: DashboardKey, breakpoint: DashboardBreakpoint
    ) -> DashboardLayoutResponse:
        personal = self._query(dashboard_key, breakpoint, owner_type="user", user_id=self._user_id)
        if personal:
            return self._response(personal, dashboard_key, breakpoint, "personal")
        tenant = self._query(dashboard_key, breakpoint, owner_type="tenant", role_key=self._role)
        if tenant:
            return self._response(tenant, dashboard_key, breakpoint, "tenant")
        return DashboardLayoutResponse(
            dashboard_key=dashboard_key,
            breakpoint=breakpoint,
            source="system",
            widgets=SYSTEM_LAYOUTS[dashboard_key],
        )

    def save_layout(
        self, dashboard_key: DashboardKey, data: DashboardLayoutUpdate
    ) -> DashboardLayoutResponse:
        if data.publish_as_tenant_default and self._role not in LAYOUT_ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="Insufficient role to publish layouts")
        if data.publish_as_tenant_default and data.role_key and data.role_key not in LAYOUT_TARGET_ROLES:
            raise HTTPException(status_code=422, detail="Unknown dashboard layout role")
        self._validate_widgets(dashboard_key, data.widgets)
        owner_type = "tenant" if data.publish_as_tenant_default else "user"
        role_key = (data.role_key or self._role) if owner_type == "tenant" else None
        owner_user_id = None if owner_type == "tenant" else self._user_id
        existing = self._query(
            dashboard_key,
            data.breakpoint,
            owner_type=owner_type,
            user_id=owner_user_id,
            role_key=role_key,
            include_unpublished=True,
        )
        payload = {
            "tenant_id": self._tenant_id,
            "dashboard_key": dashboard_key,
            "owner_type": owner_type,
            "owner_user_id": owner_user_id,
            "role_key": role_key,
            "breakpoint": data.breakpoint,
            "layout_version": int((existing or {}).get("layout_version") or 0) + 1,
            "widgets": [widget.model_dump() for widget in data.widgets],
            "is_published": owner_type == "tenant",
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if existing:
            result = (
                self._client.table("dashboard_layouts")
                .update(payload)
                .eq("tenant_id", self._tenant_id)
                .eq("id", existing["id"])
                .execute()
            )
        else:
            payload.update({"id": str(uuid4()), "created_at": payload["updated_at"]})
            result = self._client.table("dashboard_layouts").insert(payload).execute()
        row = (result.data or [payload])[0]
        return self._response(row, dashboard_key, data.breakpoint, owner_type)

    def reset_personal_layout(
        self, dashboard_key: DashboardKey, breakpoint: DashboardBreakpoint
    ) -> DashboardLayoutResponse:
        (
            self._client.table("dashboard_layouts")
            .delete()
            .eq("tenant_id", self._tenant_id)
            .eq("dashboard_key", dashboard_key)
            .eq("owner_type", "user")
            .eq("owner_user_id", self._user_id)
            .eq("breakpoint", breakpoint)
            .execute()
        )
        return self.get_layout(dashboard_key, breakpoint)

    @staticmethod
    def _validate_widgets(
        dashboard_key: DashboardKey, widgets: list[DashboardWidgetLayout]
    ) -> None:
        keys = {widget.widget_key for widget in widgets}
        unknown = keys - ALLOWED_WIDGETS[dashboard_key]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown {dashboard_key} dashboard widgets: {', '.join(sorted(unknown))}",
            )
        missing = REQUIRED_WIDGETS[dashboard_key] - keys
        hidden = {
            widget.widget_key
            for widget in widgets
            if widget.widget_key in REQUIRED_WIDGETS[dashboard_key] and not widget.visible
        }
        if missing or hidden:
            invalid = sorted(missing | hidden)
            raise HTTPException(
                status_code=422,
                detail=f"Required widgets must remain visible: {', '.join(invalid)}",
            )
        required_orders = [
            widget.order for widget in widgets if widget.widget_key in REQUIRED_WIDGETS[dashboard_key]
        ]
        optional_orders = [
            widget.order
            for widget in widgets
            if widget.visible and widget.widget_key not in REQUIRED_WIDGETS[dashboard_key]
        ]
        if required_orders and optional_orders and max(required_orders) > min(optional_orders):
            raise HTTPException(
                status_code=422,
                detail="Required decision widgets must remain above supporting widgets",
            )

    def _query(
        self,
        dashboard_key: str,
        breakpoint: str,
        *,
        owner_type: str,
        user_id: str | None = None,
        role_key: str | None = None,
        include_unpublished: bool = False,
    ) -> dict | None:  # type: ignore[type-arg]
        query = (
            self._client.table("dashboard_layouts")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .eq("dashboard_key", dashboard_key)
            .eq("breakpoint", breakpoint)
            .eq("owner_type", owner_type)
        )
        if user_id:
            query = query.eq("owner_user_id", user_id)
        if role_key:
            query = query.eq("role_key", role_key)
        if owner_type == "tenant" and not include_unpublished:
            query = query.eq("is_published", True)
        result = query.maybe_single().execute()
        return result.data if result else None

    @staticmethod
    def _response(
        row: dict, dashboard_key: DashboardKey, breakpoint: DashboardBreakpoint, source: str
    ) -> DashboardLayoutResponse:  # type: ignore[type-arg]
        return DashboardLayoutResponse(
            dashboard_key=dashboard_key,
            breakpoint=breakpoint,
            source="tenant" if source == "tenant" else "personal",
            layout_version=int(row.get("layout_version") or 1),
            widgets=[DashboardWidgetLayout.model_validate(widget) for widget in row.get("widgets") or []],
        )
