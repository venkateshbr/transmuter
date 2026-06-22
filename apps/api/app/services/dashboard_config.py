"""Tenant dashboard registry and defaults."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from supabase import Client

from app.domain.dashboard_config import (
    DashboardConfigItem,
    DashboardConfigResponse,
    DashboardConfigUpdate,
)

DEFAULT_DASHBOARD_ROLES = ["transformation_office", "initiative_owner", "viewer"]
STARTER_ENABLED_DASHBOARDS = {
    "executive_dashboard",
    "financial_overview",
    "initiative_portfolio",
}


@dataclass(frozen=True)
class DashboardDefinition:
    dashboard_key: str
    label: str
    route_path: str
    menu_group: str
    icon: str
    display_order: int


DASHBOARD_DEFINITIONS: tuple[DashboardDefinition, ...] = (
    DashboardDefinition(
        "executive_dashboard", "Executive Dashboard", "/dashboard", "dashboard", "grid", 10
    ),
    DashboardDefinition(
        "financial_overview", "Financial Overview", "/financials", "dashboard", "payments", 20
    ),
    DashboardDefinition(
        "initiative_portfolio",
        "Initiative Portfolio",
        "/financials/initiative-portfolio",
        "dashboard",
        "table_chart",
        30,
    ),
    DashboardDefinition(
        "investments_payback",
        "Investments & Payback",
        "/financials/investments-payback",
        "dashboard",
        "request_quote",
        40,
    ),
    DashboardDefinition(
        "bankable_plan",
        "Bankable Plan",
        "/financials/bankable-plan",
        "dashboard",
        "account_balance",
        50,
    ),
    DashboardDefinition(
        "benefits_register",
        "Benefits Register",
        "/financials/benefits-register",
        "dashboard",
        "fact_check",
        60,
    ),
    DashboardDefinition(
        "benefit_tracking",
        "Benefit Tracking",
        "/financials/benefit-tracking",
        "dashboard",
        "trending_up",
        70,
    ),
    DashboardDefinition(
        "waterline", "Waterline", "/financials/waterline", "dashboard", "water_drop", 80
    ),
    DashboardDefinition(
        "control_tower", "Control Tower", "/reports/control-tower", "dashboard", "summarize", 90
    ),
    DashboardDefinition(
        "shared_costs", "Shared Costs", "/shared-costs", "primary", "account_balance", 100
    ),
)


class DashboardConfigService:
    def __init__(self, client: Client, tenant_id: str) -> None:
        self._client = client
        self._tenant_id = str(tenant_id)

    def ensure_defaults(self, *, profile: str = "starter_default") -> int:
        enabled = (
            {definition.dashboard_key for definition in DASHBOARD_DEFINITIONS}
            if profile == "demo_full"
            else STARTER_ENABLED_DASHBOARDS
        )
        rows = []
        existing = {
            row["dashboard_key"]
            for row in self._client.table("tenant_dashboard_config")
            .select("dashboard_key")
            .eq("tenant_id", self._tenant_id)
            .execute()
            .data
            or []
        }
        now = datetime.now(UTC).isoformat()
        for definition in DASHBOARD_DEFINITIONS:
            if definition.dashboard_key in existing:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tenant_id,
                    "dashboard_key": definition.dashboard_key,
                    "label": definition.label,
                    "route_path": definition.route_path,
                    "menu_group": definition.menu_group,
                    "icon": definition.icon,
                    "display_order": definition.display_order,
                    "is_enabled": definition.dashboard_key in enabled,
                    "allowed_roles": DEFAULT_DASHBOARD_ROLES,
                    "is_system": True,
                    "metadata": {"profile": profile},
                    "created_at": now,
                    "updated_at": now,
                }
            )
        if not rows:
            return 0
        self._client.table("tenant_dashboard_config").insert(rows).execute()
        return len(rows)

    def enable_all_defaults(self) -> int:
        self.ensure_defaults(profile="demo_full")
        result = (
            self._client.table("tenant_dashboard_config")
            .update({"is_enabled": True, "updated_at": datetime.now(UTC).isoformat()})
            .eq("tenant_id", self._tenant_id)
            .in_(
                "dashboard_key", [definition.dashboard_key for definition in DASHBOARD_DEFINITIONS]
            )
            .execute()
        )
        return len(result.data or [])

    def get_configuration(self) -> DashboardConfigResponse:
        self.ensure_defaults()
        result = (
            self._client.table("tenant_dashboard_config")
            .select("*")
            .eq("tenant_id", self._tenant_id)
            .order("menu_group")
            .order("display_order")
            .order("label")
            .execute()
        )
        return DashboardConfigResponse(dashboards=[self._to_item(row) for row in result.data or []])

    def update_configuration(self, data: DashboardConfigUpdate) -> DashboardConfigResponse:
        self.ensure_defaults()
        now = datetime.now(UTC).isoformat()
        for item in data.dashboards:
            payload = self._payload(item)
            payload["updated_at"] = now
            existing = (
                self._client.table("tenant_dashboard_config")
                .select("id")
                .eq("tenant_id", self._tenant_id)
                .eq("dashboard_key", item.dashboard_key)
                .maybe_single()
                .execute()
            )
            if existing and existing.data:
                (
                    self._client.table("tenant_dashboard_config")
                    .update(payload)
                    .eq("tenant_id", self._tenant_id)
                    .eq("id", existing.data["id"])
                    .execute()
                )
            else:
                payload.update(
                    {
                        "id": item.id or str(uuid4()),
                        "tenant_id": self._tenant_id,
                        "created_at": now,
                    }
                )
                self._client.table("tenant_dashboard_config").insert(payload).execute()
        return self.get_configuration()

    @staticmethod
    def _payload(item: DashboardConfigItem) -> dict[str, Any]:
        return {
            "dashboard_key": item.dashboard_key,
            "label": item.label,
            "route_path": item.route_path,
            "menu_group": item.menu_group,
            "icon": item.icon,
            "display_order": item.display_order,
            "is_enabled": item.is_enabled,
            "allowed_roles": item.allowed_roles or DEFAULT_DASHBOARD_ROLES,
            "is_system": item.is_system,
            "metadata": item.metadata or {},
        }

    @staticmethod
    def _to_item(row: dict[str, Any]) -> DashboardConfigItem:
        return DashboardConfigItem(
            id=row.get("id"),
            dashboard_key=row["dashboard_key"],
            label=row["label"],
            route_path=row["route_path"],
            menu_group=row.get("menu_group") or "dashboard",
            icon=row.get("icon") or "grid",
            display_order=int(row.get("display_order") or 0),
            is_enabled=bool(row.get("is_enabled", True)),
            allowed_roles=row.get("allowed_roles") or DEFAULT_DASHBOARD_ROLES,
            is_system=bool(row.get("is_system", True)),
            metadata=row.get("metadata") or {},
        )
