"""KPI API integration tests — Karya #43."""

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
        json={"name": "KPI Test Initiative", "priority": "low", "country": "Singapore"},
        headers=auth(admin_token),
    )
    return resp.json()["id"]


def test_kpi_crud(admin_token: str, init_id: str) -> None:
    # Create KPI
    resp = client.post(
        f"/initiatives/{init_id}/kpis",
        json={
            "name": "EBITDA Margin",
            "type": "gross_margin",
            "frequency": "quarterly",
            "unit": "%"
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    kpi = resp.json()
    kpi_id = kpi["id"]
    assert kpi["name"] == "EBITDA Margin"

    # Update KPI
    resp = client.put(
        f"/initiatives/{init_id}/kpis/{kpi_id}",
        json={"name": "EBITDA Margin (%)", "frequency": "monthly"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "EBITDA Margin (%)"
    assert resp.json()["frequency"] == "monthly"

    # List KPIs
    resp = client.get(f"/initiatives/{init_id}/kpis", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(k["id"] == kpi_id for k in data["items"])


def test_kpi_entries_upsert(admin_token: str, init_id: str) -> None:
    # Create KPI
    kpi = client.post(
        f"/initiatives/{init_id}/kpis",
        json={"name": "Revenue Target", "type": "operational", "unit": "USD"},
        headers=auth(admin_token),
    ).json()
    kpi_id = kpi["id"]

    # Upsert entries
    resp = client.put(
        f"/initiatives/{init_id}/kpis/{kpi_id}/entries",
        json=[
            {"year": 2026, "quarter": 1, "value_base": "1000", "value_actual": "1100"},
            {"year": 2026, "quarter": 2, "value_base": "1200"} # No actuals yet
        ],
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 2
    
    q1 = next(e for e in entries if e["quarter"] == 1)
    q2 = next(e for e in entries if e["quarter"] == 2)
    assert float(q1["value_base"]) == 1000.0
    assert float(q1["value_actual"]) == 1100.0
    assert q2["value_actual"] is None

    # Update q2 with actuals
    resp = client.put(
        f"/initiatives/{init_id}/kpis/{kpi_id}/entries",
        json=[
            {
                "year": 2026, "quarter": 2,
                "value_base": "1200", "value_actual": "1000"
            } # Missed target
        ],
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    q2_updated = next(e for e in resp.json() if e["quarter"] == 2)
    assert float(q2_updated["value_actual"]) == 1000.0


def test_kpi_pulse_summary(admin_token: str, init_id: str) -> None:
    # Pulse is global across portfolio, so we check the endpoint works and formats correctly.
    # We just created some KPIs, so we should see hitting/missing stats.
    resp = client.get("/portfolio/kpi-pulse", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_kpis" in data
    assert "hitting_base" in data
    assert "missing_base" in data
    assert "no_actuals" in data
    assert "health_score" in data
    
    # We should have at least 1 hitting and 1 missing (from Revenue Target Q1 and Q2)
    assert data["total_kpis"] > 0
