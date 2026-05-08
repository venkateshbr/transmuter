"""Milestone API integration tests — Aksha #42."""

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.main import app

client = TestClient(app, raise_server_exceptions=True)

# ── Auth helper ───────────────────────────────────────────────────────────────


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
    # Get or create an initiative to attach milestones to
    resp = client.post(
        "/initiatives",
        json={"name": "Milestone Test Initiative", "priority": "low", "country": "Singapore"},
        headers=auth(admin_token),
    )
    return resp.json()["id"]


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_milestone_crud_and_pressure_recalc(admin_token: str, init_id: str) -> None:
    # End-to-end: save milestone -> pressure recalculated -> stored value correct
    resp = client.post(
        f"/initiatives/{init_id}/milestones",
        json={
            "name": "Test Milestone",
            "status": "not_started",
            "planned_end": "2030-01-01",  # future -> slack penalty 0
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    ms1 = resp.json()
    assert ms1["pressure_score"] is not None
    # Just created, status not started, future date. Self status = 0.1, others 0.
    assert float(ms1["pressure_score"]) == 0.1

    # Update to complete -> pressure drops to 0
    resp = client.put(
        f"/milestones/{ms1['id']}",
        json={"status": "complete"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    ms1_updated = resp.json()
    assert float(ms1_updated["pressure_score"]) == 0.0


def test_circular_dependency(admin_token: str, init_id: str) -> None:
    # Create A and B
    msA = client.post(
        f"/initiatives/{init_id}/milestones",
        json={"name": "A"},
        headers=auth(admin_token),
    ).json()
    msB = client.post(
        f"/initiatives/{init_id}/milestones",
        json={"name": "B"},
        headers=auth(admin_token),
    ).json()

    # Link A -> B (B depends on A)
    # B is downstream, A is upstream. Post to B's dependencies with A as upstream.
    resp = client.post(
        f"/milestones/{msB['id']}/dependencies",
        json={"upstream_milestone_id": msA["id"]},
        headers=auth(admin_token),
    )
    assert resp.status_code == 201

    # Attempt to link B -> A (A depends on B)
    resp = client.post(
        f"/milestones/{msA['id']}/dependencies",
        json={"upstream_milestone_id": msB["id"]},
        headers=auth(admin_token),
    )
    assert resp.status_code == 400
    assert "cycle" in resp.json()["detail"].lower()


def test_blast_radius_recalc(admin_token: str, init_id: str) -> None:
    # Adding a dependent milestone increases blast_radius score
    ms1 = client.post(
        f"/initiatives/{init_id}/milestones",
        json={"name": "Upstream"},
        headers=auth(admin_token),
    ).json()
    ms2 = client.post(
        f"/initiatives/{init_id}/milestones",
        json={"name": "Downstream"},
        headers=auth(admin_token),
    ).json()

    # Check blast radius before (detail view)
    resp = client.get(f"/milestones/{ms1['id']}", headers=auth(admin_token))
    assert float(resp.json()["pressure_blast_radius"]) == 0.0

    # Add dependency: ms2 depends on ms1
    client.post(
        f"/milestones/{ms2['id']}/dependencies",
        json={"upstream_milestone_id": ms1["id"]},
        headers=auth(admin_token),
    )

    # Check blast radius after
    resp = client.get(f"/milestones/{ms1['id']}", headers=auth(admin_token))
    assert float(resp.json()["pressure_blast_radius"]) == 1.0


def test_slack_penalty_recalc(admin_token: str, init_id: str) -> None:
    # Overdue milestone -> 1.5 slack_penalty
    ms1 = client.post(
        f"/initiatives/{init_id}/milestones",
        json={
            "name": "Overdue MS",
            "planned_end": "2020-01-01",  # Past date
        },
        headers=auth(admin_token),
    ).json()

    resp = client.get(f"/milestones/{ms1['id']}", headers=auth(admin_token))
    assert float(resp.json()["pressure_slack"]) == 1.5


def test_checklist_score_recalc(admin_token: str, init_id: str) -> None:
    ms1 = client.post(
        f"/initiatives/{init_id}/milestones",
        json={"name": "Checklist MS"},
        headers=auth(admin_token),
    ).json()

    # Add item -> 0.5 penalty
    item1 = client.post(
        f"/milestones/{ms1['id']}/checklist",
        json={"text": "Task 1", "sort_order": 0},
        headers=auth(admin_token),
    ).json()

    resp = client.get(f"/milestones/{ms1['id']}", headers=auth(admin_token))
    assert float(resp.json()["pressure_checklist"]) == 0.5

    # Complete item -> 0.0 penalty
    client.put(
        f"/milestones/{ms1['id']}/checklist/{item1['id']}",
        json={"completed": True},
        headers=auth(admin_token),
    )

    resp = client.get(f"/milestones/{ms1['id']}", headers=auth(admin_token))
    assert float(resp.json()["pressure_checklist"]) == 0.0
