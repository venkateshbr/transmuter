"""Dashboard widget layout contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

DashboardKey = Literal["operational", "financial"]
DashboardBreakpoint = Literal["desktop", "tablet"]
DashboardWidgetSize = Literal["small", "medium", "wide", "full"]


class DashboardWidgetLayout(BaseModel):
    widget_key: str = Field(..., pattern=r"^[a-z0-9_]+$", max_length=120)
    order: int = Field(..., ge=0, le=1000)
    size: DashboardWidgetSize = "medium"
    visible: bool = True


class DashboardLayoutUpdate(BaseModel):
    breakpoint: DashboardBreakpoint = "desktop"
    widgets: list[DashboardWidgetLayout] = Field(default_factory=list, max_length=64)
    publish_as_tenant_default: bool = False
    role_key: str | None = Field(None, max_length=80)

    @model_validator(mode="after")
    def validate_unique_widgets(self) -> DashboardLayoutUpdate:
        keys = [widget.widget_key for widget in self.widgets]
        if len(keys) != len(set(keys)):
            raise ValueError("Widget keys must be unique")
        return self


class DashboardLayoutResponse(BaseModel):
    dashboard_key: DashboardKey
    breakpoint: DashboardBreakpoint
    source: Literal["personal", "tenant", "system"]
    layout_version: int = 1
    widgets: list[DashboardWidgetLayout] = Field(default_factory=list)
