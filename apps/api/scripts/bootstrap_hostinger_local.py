"""Bootstrap Hostinger local Supabase with platform/admin shell data only.

This script intentionally does not seed operational portfolio data such as
initiatives, meetings, action items, financial entries, or cost lines.

Usage:
    cd apps/api
    HOSTINGER_ADMIN_PASSWORD='...' uv run python scripts/bootstrap_hostinger_local.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from supabase import Client

repo_root = Path(__file__).resolve().parents[3]
api_root = Path(__file__).resolve().parents[1]
load_dotenv(repo_root / ".env")
load_dotenv(api_root / ".env", override=True)

from app.core.config import settings  # noqa: E402
from app.core.database import get_supabase_admin  # noqa: E402
from app.services.tenant_bootstrap import TenantBootstrapService  # noqa: E402


@dataclass(frozen=True)
class BootstrapConfig:
    tenant_name: str
    tenant_slug: str
    tenant_admin_email: str
    tenant_admin_name: str
    tenant_admin_password: str
    platform_admin_email: str
    platform_admin_password: str
    planned_user_count: int


def load_bootstrap_config() -> BootstrapConfig:
    shared_password = os.environ.get("HOSTINGER_ADMIN_PASSWORD", "")
    tenant_admin_password = os.environ.get("HOSTINGER_TENANT_ADMIN_PASSWORD") or shared_password
    platform_admin_password = os.environ.get("HOSTINGER_PLATFORM_ADMIN_PASSWORD") or shared_password
    if not tenant_admin_password or not platform_admin_password:
        raise RuntimeError(
            "Set HOSTINGER_ADMIN_PASSWORD or both HOSTINGER_TENANT_ADMIN_PASSWORD and "
            "HOSTINGER_PLATFORM_ADMIN_PASSWORD before running bootstrap."
        )

    platform_email = os.environ.get("HOSTINGER_PLATFORM_ADMIN_EMAIL") or _first_platform_email()
    return BootstrapConfig(
        tenant_name=os.environ.get("HOSTINGER_BOOTSTRAP_TENANT_NAME", "Transmuter Platform Admin"),
        tenant_slug=os.environ.get("HOSTINGER_BOOTSTRAP_TENANT_SLUG", "transmuter-admin"),
        tenant_admin_email=os.environ.get("HOSTINGER_TENANT_ADMIN_EMAIL", "admin@ishirock.dev"),
        tenant_admin_name=os.environ.get("HOSTINGER_TENANT_ADMIN_NAME", "Tenant Admin"),
        tenant_admin_password=tenant_admin_password,
        platform_admin_email=platform_email,
        platform_admin_password=platform_admin_password,
        planned_user_count=int(os.environ.get("HOSTINGER_BOOTSTRAP_PLANNED_USERS", "1")),
    )


def bootstrap(client: Client, config: BootstrapConfig) -> dict[str, Any]:
    platform_user_id = ensure_auth_user(
        client,
        email=config.platform_admin_email,
        password=config.platform_admin_password,
        user_metadata={"role": "platform_admin"},
        app_metadata={"role": "platform_admin", "platform_admin": True},
    )
    tenant = ensure_organization(client, config)
    tenant_id = tenant["id"]
    tenant_user_id = ensure_auth_user(
        client,
        email=config.tenant_admin_email,
        password=config.tenant_admin_password,
        user_metadata={
            "tenant_id": tenant_id,
            "role": "transformation_office",
            "display_name": config.tenant_admin_name,
        },
        app_metadata={},
    )
    ensure_tenant_admin_user(client, tenant_id, tenant_user_id, config)
    plans = ensure_subscription_plans(client, tenant_id)
    subscription = ensure_tenant_subscription(client, tenant_id, plans[0], config)
    master_config = TenantBootstrapService(client).bootstrap_tenant(tenant_id)

    return {
        "supabase_target": settings.supabase_target,
        "tenant_id": tenant_id,
        "tenant_slug": config.tenant_slug,
        "platform_admin_user_id": platform_user_id,
        "tenant_admin_user_id": tenant_user_id,
        "subscription_plan_count": len(plans),
        "tenant_subscription_id": subscription.get("id"),
        "master_config": master_config,
    }


def ensure_auth_user(
    client: Client,
    *,
    email: str,
    password: str,
    user_metadata: dict[str, Any],
    app_metadata: dict[str, Any],
) -> str:
    existing_user_id = find_auth_user_id_by_email(client, email)
    payload = {
        "email_confirm": True,
        "password": password,
        "user_metadata": user_metadata,
        "app_metadata": app_metadata,
    }
    if existing_user_id:
        client.auth.admin.update_user_by_id(existing_user_id, payload)
        return existing_user_id

    response = client.auth.admin.create_user({"email": email, **payload})
    user = getattr(response, "user", None)
    user_id = getattr(user, "id", None) or getattr(response, "id", None)
    if not user_id:
        raise RuntimeError(f"Supabase Auth did not return a user id for {email}.")
    return str(user_id)


def find_auth_user_id_by_email(client: Client, email: str) -> str | None:
    page = 1
    per_page = 100
    while True:
        users = client.auth.admin.list_users(page=page, per_page=per_page)
        for user in users:
            if (getattr(user, "email", "") or "").lower() == email.lower():
                return str(user.id)
        if len(users) < per_page:
            return None
        page += 1


def ensure_organization(client: Client, config: BootstrapConfig) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    settings_payload = {
        "billing": {
            "provider": "stripe",
            "subscription_status": "not_configured",
            "planned_user_count": config.planned_user_count,
        },
        "bootstrap": {"source": "bootstrap_hostinger_local.py"},
    }
    existing = (
        client.table("organizations")
        .select("*")
        .eq("slug", config.tenant_slug)
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        current_settings = existing.data.get("settings") or {}
        payload = {
            "name": config.tenant_name,
            "settings": {
                **current_settings,
                "billing": {
                    **(current_settings.get("billing") or {}),
                    **settings_payload["billing"],
                },
                "bootstrap": settings_payload["bootstrap"],
            },
            "updated_at": now,
        }
        result = (
            client.table("organizations").update(payload).eq("id", existing.data["id"]).execute()
        )
        return result.data[0] if result.data else {**existing.data, **payload}

    result = (
        client.table("organizations")
        .insert(
            {
                "id": str(uuid4()),
                "name": config.tenant_name,
                "slug": config.tenant_slug,
                "settings": settings_payload,
            }
        )
        .execute()
    )
    return result.data[0]


def ensure_tenant_admin_user(
    client: Client,
    tenant_id: str,
    user_id: str,
    config: BootstrapConfig,
) -> None:
    payload = {
        "tenant_id": tenant_id,
        "email": config.tenant_admin_email,
        "display_name": config.tenant_admin_name,
        "role": "transformation_office",
        "status": "active",
        "onboarding_completed": True,
        "must_change_password": False,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    existing = (
        client.table("users").select("id").eq("tenant_id", tenant_id).eq("id", user_id).maybe_single().execute()
    )
    if existing and existing.data:
        client.table("users").update(payload).eq("tenant_id", tenant_id).eq("id", user_id).execute()
        return
    client.table("users").insert({"id": user_id, **payload}).execute()


def ensure_subscription_plans(client: Client, tenant_id: str) -> list[dict[str, Any]]:
    plans = [
        ("team", "Transmuter Team", 1, 50, 99900, "month", settings.stripe_price_team_monthly),
        ("team", "Transmuter Team", 1, 50, 999000, "year", settings.stripe_price_team_annual),
        (
            "business",
            "Transmuter Business",
            51,
            100,
            199900,
            "month",
            settings.stripe_price_business_monthly,
        ),
        (
            "business",
            "Transmuter Business",
            51,
            100,
            1999000,
            "year",
            settings.stripe_price_business_annual,
        ),
        ("enterprise", "Transmuter Enterprise", 101, None, None, "custom", ""),
    ]
    return [
        upsert_subscription_plan(
            client,
            tenant_id=tenant_id,
            code=code,
            name=name,
            user_limit_min=user_limit_min,
            user_limit_max=user_limit_max,
            amount_cents=amount_cents,
            billing_interval=billing_interval,
            stripe_price_id=stripe_price_id,
        )
        for (
            code,
            name,
            user_limit_min,
            user_limit_max,
            amount_cents,
            billing_interval,
            stripe_price_id,
        ) in plans
    ]


def upsert_subscription_plan(
    client: Client,
    *,
    tenant_id: str,
    code: str,
    name: str,
    user_limit_min: int,
    user_limit_max: int | None,
    amount_cents: int | None,
    billing_interval: str,
    stripe_price_id: str,
) -> dict[str, Any]:
    payload = {
        "tenant_id": tenant_id,
        "code": code,
        "name": name,
        "user_limit_min": user_limit_min,
        "user_limit_max": user_limit_max,
        "amount_cents": amount_cents,
        "currency": "usd",
        "billing_interval": billing_interval,
        "stripe_price_id": stripe_price_id or None,
        "is_active": True,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    existing = (
        client.table("subscription_plans")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("code", code)
        .eq("billing_interval", billing_interval)
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        result = (
            client.table("subscription_plans").update(payload).eq("id", existing.data["id"]).execute()
        )
        return result.data[0] if result.data else {**existing.data, **payload}
    result = client.table("subscription_plans").insert(payload).execute()
    return result.data[0]


def ensure_tenant_subscription(
    client: Client,
    tenant_id: str,
    plan: dict[str, Any],
    config: BootstrapConfig,
) -> dict[str, Any]:
    payload = {
        "tenant_id": tenant_id,
        "plan_id": plan["id"],
        "provider": "stripe",
        "status": "not_configured",
        "planned_user_count": config.planned_user_count,
        "metadata": {"bootstrap": "hostinger_local"},
        "updated_at": datetime.now(UTC).isoformat(),
    }
    existing = (
        client.table("tenant_subscriptions")
        .select("*")
        .eq("tenant_id", tenant_id)
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        result = (
            client.table("tenant_subscriptions")
            .update(payload)
            .eq("id", existing.data["id"])
            .execute()
        )
        return result.data[0] if result.data else {**existing.data, **payload}
    result = client.table("tenant_subscriptions").insert(payload).execute()
    return result.data[0]


def _first_platform_email() -> str:
    emails = [email.strip() for email in settings.platform_admin_emails.split(",") if email.strip()]
    return emails[0] if emails else "operator@example.com"


def main() -> int:
    config = load_bootstrap_config()
    if config.platform_admin_email.lower() not in {
        email.strip().lower()
        for email in settings.platform_admin_emails.split(",")
        if email.strip()
    }:
        print(
            "WARNING: HOSTINGER_PLATFORM_ADMIN_EMAIL is not present in PLATFORM_ADMIN_EMAILS; "
            "platform login will be rejected until the env allowlist is updated.",
            file=sys.stderr,
        )

    result = bootstrap(get_supabase_admin(), config)
    print("Hostinger local Supabase bootstrap completed.")
    print(f"Supabase target: {result['supabase_target']}")
    print(f"Tenant: {result['tenant_slug']} ({result['tenant_id']})")
    print(f"Subscription plans: {result['subscription_plan_count']}")
    print(f"Master config: {result['master_config']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
