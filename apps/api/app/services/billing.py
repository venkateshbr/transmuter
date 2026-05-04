"""Billing service — Stripe checkout and tenant provisioning."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass
from secrets import token_urlsafe
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import EmailStr, TypeAdapter
from supabase import Client
from supabase_auth.errors import AuthApiError

from app.core.config import settings


@dataclass(frozen=True)
class BillingPlan:
    code: str
    name: str
    user_limit_min: int
    user_limit_max: int | None
    amount_cents: int | None
    currency: str
    billing_interval: str
    stripe_price_id: str


def select_billing_plan(planned_user_count: int, billing_interval: str = "month") -> BillingPlan:
    if billing_interval not in {"month", "year"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported billing interval")
    if planned_user_count <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Planned users must be greater than zero")
    if planned_user_count <= 50:
        return BillingPlan(
            code="team",
            name="Transmuter Team",
            user_limit_min=1,
            user_limit_max=50,
            amount_cents=99900 if billing_interval == "month" else 999000,
            currency="usd",
            billing_interval=billing_interval,
            stripe_price_id=settings.stripe_price_team_monthly if billing_interval == "month" else settings.stripe_price_team_annual,
        )
    if planned_user_count <= 100:
        return BillingPlan(
            code="business",
            name="Transmuter Business",
            user_limit_min=51,
            user_limit_max=100,
            amount_cents=199900 if billing_interval == "month" else 1999000,
            currency="usd",
            billing_interval=billing_interval,
            stripe_price_id=settings.stripe_price_business_monthly if billing_interval == "month" else settings.stripe_price_business_annual,
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Plans above 100 users require enterprise pricing. Please contact sales.",
    )


def public_plan_catalog() -> list[dict[str, Any]]:
    return [
        {
            "code": "team",
            "name": "Transmuter Team",
            "user_limit_min": 1,
            "user_limit_max": 50,
            "monthly_amount_cents": 99900,
            "annual_amount_cents": 999000,
            "currency": "usd",
            "checkout_enabled": True,
        },
        {
            "code": "business",
            "name": "Transmuter Business",
            "user_limit_min": 51,
            "user_limit_max": 100,
            "monthly_amount_cents": 199900,
            "annual_amount_cents": 1999000,
            "currency": "usd",
            "checkout_enabled": True,
        },
        {
            "code": "enterprise",
            "name": "Transmuter Enterprise",
            "user_limit_min": 101,
            "user_limit_max": None,
            "monthly_amount_cents": None,
            "annual_amount_cents": None,
            "currency": "usd",
            "checkout_enabled": False,
        },
    ]


def stripe_price_configuration() -> list[dict[str, Any]]:
    return [
        {
            "env_key": "STRIPE_PRICE_TEAM_MONTHLY",
            "plan_code": "team",
            "plan_name": "Transmuter Team",
            "billing_interval": "month",
            "amount_cents": 99900,
            "currency": "usd",
            "price_id": settings.stripe_price_team_monthly or None,
            "configured": bool(settings.stripe_price_team_monthly),
        },
        {
            "env_key": "STRIPE_PRICE_TEAM_ANNUAL",
            "plan_code": "team",
            "plan_name": "Transmuter Team",
            "billing_interval": "year",
            "amount_cents": 999000,
            "currency": "usd",
            "price_id": settings.stripe_price_team_annual or None,
            "configured": bool(settings.stripe_price_team_annual),
        },
        {
            "env_key": "STRIPE_PRICE_BUSINESS_MONTHLY",
            "plan_code": "business",
            "plan_name": "Transmuter Business",
            "billing_interval": "month",
            "amount_cents": 199900,
            "currency": "usd",
            "price_id": settings.stripe_price_business_monthly or None,
            "configured": bool(settings.stripe_price_business_monthly),
        },
        {
            "env_key": "STRIPE_PRICE_BUSINESS_ANNUAL",
            "plan_code": "business",
            "plan_name": "Transmuter Business",
            "billing_interval": "year",
            "amount_cents": 1999000,
            "currency": "usd",
            "price_id": settings.stripe_price_business_annual or None,
            "configured": bool(settings.stripe_price_business_annual),
        },
    ]


class BillingProvisioningService:
    def __init__(self, client: Client) -> None:
        self._client = client

    def create_signup_intent(
        self,
        *,
        organization_name: str,
        organization_slug: str,
        admin_display_name: str,
        admin_email: str,
        planned_user_count: int,
        billing_interval: str = "month",
    ) -> dict[str, Any]:
        plan = select_billing_plan(planned_user_count, billing_interval)
        org = self._ensure_pending_organization(
            name=organization_name,
            slug=organization_slug,
            planned_user_count=planned_user_count,
            plan=plan,
        )
        plan_record = self._ensure_subscription_plan(tenant_id=org["id"], plan=plan)
        now = datetime.now(UTC).isoformat()
        result = (
            self._client.table("signup_intents")
            .insert(
                {
                    "tenant_id": org["id"],
                    "organization_name": organization_name,
                    "organization_slug": organization_slug,
                    "admin_email": str(self._email(admin_email)),
                    "admin_display_name": admin_display_name,
                    "planned_user_count": planned_user_count,
                    "plan_code": plan.code,
                    "billing_interval": plan.billing_interval,
                    "status": "pending_checkout",
                    "metadata": {"subscription_plan_id": plan_record["id"]},
                    "updated_at": now,
                }
            )
            .execute()
        )
        intent = result.data[0]
        return {"intent": intent, "organization": org, "plan": plan, "plan_record": plan_record}

    def mark_checkout_created(
        self,
        *,
        signup_intent_id: str,
        checkout_session_id: str,
        checkout_url: str,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        intent = self._get_signup_intent(signup_intent_id)
        self._client.table("signup_intents").update(
            {
                "status": "checkout_created",
                "stripe_checkout_session_id": checkout_session_id,
                "metadata": {**(intent.get("metadata") or {}), "checkout_url": checkout_url},
                "updated_at": now,
            }
        ).eq("id", signup_intent_id).execute()

    def provision_checkout_session(self, session: dict[str, Any]) -> dict[str, Any]:
        metadata = session.get("metadata") or {}
        signup_intent_id = str(metadata.get("signup_intent_id") or "").strip()
        intent = self._get_signup_intent(signup_intent_id) if signup_intent_id else None
        organization_name = (intent or {}).get("organization_name") or self._require_metadata(metadata, "organization_name")
        organization_slug = (intent or {}).get("organization_slug") or self._require_metadata(metadata, "organization_slug")
        admin_display_name = (intent or {}).get("admin_display_name") or self._require_metadata(metadata, "admin_display_name")
        admin_email = self._email((intent or {}).get("admin_email") or self._require_metadata(metadata, "admin_email"))
        planned_user_count = int((intent or {}).get("planned_user_count") or self._int_metadata(metadata, "planned_user_count", default=1))

        org = self._ensure_organization(
            name=organization_name,
            slug=organization_slug,
            session=session,
            planned_user_count=planned_user_count,
            tenant_id=(intent or {}).get("tenant_id"),
        )
        user_id = self._ensure_initial_admin(
            tenant_id=org["id"],
            email=str(admin_email),
            display_name=admin_display_name,
        )
        subscription = self._upsert_tenant_subscription(
            tenant_id=org["id"],
            session=session,
            signup_intent=intent,
            planned_user_count=planned_user_count,
        )
        if intent:
            self._client.table("signup_intents").update(
                {
                    "status": "provisioned",
                    "stripe_customer_id": session.get("customer"),
                    "stripe_subscription_id": session.get("subscription"),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", intent["id"]).execute()
        return {
            "tenant_id": org["id"],
            "organization_slug": org["slug"],
            "initial_admin_user_id": user_id,
            "tenant_subscription_id": subscription["id"],
            "provisioning_status": "provisioned",
        }

    def sync_subscription_event(self, subscription: dict[str, Any]) -> dict[str, Any]:
        subscription_id = str(subscription.get("id") or "")
        customer_id = str(subscription.get("customer") or "")
        if not subscription_id and not customer_id:
            return {"provisioning_status": "ignored"}

        query = self._client.table("tenant_subscriptions").select("*")
        existing = None
        if subscription_id:
            response = query.eq("stripe_subscription_id", subscription_id).maybe_single().execute()
            existing = response.data if response else None
        if not existing and customer_id:
            response = (
                self._client.table("tenant_subscriptions")
                .select("*")
                .eq("stripe_customer_id", customer_id)
                .maybe_single()
                .execute()
            )
            existing = response.data if response else None
        if not existing:
            return {"provisioning_status": "subscription_not_matched"}

        update = {
            "status": subscription.get("status") or existing.get("status"),
            "stripe_subscription_id": subscription_id or existing.get("stripe_subscription_id"),
            "stripe_customer_id": customer_id or existing.get("stripe_customer_id"),
            "current_period_end": self._stripe_timestamp(subscription.get("current_period_end")),
            "cancel_at_period_end": bool(subscription.get("cancel_at_period_end") or False),
            "metadata": {**(existing.get("metadata") or {}), "last_subscription_event": subscription},
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = (
            self._client.table("tenant_subscriptions")
            .update(update)
            .eq("id", existing["id"])
            .execute()
        )
        return {
            "provisioning_status": "subscription_synced",
            "tenant_id": existing["tenant_id"],
            "tenant_subscription_id": (result.data[0] if result.data else existing)["id"],
        }

    def _ensure_pending_organization(
        self,
        *,
        name: str,
        slug: str,
        planned_user_count: int,
        plan: BillingPlan,
    ) -> dict[str, Any]:
        existing = (
            self._client.table("organizations")
            .select("*")
            .eq("slug", slug)
            .maybe_single()
            .execute()
        )
        now = datetime.now(UTC).isoformat()
        billing_settings = self._billing_settings(
            session={},
            planned_user_count=planned_user_count,
            subscription_status="pending_checkout",
            plan=plan,
        )
        if existing and existing.data:
            org = existing.data
            users = (
                self._client.table("users")
                .select("id", count="exact")
                .eq("tenant_id", org["id"])
                .execute()
            )
            subscription = (
                self._client.table("tenant_subscriptions")
                .select("id,status")
                .eq("tenant_id", org["id"])
                .maybe_single()
                .execute()
            )
            if (users.count or 0) > 0 or (subscription and subscription.data and subscription.data.get("status") not in {"not_configured", "pending_checkout"}):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug is already in use")
            settings = org.get("settings") or {}
            settings["billing"] = {**settings.get("billing", {}), **billing_settings}
            result = (
                self._client.table("organizations")
                .update({"name": name, "settings": settings, "updated_at": now})
                .eq("id", org["id"])
                .execute()
            )
            return result.data[0] if result.data else {**org, "settings": settings}

        org_id = str(uuid4())
        result = (
            self._client.table("organizations")
            .insert(
                {
                    "id": org_id,
                    "name": name,
                    "slug": slug,
                    "settings": {
                        "billing": billing_settings,
                        "nudge_overdue_days": 7,
                        "nudge_nuclear_days": 14,
                    },
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {"id": org_id, "name": name, "slug": slug}

    def _ensure_subscription_plan(self, *, tenant_id: str, plan: BillingPlan) -> dict[str, Any]:
        payload = {
            "tenant_id": tenant_id,
            "code": plan.code,
            "name": plan.name,
            "user_limit_min": plan.user_limit_min,
            "user_limit_max": plan.user_limit_max,
            "amount_cents": plan.amount_cents,
            "currency": plan.currency,
            "billing_interval": plan.billing_interval,
            "stripe_price_id": plan.stripe_price_id or None,
            "is_active": True,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        existing = (
            self._client.table("subscription_plans")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("code", plan.code)
            .eq("billing_interval", plan.billing_interval)
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            result = (
                self._client.table("subscription_plans")
                .update(payload)
                .eq("id", existing.data["id"])
                .execute()
            )
            return result.data[0] if result.data else {**existing.data, **payload}
        result = self._client.table("subscription_plans").insert(payload).execute()
        return result.data[0]

    def _get_signup_intent(self, signup_intent_id: str) -> dict[str, Any] | None:
        if not signup_intent_id:
            return None
        response = (
            self._client.table("signup_intents")
            .select("*")
            .eq("id", signup_intent_id)
            .maybe_single()
            .execute()
        )
        return response.data if response else None

    def _ensure_organization(
        self,
        *,
        name: str,
        slug: str,
        session: dict[str, Any],
        planned_user_count: int,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        query = self._client.table("organizations").select("*")
        existing = query.eq("id", tenant_id).maybe_single().execute() if tenant_id else query.eq("slug", slug).maybe_single().execute()
        now = datetime.now(UTC).isoformat()
        billing_settings = self._billing_settings(
            session=session,
            planned_user_count=planned_user_count,
            subscription_status=self._subscription_status(session),
        )

        if existing and existing.data:
            org = existing.data
            settings = org.get("settings") or {}
            settings["billing"] = {**settings.get("billing", {}), **billing_settings}
            result = (
                self._client.table("organizations")
                .update({"name": name, "settings": settings, "updated_at": now})
                .eq("id", org["id"])
                .execute()
            )
            return result.data[0] if result.data else {**org, "settings": settings}

        org_id = str(uuid4())
        result = (
            self._client.table("organizations")
            .insert(
                {
                    "id": org_id,
                    "name": name,
                    "slug": slug,
                    "settings": {
                        "billing": billing_settings,
                        "nudge_overdue_days": 7,
                        "nudge_nuclear_days": 14,
                    },
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {"id": org_id, "name": name, "slug": slug}

    def _upsert_tenant_subscription(
        self,
        *,
        tenant_id: str,
        session: dict[str, Any],
        signup_intent: dict[str, Any] | None,
        planned_user_count: int,
    ) -> dict[str, Any]:
        plan_id = ((signup_intent or {}).get("metadata") or {}).get("subscription_plan_id")
        payload = {
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "signup_intent_id": (signup_intent or {}).get("id"),
            "provider": "stripe",
            "status": self._subscription_status(session),
            "checkout_status": session.get("status"),
            "payment_status": session.get("payment_status"),
            "planned_user_count": planned_user_count,
            "stripe_customer_id": session.get("customer"),
            "stripe_subscription_id": session.get("subscription"),
            "stripe_checkout_session_id": session.get("id"),
            "metadata": {"checkout_session": session},
            "updated_at": datetime.now(UTC).isoformat(),
        }
        existing = (
            self._client.table("tenant_subscriptions")
            .select("*")
            .eq("tenant_id", tenant_id)
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            result = (
                self._client.table("tenant_subscriptions")
                .update(payload)
                .eq("id", existing.data["id"])
                .execute()
            )
            return result.data[0] if result.data else {**existing.data, **payload}
        result = self._client.table("tenant_subscriptions").insert(payload).execute()
        return result.data[0]

    def _ensure_initial_admin(self, *, tenant_id: str, email: str, display_name: str) -> str:
        existing_user = (
            self._client.table("users")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        if existing_user and existing_user.data:
            user_id = existing_user.data["id"]
            self._client.table("users").update(
                {
                    "display_name": display_name,
                    "role": "transformation_office",
                    "status": "active",
                    "onboarding_completed": False,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ).eq("tenant_id", tenant_id).eq("id", user_id).execute()
            return user_id

        email_owner = (
            self._client.table("users")
            .select("id, tenant_id")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        if email_owner and email_owner.data and email_owner.data.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Initial admin email already belongs to another tenant",
            )

        auth_user_id = self._ensure_auth_invite_user(
            tenant_id=tenant_id,
            email=email,
            display_name=display_name,
        )
        self._client.table("users").insert(
            {
                "id": auth_user_id,
                "tenant_id": tenant_id,
                "email": email,
                "display_name": display_name,
                "title": "Initial Admin",
                "role": "transformation_office",
                "status": "active",
                "onboarding_completed": False,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
        return auth_user_id

    def _ensure_auth_invite_user(self, *, tenant_id: str, email: str, display_name: str) -> str:
        existing_id = self._find_auth_user_id(email)
        metadata = {
            "tenant_id": tenant_id,
            "role": "transformation_office",
            "display_name": display_name,
        }
        if existing_id:
            self._client.auth.admin.update_user_by_id(
                existing_id,
                {"user_metadata": metadata},
            )
            return existing_id

        try:
            response = self._client.auth.admin.invite_user_by_email(
                email,
                {"data": metadata},
            )
        except AuthApiError as exc:
            return self._create_deferred_auth_invite(
                tenant_id=tenant_id,
                email=email,
                display_name=display_name,
                reason=exc.message,
            )
        return str(response.user.id)

    def _create_deferred_auth_invite(
        self,
        *,
        tenant_id: str,
        email: str,
        display_name: str,
        reason: str,
    ) -> str:
        response = self._client.auth.admin.create_user(
            {
                "email": email,
                "password": f"TransmuterInvite{token_urlsafe(24)}!",
                "email_confirm": False,
                "user_metadata": {
                    "tenant_id": tenant_id,
                    "role": "transformation_office",
                    "display_name": display_name,
                    "invite_delivery_status": "deferred",
                    "invite_delivery_reason": reason[:160],
                },
            }
        )
        return str(response.user.id)

    def _find_auth_user_id(self, email: str) -> str | None:
        page = 1
        per_page = 100
        while True:
            users = self._client.auth.admin.list_users(page=page, per_page=per_page)
            for user in users:
                if getattr(user, "email", None) == email:
                    return str(user.id)
            if len(users) < per_page:
                return None
            page += 1

    @staticmethod
    def _require_metadata(metadata: dict[str, Any], key: str) -> str:
        value = str(metadata.get(key) or "").strip()
        if not value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing checkout metadata: {key}",
            )
        return value

    @staticmethod
    def _int_metadata(metadata: dict[str, Any], key: str, *, default: int) -> int:
        try:
            return max(1, int(metadata.get(key) or default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _email(value: str) -> EmailStr:
        return TypeAdapter(EmailStr).validate_python(value)

    @staticmethod
    def _subscription_status(session: dict[str, Any]) -> str:
        if session.get("payment_status") == "paid" and session.get("subscription"):
            return "active"
        return "pending_stripe_sync"

    @staticmethod
    def _stripe_timestamp(value: Any) -> str | None:
        try:
            return datetime.fromtimestamp(int(value), UTC).isoformat()
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _billing_settings(
        *,
        session: dict[str, Any],
        planned_user_count: int,
        subscription_status: str,
        plan: BillingPlan | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        return {
            "provider": "stripe",
            "checkout_session_id": session.get("id"),
            "customer_id": session.get("customer"),
            "subscription_id": session.get("subscription"),
            "subscription_status": subscription_status,
            "checkout_status": session.get("status"),
            "payment_status": session.get("payment_status"),
            "planned_user_count": planned_user_count,
            "plan_code": plan.code if plan else None,
            "plan_name": plan.name if plan else None,
            "amount_cents": plan.amount_cents if plan else None,
            "price_per_user_cents": None,
            "currency": (plan.currency if plan else "usd"),
            "billing_interval": (plan.billing_interval if plan else "month"),
            "last_event_at": now,
        }
