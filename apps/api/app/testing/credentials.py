"""Local-only credential loading for real fixture-backed tests.

Secrets are resolved from environment variables or the ignored
``scratch/test-credentials.json`` file. No committed fallback password exists.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def fixture_credentials(
    *, tenant: str = "acme", role: str = "transformation_office"
) -> tuple[str, str]:
    env_email = os.environ.get("TRANSMUTER_TEST_EMAIL") or os.environ.get("TRANSMUTER_E2E_EMAIL")
    env_password = os.environ.get("TRANSMUTER_TEST_PASSWORD") or os.environ.get(
        "TRANSMUTER_E2E_PASSWORD"
    )
    if env_email and env_password:
        return env_email, env_password
    if env_email or env_password:
        raise RuntimeError("Both fixture email and password environment variables are required")

    configured_path = os.environ.get("TRANSMUTER_TEST_CREDENTIALS_FILE")
    path = (
        Path(configured_path).expanduser()
        if configured_path
        else Path(__file__).resolve().parents[4] / "scratch" / "test-credentials.json"
    )
    if not path.is_file():
        raise RuntimeError(
            "Fixture credentials are required via environment variables or "
            "scratch/test-credentials.json"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    tenant_admin = str((payload.get("tenant_admins") or {}).get(tenant) or "")
    password = str(payload.get("shared_fixture_password") or "")
    if not tenant_admin or not password:
        raise RuntimeError("Local fixture credential file is missing required fields")
    domain = tenant_admin.rsplit("@", 1)[-1]
    role_email = f"rbac-{role.replace('_', '-')}@{domain}"
    return role_email, password
