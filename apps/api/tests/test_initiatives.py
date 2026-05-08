"""Initiative API integration tests — Aksha #36."""

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.main import app

client = TestClient(app, raise_server_exceptions=True)

ORG_ID = "9a739f1b-cba1-45e9-af8d-ec0c9807f56e"


# ── Auth helper ───────────────────────────────────────────────────────────────


def get_token(email: str = "admin@ishirock.dev", password: str = "Transmuter2026!") -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return get_token("admin@ishirock.dev")


@pytest.fixture(scope="module")
def owner_token() -> str:
    return get_token("owner.revenue@ishirock.dev")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── List tests ────────────────────────────────────────────────────────────────


def test_list_initiatives_returns_seeded_data(admin_token: str) -> None:
    resp = client.get("/initiatives", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5
    codes = [i["initiative_code"] for i in data["items"]]
    assert "TRN-001" in codes
    assert "TRN-004" in codes


def test_list_filter_by_rag(admin_token: str) -> None:
    resp = client.get("/initiatives?rag_status=red", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert all(i["rag_status"] == "red" for i in data["items"])
    assert data["total"] >= 1


def test_list_filter_by_stage(admin_token: str) -> None:
    resp = client.get("/initiatives?stage=scoping", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert all(i["stage"] == "scoping" for i in data["items"])


def test_list_search(admin_token: str) -> None:
    resp = client.get("/initiatives?search=ERP", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any("ERP" in i["name"] for i in data["items"])


def test_list_requires_auth() -> None:
    resp = client.get("/initiatives")
    # FastAPI HTTPBearer returns 403 when Authorization header is missing
    assert resp.status_code in (401, 403)


# ── Create + Get + Update ─────────────────────────────────────────────────────


def test_create_get_update_delete(admin_token: str) -> None:
    # Create
    resp = client.post(
        "/initiatives",
        json={"name": "Test Initiative from Pytest", "priority": "low", "country": "Singapore"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    created = resp.json()
    iid = created["id"]
    code = created["initiative_code"]
    assert code.startswith("TRN-")
    assert created["stage"] == "scoping"
    assert created["rag_status"] == "green"

    # Get
    resp = client.get(f"/initiatives/{iid}", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Initiative from Pytest"

    # Update
    resp = client.put(
        f"/initiatives/{iid}",
        json={"name": "Updated by Test", "priority": "high"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == "high"
    assert resp.json()["name"] == "Updated by Test"

    # Archive
    resp = client.post(f"/initiatives/{iid}/archive", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["archived_at"] is not None

    # Archived initiative excluded from default list
    resp = client.get("/initiatives", headers=auth(admin_token))
    codes_in_list = [i["initiative_code"] for i in resp.json()["items"]]
    assert code not in codes_in_list

    # Delete (TO only)
    resp = client.delete(f"/initiatives/{iid}", headers=auth(admin_token))
    assert resp.status_code == 204

    # Confirm deleted
    resp = client.get(f"/initiatives/{iid}", headers=auth(admin_token))
    assert resp.status_code == 404


def test_initiative_code_unique_and_sequential(admin_token: str) -> None:
    codes = []
    for _ in range(3):
        resp = client.post(
            "/initiatives",
            json={"name": f"Sequential test {len(codes)}"},
            headers=auth(admin_token),
        )
        assert resp.status_code == 201
        codes.append(resp.json()["initiative_code"])

    # All codes unique
    assert len(set(codes)) == 3
    # All start with TRN-
    assert all(c.startswith("TRN-") for c in codes)

    # Clean up
    for resp_data in [
        client.get("/initiatives?search=Sequential+test", headers=auth(admin_token)).json()["items"]
    ]:
        for item in resp_data:
            client.delete(f"/initiatives/{item['id']}", headers=auth(admin_token))


def test_delete_requires_admin_role(owner_token: str) -> None:
    """Initiative owners cannot delete initiatives."""
    # Get any initiative to try deleting
    resp = client.get("/initiatives", headers=auth(owner_token))
    if not resp.json()["items"]:
        pytest.skip("No initiatives available for this test")
    iid = resp.json()["items"][0]["id"]
    resp = client.delete(f"/initiatives/{iid}", headers=auth(owner_token))
    assert resp.status_code == 403


# ── CSV Export ────────────────────────────────────────────────────────────────


def test_export_csv(admin_token: str) -> None:
    resp = client.get("/initiatives/export", headers=auth(admin_token))
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    assert lines[0].startswith("initiative_code")  # header row
    assert len(lines) >= 6  # header + 5 seeded initiatives
