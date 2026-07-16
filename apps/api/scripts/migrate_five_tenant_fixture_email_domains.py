"""Migrate the five owned dev fixture tenants from reserved to login-safe emails.

The command is dry-run by default. It is fixed to the reviewed five-tenant
fixture and cannot accept arbitrary tenants or email mappings.
"""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from pydantic import EmailStr, TypeAdapter

from scripts.multi_tenant_transformation_profiles import COMPANY_PROFILES, CompanyProfile
from scripts.seed_operating_model_users import ROLES

CONFIRMATION = "migrate-five-tenant-fixture-emails-dev"
LEGACY_DOMAINS_BY_SLUG = {
    "qa-e2e-20260712-acme-global-manufacturing": ("acme-global-manufacturing.transmuter.test"),
    "qa-e2e-20260712-northstar-retail-group": "northstar-retail-group.transmuter.test",
    "qa-e2e-20260712-meridian-commercial-bank": ("meridian-commercial-bank.transmuter.test"),
    "qa-e2e-20260712-solstice-health-network": "solstice-health-network.transmuter.test",
    "qa-e2e-20260712-horizon-energy-utilities": ("horizon-energy-utilities.transmuter.test"),
}


class MigrationError(RuntimeError):
    """Sanitized migration failure that never includes identities or credentials."""


@dataclass(frozen=True, slots=True)
class AuthSnapshot:
    subject_id: str = field(repr=False)
    email: str = field(repr=False)
    app_metadata: dict[str, Any] = field(repr=False)
    user_metadata: dict[str, Any] = field(repr=False)
    auth_role: str = field(repr=False)
    is_super_admin: bool = field(repr=False)


