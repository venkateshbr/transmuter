"""Seed the guarded five-tenant dev acceptance portfolio.

Usage:
    cd apps/api
    TRANSMUTER_MULTI_TENANT_PASSWORD=... HOSTINGER_API_KEY=... \
      uv run python scripts/seed_five_tenant_transformation_program.py \
        --environment dev \
        --hostinger-project transmuter-dev-hostinger \
        --confirm seed-five-tenant-dev-program
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from dotenv import dotenv_values, load_dotenv

from scripts.multi_tenant_transformation_profiles import (
    COMPANY_PROFILES,
    CompanyProfile,
    build_profile_initiative_rows,
)
from scripts.seed_operating_model_users import ROLES

DEV_APP_URL = "https://transmuter-dev.ishirock.tech"
DEV_HOSTINGER_PROJECT = "transmuter-dev-hostinger"
DEV_SCHEMA = "transmuter_dev"
DEV_SUPABASE_URL = "https://supabase.ishirock.tech"
HOSTINGER_API_ORIGIN = "https://developers.hostinger.com/api"
HTTP_USER_AGENT = "transmuter-five-tenant-dev-fixture/1.0"
CONFIRMATION = "seed-five-tenant-dev-program"
FIXTURE_OWNER = "five-tenant-qa-20260712"


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("dev",), required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--hostinger-project")
    parser.add_argument("--hostinger-vps-id", default=os.environ.get("HOSTINGER_VPS_ID", "1695814"))
    parser.add_argument("--env-file")
    parser.add_argument("--manifest")
    return parser.parse_args()


def load_runtime_environment(args: argparse.Namespace) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=repo_root / ".env", override=False)
    if args.env_file:
        load_dotenv(dotenv_path=args.env_file, override=True)
    if args.hostinger_project:
        if args.hostinger_project != DEV_HOSTINGER_PROJECT:
            raise RuntimeError(
                f"Only Hostinger project {DEV_HOSTINGER_PROJECT!r} is allowed for this fixture"
            )
        environment = fetch_hostinger_environment_safely(
            args.hostinger_project, args.hostinger_vps_id
        )
        for key, value in dotenv_values(stream=StringIO(environment)).items():
            if value is not None:
                os.environ[key] = value


def fetch_hostinger_environment_safely(project_name: str, vps_id: str) -> str:
    if project_name != DEV_HOSTINGER_PROJECT or not vps_id.isdigit():
        raise RuntimeError("Hostinger project or VPS identifier is not the reviewed dev target")
    token = os.environ.get("HOSTINGER_API_TOKEN") or os.environ.get("HOSTINGER_API_KEY")
    if not token:
        raise RuntimeError("HOSTINGER_API_KEY or HOSTINGER_API_TOKEN is required")
    request = Request(
        f"{HOSTINGER_API_ORIGIN}/vps/v1/virtual-machines/{vps_id}/docker/{project_name}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": HTTP_USER_AGENT,
        },
    )
    try:
        with build_opener(_NoRedirectHandler()).open(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Hostinger project environment lookup failed") from None
    environment = str(payload.get("environment") or "")
    if not environment:
        raise RuntimeError(f"Hostinger project {project_name!r} returned no environment")
    return environment


def assert_dev_target(args: argparse.Namespace) -> None:
    if args.confirm != CONFIRMATION:
        raise RuntimeError(f"--confirm must exactly equal {CONFIRMATION!r}")
    runtime_environment = (
        (os.environ.get("TRANSMUTER_ENVIRONMENT") or os.environ.get("ENVIRONMENT") or "")
        .strip()
        .lower()
    )
    if runtime_environment not in {"dev", "development"}:
        raise RuntimeError(
            "TRANSMUTER_ENVIRONMENT/ENVIRONMENT must identify the development environment"
        )
    schema = (os.environ.get("SUPABASE_SCHEMA") or os.environ.get("DB_SCHEMA") or "").strip()
    if schema != DEV_SCHEMA:
        raise RuntimeError(f"Refusing seed outside Supabase schema {DEV_SCHEMA!r}; got {schema!r}")
    app_url = (os.environ.get("APP_PUBLIC_URL") or "").rstrip("/")
    if app_url != DEV_APP_URL:
        raise RuntimeError(f"Refusing seed outside {DEV_APP_URL!r}; got {app_url!r}")
    supabase_target = (os.environ.get("SUPABASE_TARGET") or "").strip().lower()
    supabase_url = (
        os.environ.get("SUPABASE_LOCAL_URL") or os.environ.get("SUPABASE_URL") or ""
    ).rstrip("/")
    if supabase_target != "local" or supabase_url != DEV_SUPABASE_URL:
        raise RuntimeError(
            f"Dev seed requires SUPABASE_TARGET=local and endpoint {DEV_SUPABASE_URL!r}"
        )


def required_password() -> str:
    password = os.environ.get("TRANSMUTER_MULTI_TENANT_PASSWORD", "")
    if len(password) < 12:
        raise RuntimeError("TRANSMUTER_MULTI_TENANT_PASSWORD must be at least 12 characters")
    return password


def _existing_tenant(client: Any, slug: str) -> dict[str, Any] | None:
    result = (
        client.table("organizations")
        .select("id,slug,settings")
        .eq("slug", slug)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return None
    return dict(result.data)


def _existing_tenant_id(client: Any, slug: str) -> str | None:
    row = _existing_tenant(client, slug)
    return str(row["id"]) if row else None


def _auth_user(client: Any, email: str) -> Any | None:
    page = 1
    while True:
        users = client.auth.admin.list_users(page=page, per_page=100)
        if not users:
            return None
        for user in users:
            if (getattr(user, "email", "") or "").lower() == email.lower():
                return user
        if len(users) < 100:
            return None
        page += 1


def assert_auth_email_safe(
    client: Any,
    *,
    email: str,
    expected_tenant_id: str | None,
    expected_role: str,
) -> None:
    auth_user = _auth_user(client, email)
    if auth_user is None:
        return
    if expected_tenant_id is None:
        raise RuntimeError(f"Existing auth email {email!r} has no owned fixture tenant")
    from scripts import seed_enterprise_transformation_scenario as enterprise

    enterprise.assert_owned_auth_identity(
        client,
        auth_user,
        email=email,
        tenant_id=expected_tenant_id,
        role=expected_role,
        fixture_owner=FIXTURE_OWNER,
    )


def _role_email(profile: CompanyProfile, role: str) -> str:
    return f"rbac-{role.replace('_', '-')}@{profile.email_domain}".lower()


def assert_profile_auth_emails_safe(client: Any, profile: CompanyProfile) -> None:
    from scripts import seed_enterprise_transformation_scenario as enterprise

    tenant = _existing_tenant(client, profile.slug)
    tenant_id = str(tenant["id"]) if tenant else None
    expected_identities = {f"admin@{profile.email_domain}": "transformation_office"} | {
        _role_email(profile, role): role for role in ROLES
    }
    if tenant_id:
        settings = tenant.get("settings") or {}
        expected_org_marker = {"owner": FIXTURE_OWNER, "slug": profile.slug}
        if settings.get(enterprise.ORG_FIXTURE_MARKER_KEY) != expected_org_marker:
            raise RuntimeError(f"Existing tenant {profile.slug!r} is not owned by this fixture")
        platform_users = (
            client.table("users")
            .select("id,email,role,tenant_id")
            .eq("tenant_id", tenant_id)
            .execute()
            .data
            or []
        )
        platform_emails = [str(row.get("email") or "").lower() for row in platform_users]
        platform_ids = [str(row.get("id") or "") for row in platform_users]
        invalid_rows = [
            row
            for row, email in zip(platform_users, platform_emails, strict=True)
            if not row.get("id")
            or expected_identities.get(email) != str(row.get("role"))
            or str(row.get("tenant_id")) != tenant_id
        ]
        if (
            invalid_rows
            or len(platform_emails) != len(set(platform_emails))
            or len(platform_ids) != len(set(platform_ids))
        ):
            raise RuntimeError(
                f"Fixture tenant {profile.slug!r} has {len(invalid_rows)} invalid or duplicate "
                "platform identity rows"
            )
        for row, email in zip(platform_users, platform_emails, strict=True):
            response = client.auth.admin.get_user_by_id(str(row["id"]))
            auth_user = getattr(response, "user", None)
            if not auth_user or (getattr(auth_user, "email", "") or "").lower() != email:
                raise RuntimeError(
                    f"Fixture tenant {profile.slug!r} has a platform/Auth subject mismatch"
                )
            enterprise.assert_owned_auth_identity(
                client,
                auth_user,
                email=email,
                tenant_id=tenant_id,
                role=str(row["role"]),
                fixture_owner=FIXTURE_OWNER,
            )
        for table in (
            "integration_connections",
            "integration_oauth_states",
            "user_invites",
        ):
            if _count(client, table, tenant_id):
                raise RuntimeError(
                    f"Refusing to reset fixture tenant {profile.slug!r} with {table} records"
                )
    for email, role in expected_identities.items():
        assert_auth_email_safe(
            client,
            email=email,
            expected_tenant_id=tenant_id,
            expected_role=role,
        )


def assign_operating_model(
    client: Any,
    *,
    tenant_id: str,
    role_user_ids: dict[str, str],
) -> None:
    initiatives = (
        client.table("initiatives")
        .select("id,initiative_code,workstream_id")
        .eq("tenant_id", tenant_id)
        .order("initiative_code")
        .execute()
        .data
        or []
    )
    workstreams = (
        client.table("workstreams")
        .select("id,name")
        .eq("tenant_id", tenant_id)
        .order("name")
        .execute()
        .data
        or []
    )
    if len(initiatives) != 10 or len(workstreams) != 5:
        raise RuntimeError("Operating-model assignment requires 10 initiatives and 5 workstreams")

    client.table("user_workstreams").delete().eq("tenant_id", tenant_id).execute()
    lead_workstreams = workstreams[:2]
    client.table("user_workstreams").insert(
        [
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "user_id": role_user_ids["workstream_lead"],
                "workstream_id": str(workstream["id"]),
            }
            for workstream in lead_workstreams
        ]
    ).execute()
    client.table("initiative_team").delete().eq("tenant_id", tenant_id).execute()
    team_rows: list[dict[str, object]] = []
    for index, initiative in enumerate(initiatives, start=1):
        initiative_id = str(initiative["id"])
        owner_id = (
            role_user_ids["initiative_owner"] if index in {2, 5, 8} else role_user_ids["pmo_lead"]
        )
        client.table("initiatives").update(
            {
                "owner_id": owner_id,
                "group_owner_id": role_user_ids["business_benefit_owner"],
            }
        ).eq("tenant_id", tenant_id).eq("id", initiative_id).execute()
        team_rows.extend(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "user_id": owner_id,
                    "role": "owner",
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "user_id": role_user_ids["business_benefit_owner"],
                    "role": "benefit_owner",
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "user_id": role_user_ids["finance_lead"],
                    "role": "finance_reviewer",
                },
            ]
        )
    client.table("initiative_team").insert(team_rows).execute()


def _rows(client: Any, table: str, tenant_id: str, columns: str = "*") -> list[dict[str, Any]]:
    result = client.table(table).select(columns).eq("tenant_id", tenant_id).execute()
    return list(result.data or [])


def _count(client: Any, table: str, tenant_id: str) -> int:
    result = (
        client.table(table)
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    return int(result.count or 0)


def assert_tenant_invariants(client: Any, tenant_id: str) -> dict[str, int]:
    initiatives = _rows(client, "initiatives", tenant_id, "id,initiative_code")
    initiative_ids = {str(row["id"]) for row in initiatives}
    if len(initiatives) != 10 or len({row["initiative_code"] for row in initiatives}) != 10:
        raise AssertionError("Tenant must have exactly 10 uniquely coded initiatives")

    minimum_counts = {
        "users": 10,
        "milestones": 30,
        "milestone_checklist": 30,
        "kpis": 20,
        "kpi_entries": 240,
        "risks": 20,
        "status_updates": 20,
        "initiative_dependencies": 3,
        "gate_submissions": 41,
        "financial_benefit_lines": 30,
        "financial_metric_values": 2220,
        "financial_cost_lines": 90,
        "financial_forecasts": 30,
        "bankable_plans": 11,
        "benefit_realization_ledger": 240,
        "workstream_target_locks": 5,
        "shared_cost_pools": 4,
        "tenant_dashboard_config": 10,
    }
    counts = {"initiatives": len(initiatives)}
    for table, minimum in minimum_counts.items():
        count = _count(client, table, tenant_id)
        counts[table] = count
        if count < minimum:
            raise AssertionError(f"{table} count {count} is below required minimum {minimum}")

    for table in ("meetings", "meeting_sessions", "agenda_items", "action_items"):
        count = _count(client, table, tenant_id)
        counts[table] = count
        if count != 0:
            raise AssertionError(f"{table} must remain empty for non-meeting acceptance tenants")

    coverage_tables = {
        "milestones": 3,
        "kpis": 2,
        "risks": 2,
        "status_updates": 2,
        "financial_benefit_lines": 3,
        "financial_forecasts": 3,
    }
    for table, minimum in coverage_tables.items():
        rows = _rows(client, table, tenant_id, "initiative_id")
        coverage = Counter(str(row["initiative_id"]) for row in rows)
        missing = sorted(iid for iid in initiative_ids if coverage[iid] < minimum)
        if missing:
            raise AssertionError(f"{table} does not cover every initiative: {missing}")
    return counts


def seed_profiles(client: Any, password: str) -> list[dict[str, object]]:
    from app.core.auth_metadata import verify_scoped_authorization
    from app.core.database import get_supabase_schema
    from scripts import seed_enterprise_transformation_scenario as enterprise
    from scripts.seed_operating_model_users import seed_users

    if get_supabase_schema() != DEV_SCHEMA:
        raise RuntimeError("Loaded API client is not scoped to the dev schema")

    for profile in COMPANY_PROFILES:
        assert_profile_auth_emails_safe(client, profile)

    manifests: list[dict[str, object]] = []
    for profile in COMPANY_PROFILES:
        initiative_rows = build_profile_initiative_rows(enterprise.INITIATIVES, profile)
        admin_email = f"admin@{profile.email_domain}".lower()
        result = enterprise.seed_enterprise_transformation_scenario(
            client,
            seed_environment="dev",
            seed_confirmation=enterprise.DEV_SEED_CONFIRMATION,
            fixture_owner=FIXTURE_OWNER,
            org_name=profile.name,
            org_slug=profile.slug,
            admin_email=admin_email,
            admin_password=password,
            admin_display_name=profile.admin_display_name,
            admin_title=profile.admin_title,
            baseline_revenue=profile.baseline_revenue,
            baseline_gross_margin=profile.baseline_gross_margin,
            reporting_currency=profile.currency,
            fiscal_year_start_month=profile.fiscal_start_month,
            theme=profile.theme,
            country=profile.country,
            initiatives=initiative_rows,
            value_scale=profile.value_scale,
            include_meetings=False,
        )
        tenant_id = str(result["tenant_id"])
        role_user_ids = seed_users(
            client,
            tenant_id=tenant_id,
            email_domain=profile.email_domain,
            password=password,
            fixture_owner=FIXTURE_OWNER,
            existing_auth_validator=lambda user, email, role, tenant_id=tenant_id: (
                enterprise.assert_owned_auth_identity(
                    client,
                    user,
                    email=email,
                    tenant_id=tenant_id,
                    role=role,
                    fixture_owner=FIXTURE_OWNER,
                )
            ),
            auth_user_finalizer=lambda user_id, _email, _role, tenant_id=tenant_id: (
                enterprise.mark_auth_fixture_owner(
                    client,
                    user_id,
                    tenant_id=tenant_id,
                    fixture_owner=FIXTURE_OWNER,
                )
            ),
        )
        assign_operating_model(client, tenant_id=tenant_id, role_user_ids=role_user_ids)
        verify_scoped_authorization(
            client.auth.admin,
            str(result["admin_user_id"]),
            scope=DEV_SCHEMA,
            authorization={"tenant_id": tenant_id, "role": "transformation_office"},
        )
        for role, user_id in role_user_ids.items():
            verify_scoped_authorization(
                client.auth.admin,
                user_id,
                scope=DEV_SCHEMA,
                authorization={"tenant_id": tenant_id, "role": role},
            )
        counts = assert_tenant_invariants(client, tenant_id)
        manifests.append(
            {
                "name": profile.name,
                "slug": profile.slug,
                "tenant_id": tenant_id,
                "admin_email": admin_email,
                "currency": profile.currency,
                "fiscal_start_month": profile.fiscal_start_month,
                "scenario_as_of_date": enterprise.SCENARIO_AS_OF_DATE.isoformat(),
                "counts": counts,
            }
        )
        print(f"Seeded {profile.name}: {tenant_id} ({counts['initiatives']} initiatives)")
    return manifests


def write_manifest(path: str, manifests: list[dict[str, object]]) -> None:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"environment": "dev", "tenants": manifests}, indent=2) + "\n")


def main() -> None:
    args = parse_args()
    load_runtime_environment(args)
    assert_dev_target(args)
    password = required_password()

    from app.core.database import get_supabase_admin

    manifests = seed_profiles(get_supabase_admin(), password)
    if args.manifest:
        write_manifest(args.manifest, manifests)
    print(f"Seeded and verified {len(manifests)} isolated dev tenants")


if __name__ == "__main__":
    main()
