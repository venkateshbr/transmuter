"""Meeting Command Center API coverage."""

from __future__ import annotations

import os
from datetime import date, timedelta
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from app.main import app
from app.services.email_delivery import EmailDeliveryResult

client = TestClient(app, raise_server_exceptions=True)


def get_token(email: str = "admin@ishirock.dev", password: str = "Transmuter2026!") -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    return get_token()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_initiative(token: str) -> dict:
    response = client.post(
        "/initiatives",
        json={
            "name": f"Meeting Command Center Initiative {uuid4()}",
            "priority": "medium",
            "country": "Singapore",
            "summary": "Initiative context for meeting command center tests.",
        },
        headers=auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_meeting_with_session(token: str, initiative_id: str) -> tuple[dict, dict, dict]:
    meeting_response = client.post(
        "/meetings",
        json={
            "name": f"Meeting Command Center {uuid4()}",
            "scope": "all",
            "recurrence": "weekly",
            "description": "Command center test series",
        },
        headers=auth(token),
    )
    assert meeting_response.status_code == 201, meeting_response.text
    meeting = meeting_response.json()

    agenda_response = client.post(
        f"/meetings/{meeting['id']}/agenda",
        json={"text": "Review linked initiative", "initiative_id": initiative_id},
        headers=auth(token),
    )
    assert agenda_response.status_code == 201, agenda_response.text
    agenda = agenda_response.json()

    session_response = client.post(
        f"/meetings/{meeting['id']}/sessions/start",
        json={},
        headers=auth(token),
    )
    assert session_response.status_code == 200, session_response.text
    return meeting, agenda, session_response.json()


def test_meeting_artifacts_actions_risks_carry_forward_and_minutes(
    admin_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_deliver(self, *, to, subject, text, html=None):  # noqa: ANN001, ARG001
        assert to
        assert subject.startswith("Minutes:")
        assert "## Actions" in text
        return EmailDeliveryResult(status="sent", detail="email", recipient_count=len(to))

    monkeypatch.setattr("app.services.email_delivery.EmailDeliveryService.deliver", fake_deliver)

    initiative = create_initiative(admin_token)
    meeting, agenda, session = create_meeting_with_session(admin_token, initiative["id"])
    profile_response = client.get("/auth/me", headers=auth(admin_token))
    assert profile_response.status_code == 200, profile_response.text
    attendee_response = client.post(
        f"/meetings/{meeting['id']}/attendees",
        json={"user_id": profile_response.json()["id"]},
        headers=auth(admin_token),
    )
    assert attendee_response.status_code == 201, attendee_response.text

    action_response = client.post(
        f"/meetings/sessions/{session['id']}/artifacts",
        json={
            "artifact_type": "action",
            "title": "Follow up on benefits owner",
            "description": "Follow up on benefits owner",
            "agenda_item_id": agenda["id"],
            "initiative_id": initiative["id"],
            "priority": "high",
            "status": "open",
        },
        headers=auth(admin_token),
    )
    assert action_response.status_code == 201, action_response.text
    action_artifact = action_response.json()
    assert action_artifact["linked_record_type"] == "action_item"

    session_detail = client.get(
        f"/meetings/sessions/{session['id']}",
        headers=auth(admin_token),
    ).json()
    assert any(
        item["description"] == "Follow up on benefits owner"
        for item in session_detail["action_items"]
    )
    assert any(
        item["title"] == "Follow up on benefits owner" for item in session_detail["artifacts"]
    )

    update_response = client.put(
        f"/meeting-artifacts/{action_artifact['id']}",
        json={"status": "completed"},
        headers=auth(admin_token),
    )
    assert update_response.status_code == 200, update_response.text
    actions = client.get("/portfolio/action-items", headers=auth(admin_token)).json()["items"]
    synced = next(item for item in actions if item["id"] == action_artifact["linked_record_id"])
    assert synced["status"] == "completed"

    open_action = client.post(
        f"/meetings/sessions/{session['id']}/artifacts",
        json={
            "artifact_type": "action",
            "title": "Carry this action forward",
            "initiative_id": initiative["id"],
            "status": "open",
        },
        headers=auth(admin_token),
    ).json()
    assert open_action["linked_record_type"] == "action_item"

    risk_response = client.post(
        f"/meetings/sessions/{session['id']}/artifacts",
        json={
            "artifact_type": "risk",
            "title": "Adoption readiness risk",
            "description": "Adoption readiness risk",
            "initiative_id": initiative["id"],
            "priority": "medium",
        },
        headers=auth(admin_token),
    )
    assert risk_response.status_code == 201, risk_response.text
    assert risk_response.json()["linked_record_type"] == "risk"
    risks = client.get(f"/initiatives/{initiative['id']}/risks", headers=auth(admin_token)).json()
    assert any(item["description"] == "Adoption readiness risk" for item in risks["items"])

    client.patch(
        f"/meetings/sessions/{session['id']}",
        json={
            "notes": (
                "Rupa Menon: Action: confirm benefits owner by 2026-06-10. "
                "Vishwa Rao: Decision: keep delivery risk under weekly review. "
                "Meeting Command Center Initiative is amber until owner alignment is complete."
            )
        },
        headers=auth(admin_token),
    )
    extraction_response = client.post(
        f"/meetings/sessions/{session['id']}/ai/extract",
        json={},
        headers=auth(admin_token),
    )
    assert extraction_response.status_code == 200, extraction_response.text
    extraction = extraction_response.json()
    assert extraction["status"] == "pending_review"
    assert extraction["action_items"]

    minutes_response = client.post(
        f"/meetings/sessions/{session['id']}/minutes/generate",
        json={"force": True},
        headers=auth(admin_token),
    )
    assert minutes_response.status_code == 200, minutes_response.text
    assert minutes_response.json()["minutes_status"] == "draft"
    assert "## Actions" in minutes_response.json()["minutes_markdown"]

    send_response = client.post(
        f"/meetings/sessions/{session['id']}/minutes/send",
        json={},
        headers=auth(admin_token),
    )
    assert send_response.status_code == 200, send_response.text
    assert send_response.json()["minutes_status"] == "sent"

    client.post(f"/meetings/sessions/{session['id']}/end", json={}, headers=auth(admin_token))
    next_session_date = (
        date.fromisoformat(session["session_date"]) + timedelta(days=1)
    ).isoformat()
    next_session = client.post(
        f"/meetings/{meeting['id']}/sessions/start",
        json={"session_date": next_session_date},
        headers=auth(admin_token),
    ).json()
    next_detail = client.get(
        f"/meetings/sessions/{next_session['id']}",
        headers=auth(admin_token),
    ).json()
    assert any(
        item["description"] == "Carry this action forward"
        for item in next_detail["carry_forward_action_items"]
    )

    delete_response = client.delete(
        f"/meeting-artifacts/{open_action['id']}",
        headers=auth(admin_token),
    )
    assert delete_response.status_code == 204


def test_microsoft_external_event_gracefully_degrades(admin_token: str) -> None:
    initiative = create_initiative(admin_token)
    meeting, _agenda, _session = create_meeting_with_session(admin_token, initiative["id"])
    response = client.post(
        f"/meetings/{meeting['id']}/external-events/microsoft",
        json={
            "start_date_time": "2026-06-10T09:00:00",
            "end_date_time": "2026-06-10T10:00:00",
            "time_zone": "UTC",
        },
        headers=auth(admin_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "microsoft"
    assert body["sync_status"] in {"not_configured", "failed", "synced"}
