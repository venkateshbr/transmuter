"""Governance & Stage Gate integration tests — Karya #48."""

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def get_token(email: str = "admin@ishirock.dev") -> str:
    resp = client.post("/auth/login", json={"email": email, "password": "Transmuter2026!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return get_token("admin@ishirock.dev")


def auth(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def init_id(admin_token):
    # Create initiative
    resp = client.post(
        "/initiatives",
        json={"name": "Governance Test", "priority": "high", "country": "Singapore"},
        headers=auth(admin_token),
    )
    iid = resp.json()["id"]

    # Create a gate for it (Gate 1: Concept -> Business Case)
    # This usually happens via setup/seeding, but we'll do it manually here if needed or assume existence.
    # The stage_gates table needs an entry.
    # However, since we're using real DB, let's just insert it.
    from app.core.database import get_supabase_admin

    supabase = get_supabase_admin()
    user_resp = client.get("/auth/me", headers=auth(admin_token))
    tid = user_resp.json()["tenant_id"]

    supabase.table("stage_gates").insert(
        {
            "tenant_id": tid,
            "initiative_id": iid,
            "gate_number": 1,
            "label": "Concept Approval",
            "from_stage": "scoping",
            "to_stage": "in_progress",
        }
    ).execute()

    return iid


def test_governance_lifecycle(admin_token, init_id):
    # 1. Fetch Status
    resp = client.get(f"/initiatives/{init_id}/governance", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["gates"]) == 1
    assert data["active_submission"] is None

    # 2. Submit Gate 1
    resp = client.post(
        f"/initiatives/{init_id}/gates/1/submit",
        json={
            "criteria_snapshot": [{"id": "c1", "label": "Concept Doc", "ticked": True}],
            "commentary": "Ready for review",
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    sub = resp.json()
    sub_id = sub["id"]
    assert sub["decision"] == "pending"
    assert sub["initiative_code"].startswith("TRN-")
    assert sub["initiative_name"] == "Governance Test"

    portfolio_resp = client.get("/portfolio/governance", headers=auth(admin_token))
    assert portfolio_resp.status_code == 200
    portfolio_submission = next(
        item for item in portfolio_resp.json()["submissions"] if item["id"] == sub_id
    )
    assert portfolio_submission["initiative_code"] == sub["initiative_code"]
    assert portfolio_submission["initiative_name"] == "Governance Test"

    # 3. Decision - Try with non-admin (if possible) or just verify admin logic
    # In our seed, admin@ishirock.dev HAS transformation_office role (standard setup).
    resp = client.patch(
        f"/governance/submissions/{sub_id}/decide",
        json={"decision": "approved", "commentary": "Good job"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "approved"

    # 4. Verify Initiative Stage Updated
    resp = client.get(f"/initiatives/{init_id}", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["stage"] == "in_progress"
