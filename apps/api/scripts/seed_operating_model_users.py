"""
Seed and probe deterministic operating-model users for a tenant.

Examples:
    cd apps/api
    HOSTINGER_API_KEY=... uv run python scripts/seed_operating_model_users.py \
      --hostinger-project transmuter-dev-hostinger \
      --tenant-slug acme-transformation-lab \
      --probe-api
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from dotenv import dotenv_values, load_dotenv

ROLES: tuple[str, ...] = (
    "transformation_office",
    "tenant_admin",
    "pmo_lead",
    "finance_lead",
    "workstream_lead",
    "initiative_owner",
    "business_benefit_owner",
    "executive_sponsor",
    "viewer",
)

ROLE_NAMES: dict[str, str] = {
    "transformation_office": "Transformation Office Director",
    "tenant_admin": "Tenant Administrator",
    "pmo_lead": "PMO Lead",
    "finance_lead": "Finance Lead",
    "workstream_lead": "Workstream Lead",
    "initiative_owner": "Initiative Owner",
    "business_benefit_owner": "Business Benefit Owner",
    "executive_sponsor": "Executive Sponsor",
    "viewer": "Management Viewer",
}

USERS_MANAGE_ROLES = {"transformation_office", "tenant_admin"}
TENANT_SETUP_ROLES = {"transformation_office", "tenant_admin"}
PORTFOLIO_VIEW_ROLES = {
    "transformation_office",
    "tenant_admin",
    "pmo_lead",
    "finance_lead",
    "workstream_lead",
    "business_benefit_owner",
    "executive_sponsor",
    "viewer",
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def load_runtime_environment(args: argparse.Namespace) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=repo_root / ".env", override=False)
    if args.env_file:
        load_dotenv(dotenv_path=args.env_file, override=True)
    if args.hostinger_project:
        environment = fetch_hostinger_environment(args.hostinger_project, args.hostinger_vps_id)
        for key, value in dotenv_values(stream=StringIO(environment)).items():
            if value is not None:
                os.environ[key] = value


def fetch_hostinger_environment(project_name: str, vps_id: str) -> str:
    token = os.environ.get("HOSTINGER_API_TOKEN") or os.environ.get("HOSTINGER_API_KEY")
    if not token:
        raise RuntimeError("HOSTINGER_API_KEY or HOSTINGER_API_TOKEN is required")
    api_base = os.environ.get("HOSTINGER_API_BASE_URL", "https://developers.hostinger.com/api")
    completed = subprocess.run(
        [
            "curl",
            "-fsS",
            "-H",
            f"Authorization: Bearer {token}",
            f"{api_base}/vps/v1/virtual-machines/{vps_id}/docker/{project_name}",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(completed.stdout)
    environment = str(payload.get("environment") or "")
    if not environment:
        raise RuntimeError(f"Hostinger project {project_name!r} did not return an environment")
    return environment


def import_app_clients():
    from app.core.database import get_supabase_admin

    return get_supabase_admin()


def find_tenant(client: Any, tenant_slug: str | None) -> dict[str, Any]:
    if tenant_slug:
        result = (
            client.table("organizations")
            .select("id,name,slug")
            .eq("slug", tenant_slug)
            .maybe_single()
            .execute()
        )
        if result and result.data:
            return result.data
        raise RuntimeError(f"Tenant slug not found: {tenant_slug}")
    result = client.table("organizations").select("id,name,slug").limit(1).execute()
    if not result.data:
        raise RuntimeError("No tenant organizations found")
    return result.data[0]


def find_auth_user_id_by_email(client: Any, email: str) -> str | None:
    page = 1
    per_page = 100
    while True:
        users = client.auth.admin.list_users(page=page, per_page=per_page)
        if not users:
            return None
        for user in users:
            if (getattr(user, "email", "") or "").lower() == email.lower():
                return str(user.id)
        if len(users) < per_page:
            return None
        page += 1


def ensure_auth_user(
    client: Any,
    *,
    email: str,
    password: str,
    tenant_id: str,
    role: str,
    display_name: str,
) -> str:
    metadata = {"tenant_id": tenant_id, "role": role, "display_name": display_name}
    auth_id = find_auth_user_id_by_email(client, email)
    if auth_id:
        client.auth.admin.update_user_by_id(
            auth_id,
            {
                "password": password,
                "email_confirm": True,
                "user_metadata": metadata,
            },
        )
        return auth_id
    created = client.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": metadata,
        }
    )
    return str(created.user.id)


def first_row(client: Any, table: str, tenant_id: str, select: str = "*") -> dict[str, Any] | None:
    query = client.table(table).select(select).eq("tenant_id", tenant_id).limit(1)
    if table == "initiatives":
        query = query.is_("archived_at", "null")
    result = query.execute()
    return result.data[0] if result.data else None


def ensure_user_workstream(client: Any, tenant_id: str, user_id: str, workstream_id: str) -> None:
    client.table("user_workstreams").delete().eq("tenant_id", tenant_id).eq(
        "user_id", user_id
    ).execute()
    client.table("user_workstreams").insert(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "workstream_id": workstream_id,
        }
    ).execute()


def seed_users(
    client: Any,
    *,
    tenant_id: str,
    email_domain: str,
    password: str,
) -> dict[str, str]:
    workstream = first_row(client, "workstreams", tenant_id, "id,name")
    initiative = first_row(client, "initiatives", tenant_id, "id,name,workstream_id")
    seeded: dict[str, str] = {}

    for role in ROLES:
        display_name = f"RBAC {ROLE_NAMES[role]}"
        email = f"rbac-{role.replace('_', '-')}@{email_domain}".lower()
        user_id = ensure_auth_user(
            client,
            email=email,
            password=password,
            tenant_id=tenant_id,
            role=role,
            display_name=display_name,
        )
        client.table("users").upsert(
            {
                "id": user_id,
                "tenant_id": tenant_id,
                "email": email,
                "display_name": display_name,
                "title": ROLE_NAMES[role],
                "department": "Transformation Office RBAC Test",
                "timezone": "UTC",
                "role": role,
                "status": "active",
                "must_change_password": False,
                "onboarding_completed": True,
                "updated_at": now(),
            },
            on_conflict="id",
        ).execute()
        seeded[role] = user_id

    if workstream and seeded.get("workstream_lead"):
        ensure_user_workstream(client, tenant_id, seeded["workstream_lead"], str(workstream["id"]))
    if initiative and seeded.get("initiative_owner"):
        client.table("initiatives").update(
            {"owner_id": seeded["initiative_owner"], "updated_at": now()}
        ).eq("tenant_id", tenant_id).eq("id", initiative["id"]).execute()
    if initiative and initiative.get("workstream_id") and seeded.get("workstream_lead"):
        ensure_user_workstream(
            client,
            tenant_id,
            seeded["workstream_lead"],
            str(initiative["workstream_id"]),
        )
    if initiative and seeded.get("business_benefit_owner"):
        client.table("initiatives").update(
            {"group_owner_id": seeded["business_benefit_owner"], "updated_at": now()}
        ).eq("tenant_id", tenant_id).eq("id", initiative["id"]).execute()

    return seeded


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    expected: set[int] | None = None,
) -> tuple[int, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
            status = response.status
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {"error": raw}
        except json.JSONDecodeError:
            payload = {"error": raw}
        status = exc.code
    if expected is not None and status not in expected:
        raise AssertionError(f"{method} {url} returned {status}: {payload}")
    return status, payload


def login(api_base_url: str, email: str, password: str) -> str:
    status, payload = request_json(
        "POST",
        f"{api_base_url}/auth/login",
        body={"email": email, "password": password},
        expected={200},
    )
    if status != 200 or not payload.get("access_token"):
        raise AssertionError(f"Login failed for {email}: {payload}")
    return str(payload["access_token"])


def probe_api(
    client: Any,
    *,
    api_base_url: str,
    email_domain: str,
    password: str,
    tenant_id: str,
) -> list[dict[str, Any]]:
    config_by_role: dict[str, Any] = {}
    results: list[dict[str, Any]] = []

    for role in ROLES:
        email = f"rbac-{role.replace('_', '-')}@{email_domain}".lower()
        token = login(api_base_url, email, password)
        _, profile = request_json("GET", f"{api_base_url}/auth/me", token=token, expected={200})
        if profile["role"] != role:
            raise AssertionError(f"{email} authenticated with role {profile['role']}, expected {role}")

        dashboard_status, _ = request_json(
            "GET", f"{api_base_url}/dashboard", token=token, expected={200, 403, 404}
        )
        config_status, config_payload = request_json(
            "GET",
            f"{api_base_url}/admin/dashboard-configuration",
            token=token,
            expected={200, 403},
        )
        if config_status == 200:
            config_by_role[role] = config_payload

        expected_config_status = 200 if role in PORTFOLIO_VIEW_ROLES else 403
        if config_status != expected_config_status:
            raise AssertionError(
                f"{role} dashboard configuration status {config_status}, "
                f"expected {expected_config_status}"
            )

        probe_email = f"rbac-probe-{role.replace('_', '-')}-{uuid4().hex[:10]}@{email_domain}"
        invite_status, invite_payload = request_json(
            "POST",
            f"{api_base_url}/invites",
            token=token,
            body={
                "email": probe_email,
                "display_name": f"RBAC Probe {role}",
                "role": "viewer",
                "title": "Temporary RBAC Probe",
                "department": "RBAC Probe",
                "workstream_ids": [],
            },
            expected={201, 403, 409},
        )
        expected_invite_status = 201 if role in USERS_MANAGE_ROLES else 403
        if invite_status != expected_invite_status:
            raise AssertionError(
                f"{role} invite status {invite_status}, expected {expected_invite_status}: "
                f"{invite_payload}"
            )
        cleanup_probe_invite(client, tenant_id, probe_email)

        update_status = 403
        if "transformation_office" in config_by_role:
            config_body = config_by_role["transformation_office"]
            update_status, _ = request_json(
                "PUT",
                f"{api_base_url}/admin/dashboard-configuration",
                token=token,
                body=config_body,
                expected={200, 403},
            )
            expected_update_status = 200 if role in TENANT_SETUP_ROLES else 403
            if update_status != expected_update_status:
                raise AssertionError(
                    f"{role} dashboard update status {update_status}, "
                    f"expected {expected_update_status}"
                )

        results.append(
            {
                "role": role,
                "auth_me": 200,
                "dashboard": dashboard_status,
                "dashboard_configuration": config_status,
                "invite_create": invite_status,
                "dashboard_configuration_update": update_status,
            }
        )
    return results


def cleanup_probe_invite(client: Any, tenant_id: str, email: str) -> None:
    client.table("user_invites").delete().eq("tenant_id", tenant_id).eq("email", email).execute()
    auth_id = find_auth_user_id_by_email(client, email)
    if auth_id:
        client.auth.admin.delete_user(auth_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-slug", default=os.environ.get("TRANSMUTER_RBAC_TENANT_SLUG"))
    parser.add_argument("--email-domain", default="acme-transformation.dev")
    parser.add_argument(
        "--password",
        default=os.environ.get("TRANSMUTER_RBAC_SAMPLE_PASSWORD", "Transmuter2026!"),
    )
    parser.add_argument("--env-file")
    parser.add_argument("--hostinger-project")
    parser.add_argument("--hostinger-vps-id", default=os.environ.get("HOSTINGER_VPS_ID", "1695814"))
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get(
            "TRANSMUTER_API_BASE_URL", "https://transmuter-dev.ishirock.tech/api"
        ).rstrip("/"),
    )
    parser.add_argument("--probe-api", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_runtime_environment(args)
    client = import_app_clients()
    tenant = find_tenant(client, args.tenant_slug)
    tenant_id = str(tenant["id"])
    seeded = seed_users(
        client,
        tenant_id=tenant_id,
        email_domain=args.email_domain,
        password=args.password,
    )
    print(
        json.dumps(
            {
                "tenant": tenant,
                "seeded_roles": sorted(seeded),
                "sample_email_domain": args.email_domain,
            },
            indent=2,
        )
    )
    if args.probe_api:
        results = probe_api(
            client,
            api_base_url=args.api_base_url,
            email_domain=args.email_domain,
            password=args.password,
            tenant_id=tenant_id,
        )
        print(json.dumps({"api_probe_results": results}, indent=2))


if __name__ == "__main__":
    main()
