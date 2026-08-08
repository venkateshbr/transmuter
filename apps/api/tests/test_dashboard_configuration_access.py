"""Authorization regression coverage for tenant dashboard configuration."""

from fastapi.testclient import TestClient

from app.domain.dashboard_config import DashboardConfigItem
from app.main import app
from app.routers.auth import PLATFORM_TENANT_ID, _mint_token
from app.services.dashboard_config import DASHBOARD_DEFINITIONS

client = TestClient(app)


def test_financial_operations_menu_contract_and_defaults() -> None:
    item = DashboardConfigItem(
        dashboard_key="benefit_tracking",
        label="Benefit Ledger",
        route_path="/financials/benefit-tracking",
        menu_group="financial_operations",
    )
    legacy = item.model_copy(update={"menu_group": "operations"})

    assert item.menu_group == "financial_operations"
    assert DashboardConfigItem.model_validate(legacy.model_dump()).menu_group == "operations"
    assert {
        definition.menu_group
        for definition in DASHBOARD_DEFINITIONS
        if definition.dashboard_key
        in {"benefit_tracking", "benefits_register", "bankable_plan", "waterline", "shared_costs"}
    } == {"financial_operations"}


def test_platform_admin_cannot_request_tenant_dashboard_configuration() -> None:
    token = _mint_token(
        str(PLATFORM_TENANT_ID),
        str(PLATFORM_TENANT_ID),
        "platform_admin",
    )

    response = client.get(
        "/dashboard/configuration",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Tenant context is required"}


def test_platform_admin_cannot_request_tenant_dashboard_layout() -> None:
    token = _mint_token(
        str(PLATFORM_TENANT_ID),
        str(PLATFORM_TENANT_ID),
        "platform_admin",
    )

    response = client.get(
        "/dashboard/operational/layout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Tenant context is required"}
