"""Reconcile Supabase Auth authorization claims with canonical platform users.

Run a dry-run by default::

    uv run python -m app.cli.reconcile_auth_claims

Apply changes explicitly::

    uv run python -m app.cli.reconcile_auth_claims --apply

Production and every cleanup apply require ``CONFIRM_PROD_AUTH_RECONCILE=1``.
Cleanup apply also requires ``CONFIRM_AUTH_CLAIM_CLEANUP=1``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, TextIO

from app.core.auth_metadata import (
    AUTHORIZATION_METADATA_KEYS,
    AUTHORIZATION_SCOPES,
    authorization_metadata_key,
)

DEFAULT_PAGE_SIZE = 100
PRODUCTION_ENVIRONMENTS = frozenset({"prod", "production"})
ReconciliationPhase = Literal["seed", "cleanup"]
GLOBAL_APP_AUTHORIZATION_KEYS = ("tenant_id", "role", "platform_admin")


@dataclass(frozen=True)
class CanonicalUser:
    user_id: str
    tenant_id: str
    role: str


@dataclass
class ReconciliationReport:
    mode: str
    environment: str
    phase: ReconciliationPhase
    authorization_scope: str
    strict_orphans: bool
    counts: dict[str, int] = field(
        default_factory=lambda: {
            "platform_users_scanned": 0,
            "auth_users_scanned": 0,
            "platform_admins_skipped": 0,
            "unchanged": 0,
            "updates_planned": 0,
            "updates_applied": 0,
            "missing_auth_users": 0,
            "orphan_auth_users": 0,
            "structural_errors": 0,
            "update_errors": 0,
            "residual_errors": 0,
        }
    )
    records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        blocking_error = any(
            self.counts[key]
            for key in (
                "missing_auth_users",
                "structural_errors",
                "update_errors",
                "residual_errors",
            )
        )
        return blocking_error or (self.strict_orphans and self.counts["orphan_auth_users"] > 0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "failed" if self.has_errors else "ok",
            "mode": self.mode,
            "environment": self.environment,
            "phase": self.phase,
            "authorization_scope": self.authorization_scope,
            "strict_orphans": self.strict_orphans,
            "counts": self.counts,
            "records": self.records,
        }


def reconcile_auth_claims(
    client: Any,
    *,
    apply: bool = False,
    environment: str = "development",
    allowed_platform_admin_emails: Iterable[str] = (),
    page_size: int = DEFAULT_PAGE_SIZE,
    phase: ReconciliationPhase = "seed",
    authorization_scope: str = "public",
    strict_orphans: bool = False,
) -> ReconciliationReport:
    """Reconcile every ordinary Auth identity against its platform user row.

    Platform ``users`` rows are authoritative for tenant and role. All reads and
    structural checks finish before apply mode writes anything.
    """

    if page_size < 1:
        raise ValueError("page_size must be positive")
    if phase not in {"seed", "cleanup"}:
        raise ValueError("phase must be 'seed' or 'cleanup'")
    scoped_metadata_key = authorization_metadata_key(authorization_scope)

    report = ReconciliationReport(
        mode="apply" if apply else "dry_run",
        environment=_normalized_environment(environment),
        phase=phase,
        authorization_scope=authorization_scope,
        strict_orphans=strict_orphans,
    )
    platform_rows = _list_platform_users(client, page_size=page_size)
    auth_users = _list_auth_users(client, page_size=page_size)
    report.counts["platform_users_scanned"] = len(platform_rows)
    report.counts["auth_users_scanned"] = len(auth_users)

    platform_by_id = _index_platform_users(platform_rows, report)
    auth_by_id = _index_auth_users(auth_users, report)
    auth_user_values = auth_by_id.values()
    platform_admin_marker_ids = _platform_admin_marker_ids(
        auth_user_values, allowed_platform_admin_emails
    )
    platform_admin_ids = _valid_platform_admin_ids(auth_user_values, allowed_platform_admin_emails)
    hybrid_platform_admin_ids = platform_admin_marker_ids - platform_admin_ids
    for user_id in sorted(hybrid_platform_admin_ids):
        report.counts["structural_errors"] += 1
        details = (
            _canonical_claim_details(platform_by_id[user_id]) if user_id in platform_by_id else {}
        )
        report.records.append(
            _record(
                user_id,
                "error",
                code="hybrid_platform_admin_authorization",
                **details,
            )
        )
    conflicting_platform_admin_ids = platform_admin_ids & platform_by_id.keys()
    for user_id in sorted(conflicting_platform_admin_ids):
        report.counts["structural_errors"] += 1
        report.records.append(
            _record(
                user_id,
                "error",
                code="platform_admin_platform_user_conflict",
                **_canonical_claim_details(platform_by_id[user_id]),
            )
        )
    for user_id in sorted(platform_admin_ids - conflicting_platform_admin_ids):
        report.counts["platform_admins_skipped"] += 1
        report.records.append(_record(user_id, "platform_admin_skipped"))

    for user_id in sorted(platform_by_id.keys() - platform_admin_ids - auth_by_id.keys()):
        report.counts["missing_auth_users"] += 1
        report.records.append(
            _record(
                user_id,
                "error",
                code="missing_auth_user",
                **_canonical_claim_details(platform_by_id[user_id]),
            )
        )

    reserved_platform_admin_ids = platform_admin_ids | hybrid_platform_admin_ids
    for user_id in sorted(auth_by_id.keys() - reserved_platform_admin_ids - platform_by_id.keys()):
        report.counts["orphan_auth_users"] += 1
        report.records.append(
            _record(
                user_id,
                "error" if strict_orphans else "warning",
                code="orphan_auth_user",
            )
        )

    if report.has_errors:
        return report

    reconciliations: list[tuple[CanonicalUser, Any, dict[str, Any], dict[str, Any]]] = []
    ordinary_user_ids = (platform_by_id.keys() & auth_by_id.keys()) - reserved_platform_admin_ids
    for user_id in sorted(ordinary_user_ids):
        canonical = platform_by_id[user_id]
        auth_user = auth_by_id[user_id]
        desired_app_metadata, desired_user_metadata = _desired_metadata(
            canonical,
            auth_user,
            scoped_metadata_key=scoped_metadata_key,
            phase=phase,
        )
        if (
            _metadata(auth_user, "app_metadata") == desired_app_metadata
            and _metadata(auth_user, "user_metadata") == desired_user_metadata
        ):
            report.counts["unchanged"] += 1
            report.records.append(
                _record(user_id, "unchanged", **_canonical_claim_details(canonical))
            )
            continue

        report.counts["updates_planned"] += 1
        reconciliations.append((canonical, auth_user, desired_app_metadata, desired_user_metadata))
        if not apply:
            report.records.append(
                _record(
                    user_id,
                    "would_update",
                    changes=_metadata_changes(
                        auth_user,
                        canonical,
                        scoped_metadata_key=scoped_metadata_key,
                        phase=phase,
                    ),
                    **_canonical_claim_details(canonical),
                )
            )

    if not apply:
        return report

    for canonical, _auth_user, desired_app_metadata, desired_user_metadata in reconciliations:
        _apply_and_verify(
            client,
            canonical=canonical,
            desired_app_metadata=desired_app_metadata,
            desired_user_metadata=desired_user_metadata,
            scoped_metadata_key=scoped_metadata_key,
            phase=phase,
            report=report,
        )
    return report


def _list_platform_users(client: Any, *, page_size: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        response = (
            client.table("users")
            .select("id, tenant_id, role")
            .order("id")
            .range(start, start + page_size - 1)
            .execute()
        )
        page = list(getattr(response, "data", None) or [])
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size


def _list_auth_users(client: Any, *, page_size: int) -> list[Any]:
    users: list[Any] = []
    page = 1
    while True:
        batch = list(client.auth.admin.list_users(page=page, per_page=page_size) or [])
        users.extend(batch)
        if len(batch) < page_size:
            return users
        page += 1


def _index_platform_users(
    rows: list[dict[str, Any]], report: ReconciliationReport
) -> dict[str, CanonicalUser]:
    indexed: dict[str, CanonicalUser] = {}
    for index, row in enumerate(rows):
        user_id = _nonempty_string(row.get("id"))
        tenant_id = _nonempty_string(row.get("tenant_id"))
        role = _nonempty_string(row.get("role"))
        if not user_id or not tenant_id or not role:
            report.counts["structural_errors"] += 1
            report.records.append(
                {
                    "user_ref": _row_ref("platform", index),
                    "outcome": "error",
                    "code": "invalid_platform_user",
                }
            )
            continue
        if user_id in indexed:
            report.counts["structural_errors"] += 1
            report.records.append(_record(user_id, "error", code="duplicate_platform_user"))
            continue
        indexed[user_id] = CanonicalUser(user_id=user_id, tenant_id=tenant_id, role=role)
    return indexed


def _index_auth_users(users: list[Any], report: ReconciliationReport) -> dict[str, Any]:
    indexed: dict[str, Any] = {}
    for index, user in enumerate(users):
        user_id = _nonempty_string(getattr(user, "id", None))
        if not user_id:
            report.counts["structural_errors"] += 1
            report.records.append(
                {
                    "user_ref": _row_ref("auth", index),
                    "outcome": "error",
                    "code": "invalid_auth_user",
                }
            )
            continue
        if user_id in indexed:
            report.counts["structural_errors"] += 1
            report.records.append(_record(user_id, "error", code="duplicate_auth_user"))
            continue
        indexed[user_id] = user
    return indexed


def _valid_platform_admin_ids(
    auth_users: Iterable[Any], allowed_platform_admin_emails: Iterable[str]
) -> set[str]:
    allowlist = {email.strip().lower() for email in allowed_platform_admin_emails if email.strip()}
    valid_ids: set[str] = set()
    for user in auth_users:
        email = _nonempty_string(getattr(user, "email", None)).lower()
        app_metadata = _metadata(user, "app_metadata")
        if (
            email in allowlist
            and app_metadata.get("role") == "platform_admin"
            and app_metadata.get("platform_admin") is True
            and "tenant_id" not in app_metadata
            and not any(
                authorization_metadata_key(scope) in app_metadata for scope in AUTHORIZATION_SCOPES
            )
        ):
            valid_ids.add(str(user.id))
    return valid_ids


def _platform_admin_marker_ids(
    auth_users: Iterable[Any], allowed_platform_admin_emails: Iterable[str]
) -> set[str]:
    allowlist = {email.strip().lower() for email in allowed_platform_admin_emails if email.strip()}
    return {
        str(user.id)
        for user in auth_users
        if _nonempty_string(getattr(user, "email", None)).lower() in allowlist
        and _metadata(user, "app_metadata").get("role") == "platform_admin"
        and _metadata(user, "app_metadata").get("platform_admin") is True
    }


def _desired_metadata(
    canonical: CanonicalUser,
    auth_user: Any,
    *,
    scoped_metadata_key: str,
    phase: ReconciliationPhase,
) -> tuple[dict[str, Any], dict[str, Any]]:
    app_metadata = {
        **_metadata(auth_user, "app_metadata"),
        scoped_metadata_key: {
            "tenant_id": canonical.tenant_id,
            "role": canonical.role,
        },
    }
    for key in GLOBAL_APP_AUTHORIZATION_KEYS:
        app_metadata.pop(key, None)
    user_metadata = _metadata(auth_user, "user_metadata")
    if phase == "cleanup":
        for key in AUTHORIZATION_METADATA_KEYS:
            user_metadata.pop(key, None)
    return app_metadata, user_metadata


def _metadata_changes(
    auth_user: Any,
    canonical: CanonicalUser,
    *,
    scoped_metadata_key: str,
    phase: ReconciliationPhase,
) -> list[str]:
    changes: list[str] = []
    app_metadata = _metadata(auth_user, "app_metadata")
    user_metadata = _metadata(auth_user, "user_metadata")
    if app_metadata.get(scoped_metadata_key) != {
        "tenant_id": canonical.tenant_id,
        "role": canonical.role,
    }:
        changes.append("set_scoped_authorization")
    if any(key in app_metadata for key in GLOBAL_APP_AUTHORIZATION_KEYS):
        changes.append("remove_global_app_authorization")
    if phase == "cleanup":
        if "tenant_id" in user_metadata:
            changes.append("remove_user_tenant_id")
        if "role" in user_metadata:
            changes.append("remove_user_role")
    return changes


def _apply_and_verify(
    client: Any,
    *,
    canonical: CanonicalUser,
    desired_app_metadata: dict[str, Any],
    desired_user_metadata: dict[str, Any],
    scoped_metadata_key: str,
    phase: ReconciliationPhase,
    report: ReconciliationReport,
) -> None:
    try:
        payload: dict[str, Any] = {
            "app_metadata": {
                scoped_metadata_key: {
                    "tenant_id": canonical.tenant_id,
                    "role": canonical.role,
                },
                "tenant_id": None,
                "role": None,
                "platform_admin": None,
            }
        }
        if phase == "cleanup":
            # GoTrue merges metadata maps. Null values are required to delete keys.
            payload["user_metadata"] = {"tenant_id": None, "role": None}
        client.auth.admin.update_user_by_id(canonical.user_id, payload)
    except Exception as exc:
        report.counts["update_errors"] += 1
        report.records.append(
            _record(
                canonical.user_id,
                "error",
                code="update_failed",
                error_type=type(exc).__name__,
            )
        )
        return

    try:
        response = client.auth.admin.get_user_by_id(canonical.user_id)
        refetched = getattr(response, "user", None) or response
    except Exception as exc:
        report.counts["residual_errors"] += 1
        report.records.append(
            _record(
                canonical.user_id,
                "error",
                code="refetch_failed",
                error_type=type(exc).__name__,
            )
        )
        return

    residual_codes = _residual_codes(
        refetched,
        canonical=canonical,
        desired_app_metadata=desired_app_metadata,
        desired_user_metadata=desired_user_metadata,
        phase=phase,
    )
    if residual_codes:
        report.counts["residual_errors"] += 1
        report.records.append(
            _record(
                canonical.user_id,
                "error",
                code="verification_failed",
                residual_codes=residual_codes,
            )
        )
        return

    report.counts["updates_applied"] += 1
    report.records.append(
        _record(canonical.user_id, "updated", **_canonical_claim_details(canonical))
    )


def _residual_codes(
    auth_user: Any,
    *,
    canonical: CanonicalUser,
    desired_app_metadata: dict[str, Any],
    desired_user_metadata: dict[str, Any],
    phase: ReconciliationPhase,
) -> list[str]:
    codes: list[str] = []
    if _nonempty_string(getattr(auth_user, "id", None)) != canonical.user_id:
        codes.append("user_id_mismatch")
    app_metadata = _metadata(auth_user, "app_metadata")
    user_metadata = _metadata(auth_user, "user_metadata")
    if app_metadata != desired_app_metadata:
        codes.append("app_metadata_mismatch")
    if user_metadata != desired_user_metadata:
        codes.append("user_metadata_mismatch")
    if phase == "cleanup" and set(AUTHORIZATION_METADATA_KEYS) & user_metadata.keys():
        codes.append("authorization_in_user_metadata")
    return codes


def _metadata(user: Any, key: str) -> dict[str, Any]:
    value = getattr(user, key, None) or {}
    return dict(value) if isinstance(value, dict) else {}


def _nonempty_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _user_ref(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]
    return f"usr_{digest}"


def _row_ref(source: str, index: int) -> str:
    return f"{source}_row_{index + 1}"


def _record(user_id: str, outcome: str, **details: Any) -> dict[str, Any]:
    return {"user_ref": _user_ref(user_id), "outcome": outcome, **details}


def _canonical_claim_details(canonical: CanonicalUser) -> dict[str, str]:
    value = f"{canonical.tenant_id}\0{canonical.role}"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return {"canonical_claims_ref": f"clm_{digest}"}


def _normalized_environment(environment: str) -> str:
    return environment.strip().lower() or "development"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply planned metadata changes. The default is a read-only dry-run.",
    )
    parser.add_argument(
        "--phase",
        choices=("seed", "cleanup"),
        default="seed",
        help="Reconciliation phase. Seed is the safe, non-destructive default.",
    )
    parser.add_argument(
        "--strict-orphans",
        action="store_true",
        help="Treat Auth users without a platform row as blocking errors.",
    )
    parser.add_argument("--page-size", type=_positive_int, default=DEFAULT_PAGE_SIZE)
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    client: Any | None = None,
    environment: str | None = None,
    authorization_scope: str | None = None,
    allowed_platform_admin_emails: Iterable[str] | None = None,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
) -> int:
    args = _parse_args(argv)
    runtime_environ = os.environ if environ is None else environ
    output = sys.stdout if stdout is None else stdout

    if environment is None or allowed_platform_admin_emails is None:
        from app.core.config import settings

        environment = environment if environment is not None else settings.environment
        if allowed_platform_admin_emails is None:
            allowed_platform_admin_emails = settings.platform_admin_emails.split(",")

    normalized_environment = _normalized_environment(environment)
    if authorization_scope is None:
        from app.core.database import get_supabase_schema

        authorization_scope = get_supabase_schema()
    authorization_metadata_key(authorization_scope)

    if (
        args.apply
        and (
            normalized_environment in PRODUCTION_ENVIRONMENTS
            or authorization_scope == "transmuter"
            or args.phase == "cleanup"
        )
        and runtime_environ.get("CONFIRM_PROD_AUTH_RECONCILE") != "1"
    ):
        print(
            json.dumps(
                {
                    "status": "failed",
                    "mode": "apply",
                    "environment": normalized_environment,
                    "authorization_scope": authorization_scope,
                    "error": "production_confirmation_required",
                },
                sort_keys=True,
            ),
            file=output,
        )
        return 2

    if (
        args.apply
        and args.phase == "cleanup"
        and runtime_environ.get("CONFIRM_AUTH_CLAIM_CLEANUP") != "1"
    ):
        print(
            json.dumps(
                {
                    "status": "failed",
                    "mode": "apply",
                    "phase": "cleanup",
                    "environment": normalized_environment,
                    "authorization_scope": authorization_scope,
                    "error": "cleanup_confirmation_required",
                },
                sort_keys=True,
            ),
            file=output,
        )
        return 2

    if client is None:
        from app.core.database import get_supabase_admin

        client = get_supabase_admin()

    report = reconcile_auth_claims(
        client,
        apply=args.apply,
        environment=normalized_environment,
        allowed_platform_admin_emails=allowed_platform_admin_emails,
        page_size=args.page_size,
        phase=args.phase,
        authorization_scope=authorization_scope,
        strict_orphans=args.strict_orphans,
    )
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True), file=output)
    return 1 if report.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
