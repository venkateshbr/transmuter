from __future__ import annotations

import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from urllib.parse import parse_qs
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_supabase_admin
from app.main import app
from app.routers.auth import PLATFORM_TENANT_ID, _mint_token
from app.routers.platform import DeleteTenantRequest, delete_tenant

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
    assert "portfolio_rag_documents" in preview_data["table_counts"]


def test_platform_tenant_delete_preview_includes_portfolio_rag_documents() -> None:
    overview = client.get("/platform/overview", headers=_platform_headers())
    overview.raise_for_status()
    tenant = overview.json()["tenants"][0]

    preview = client.get(
        f"/platform/tenants/{tenant['tenant_id']}/delete-preview",
        headers=_platform_headers(),
    )

    assert preview.status_code == 200
    assert "portfolio_rag_documents" in preview.json()["table_counts"]


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


async def test_platform_tenant_delete_cleans_bootstrap_financial_config_before_organization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = UUID("b7a91745-5542-4aeb-8125-474e221b8f37")
    fake_admin = _FakePlatformAdmin(
        tenant_id=str(tenant_id),
        slug="pilot-blank-da4f4031",
        counts={
            "financial_config_items": 20,
            "financial_config_groups": 10,
        },
    )
    monkeypatch.setattr("app.routers.platform.get_supabase_admin", lambda: fake_admin)

    data = await delete_tenant(
        tenant_id,
        DeleteTenantRequest(confirm_slug="pilot-blank-da4f4031"),
        CurrentUser(
            id=PLATFORM_TENANT_ID,
            tenant_id=PLATFORM_TENANT_ID,
            role="platform_admin",
        ),
    )

    assert data["deleted_rows"]["financial_config_items"] == 20
    assert data["deleted_rows"]["financial_config_groups"] == 10
    assert data["object_counts"]["financials"] == 30
    assert fake_admin.deleted_tables.index("financial_config_items") < fake_admin.deleted_tables.index(
        "financial_config_groups"
    )
    assert fake_admin.deleted_tables.index("financial_config_groups") < fake_admin.deleted_tables.index(
        "organizations"
    )


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


def test_billing_config_exposes_slug_validation_metadata() -> None:
    config = client.get("/billing/config")

    assert config.status_code == 200
    data = config.json()
    assert data["organization_slug_pattern"] == r"^[a-z0-9-]+$"
    assert data["organization_slug_min_length"] == 2
    assert data["organization_slug_max_length"] == 80


def test_checkout_session_resolves_redirect_urls_from_request_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "payment_provider", "stripe")
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_123")

    fake_service = _FakeBillingProvisioningService()
    fake_stripe = _FakeStripeAsyncClient(
        response_payload={"id": "cs_test_123", "url": "https://stripe.example/session"}
    )
    monkeypatch.setattr("app.routers.billing.BillingProvisioningService", lambda client: fake_service)
    monkeypatch.setattr("app.routers.billing.httpx.AsyncClient", lambda timeout: fake_stripe)

    response = client.post(
        "/billing/checkout-session",
        headers={"Origin": "https://demo.transmuter.test"},
        json={
            **_checkout_payload(),
            "success_url": "/billing/checkout/success?source=demo",
            "cancel_url": "https://example.com/cancel",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"checkout_url": "https://stripe.example/session", "session_id": "cs_test_123"}
    assert fake_stripe.last_request is not None
    sent = parse_qs(str(fake_stripe.last_request["content"]))
    assert sent["success_url"] == ["https://demo.transmuter.test/billing/checkout/success?source=demo"]
    assert sent["cancel_url"] == ["https://example.com/cancel"]


def test_billing_portal_session_resolves_return_url_from_request_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_123")
    monkeypatch.setitem(
        app.dependency_overrides,
        get_current_user,
        lambda: CurrentUser(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
            role="transformation_office",
            status="active",
            must_change_password=False,
        ),
    )

    fake_admin = _FakeSupabaseAdmin(
        org_data={"settings": {"billing": {"customer_id": "cus_test_123"}}},
        subscription_data={"stripe_customer_id": "cus_test_123"},
    )
    fake_stripe = _FakeStripeAsyncClient(
        response_payload={"id": "bps_test_123", "url": "https://stripe.example/portal"}
    )
    monkeypatch.setattr("app.routers.billing.get_supabase_admin", lambda: fake_admin)
    monkeypatch.setattr("app.routers.billing.httpx.AsyncClient", lambda timeout: fake_stripe)

    try:
        response = client.post(
            "/billing/portal-session",
            headers={"Origin": "https://demo.transmuter.test"},
            json={"return_url": "/billing/manage?tab=portal"},
        )

        assert response.status_code == 200
        assert response.json() == {"portal_url": "https://stripe.example/portal"}
        assert fake_stripe.last_request is not None
        sent = parse_qs(str(fake_stripe.last_request["content"]))
        assert sent["return_url"] == ["https://demo.transmuter.test/billing/manage?tab=portal"]
    finally:
        app.dependency_overrides.clear()


class _FakeBillingProvisioningService:
    def create_signup_intent(self, **kwargs: object) -> dict[str, object]:
        plan = SimpleNamespace(
            code="team",
            name="Transmuter Team",
            billing_interval=kwargs["billing_interval"],
            currency="usd",
            amount_cents=99900,
            stripe_price_id="price_test_123",
        )
        intent = {"id": "intent_test_123", "tenant_id": "tenant_test_123"}
        return {"intent": intent, "plan": plan}

    def mark_checkout_created(self, **kwargs: object) -> None:
        self.last_mark_checkout_created = kwargs  # type: ignore[attr-defined]


class _FakeStripeAsyncClient:
    def __init__(self, response_payload: dict[str, object]) -> None:
        self.response_payload = response_payload
        self.last_request: dict[str, object] | None = None

    async def __aenter__(self) -> _FakeStripeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, content: str, headers: dict[str, str]) -> object:
        self.last_request = {"url": url, "content": content, "headers": headers}
        return SimpleNamespace(status_code=200, json=lambda: self.response_payload)


