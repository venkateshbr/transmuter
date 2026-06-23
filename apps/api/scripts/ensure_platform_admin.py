"""Ensure the configured platform admin Supabase Auth user exists.

Usage:
    cd apps/api
    PLATFORM_ADMIN_BOOTSTRAP_PASSWORD='...' uv run python scripts/ensure_platform_admin.py
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parents[3]
api_root = Path(__file__).resolve().parents[1]
load_dotenv(repo_root / ".env")
load_dotenv(api_root / ".env", override=True)

from app.bootstrap.platform_admin import ensure_platform_admin_user  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import get_supabase_admin  # noqa: E402


def main() -> int:
    result = ensure_platform_admin_user(
        get_supabase_admin(),
        allowed_emails=settings.platform_admin_emails,
        bootstrap_email=settings.platform_admin_bootstrap_email,
        bootstrap_password=settings.platform_admin_bootstrap_password,
        enabled=settings.platform_admin_bootstrap_enabled,
    )
    print(f"Platform admin bootstrap status: {result.status}")
    if result.email:
        print(f"Email: {result.email}")
    if result.user_id:
        print(f"User id: {result.user_id}")
    if result.message:
        print(result.message)
    return 1 if result.status in {"missing_email", "missing_password", "misconfigured"} else 0


if __name__ == "__main__":
    raise SystemExit(main())

