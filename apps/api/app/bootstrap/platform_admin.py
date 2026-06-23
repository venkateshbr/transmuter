"""Idempotent Supabase Auth bootstrap for Transmuter platform administrators."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from supabase import Client

logger = logging.getLogger(__name__)

BootstrapStatus = Literal[
    "created",
    "disabled",
    "metadata_updated",
    "missing_email",
    "missing_password",
    "misconfigured",
    "skipped",
]
RotationStatus = Literal[
    "missing_previous_email",
    "renamed",
    "target_created",
    "target_exists",
]


@dataclass(frozen=True)
class PlatformAdminBootstrapResult:
    status: BootstrapStatus
    email: str | None = None
    user_id: str | None = None
    message: str = ""


@dataclass(frozen=True)
class PlatformAdminRotationResult:
    status: RotationStatus | BootstrapStatus
    previous_email: str | None = None
    target_email: str | None = None
    user_id: str | None = None
    message: str = ""


def ensure_platform_admin_on_startup() -> PlatformAdminBootstrapResult:
    """Run the configured platform-admin Auth bootstrap during API startup.

    Startup must remain resilient if Supabase Auth has a transient problem; the
    platform admin route still enforces metadata and allowlist checks at request
    time.
    """

    from app.core.config import settings
    from app.core.database import get_supabase_admin

    preflight = _startup_preflight(
        allowed_emails=settings.platform_admin_emails,
        bootstrap_email=settings.platform_admin_bootstrap_email,
        enabled=settings.platform_admin_bootstrap_enabled,
    )
    if preflight is not None:
        _log_result(preflight)
        return preflight

    try:
        result = ensure_platform_admin_user(
            get_supabase_admin(),
            allowed_emails=settings.platform_admin_emails,
            bootstrap_email=settings.platform_admin_bootstrap_email,
            bootstrap_password=settings.platform_admin_bootstrap_password,
            enabled=settings.platform_admin_bootstrap_enabled,
        )
    except Exception:
        logger.exception("Platform admin bootstrap failed during API startup.")
        return PlatformAdminBootstrapResult(
            status="misconfigured",
            message="Platform admin bootstrap failed during API startup.",
        )

    _log_result(result)
    return result


def _startup_preflight(
    *,
    allowed_emails: str,
    bootstrap_email: str,
    enabled: bool,
) -> PlatformAdminBootstrapResult | None:
    if not enabled:
        return PlatformAdminBootstrapResult(status="disabled", message="Bootstrap disabled.")

    allowlist = _parse_emails(allowed_emails)
    email = _target_email(allowlist, bootstrap_email)
    if not email:
        return PlatformAdminBootstrapResult(
            status="missing_email",
            message="Set PLATFORM_ADMIN_EMAILS or PLATFORM_ADMIN_BOOTSTRAP_EMAIL.",
        )
    if email not in allowlist:
        return PlatformAdminBootstrapResult(
            status="misconfigured",
            email=email,
            message=(
                "PLATFORM_ADMIN_BOOTSTRAP_EMAIL must also be present in PLATFORM_ADMIN_EMAILS."
            ),
        )
    return None


def _log_result(result: PlatformAdminBootstrapResult) -> None:
    if result.status in {"created", "metadata_updated"}:
        logger.info("Platform admin bootstrap %s for %s.", result.status, result.email)
    elif result.status in {"missing_password", "misconfigured"}:
        logger.warning("Platform admin bootstrap skipped: %s", result.message)
    else:
        logger.debug("Platform admin bootstrap status=%s email=%s", result.status, result.email)


def ensure_platform_admin_user(
    client: Client,
    *,
    allowed_emails: str,
    bootstrap_email: str = "",
    bootstrap_password: str = "",
    enabled: bool = True,
) -> PlatformAdminBootstrapResult:
    """Ensure exactly the configured platform admin Auth user can receive platform access.

    This function only uses Supabase Auth admin APIs. It deliberately does not
    write to Transmuter's tenant-scoped `users` table or seed any tenant data.
    """

    if not enabled:
        return PlatformAdminBootstrapResult(status="disabled", message="Bootstrap disabled.")

    allowlist = _parse_emails(allowed_emails)
    email = _target_email(allowlist, bootstrap_email)
    if not email:
        return PlatformAdminBootstrapResult(
            status="missing_email",
            message="Set PLATFORM_ADMIN_EMAILS or PLATFORM_ADMIN_BOOTSTRAP_EMAIL.",
        )
    if email not in allowlist:
        return PlatformAdminBootstrapResult(
            status="misconfigured",
            email=email,
            message=(
                "PLATFORM_ADMIN_BOOTSTRAP_EMAIL must also be present in PLATFORM_ADMIN_EMAILS."
            ),
        )

    user = _find_auth_user_by_email(client, email)
    if user is not None:
        user_id = str(user.id)
        app_metadata = _metadata(user, "app_metadata")
        user_metadata = _metadata(user, "user_metadata")
        if _has_complete_platform_metadata(app_metadata):
            return PlatformAdminBootstrapResult(status="skipped", email=email, user_id=user_id)

        client.auth.admin.update_user_by_id(
            user_id,
            {
                "app_metadata": {
                    **app_metadata,
                    "role": "platform_admin",
                    "platform_admin": True,
                },
                "user_metadata": {
                    **user_metadata,
                    "role": "platform_admin",
                },
            },
        )
        return PlatformAdminBootstrapResult(
            status="metadata_updated",
            email=email,
            user_id=user_id,
            message="Existing Auth user metadata updated.",
        )

    if not bootstrap_password:
        return PlatformAdminBootstrapResult(
            status="missing_password",
            email=email,
            message=(
                "Platform admin Auth user is missing. Set "
                "PLATFORM_ADMIN_BOOTSTRAP_PASSWORD to create it."
            ),
        )

    response = client.auth.admin.create_user(
        {
            "email": email,
            "email_confirm": True,
            "password": bootstrap_password,
            "user_metadata": {"role": "platform_admin"},
            "app_metadata": {"role": "platform_admin", "platform_admin": True},
        }
    )
    user_id = _created_user_id(response)
    return PlatformAdminBootstrapResult(status="created", email=email, user_id=user_id)


def rotate_platform_admin_email(
    client: Client,
    *,
    previous_email: str,
    allowed_emails: str,
    target_email: str = "",
    bootstrap_password: str = "",
) -> PlatformAdminRotationResult:
    previous = previous_email.strip().lower()
    if not previous:
        return PlatformAdminRotationResult(
            status="missing_previous_email",
            message="Set PLATFORM_ADMIN_PREVIOUS_EMAIL before rotating.",
        )

    allowlist = _parse_emails(allowed_emails)
    target = _target_email(allowlist, target_email)
    if not target:
        return PlatformAdminRotationResult(
            status="missing_email",
            previous_email=previous,
            message="Set PLATFORM_ADMIN_EMAILS or PLATFORM_ADMIN_BOOTSTRAP_EMAIL.",
        )
    if target not in allowlist:
        return PlatformAdminRotationResult(
            status="misconfigured",
            previous_email=previous,
            target_email=target,
            message=(
                "PLATFORM_ADMIN_BOOTSTRAP_EMAIL must also be present in PLATFORM_ADMIN_EMAILS."
            ),
        )

    previous_user = _find_auth_user_by_email(client, previous)
    target_user = _find_auth_user_by_email(client, target)
    if target_user is not None:
        ensured = ensure_platform_admin_user(
            client,
            allowed_emails=allowed_emails,
            bootstrap_email=target,
            bootstrap_password=bootstrap_password,
        )
        if previous_user is not None and str(previous_user.id) != str(target_user.id):
            _revoke_platform_admin_metadata(client, previous_user)
        return PlatformAdminRotationResult(
            status="target_exists",
            previous_email=previous,
            target_email=target,
            user_id=str(target_user.id),
            message=ensured.message or "Target platform admin Auth user already exists.",
        )

    if previous_user is not None:
        user_id = str(previous_user.id)
        client.auth.admin.update_user_by_id(
            user_id,
            {
                "email": target,
                "email_confirm": True,
                "app_metadata": {
                    **_metadata(previous_user, "app_metadata"),
                    "role": "platform_admin",
                    "platform_admin": True,
                },
                "user_metadata": {
                    **_metadata(previous_user, "user_metadata"),
                    "role": "platform_admin",
                },
            },
        )
        return PlatformAdminRotationResult(
            status="renamed",
            previous_email=previous,
            target_email=target,
            user_id=user_id,
            message="Previous platform admin Auth user email renamed.",
        )

    created = ensure_platform_admin_user(
        client,
        allowed_emails=allowed_emails,
        bootstrap_email=target,
        bootstrap_password=bootstrap_password,
    )
    return PlatformAdminRotationResult(
        status="target_created" if created.status == "created" else created.status,
        previous_email=previous,
        target_email=target,
        user_id=created.user_id,
        message=created.message,
    )


def _parse_emails(value: str) -> tuple[str, ...]:
    return tuple(item.strip().lower() for item in value.split(",") if item.strip())


def _target_email(allowlist: tuple[str, ...], bootstrap_email: str) -> str:
    configured = bootstrap_email.strip().lower()
    if configured:
        return configured
    return allowlist[0] if allowlist else ""


def _find_auth_user_by_email(client: Client, email: str) -> Any | None:
    page = 1
    per_page = 100
    while True:
        users = client.auth.admin.list_users(page=page, per_page=per_page)
        for user in users:
            if (getattr(user, "email", "") or "").lower() == email:
                return user
        if len(users) < per_page:
            return None
        page += 1


def _metadata(user: Any, key: str) -> dict[str, Any]:
    value = getattr(user, key, None) or {}
    return dict(value) if isinstance(value, dict) else {}


def _has_complete_platform_metadata(app_metadata: dict[str, Any]) -> bool:
    return (
        app_metadata.get("role") == "platform_admin" and app_metadata.get("platform_admin") is True
    )


def _created_user_id(response: Any) -> str | None:
    user = getattr(response, "user", None)
    user_id = getattr(user, "id", None) or getattr(response, "id", None)
    return str(user_id) if user_id else None


def _revoke_platform_admin_metadata(client: Client, user: Any) -> None:
    app_metadata = _metadata(user, "app_metadata")
    user_metadata = _metadata(user, "user_metadata")
    if app_metadata.get("role") == "platform_admin":
        app_metadata.pop("role", None)
    if app_metadata.get("platform_admin") is True:
        app_metadata.pop("platform_admin", None)
    if user_metadata.get("role") == "platform_admin":
        user_metadata.pop("role", None)
    client.auth.admin.update_user_by_id(
        str(user.id),
        {
            "app_metadata": app_metadata,
            "user_metadata": user_metadata,
        },
    )
