from __future__ import annotations

import hashlib
import hmac
import json
import time
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_supabase_admin
from app.main import app
from app.routers.auth import PLATFORM_TENANT_ID, _mint_token

client = TestClient(app)


def _platform_headers() -> dict[str, str]:
    return {
        "Authorization": (
            "Bearer "
            + _mint_token(str(PLATFORM_TENANT_ID), str(PLATFORM_TENANT_ID), "platform_admin")
        )
    }


def test_platform_overview_and_delete_preview_use_real_supabase() -> None:
    overview = client.get("/platform/overview", headers=_platform_headers())

    assert overview.status_code == 200
    data = overview.json()
    assert data["summary"]["tenant_count"] >= 1
    assert data["summary"]["required_price_count"] >= 1
    assert data["tenants"]

    tenant_id = UUID(data["tenants"][0]["tenant_id"])
    preview = client.get(
        f"/platform/tenants/{tenant_id}/delete-preview",
        headers=_platform_headers(),
    )

    assert preview.status_code == 200
    preview_data = preview.json()
    assert preview_data["tenant_id"] == str(tenant_id)
    assert "users" in preview_data["object_counts"]
    assert "initiatives" in preview_data["object_counts"]


def test_platform_delete_preview_returns_404_for_missing_real_tenant() -> None:
    missing = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

    response = client.get(
        f"/platform/tenants/{missing}/delete-preview",
        headers=_platform_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found"


def test_platform_tenant_delete_rejects_platform_pseudo_tenant() -> None:
    response = client.request(
        "DELETE",
        f"/platform/tenants/{PLATFORM_TENANT_ID}",
        headers=_platform_headers(),
        json={"confirm_slug": "platform"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Platform pseudo-tenant cannot be deleted"


def test_platform_tenant_delete_rejects_wrong_confirmation_slug() -> None:
    overview = client.get("/platform/overview", headers=_platform_headers())
    overview.raise_for_status()
    tenant = overview.json()["tenants"][0]

    response = client.request(
        "DELETE",
        f"/platform/tenants/{tenant['tenant_id']}",
        headers=_platform_headers(),
        json={"confirm_slug": f"not-{tenant['slug']}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Confirmation slug does not match tenant slug"


def test_billing_config_and_checkout_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    config = client.get("/billing/config")

    assert config.status_code == 200
    assert config.json()["provider"] in {"stripe", settings.payment_provider}

    monkeypatch.setattr(settings, "payment_provider", "disabled")
    disabled = client.post(
        "/billing/checkout-session",
        json=_checkout_payload(),
    )
    assert disabled.status_code == 400

    monkeypatch.setattr(settings, "payment_provider", "stripe")
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    not_configured = client.post(
        "/billing/checkout-session",
        json=_checkout_payload(),
    )
    assert not_configured.status_code == 503


def test_billing_webhook_signature_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")

    missing_secret = client.post("/billing/webhook", content=b"{}")
    assert missing_secret.status_code == 503

    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret")
    missing_signature = client.post("/billing/webhook", content=b"{}")
    assert missing_signature.status_code == 400
    assert missing_signature.json()["detail"] == "Missing Stripe signature"

    invalid_signature = client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "t=not-a-timestamp,v1=bad"},
    )
    assert invalid_signature.status_code == 400
    assert invalid_signature.json()["detail"] == "Invalid timestamp"

    stale_payload = b'{"type":"ignored.event","data":{"object":{}}}'
    stale_header = _stripe_signature_header(stale_payload, timestamp=int(time.time()) - 600)
    stale = client.post(
        "/billing/webhook",
        content=stale_payload,
        headers={"Stripe-Signature": stale_header},
    )
    assert stale.status_code == 400
    assert stale.json()["detail"] == "Stale Stripe signature"


def test_billing_webhook_accepts_signed_ignored_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret")
    payload = json.dumps({"type": "invoice.payment_succeeded", "data": {"object": {}}}).encode()

    response = client.post(
        "/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": _stripe_signature_header(payload)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "event_type": "invoice.payment_succeeded",
        "provisioning_status": "ignored",
        "tenant_id": None,
        "organization_slug": None,
        "initial_admin_user_id": None,
    }


def test_platform_overview_requires_platform_role() -> None:
    admin = get_supabase_admin()
    user = admin.table("users").select("id, tenant_id").limit(1).single().execute().data
    if not user:
        pytest.skip("real Supabase user is required for role guard verification")

    headers = {
        "Authorization": (
            "Bearer " + _mint_token(user["id"], user["tenant_id"], "transformation_office")
        )
    }

    response = client.get("/platform/overview", headers=headers)

    assert response.status_code == 403


def _checkout_payload() -> dict[str, object]:
    return {
        "organization_name": "Acceptance Billing Org",
        "organization_slug": "acceptance-billing-org",
        "admin_display_name": "Acceptance Admin",
        "admin_email": "acceptance@example.com",
        "initial_password": "Transmuter2026!",
        "planned_user_count": 25,
        "billing_interval": "month",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
    }


def _stripe_signature_header(payload: bytes, timestamp: int | None = None) -> str:
    ts = timestamp or int(time.time())
    signed_payload = f"{ts}.".encode() + payload
    signature = hmac.new(
        settings.stripe_webhook_secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={ts},v1={signature}"
