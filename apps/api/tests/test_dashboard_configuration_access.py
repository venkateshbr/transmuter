"""Authorization regression coverage for tenant dashboard configuration."""

from fastapi.testclient import TestClient

from app.main import app
from app.routers.auth import PLATFORM_TENANT_ID, _mint_token

client = TestClient(app)


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