@dataclass(frozen=True, slots=True)
class IdentityMigration:
    tenant_slug: str
    identity_key: str
    tenant_id: str = field(repr=False)
    subject_id: str = field(repr=False)
    role: str = field(repr=False)
    old_email: str = field(repr=False)
    new_email: str = field(repr=False)
    state: Literal["pending", "complete"]
    snapshot: AuthSnapshot = field(repr=False)


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    identities: tuple[IdentityMigration, ...]
    auth_snapshots: dict[str, AuthSnapshot] = field(repr=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("dev",), required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--hostinger-project", required=True)
    parser.add_argument("--hostinger-vps-id", default=os.environ.get("HOSTINGER_VPS_ID", "1695814"))
    parser.add_argument("--env-file")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--journal")
    return parser.parse_args()


def expected_email_mappings(profile: CompanyProfile) -> dict[str, tuple[str, str, str]]:
    legacy_domain = LEGACY_DOMAINS_BY_SLUG.get(profile.slug)
    if not legacy_domain:
        raise MigrationError("Fixture profile is outside the reviewed migration allowlist")
    mappings = {
        f"admin@{legacy_domain}": (
            f"admin@{profile.email_domain}",
            "transformation_office",
            "admin",
        )
    }
    for role in ROLES:
        local = f"rbac-{role.replace('_', '-')}"
        mappings[f"{local}@{legacy_domain}"] = (
            f"{local}@{profile.email_domain}",
            role,
            role,
        )
    if len(mappings) != 10:
        raise MigrationError("Fixture identity mapping must contain exactly ten users")
    adapter = TypeAdapter(EmailStr)
    for new_email, _role, _identity_key in mappings.values():
        try:
            adapter.validate_python(new_email)
        except ValueError:
            raise MigrationError("Approved dev QA email mapping is invalid") from None
    return mappings


def _list_auth_users(client: Any) -> list[Any]:
    users: list[Any] = []
    page = 1
    while True:
        batch = list(client.auth.admin.list_users(page=page, per_page=100) or [])
        users.extend(batch)
        if len(batch) < 100:
            return users
        page += 1


def _auth_snapshot(user: Any) -> AuthSnapshot:
    return AuthSnapshot(
        subject_id=str(user.id),
        email=str(getattr(user, "email", "") or "").lower(),
        app_metadata=deepcopy(dict(getattr(user, "app_metadata", None) or {})),
        user_metadata=deepcopy(dict(getattr(user, "user_metadata", None) or {})),
        auth_role=str(getattr(user, "role", "") or ""),
        is_super_admin=bool(getattr(user, "is_super_admin", False)),
    )


def _auth_user_by_id(client: Any, subject_id: str) -> Any:
    response = client.auth.admin.get_user_by_id(subject_id)
    user = getattr(response, "user", None)
    if user is None:
        raise MigrationError("Fixture Auth subject disappeared during migration")
    return user


def _platform_email_rows(client: Any, email: str) -> list[dict[str, Any]]:
    result = client.table("users").select("id,tenant_id,email,role").ilike("email", email).execute()
    return list(result.data or [])


def _assert_no_protected_tenant_state(client: Any, tenant_id: str) -> None:
    from scripts.seed_five_tenant_transformation_program import _count

    for table in ("user_invites", "integration_connections", "integration_oauth_states"):
        if _count(client, table, tenant_id):
            raise MigrationError("Fixture tenant has protected state; migration is not allowed")


def preflight(client: Any) -> MigrationPlan:
    from scripts import seed_enterprise_transformation_scenario as enterprise
    from scripts.seed_five_tenant_transformation_program import FIXTURE_OWNER, _existing_tenant

    auth_users = _list_auth_users(client)
    auth_snapshots: dict[str, AuthSnapshot] = {}
    for user in auth_users:
        snapshot = _auth_snapshot(user)
        if snapshot.subject_id in auth_snapshots:
            raise MigrationError("Shared Auth contains duplicate fixture subject identifiers")
        auth_snapshots[snapshot.subject_id] = snapshot
    if len(auth_snapshots) != len(auth_users):
        raise MigrationError("Shared Auth contains duplicate fixture subject identifiers")
    auth_by_email: dict[str, list[AuthSnapshot]] = {}
    for snapshot in auth_snapshots.values():
        auth_by_email.setdefault(snapshot.email, []).append(snapshot)

    identities: list[IdentityMigration] = []
    subject_ids: set[str] = set()
    for profile in COMPANY_PROFILES:
        tenant = _existing_tenant(client, profile.slug)
        if tenant is None:
            raise MigrationError("A reviewed fixture tenant does not exist")
        tenant_id = str(tenant["id"])
        marker = (tenant.get("settings") or {}).get(enterprise.ORG_FIXTURE_MARKER_KEY)
        if marker != {"owner": FIXTURE_OWNER, "slug": profile.slug}:
            raise MigrationError("Fixture organization ownership marker is invalid")
        _assert_no_protected_tenant_state(client, tenant_id)

        rows = list(
            client.table("users")
            .select("id,tenant_id,email,role")
            .eq("tenant_id", tenant_id)
            .execute()
            .data
            or []
        )
        if len(rows) != 10:
            raise MigrationError("Fixture tenant must contain exactly ten platform users")
        mappings = expected_email_mappings(profile)
        new_to_old = {new: old for old, (new, _role, _key) in mappings.items()}
        seen_pairs: set[str] = set()
        for row in rows:
            current_email = str(row.get("email") or "").lower()
            if current_email in mappings:
                old_email = current_email
                state: Literal["pending", "complete"] = "pending"
            elif current_email in new_to_old:
                old_email = new_to_old[current_email]
                state = "complete"
            else:
                raise MigrationError("Fixture tenant contains an unexpected platform identity")
            new_email, expected_role, identity_key = mappings[old_email]
            if old_email in seen_pairs or str(row.get("role")) != expected_role:
                raise MigrationError("Fixture identity role or uniqueness check failed")
            seen_pairs.add(old_email)
            subject_id = str(row.get("id") or "")
            if not subject_id or subject_id in subject_ids:
                raise MigrationError("Fixture subject identifiers must be globally unique")

            auth_user = _auth_user_by_id(client, subject_id)
            auth_email = str(getattr(auth_user, "email", "") or "").lower()
            if auth_email != current_email:
                raise MigrationError("Fixture Auth and platform emails are split")
            listed_auth = auth_by_email.get(current_email, [])
            current_platform = _platform_email_rows(client, current_email)
            current_snapshot = _auth_snapshot(auth_user)
            if (
                current_snapshot.auth_role != "authenticated"
                or current_snapshot.is_super_admin
                or len(listed_auth) != 1
                or listed_auth[0] != current_snapshot
                or auth_snapshots.get(subject_id) != current_snapshot
                or len(current_platform) != 1
                or str(current_platform[0].get("id")) != subject_id
                or str(current_platform[0].get("tenant_id")) != tenant_id
                or str(current_platform[0].get("role")) != expected_role
            ):
                raise MigrationError("Fixture identity has unsafe Auth privilege or collision")
            try:
                enterprise.assert_owned_auth_identity(
                    client,
                    auth_user,
                    email=current_email,
                    tenant_id=tenant_id,
                    role=expected_role,
                    fixture_owner=FIXTURE_OWNER,
                )
            except Exception:
                raise MigrationError(
                    "Fixture Auth authorization or ownership preflight failed"
                ) from None

            if state == "pending":
                if auth_by_email.get(new_email) or _platform_email_rows(client, new_email):
                    raise MigrationError("A fixture target email is already claimed")
            elif auth_by_email.get(old_email) or _platform_email_rows(client, old_email):
                raise MigrationError("A completed fixture identity retains a legacy collision")

            identities.append(
                IdentityMigration(
                    tenant_slug=profile.slug,
                    identity_key=identity_key,
                    tenant_id=tenant_id,
                    subject_id=subject_id,
                    role=expected_role,
                    old_email=old_email,
                    new_email=new_email,
                    state=state,
                    snapshot=current_snapshot,
                )
            )
            subject_ids.add(subject_id)
        if seen_pairs != set(mappings):
            raise MigrationError("Fixture tenant identity mapping is incomplete")

    if len(identities) != 50 or len(subject_ids) != 50:
        raise MigrationError("Migration requires exactly fifty unique fixture identities")
    identities.sort(key=lambda item: (item.tenant_slug, item.identity_key))
    return MigrationPlan(tuple(identities), auth_snapshots)


def _assert_auth_snapshot(user: Any, identity: IdentityMigration, email: str) -> None:
    current = _auth_snapshot(user)
    if (
        current.subject_id != identity.subject_id
        or current.email != email
        or current.app_metadata != identity.snapshot.app_metadata
        or current.user_metadata != identity.snapshot.user_metadata
        or current.auth_role != identity.snapshot.auth_role
        or current.is_super_admin != identity.snapshot.is_super_admin
    ):
        raise MigrationError("Fixture Auth snapshot changed unexpectedly")


def _verify_identity(client: Any, identity: IdentityMigration, email: str) -> None:
    from scripts import seed_enterprise_transformation_scenario as enterprise
    from scripts.seed_five_tenant_transformation_program import FIXTURE_OWNER

    user = _auth_user_by_id(client, identity.subject_id)
    _assert_auth_snapshot(user, identity, email)
    enterprise.assert_owned_auth_identity(
        client,
        user,
        email=email,
        tenant_id=identity.tenant_id,
        role=identity.role,
        fixture_owner=FIXTURE_OWNER,
    )


def _target_available(client: Any, identity: IdentityMigration) -> None:
    from scripts.seed_five_tenant_transformation_program import _auth_user

    if _auth_user(client, identity.new_email) is not None or _platform_email_rows(
        client, identity.new_email
    ):
        raise MigrationError("Fixture target email became occupied during migration")


def _update_auth_email(client: Any, identity: IdentityMigration, email: str) -> None:
    client.auth.admin.update_user_by_id(
        identity.subject_id,
        {"email": email, "email_confirm": True},
    )
    _assert_auth_snapshot(_auth_user_by_id(client, identity.subject_id), identity, email)


def _set_platform_email_cas(
    client: Any,
    identity: IdentityMigration,
    *,
    source_email: str,
    target_email: str,
) -> None:
    result = (
        client.table("users")
        .update({"email": target_email})
        .eq("id", identity.subject_id)
        .eq("tenant_id", identity.tenant_id)
        .eq("email", source_email)
        .execute()
    )
    rows = list(result.data or [])
    if len(rows) != 1 or str(rows[0].get("email") or "").lower() != target_email:
        raise MigrationError("Tenant-scoped platform email compare-and-set failed")


def _write_journal(path: Path, status: str, completed: list[IdentityMigration]) -> None:
    payload = {
        "environment": "dev",
        "status": status,
        "completed": [
            {"tenant_slug": item.tenant_slug, "identity": item.identity_key} for item in completed
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def _rollback_identity(client: Any, identity: IdentityMigration) -> None:
    current_platform = _platform_email_rows(client, identity.new_email)
    if current_platform:
        _set_platform_email_cas(
            client,
            identity,
            source_email=identity.new_email,
            target_email=identity.old_email,
        )
    current_auth = _auth_user_by_id(client, identity.subject_id)
    if str(getattr(current_auth, "email", "") or "").lower() == identity.new_email:
        _update_auth_email(client, identity, identity.old_email)
    _verify_identity(client, identity, identity.old_email)


def _assert_unrelated_auth_unchanged(client: Any, plan: MigrationPlan) -> None:
    migrated_ids = {item.subject_id for item in plan.identities}
    after: dict[str, AuthSnapshot] = {}
    for user in _list_auth_users(client):
        snapshot = _auth_snapshot(user)
        if snapshot.subject_id in after:
            raise MigrationError("Shared Auth subject set changed during migration")
        after[snapshot.subject_id] = snapshot
    if set(after) != set(plan.auth_snapshots):
        raise MigrationError("Shared Auth subject set changed during migration")
    for subject_id, before in plan.auth_snapshots.items():
        if subject_id in migrated_ids:
            continue
        if after[subject_id] != before:
            raise MigrationError("An unrelated shared Auth identity changed during migration")


def apply_migration(client: Any, plan: MigrationPlan, journal_path: Path) -> MigrationPlan:
    changed: list[IdentityMigration] = []
    try:
        for identity in plan.identities:
            if identity.state == "complete":
                continue
            _verify_identity(client, identity, identity.old_email)
            _target_available(client, identity)
            changed.append(identity)
            _update_auth_email(client, identity, identity.new_email)
            _set_platform_email_cas(
                client,
                identity,
                source_email=identity.old_email,
                target_email=identity.new_email,
            )
            _verify_identity(client, identity, identity.new_email)
            _write_journal(journal_path, "applying", changed)

        postflight = preflight(client)
        if any(item.state != "complete" for item in postflight.identities):
            raise MigrationError("Fixture email migration postflight is incomplete")
        before_by_key = {(item.tenant_slug, item.identity_key): item for item in plan.identities}
        for item in postflight.identities:
            before = before_by_key[(item.tenant_slug, item.identity_key)]
            if (
                item.subject_id != before.subject_id
                or item.snapshot.app_metadata != before.snapshot.app_metadata
                or item.snapshot.user_metadata != before.snapshot.user_metadata
                or item.snapshot.auth_role != before.snapshot.auth_role
                or item.snapshot.is_super_admin != before.snapshot.is_super_admin
            ):
                raise MigrationError("Fixture identity subject or authorization changed")
        _assert_unrelated_auth_unchanged(client, plan)
        _write_journal(journal_path, "complete", list(postflight.identities))
        return postflight
    except Exception:
        try:
            for identity in reversed(changed):
                _rollback_identity(client, identity)
            _write_journal(journal_path, "rolled_back", [])
        except Exception:
            _write_journal(journal_path, "rollback_failed", changed)
            raise MigrationError("Fixture email migration and rollback both failed") from None
        raise MigrationError("Fixture email migration failed and was rolled back") from None


def main() -> None:
    args = parse_args()
    if args.confirm != CONFIRMATION:
        raise MigrationError(f"--confirm must exactly equal {CONFIRMATION!r}")
    if args.apply and not args.journal:
        raise MigrationError("--journal is required with --apply")

    from scripts import seed_five_tenant_transformation_program as five_tenant

    five_tenant.load_runtime_environment(args)
    five_tenant.assert_dev_target(SimpleNamespace(confirm=five_tenant.CONFIRMATION))

    from scripts import seed_enterprise_transformation_scenario as enterprise

    enterprise.assert_seed_target_allowed("dev", enterprise.DEV_SEED_CONFIRMATION)

    from app.core.database import get_supabase_admin

    client = get_supabase_admin()
    try:
        plan = preflight(client)
        pending = sum(item.state == "pending" for item in plan.identities)
        complete = len(plan.identities) - pending
        if not args.apply:
            print(f"Fixture email migration dry-run passed: {pending} pending, {complete} complete")
            return
        result = apply_migration(
            client,
            plan,
            Path(args.journal).expanduser().resolve(),
        )
        if any(item.state != "complete" for item in result.identities):
            raise MigrationError("Fixture email migration did not complete")
    except MigrationError:
        raise
    except Exception:
        raise MigrationError("Fixture email migration guarded execution failed") from None
    print("Fixture email migration completed for 5 tenants and 50 identities")


if __name__ == "__main__":
    main()