class _FakeSupabaseQuery:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def select(self, *args: object, **kwargs: object) -> _FakeSupabaseQuery:
        return self

    def eq(self, *args: object, **kwargs: object) -> _FakeSupabaseQuery:
        return self

    def maybe_single(self) -> _FakeSupabaseQuery:
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self._data)


class _FakeSupabaseAdmin:
    def __init__(self, *, org_data: dict[str, object], subscription_data: dict[str, object]) -> None:
        self.org_data = org_data
        self.subscription_data = subscription_data

    def table(self, name: str) -> _FakeSupabaseQuery:
        if name == "organizations":
            return _FakeSupabaseQuery(self.org_data)
        if name == "tenant_subscriptions":
            return _FakeSupabaseQuery(self.subscription_data)
        return _FakeSupabaseQuery({})


class _FakePlatformAdmin:
    def __init__(self, *, tenant_id: str, slug: str, counts: dict[str, int]) -> None:
        self.org = {"id": tenant_id, "name": "Pilot Blank QA", "slug": slug}
        self.counts = counts
        self.deleted_tables: list[str] = []
        self.auth = SimpleNamespace(
            admin=SimpleNamespace(delete_user=lambda user_id: None),
        )

    def table(self, name: str) -> _FakePlatformQuery:
        return _FakePlatformQuery(self, name)


class _FakePlatformQuery:
    def __init__(self, admin: _FakePlatformAdmin, table_name: str) -> None:
        self._admin = admin
        self._table_name = table_name
        self._operation = "select"
        self._count_requested = False
        self._single = False

    def select(self, *args: object, **kwargs: object) -> _FakePlatformQuery:
        self._operation = "select"
        self._count_requested = kwargs.get("count") == "exact"
        return self

    def delete(self) -> _FakePlatformQuery:
        self._operation = "delete"
        return self

    def eq(self, *args: object, **kwargs: object) -> _FakePlatformQuery:
        return self

    def maybe_single(self) -> _FakePlatformQuery:
        self._single = True
        return self

    def limit(self, *args: object, **kwargs: object) -> _FakePlatformQuery:
        return self

    def execute(self) -> SimpleNamespace:
        if self._table_name == "organizations":
            return self._execute_organizations()
        if self._table_name == "users" and self._operation == "select" and not self._count_requested:
            return SimpleNamespace(data=[], count=0)
        if self._operation == "delete":
            count = self._admin.counts.get(self._table_name, 0)
            self._admin.counts[self._table_name] = 0
            self._admin.deleted_tables.append(self._table_name)
            return SimpleNamespace(data=[{} for _ in range(count)], count=count)
        count = self._admin.counts.get(self._table_name, 0)
        return SimpleNamespace(data=[{"id": f"{self._table_name}-row"}] if count else [], count=count)

    def _execute_organizations(self) -> SimpleNamespace:
        if self._operation != "delete":
            return SimpleNamespace(data=self._admin.org if self._single else [self._admin.org], count=1)
        remaining = {
            table_name: count
            for table_name, count in self._admin.counts.items()
            if count > 0
        }
        if remaining:
            raise AssertionError(f"organization deleted before tenant tables: {remaining}")
        self._admin.deleted_tables.append("organizations")
        return SimpleNamespace(data=[self._admin.org], count=1)


def test_platform_overview_requires_platform_role() -> None:
    admin = get_supabase_admin()
    user_response = admin.table("users").select("id, tenant_id").limit(1).execute()
    user = user_response.data[0] if user_response.data else None
    if user is None:
        pytest.skip("real Supabase user is required for role guard verification")
    assert user is not None

    headers = {
        "Authorization": (
            "Bearer "
            + _mint_token("11111111-1111-1111-1111-111111111111", user["tenant_id"], "transformation_office")
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
