"""Status Updates API integration tests — Karya #46."""

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)

def get_token(email: str = "admin@ishirock.dev", password: str = "Transmuter2026!") -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return get_token("admin@ishirock.dev")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def init_id(admin_token: str) -> str:
    resp = client.post(
        "/initiatives",
        json={"name": "Status Update Test Initiative", "priority": "high", "country": "Japan"},
        headers=auth(admin_token),
    )
    return resp.json()["id"]


def test_status_update_crud_and_submission(admin_token: str, init_id: str) -> None:
    # 1. Create a Draft Status Update
    resp = client.post(
        f"/initiatives/{init_id}/status-updates",
        json={
            "rag_status": "amber",
            "summary": "Project is slightly delayed.",
            "is_draft": True
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    draft = resp.json()
    draft_id = draft["id"]
    assert draft["is_draft"] is True
    assert draft["submitted_at"] is None
    
    # 2. Try to create another draft (should fail 409 Conflict)
    resp = client.post(
        f"/initiatives/{init_id}/status-updates",
        json={
            "rag_status": "green",
            "summary": "Another draft",
            "is_draft": True
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 409

    # 3. Retrieve the Draft
    resp = client.get(f"/initiatives/{init_id}/status-updates/draft", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["id"] == draft_id

    # 4. History should be empty because it only contains submitted updates
    resp = client.get(f"/initiatives/{init_id}/status-updates", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    # 5. Submit the Draft
    resp = client.put(
        f"/initiatives/{init_id}/status-updates/{draft_id}",
        json={
            "rag_status": "green",
            "summary": "Project is back on track.",
            "is_draft": False
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    submitted = resp.json()
    assert submitted["is_draft"] is False
    assert submitted["submitted_at"] is not None

    # 6. Draft should now be None
    resp = client.get(f"/initiatives/{init_id}/status-updates/draft", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() is None

    # 7. History should now contain the submitted update
    resp = client.get(f"/initiatives/{init_id}/status-updates", headers=auth(admin_token))
    assert resp.status_code == 200
    history = resp.json()
    assert history["total"] == 1
    assert history["items"][0]["id"] == draft_id

    # 8. Create a new update directly as submitted
    resp = client.post(
        f"/initiatives/{init_id}/status-updates",
        json={
            "rag_status": "green",
            "summary": "Everything is still fine.",
            "is_draft": False
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    direct_submit = resp.json()
    assert direct_submit["is_draft"] is False
    assert direct_submit["submitted_at"] is not None

    # 9. History should now have 2 updates (most recent first)
    resp = client.get(f"/initiatives/{init_id}/status-updates", headers=auth(admin_token))
    assert resp.status_code == 200
    history = resp.json()
    assert history["total"] == 2
    assert history["items"][0]["id"] == direct_submit["id"]  # newest first
