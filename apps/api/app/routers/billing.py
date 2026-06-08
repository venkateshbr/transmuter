from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Annotated
from urllib.parse import urlencode, urljoin, urlsplit

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import CurrentUser, require_role
from app.core.config import settings
from app.core.database import get_supabase_admin
from app.services.billing import BillingProvisioningService, public_plan_catalog

router = APIRouter(prefix="/billing", tags=["billing"])

STRIPE_CHECKOUT_URL = "https://api.stripe.com/v1/checkout/sessions"
STRIPE_PORTAL_URL = "https://api.stripe.com/v1/billing_portal/sessions"
ORGANIZATION_SLUG_PATTERN = r"^[a-z0-9-]+$"
ORGANIZATION_SLUG_MIN_LENGTH = 2
ORGANIZATION_SLUG_MAX_LENGTH = 80


class BillingConfig(BaseModel):
    provider: str
    publishable_key: str
    price_per_user_cents: int | None = None
    currency: str = "usd"
    billing_interval: str = "month"
    plans: list[dict[str, object]] = Field(default_factory=list)
    organization_slug_pattern: str = ORGANIZATION_SLUG_PATTERN
    organization_slug_min_length: int = ORGANIZATION_SLUG_MIN_LENGTH
    organization_slug_max_length: int = ORGANIZATION_SLUG_MAX_LENGTH


class CheckoutSessionRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=200)
    organization_slug: str = Field(
        ...,
        min_length=ORGANIZATION_SLUG_MIN_LENGTH,
        max_length=ORGANIZATION_SLUG_MAX_LENGTH,
        pattern=ORGANIZATION_SLUG_PATTERN,
    )
    admin_display_name: str = Field(..., min_length=2, max_length=120)
    admin_email: EmailStr
    initial_password: str = Field(..., min_length=8, max_length=128)
    planned_user_count: int = Field(..., ge=1, le=5000)
    billing_interval: str = Field(default="month", pattern=r"^(month|year)$")
    success_url: str = Field(..., min_length=1)
    cancel_url: str = Field(..., min_length=1)


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class BillingPortalRequest(BaseModel):
    return_url: str = Field(..., min_length=1)


class BillingPortalResponse(BaseModel):
    portal_url: str


class WebhookResponse(BaseModel):
    received: bool
    event_type: str | None = None
    provisioning_status: str = "not_configured"
    tenant_id: str | None = None
    organization_slug: str | None = None
    initial_admin_user_id: str | None = None


