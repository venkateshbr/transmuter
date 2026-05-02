"""Portfolio KPI API integration tests."""

import os
import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load env from parent dir
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.main import app

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

def test_get_portfolio_kpis(admin_token: str) -> None:
    """Test retrieving all KPIs across the portfolio."""
    resp = client.get("/portfolio/kpis", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    
    if data["total"] > 0:
        item = data["items"][0]
        assert "id" in item
        assert "initiative_id" in item
        assert "initiative_name" in item
        assert "health_status" in item

def test_get_portfolio_kpi_pulse(admin_token: str) -> None:
    """Test retrieving global KPI health pulse."""
    resp = client.get("/portfolio/kpi-pulse", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    
    assert "total_kpis" in data
    assert "hitting_base" in data
    assert "missing_base" in data
    assert "no_actuals" in data
    assert "health_score" in data
    assert isinstance(data["health_score"], str)
