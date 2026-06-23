"""One-time Supabase Auth email rotation for the platform admin user.

Usage:
    cd apps/api
    PLATFORM_ADMIN_PREVIOUS_EMAIL='admin@ishirock.com' \
    PLATFORM_ADMIN_BOOTSTRAP_EMAIL='venkatesh@ishirock.com' \
    uv run python scripts/rotate_platform_admin_email.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parents[3]
api_root = Path(__file__).resolve().parents[1]
load_dotenv(repo_root / ".env")
load_dotenv(api_root / ".env", override=True)

from app.bootstrap.platform_admin import rotate_platform_admin_email  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import get_supabase_admin  # noqa: E402


def main() -> int:
    result = rotate_platform_admin_email(
        get_supabase_admin(),
        previous_email=settings.platform_admin_previous_email,
        allowed_emails=settings.platform_admin_emails,
        target_email=settings.platform_admin_bootstrap_email,
        bootstrap_password=settings.platform_admin_bootstrap_password,
    )
    print(f"Platform admin rotation status: {result.status}")
    if result.previous_email:
        print(f"Previous email: {result.previous_email}")
    if result.target_email:
        print(f"Target email: {result.target_email}")
    if result.user_id:
        print(f"User id: {result.user_id}")
    if result.message:
        print(result.message)
    return (
        1
        if result.status
        in {"missing_email", "missing_password", "missing_previous_email", "misconfigured"}
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())