@router.get("/config", response_model=BillingConfig)
async def billing_config() -> BillingConfig:
    return BillingConfig(
        provider=settings.payment_provider or "stripe",
        publishable_key=settings.stripe_publishable_key,
        price_per_user_cents=None,
        plans=public_plan_catalog(),
    )


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: Request,
    body: CheckoutSessionRequest,
) -> CheckoutSessionResponse:
    if (settings.payment_provider or "stripe") != "stripe":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe billing is not enabled",
        )
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe secret key is not configured",
        )

    billing_service = BillingProvisioningService(get_supabase_admin())
    signup = billing_service.create_signup_intent(
        organization_name=body.organization_name,
        organization_slug=body.organization_slug,
        admin_display_name=body.admin_display_name,
        admin_email=str(body.admin_email),
        initial_password=body.initial_password,
        planned_user_count=body.planned_user_count,
        billing_interval=body.billing_interval,
    )
    plan = signup["plan"]
    intent = signup["intent"]
    success_url = _resolve_redirect_url(request, body.success_url)
    cancel_url = _resolve_redirect_url(request, body.cancel_url)

    payload = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "customer_email": str(body.admin_email),
        "line_items[0][quantity]": "1",
        "metadata[signup_intent_id]": intent["id"],
        "metadata[tenant_id]": intent["tenant_id"],
        "metadata[organization_name]": body.organization_name,
        "metadata[organization_slug]": body.organization_slug,
        "metadata[admin_display_name]": body.admin_display_name,
        "metadata[admin_email]": str(body.admin_email),
        "metadata[planned_user_count]": str(body.planned_user_count),
        "metadata[plan_code]": plan.code,
        "metadata[billing_interval]": plan.billing_interval,
        "subscription_data[metadata][signup_intent_id]": intent["id"],
        "subscription_data[metadata][tenant_id]": intent["tenant_id"],
        "subscription_data[metadata][organization_slug]": body.organization_slug,
        "subscription_data[metadata][admin_email]": str(body.admin_email),
    }
    if plan.stripe_price_id:
        payload["line_items[0][price]"] = plan.stripe_price_id
    else:
        payload.update(
            {
                "line_items[0][price_data][currency]": plan.currency,
                "line_items[0][price_data][unit_amount]": str(plan.amount_cents),
                "line_items[0][price_data][recurring][interval]": plan.billing_interval,
                "line_items[0][price_data][product_data][name]": plan.name,
            }
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            STRIPE_CHECKOUT_URL,
            content=urlencode(payload),
            headers={
                "Authorization": f"Bearer {settings.stripe_secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe checkout session could not be created",
        )

    data = response.json()
    billing_service.mark_checkout_created(
        signup_intent_id=intent["id"],
        checkout_session_id=data["id"],
        checkout_url=data["url"],
    )
    return CheckoutSessionResponse(checkout_url=data["url"], session_id=data["id"])


@router.post("/portal-session", response_model=BillingPortalResponse)
async def create_billing_portal_session(
    request: Request,
    body: BillingPortalRequest,
    current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> BillingPortalResponse:
    org = (
        get_supabase_admin()
        .table("organizations")
        .select("settings")
        .eq("id", str(current_user.tenant_id))
        .maybe_single()
        .execute()
    )
    subscription = (
        get_supabase_admin()
        .table("tenant_subscriptions")
        .select("stripe_customer_id")
        .eq("tenant_id", str(current_user.tenant_id))
        .maybe_single()
        .execute()
    )
    billing = ((org.data or {}).get("settings") or {}).get("billing") or {}
    customer_id = (subscription.data or {}).get("stripe_customer_id") if subscription else None
    customer_id = customer_id or billing.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stripe customer is not available yet. Complete checkout first.",
        )
    return_url = _resolve_redirect_url(request, body.return_url)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            STRIPE_PORTAL_URL,
            content=urlencode({"customer": customer_id, "return_url": return_url}),
            headers={
                "Authorization": f"Bearer {settings.stripe_secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe billing portal session could not be created",
        )
    data = response.json()
    return BillingPortalResponse(portal_url=data["url"])


@router.post("/webhook", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> WebhookResponse:
    payload = await request.body()
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured",
        )
    _verify_stripe_signature(payload, stripe_signature)

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    event_type = event.get("type")
    provisioning: dict[str, str] = {}
    provisioning_status = "ignored"
    if event_type == "checkout.session.completed":
        session = (event.get("data") or {}).get("object") or {}
        provisioning = BillingProvisioningService(get_supabase_admin()).provision_checkout_session(
            session
        )
        provisioning_status = provisioning["provisioning_status"]
    elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
        subscription = (event.get("data") or {}).get("object") or {}
        provisioning = BillingProvisioningService(get_supabase_admin()).sync_subscription_event(
            subscription
        )
        provisioning_status = provisioning["provisioning_status"]

    return WebhookResponse(
        received=True,
        event_type=event_type,
        provisioning_status=provisioning_status,
        tenant_id=provisioning.get("tenant_id"),
        organization_slug=provisioning.get("organization_slug"),
        initial_admin_user_id=provisioning.get("initial_admin_user_id"),
    )


def _verify_stripe_signature(payload: bytes, header: str | None) -> None:
    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe signature"
        )

    parts = {}
    for item in header.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts.setdefault(key, []).append(value)

    timestamps = parts.get("t") or []
    signatures = parts.get("v1") or []
    if not timestamps or not signatures:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature"
        )

    timestamp = timestamps[0]
    try:
        timestamp_int = int(timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp"
        ) from exc

    if abs(time.time() - timestamp_int) > 300:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Stale Stripe signature"
        )

    signed_payload = timestamp.encode() + b"." + payload
    expected = hmac.new(
        settings.stripe_webhook_secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature"
        )


def _resolve_redirect_url(request: Request, value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URL must not be empty",
        )

    parsed = urlsplit(candidate)
    if parsed.scheme and parsed.netloc:
        return candidate

    base_url = request.headers.get("origin") or str(request.base_url)
    if not base_url.endswith("/"):
        base_url = f"{base_url}/"
    return urljoin(base_url, candidate)
