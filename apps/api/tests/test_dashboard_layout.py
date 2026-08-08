"""Dashboard layout contract, validation, and authorization coverage."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.domain.dashboard_layout import DashboardLayoutUpdate, DashboardWidgetLayout
from app.services.dashboard_layout import SYSTEM_LAYOUTS, DashboardLayoutService


def test_system_layouts_put_required_decision_widgets_first() -> None:
    operational = SYSTEM_LAYOUTS["operational"]
    financial = SYSTEM_LAYOUTS["financial"]

    assert [item.widget_key for item in operational[:4]] == [
        "decision_strip",
        "needs_attention",
        "execution_health",
        "stage_progression",
    ]
    assert [item.widget_key for item in financial[:4]] == [
        "financial_position",
        "benefit_realization",
        "investment_payback",
        "waterline",
    ]


def test_layout_update_rejects_duplicate_widget_keys() -> None:
    with pytest.raises(ValidationError, match="Widget keys must be unique"):
        DashboardLayoutUpdate(
            widgets=[
                DashboardWidgetLayout(widget_key="decision_strip", order=10),
                DashboardWidgetLayout(widget_key="decision_strip", order=20),
            ]
        )


def test_layout_service_rejects_unknown_widgets() -> None:
    with pytest.raises(HTTPException, match="Unknown operational dashboard widgets"):
        DashboardLayoutService._validate_widgets(
            "operational",
            [*SYSTEM_LAYOUTS["operational"], DashboardWidgetLayout(widget_key="rogue", order=90)],
        )


def test_layout_service_keeps_required_widgets_visible() -> None:
    widgets = [item.model_copy(deep=True) for item in SYSTEM_LAYOUTS["financial"]]
    widgets[0].visible = False

    with pytest.raises(HTTPException, match="Required widgets must remain visible"):
        DashboardLayoutService._validate_widgets("financial", widgets)


def test_layout_service_keeps_required_widgets_above_supporting_widgets() -> None:
    widgets = [item.model_copy(deep=True) for item in SYSTEM_LAYOUTS["operational"]]
    widgets[0].order = 900

    with pytest.raises(HTTPException, match="must remain above supporting widgets"):
        DashboardLayoutService._validate_widgets("operational", widgets)


def test_non_admin_cannot_publish_a_role_default() -> None:
    service = DashboardLayoutService(object(), "tenant", "user", "viewer")  # type: ignore[arg-type]

    with pytest.raises(HTTPException, match="Insufficient role"):
        service.save_layout(
            "operational",
            DashboardLayoutUpdate(
                widgets=SYSTEM_LAYOUTS["operational"],
                publish_as_tenant_default=True,
            ),
        )


def test_dashboard_layout_migration_enforces_tenant_and_owner_rls() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "supabase/migrations/20260808000001_dashboard_operations_and_layouts.sql"
    ).read_text(encoding="utf-8")

    assert "ALTER TABLE dashboard_layouts ENABLE ROW LEVEL SECURITY" in migration
    assert "tenant_id = current_tenant_id()" in migration
    assert "owner_user_id = auth.uid()" in migration
    assert "role_key = current_user_role()" in migration
    assert "current_user_role() IN ('transformation_office', 'tenant_admin')" in migration
