"""Risk API integration tests — Karya #44."""

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
        json={"name": "Risk Test Initiative", "priority": "low", "country": "Singapore"},
        headers=auth(admin_token),
    )
    return resp.json()["id"]


def test_risk_crud_and_auto_rating(admin_token: str, init_id: str) -> None:
    # High impact x High likelihood = High rating
    resp = client.post(
        f"/initiatives/{init_id}/risks",
        json={
            "description": "Server failure during peak",
            "type": "technology",
            "impact": "high",
            "likelihood": "high"
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    risk = resp.json()
    risk_id = risk["id"]
    assert risk["rating"] == "high"

    # Update: High impact x Low likelihood = Medium rating
    resp = client.put(
        f"/initiatives/{init_id}/risks/{risk_id}",
        json={"likelihood": "low"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == "medium"
    assert resp.json()["likelihood"] == "low"
    assert resp.json()["impact"] == "high"  # preserved

    # Update: Low impact x Low likelihood = Low rating
    resp = client.put(
        f"/initiatives/{init_id}/risks/{risk_id}",
        json={"impact": "low"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == "low"

    # List Risks for Initiative
    resp = client.get(f"/initiatives/{init_id}/risks", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(r["id"] == risk_id for r in data["items"])


def test_risk_heatmap_and_portfolio_list(admin_token: str, init_id: str) -> None:
    # Create another risk to ensure matrix is populated
    client.post(
        f"/initiatives/{init_id}/risks",
        json={
            "description": "Vendor bankruptcy",
            "type": "financial",
            "impact": "high",
            "likelihood": "medium" # HxM -> High
        },
        headers=auth(admin_token),
    )
    
    # Portfolio List filters
    resp = client.get("/portfolio/risks?rating=high", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    # At least the vendor bankruptcy risk should be returned
    assert data["total"] >= 1
    for r in data["items"]:
        assert r["rating"] == "high"
        
    # Heatmap
    resp = client.get("/portfolio/risks/heatmap", headers=auth(admin_token))
    assert resp.status_code == 200
    heatmap = resp.json()
    
    assert "cells" in heatmap
    assert "total_open_risks" in heatmap
    assert len(heatmap["cells"]) == 9 # 3x3 matrix
    
    # Check that HxM has count >= 1
    h_m_cell = next(
        c for c in heatmap["cells"]
        if c["impact"] == "high" and c["likelihood"] == "medium"
    )
    assert h_m_cell["count"] >= 1
