"""Tenant dashboard configuration contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DashboardMenuGroup = Literal["dashboard", "primary", "hidden"]


class DashboardConfigItem(BaseModel):
    id: str | None = None
    dashboard_key: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=200)
    route_path: str = Field(..., min_length=1, max_length=300)
    menu_group: DashboardMenuGroup = "dashboard"
    icon: str = Field("grid", min_length=1, max_length=80)
    display_order: int = 0
    is_enabled: bool = True
    allowed_roles: list[str] = Field(
        default_factory=lambda: ["transformation_office", "initiative_owner", "viewer"]
    )
    is_system: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class DashboardConfigResponse(BaseModel):
    dashboards: list[DashboardConfigItem] = Field(default_factory=list)


class DashboardConfigUpdate(BaseModel):
    dashboards: list[DashboardConfigItem] = Field(default_factory=list)
