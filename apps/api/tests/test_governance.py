"""Governance & Stage Gate integration tests — Karya #48."""

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.core.config import settings
from app.core.database import get_supabase_admin, get_supabase_schema
from app.main import app

client = TestClient(app, raise_server_exceptions=True)
REPO_ROOT = Path(__file__).resolve().parents[3]
ORIGINAL_SUPABASE_SCHEMA = settings.supabase_schema


@dataclass(frozen=True)
class CredentialCandidate:
    label: str
    email: str
    password: str
    schema: str | None = None


def _schema_from_url(value: str | None) -> str | None:
    if not value:
        return None
    host = urlparse(value).hostname or ""
    if host == "transmuter-dev.ishirock.tech":
        return "transmuter_dev"
    if host == "transmuter.ishirock.tech":
        return "transmuter"
    return None


def _credentials_from_file(path: Path, label: str) -> CredentialCandidate | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    email = data.get("adminEmail") or data.get("email")
    password = data.get("adminPassword") or data.get("password")
    if email and password:
        schema = data.get("supabaseSchema") or _schema_from_url(data.get("uiBaseUrl"))
        return CredentialCandidate(
            label=label,
            email=str(email),
            password=str(password),
            schema=str(schema) if schema else None,
        )
    return None


def _latest_launch_credentials() -> CredentialCandidate | None:
    recordings_root = REPO_ROOT / "scratch" / "launch-ui-recordings"
    candidates = sorted(
        recordings_root.glob("acme-launch-*/result.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for result_path in candidates:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "passed":
            continue
        credentials_path = result.get("credentialsPath")
        path = (
            Path(credentials_path) if credentials_path else result_path.parent / "credentials.json"
        )
        if not path.is_absolute():
            path = REPO_ROOT / path
        credentials = _credentials_from_file(
            path, f"latest passed launch run: {result_path.parent.name}"
        )
        if credentials:
            return credentials
    return None


def _credential_candidates() -> list[CredentialCandidate]:
    candidates: list[CredentialCandidate] = []
    for label, email_key, password_key, schema_key in (
        (
            "TRANSMUTER_TEST",
            "TRANSMUTER_TEST_EMAIL",
            "TRANSMUTER_TEST_PASSWORD",
            "TRANSMUTER_TEST_SUPABASE_SCHEMA",
        ),
        (
            "TRANSMUTER_E2E",
            "TRANSMUTER_E2E_EMAIL",
            "TRANSMUTER_E2E_PASSWORD",
            "TRANSMUTER_E2E_SUPABASE_SCHEMA",
        ),
    ):
        email = os.environ.get(email_key)
        password = os.environ.get(password_key)
        if email and password:
            candidates.append(
                CredentialCandidate(
                    label=label,
                    email=email,
                    password=password,
                    schema=os.environ.get(schema_key),
                )
            )

    for env_key, schema_key in (
        (
            "TRANSMUTER_GOVERNANCE_TEST_CREDENTIALS_PATH",
            "TRANSMUTER_GOVERNANCE_TEST_SUPABASE_SCHEMA",
        ),
        ("TRANSMUTER_E2E_CREDENTIALS_PATH", "TRANSMUTER_E2E_SUPABASE_SCHEMA"),
    ):
        value = os.environ.get(env_key)
        if not value:
            continue
        credentials = _credentials_from_file(Path(value), env_key)
        if credentials:
            schema = os.environ.get(schema_key) or credentials.schema
            candidates.append(
                CredentialCandidate(
                    label=credentials.label,
                    email=credentials.email,
                    password=credentials.password,
                    schema=schema,
                )
            )

    latest = _latest_launch_credentials()
    if latest:
        candidates.append(latest)
    return candidates


def _set_supabase_schema(schema: str | None) -> None:
    settings.supabase_schema = schema if schema is not None else ORIGINAL_SUPABASE_SCHEMA
    get_supabase_admin.cache_clear()


def _candidate_summary(candidate: CredentialCandidate) -> str:
    schema = candidate.schema or get_supabase_schema()
    return f"{candidate.label} ({candidate.email}, schema={schema})"


def get_token() -> tuple[str, CredentialCandidate]:
    candidates = _credential_candidates()
    if not candidates:
        raise AssertionError(
            "No E2E governance test credentials found. Run the launch E2E flow first or set "
            "TRANSMUTER_E2E_EMAIL and TRANSMUTER_E2E_PASSWORD."
        )

    failures: list[str] = []
    for candidate in candidates:
        _set_supabase_schema(candidate.schema)
        try:
            resp = client.post(
                "/auth/login",
                json={"email": candidate.email, "password": candidate.password},
            )
        except Exception as exc:
            failures.append(f"{_candidate_summary(candidate)} -> {type(exc).__name__}")
            continue
        if resp.status_code == 200:
            return resp.json()["access_token"], candidate
        failures.append(f"{_candidate_summary(candidate)} -> {resp.status_code}: {resp.text}")
    raise AssertionError(
        "Unable to authenticate E2E governance test user. Tried: " + "; ".join(failures)
    )


@pytest.fixture(scope="module")
def admin_token() -> Iterator[str]:
    original_schema = settings.supabase_schema
    try:
        token, _candidate = get_token()
        yield token
    finally:
        settings.supabase_schema = original_schema
        get_supabase_admin.cache_clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def init_id(admin_token: str) -> tuple[str, str]:
    # Create initiative
    initiative_name = f"Governance Test {uuid4().hex[:8]}"
    resp = client.post(
        "/initiatives",
        json={"name": initiative_name, "priority": "high", "country": "Singapore"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 201, resp.text
    iid = resp.json()["id"]

    return iid, initiative_name


def _criteria_snapshot(criteria: list[dict]) -> list[dict]:
    if not criteria:
        return [{"id": "c1", "criterion_id": "c1", "label": "Concept Doc", "ticked": True}]
    return [
        {
            "id": item.get("id") or item.get("criterion_id"),
            "criterion_id": item.get("criterion_id") or item.get("id"),
            "label": item["label"],
            "guidance": item.get("guidance"),
            "sort_order": item.get("sort_order", index),
            "ticked": True,
        }
        for index, item in enumerate(criteria)
    ]


def test_governance_lifecycle(admin_token: str, init_id: tuple[str, str]) -> None:
    initiative_id, initiative_name = init_id
    # 1. Fetch Status
    resp = client.get(f"/initiatives/{initiative_id}/governance", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    gate = next(item for item in data["gates"] if item["gate_number"] == 1)
    assert data["active_submission"] is None

    criteria_resp = client.get(
        f"/initiatives/{initiative_id}/gates/1/criteria",
        headers=auth(admin_token),
    )
    assert criteria_resp.status_code == 200

    # 2. Submit Gate 1
    resp = client.post(
        f"/initiatives/{initiative_id}/gates/1/submit",
        json={
            "criteria_snapshot": _criteria_snapshot(criteria_resp.json()),
            "commentary": "Ready for review",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    sub = resp.json()
    sub_id = sub["id"]
    assert sub["decision"] == "pending"
    assert sub["initiative_code"].startswith("TRN-")
    assert sub["initiative_name"] == initiative_name

    portfolio_resp = client.get("/portfolio/governance", headers=auth(admin_token))
    assert portfolio_resp.status_code == 200
    portfolio_submission = next(
        item for item in portfolio_resp.json()["submissions"] if item["id"] == sub_id
    )
    assert portfolio_submission["initiative_code"] == sub["initiative_code"]
    assert portfolio_submission["initiative_name"] == initiative_name

    # 3. Decision - the selected user must be a transformation office user.
    resp = client.patch(
        f"/governance/submissions/{sub_id}/decide",
        json={"decision": "approved", "commentary": "Good job"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "approved"

    # 4. Verify Initiative Stage Updated
    resp = client.get(f"/initiatives/{initiative_id}", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["stage"] == gate["to_stage"]
