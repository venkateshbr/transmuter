"""Real API acceptance checks against deterministic Transmuter sample data.

Run with a live API server:
    RUN_REAL_ACCEPTANCE=1 TRANSMUTER_API_BASE_URL=http://localhost:8000 pytest tests/acceptance -q
"""

from __future__ import annotations

import os
from decimal import Decimal
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REAL_ACCEPTANCE") != "1",
    reason="real API acceptance requires a running API and RUN_REAL_ACCEPTANCE=1",
)

BASE_URL = os.environ.get("TRANSMUTER_API_BASE_URL", "http://localhost:8000")
EMAIL = os.environ.get("TRANSMUTER_E2E_EMAIL", "admin@ishirock.dev")
PASSWORD = os.environ.get("TRANSMUTER_E2E_PASSWORD", "Transmuter2026!")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SHEET_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_AUTH_HEADERS: dict[str, str] | None = None


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=20)


def _auth_headers(client: httpx.Client) -> dict[str, str]:
    global _AUTH_HEADERS
    if _AUTH_HEADERS is not None:
        return _AUTH_HEADERS
    response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    response.raise_for_status()
    token = response.json()["access_token"]
    _AUTH_HEADERS = {"Authorization": f"Bearer {token}"}
    return _AUTH_HEADERS


def _workbook_sheet_names(content: bytes) -> list[str]:
    with ZipFile(BytesIO(content)) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    return [sheet.attrib["name"] for sheet in workbook.findall("main:sheets/main:sheet", SHEET_NS)]


def test_real_api_seeded_dashboard_and_meetings() -> None:
    with _client() as client:
        health = client.get("/health")
        health.raise_for_status()

        headers = _auth_headers(client)

        dashboard = client.get("/dashboard", headers=headers)
        dashboard.raise_for_status()
        dashboard_data = dashboard.json()
        assert dashboard_data["summary"]["total_initiatives"] >= 5

        chat = client.post(
            "/ai/chat",
            headers=headers,
            json={"query": "Summarize the portfolio with sources."},
        )
        chat.raise_for_status()
        chat_data = chat.json()
        assert chat_data["response"]
        assert any(item["source_type"] == "initiatives" for item in chat_data["sources"])

        meetings = client.get("/meetings", headers=headers)
        meetings.raise_for_status()
        meeting_names = {item["name"] for item in meetings.json()["items"]}
        assert "Transformation Steering Committee" in meeting_names
        assert "North Asia Workstream Review" in meeting_names


def test_real_api_executive_control_tower_phase_2a() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        dependencies = client.get("/initiative-dependencies", headers=headers)
        dependencies.raise_for_status()
        dependency_data = dependencies.json()
        assert dependency_data["rollups"]["total"] >= 1
        assert dependency_data["rollups"]["critical_path_risk"] >= 1
        assert any(
            item["upstream"]["id"] != item["downstream"]["id"] for item in dependency_data["items"]
        )

        pools = client.get("/shared-cost-pools", headers=headers)
        pools.raise_for_status()
        pool_items = pools.json()["items"]
        assert pool_items
        pool = next(item for item in pool_items if item["year"] == 2026)
        assert Decimal(pool["amount_plan"]) > Decimal("0")
        assert Decimal(pool["allocated_plan"]) == Decimal(pool["amount_plan"])

        rules = client.get(
            f"/shared-cost-pools/{pool['id']}/allocation-rules",
            headers=headers,
        )
        rules.raise_for_status()
        rule_items = rules.json()
        assert any(item["allocation_method"] == "benefit_weighted" for item in rule_items)

        runs = client.get(
            f"/shared-cost-pools/{pool['id']}/allocation-runs",
            headers=headers,
        )
        runs.raise_for_status()
        run_items = runs.json()
        assert run_items
        run = run_items[0]
        assert Decimal(run["total_amount_plan"]) == Decimal(pool["amount_plan"])
        assert sum(Decimal(item["allocated_plan"]) for item in run["allocations"]) == Decimal(
            run["total_amount_plan"]
        )

        control_tower = client.get(
            "/reports/executive-control-tower?target_year=2026",
            headers=headers,
        )
        control_tower.raise_for_status()
        control_data = control_tower.json()
        assert control_data["persona"] == "management"
        assert Decimal(control_data["value_bridge"]["allocated_costs_plan"]) > Decimal("0")
        assert control_data["dependency_risk"]["total"] == dependency_data["rollups"]["total"]

        investor_summary = client.get(
            "/reports/investor-summary?target_year=2026",
            headers=headers,
        )
        investor_summary.raise_for_status()
        investor_data = investor_summary.json()
        assert investor_data["persona"] == "investor"
        assert investor_data["summary"]["initiative_count"] >= 1

        owner_cockpit = client.get(
            "/reports/owner-cockpit?target_year=2026",
            headers=headers,
        )
        owner_cockpit.raise_for_status()
        assert owner_cockpit.json()["persona"] == "owner"

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiatives_data = initiatives.json()["items"]
        assert initiatives_data
        note_counts = []
        for item in initiatives_data:
            notes = client.get(
                f"/initiatives/{item['id']}/value-realization-notes",
                headers=headers,
            )
            notes.raise_for_status()
            note_counts.append(len(notes.json()))
        assert any(count > 0 for count in note_counts)


def test_real_api_meeting_crud_session_and_action_flow() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        users = client.get("/users", headers=headers)
        users.raise_for_status()
        user_id = users.json()["data"][0]["id"]

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        name = f"Acceptance Meeting {uuid4()}"
        created = client.post(
            "/meetings",
            headers=headers,
            json={
                "name": name,
                "scope": "all",
                "recurrence": "biweekly",
                "day_of_week": 2,
                "start_time": "13:30",
                "timezone": "UTC",
                "duration_minutes": 45,
                "series_end_date": "2030-09-30",
                "description": "Created by real API acceptance test",
                "owner_id": user_id,
                "participant_user_ids": [user_id],
                "default_agenda_items": [{"text": "Acceptance default agenda"}],
            },
        )
        created.raise_for_status()
        meeting_id = created.json()["id"]

        try:
            updated = client.put(
                f"/meetings/{meeting_id}",
                headers=headers,
                json={"description": "Updated by real API acceptance test"},
            )
            updated.raise_for_status()
            assert updated.json()["description"] == "Updated by real API acceptance test"

            agenda = client.post(
                f"/meetings/{meeting_id}/agenda",
                headers=headers,
                json={"text": "Acceptance agenda", "initiative_id": initiative_id},
            )
            agenda.raise_for_status()
            agenda_id = agenda.json()["id"]

            agenda_update = client.put(
                f"/meetings/{meeting_id}/agenda/{agenda_id}",
                headers=headers,
                json={"text": "Updated acceptance agenda"},
            )
            agenda_update.raise_for_status()
            assert agenda_update.json()["text"] == "Updated acceptance agenda"

            attendee = client.post(
                f"/meetings/{meeting_id}/attendees",
                headers=headers,
                json={"user_id": user_id},
            )
            attendee.raise_for_status()
            attendee_id = attendee.json()["id"]

            initiative_link = client.post(
                f"/meetings/{meeting_id}/initiatives",
                headers=headers,
                json={"initiative_id": initiative_id},
            )
            initiative_link.raise_for_status()
            link_id = initiative_link.json()["id"]

            window = client.get(
                f"/meetings/{meeting_id}/sessions",
                headers=headers,
                params={"anchor_date": "2030-06-10", "page_size": 3},
            )
            window.raise_for_status()
            window_data = window.json()
            assert len(window_data["items"]) == 6
            assert window_data["items"][0]["status"] == "scheduled"

            session = client.post(f"/meetings/{meeting_id}/sessions/start", headers=headers)
            session.raise_for_status()
            session_id = session.json()["id"]

            session_agenda = client.post(
                f"/meetings/sessions/{session_id}/agenda",
                headers=headers,
                json={"text": "Session-specific acceptance agenda", "initiative_id": initiative_id},
            )
            session_agenda.raise_for_status()
            session_agenda_id = session_agenda.json()["id"]

            session_attendee = client.post(
                f"/meetings/sessions/{session_id}/attendees",
                headers=headers,
                json={"user_id": user_id},
            )
            session_attendee.raise_for_status()
            session_attendee_id = session_attendee.json()["id"]

            teams = client.post(
                f"/meetings/sessions/{session_id}/external-events/microsoft",
                headers=headers,
                json={
                    "start_date_time": "2030-06-10T13:30:00",
                    "end_date_time": "2030-06-10T14:15:00",
                    "time_zone": "UTC",
                    "attendee_user_ids": [user_id],
                    "series_end_date": "2030-09-30",
                },
            )
            teams.raise_for_status()
            assert teams.json()["sync_status"] in {"not_configured", "synced", "failed"}

            notes = client.patch(
                f"/meetings/sessions/{session_id}",
                headers=headers,
                json={"notes": "Acceptance notes autosaved via real API."},
            )
            notes.raise_for_status()
            assert notes.json()["notes"] == "Acceptance notes autosaved via real API."

            transcript_text = (
                "Rupa Menon: Acceptance agenda needs a benefits owner before the next review. "
                "Vishwa Rao: Session-specific acceptance agenda has a migration risk that needs a rollback owner. "
                "Rupa Menon: Finance validation can complete after the owner is confirmed."
            )
            imported_transcript = client.post(
                f"/meetings/sessions/{session_id}/transcript/import",
                headers=headers,
                json={"transcript_text": transcript_text, "transcript_source": "manual"},
            )
            imported_transcript.raise_for_status()

            minutes = client.post(
                f"/meetings/sessions/{session_id}/minutes/generate",
                headers=headers,
                json={"force": True},
            )
            minutes.raise_for_status()
            minutes_markdown = minutes.json()["minutes_markdown"]
            assert "## AI Summary" in minutes_markdown
            assert "## Agenda Discussion" in minutes_markdown
            assert "### Session-specific acceptance agenda" in minutes_markdown
            assert "rollback owner" in minutes_markdown
            assert "## Transcript Summary Source" not in minutes_markdown
            assert "Rupa Menon:" not in minutes_markdown
            assert "Vishwa Rao:" not in minutes_markdown

            action = client.post(
                f"/meetings/sessions/{session_id}/action-items",
                headers=headers,
                json={
                    "description": "Acceptance action item",
                    "initiative_id": initiative_id,
                    "assignee_id": user_id,
                    "priority": "high",
                    "status": "open",
                },
            )
            action.raise_for_status()
            action_id = action.json()["id"]

            action_update = client.put(
                f"/action-items/{action_id}",
                headers=headers,
                json={"status": "in_progress", "due_date": "2030-12-31"},
            )
            action_update.raise_for_status()
            assert action_update.json()["status"] == "in_progress"
            assert action_update.json()["due_date"] == "2030-12-31"

            action_list = client.get("/action-items", headers=headers)
            action_list.raise_for_status()
            action_list_data = action_list.json()
            assert any(item["id"] == action_id for item in action_list_data["items"])
            assert action_list_data["stats"]["total"] >= 1
            assert action_list_data["stats"]["in_progress"] >= 1

            portfolio_actions = client.get("/portfolio/action-items", headers=headers)
            portfolio_actions.raise_for_status()
            portfolio_data = portfolio_actions.json()
            portfolio_item = next(
                item for item in portfolio_data["items"] if item["id"] == action_id
            )
            assert portfolio_item["meeting_sessions"]["meeting_id"] == meeting_id
            assert portfolio_item["users"]["display_name"]
            assert portfolio_data["stats"]["in_progress"] >= 1

            completed_action = client.put(
                f"/action-items/{action_id}",
                headers=headers,
                json={"status": "completed"},
            )
            completed_action.raise_for_status()
            assert completed_action.json()["status"] == "completed"

            ended = client.post(f"/meetings/sessions/{session_id}/end", headers=headers)
            ended.raise_for_status()
            assert ended.json()["status"] == "completed"

            client.delete(f"/action-items/{action_id}", headers=headers).raise_for_status()
            client.delete(
                f"/meetings/{meeting_id}/initiatives/{link_id}",
                headers=headers,
            ).raise_for_status()
            client.delete(
                f"/meetings/{meeting_id}/attendees/{attendee_id}",
                headers=headers,
            ).raise_for_status()
            client.delete(
                f"/meetings/{meeting_id}/agenda/{agenda_id}",
                headers=headers,
            ).raise_for_status()
            client.delete(
                f"/meetings/sessions/{session_id}/agenda/{session_agenda_id}",
                headers=headers,
            ).raise_for_status()
            client.delete(
                f"/meetings/sessions/{session_id}/attendees/{session_attendee_id}",
                headers=headers,
            ).raise_for_status()
        finally:
            client.delete(f"/meetings/{meeting_id}", headers=headers)


def test_real_api_admin_bulk_meeting_cleanup_deletes_related_records() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        users = client.get("/users", headers=headers)
        users.raise_for_status()
        user_id = users.json()["data"][0]["id"]

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        created_meeting_ids: list[str] = []
        action_ids: list[str] = []
        risk_ids: list[str] = []
        try:
            for index in range(2):
                created = client.post(
                    "/meetings",
                    headers=headers,
                    json={
                        "name": f"Acceptance Cleanup Meeting {index} {uuid4()}",
                        "scope": "all",
                        "recurrence": "weekly",
                        "day_of_week": index,
                        "start_time": "10:00",
                        "timezone": "UTC",
                        "duration_minutes": 30,
                        "series_end_date": "2030-12-31",
                        "description": "Created for admin bulk cleanup acceptance.",
                        "owner_id": user_id,
                        "participant_user_ids": [user_id],
                        "default_agenda_items": [{"text": "Cleanup default agenda"}],
                    },
                )
                created.raise_for_status()
                meeting_id = created.json()["id"]
                created_meeting_ids.append(meeting_id)

                agenda = client.post(
                    f"/meetings/{meeting_id}/agenda",
                    headers=headers,
                    json={"text": "Cleanup agenda", "initiative_id": initiative_id},
                )
                agenda.raise_for_status()

                attendee = client.post(
                    f"/meetings/{meeting_id}/attendees",
                    headers=headers,
                    json={"user_id": user_id},
                )
                attendee.raise_for_status()

                link = client.post(
                    f"/meetings/{meeting_id}/initiatives",
                    headers=headers,
                    json={"initiative_id": initiative_id},
                )
                link.raise_for_status()

                series_teams = client.post(
                    f"/meetings/{meeting_id}/external-events/microsoft",
                    headers=headers,
                    json={
                        "start_date_time": "2030-06-10T10:00:00",
                        "end_date_time": "2030-06-10T10:30:00",
                        "time_zone": "UTC",
                        "attendee_user_ids": [user_id],
                        "series_end_date": "2030-12-31",
                    },
                )
                series_teams.raise_for_status()

                session = client.post(
                    f"/meetings/{meeting_id}/sessions/start",
                    headers=headers,
                    json={"session_date": f"2030-06-{10 + index:02d}"},
                )
                session.raise_for_status()
                session_id = session.json()["id"]

                session_notes = client.patch(
                    f"/meetings/sessions/{session_id}",
                    headers=headers,
                    json={
                        "notes": "Cleanup notes",
                        "transcript_text": "Cleanup transcript",
                    },
                )
                session_notes.raise_for_status()

                session_agenda = client.post(
                    f"/meetings/sessions/{session_id}/agenda",
                    headers=headers,
                    json={
                        "text": "Cleanup session agenda",
                        "initiative_id": initiative_id,
                    },
                )
                session_agenda.raise_for_status()

                session_attendee = client.post(
                    f"/meetings/sessions/{session_id}/attendees",
                    headers=headers,
                    json={"user_id": user_id},
                )
                session_attendee.raise_for_status()

                session_teams = client.post(
                    f"/meetings/sessions/{session_id}/external-events/microsoft",
                    headers=headers,
                    json={
                        "start_date_time": "2030-06-10T10:00:00",
                        "end_date_time": "2030-06-10T10:30:00",
                        "time_zone": "UTC",
                        "attendee_user_ids": [user_id],
                    },
                )
                session_teams.raise_for_status()

                action = client.post(
                    f"/meetings/sessions/{session_id}/action-items",
                    headers=headers,
                    json={
                        "description": "Cleanup direct action",
                        "initiative_id": initiative_id,
                        "assignee_id": user_id,
                        "priority": "medium",
                    },
                )
                action.raise_for_status()
                action_ids.append(action.json()["id"])

                artifact = client.post(
                    f"/meetings/sessions/{session_id}/artifacts",
                    headers=headers,
                    json={
                        "artifact_type": "risk",
                        "title": "Cleanup linked risk",
                        "description": "Risk created by meeting cleanup acceptance.",
                        "initiative_id": initiative_id,
                        "owner_id": user_id,
                        "priority": "high",
                    },
                )
                artifact.raise_for_status()
                risk_ids.append(artifact.json()["linked_record_id"])

            candidates = client.get("/admin/meeting-cleanup-candidates", headers=headers)
            candidates.raise_for_status()
            candidate_ids = {item["id"] for item in candidates.json()["items"]}
            assert set(created_meeting_ids).issubset(candidate_ids)

            rejected = client.post(
                "/admin/meeting-cleanup/delete",
                headers=headers,
                json={"meeting_ids": created_meeting_ids, "confirm_phrase": "delete meetings"},
            )
            assert rejected.status_code == 400

            deleted = client.post(
                "/admin/meeting-cleanup/delete",
                headers=headers,
                json={
                    "meeting_ids": created_meeting_ids,
                    "confirm_phrase": "DELETE MEETINGS",
                },
            )
            deleted.raise_for_status()
            deleted_data = deleted.json()
            assert deleted_data["deleted"] is True
            assert set(deleted_data["meeting_ids"]) == set(created_meeting_ids)
            assert deleted_data["deleted_rows"]["meetings"] == 2
            assert deleted_data["deleted_rows"]["agenda_items"] >= 2
            assert deleted_data["deleted_rows"]["meeting_sessions"] >= 2
            assert deleted_data["deleted_rows"]["meeting_session_agenda_items"] >= 2
            assert deleted_data["deleted_rows"]["meeting_session_attendees"] >= 2
            assert deleted_data["deleted_rows"]["action_items"] >= 2
            assert deleted_data["linked_records"]["risk"] >= 2

            meetings = client.get("/meetings", headers=headers)
            meetings.raise_for_status()
            remaining_meeting_ids = {item["id"] for item in meetings.json()["items"]}
            assert not set(created_meeting_ids) & remaining_meeting_ids

            actions = client.get("/action-items", headers=headers)
            actions.raise_for_status()
            remaining_action_ids = {item["id"] for item in actions.json()["items"]}
            assert not set(action_ids) & remaining_action_ids

            risks = client.get(f"/initiatives/{initiative_id}/risks", headers=headers)
            risks.raise_for_status()
            remaining_risk_ids = {item["id"] for item in risks.json()["items"]}
            assert not set(risk_ids) & remaining_risk_ids
        finally:
            for meeting_id in created_meeting_ids:
                client.delete(f"/meetings/{meeting_id}", headers=headers)


def test_real_api_initiative_template_import_flow() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        template = client.get("/initiatives/template", headers=headers)
        template.raise_for_status()
        assert template.headers["content-type"] == XLSX_MEDIA_TYPE
        with ZipFile(BytesIO(template.content)) as zf:
            assert "xl/workbook.xml" in zf.namelist()

        preview = client.post(
            "/initiatives/import/preview",
            headers=headers,
            files={"file": ("template.xlsx", template.content, XLSX_MEDIA_TYPE)},
        )
        preview.raise_for_status()
        preview_data = preview.json()
        assert preview_data["name"] == "Imported Acceptance Initiative"
        assert preview_data["validation_errors"] == []
        assert preview_data["counts"] == {
            "financials": 1,
            "costs": 1,
            "kpis": 1,
            "risks": 1,
            "milestones": 1,
        }

        imported = client.post(
            "/initiatives/import",
            headers=headers,
            files={"file": ("template.xlsx", template.content, XLSX_MEDIA_TYPE)},
        )
        imported.raise_for_status()
        created = imported.json()
        initiative_id = created["id"]

        try:
            assert created["name"] == "Imported Acceptance Initiative"
            assert created["theme"] == "Finance automation"
            fetched = client.get(f"/initiatives/{initiative_id}", headers=headers)
            fetched.raise_for_status()
            fetched_data = fetched.json()
            assert fetched_data["name"] == "Imported Acceptance Initiative"
            assert fetched_data["counts"]["kpis_total"] >= 1
            assert fetched_data["counts"]["risks_open"] >= 1
            assert fetched_data["counts"]["milestones_total"] >= 1

            financials = client.get(
                f"/initiatives/{initiative_id}/financials",
                headers=headers,
            )
            financials.raise_for_status()
            row = next(
                item
                for item in financials.json()["entries"]
                if item["year"] == 2026 and item["month"] == 6
            )
            assert Decimal(row["revenue_uplift_base"]) == Decimal("100000.0000")
            assert Decimal(row["gm_uplift_high"]) == Decimal("70000.0000")

            cost_lines = client.get(
                f"/initiatives/{initiative_id}/financials/cost-lines",
                headers=headers,
            )
            cost_lines.raise_for_status()
            assert any(
                item["name"] == "Implementation support"
                and Decimal(item["amount_plan"]) == Decimal("12000.0000")
                for item in cost_lines.json()["items"]
            )

            kpis = client.get(f"/initiatives/{initiative_id}/kpis", headers=headers)
            kpis.raise_for_status()
            assert any(
                item["name"] == "Cycle time reduction"
                and item["entries"]
                and Decimal(item["entries"][0]["value_base"]) == Decimal("15.0000")
                for item in kpis.json()["items"]
            )

            risks = client.get(f"/initiatives/{initiative_id}/risks", headers=headers)
            risks.raise_for_status()
            assert any("Adoption may lag" in item["description"] for item in risks.json()["items"])

            milestones = client.get(
                f"/initiatives/{initiative_id}/milestones",
                headers=headers,
            )
            milestones.raise_for_status()
            assert any(
                item["name"] == "Pilot launch complete" for item in milestones.json()["items"]
            )

            exported = client.get(f"/initiatives/{initiative_id}/export", headers=headers)
            exported.raise_for_status()
            assert exported.headers["content-type"] == XLSX_MEDIA_TYPE
            assert _workbook_sheet_names(exported.content) == [
                "Overview",
                "Summary",
                "Benefits",
                "Costs",
                "KPIs",
                "Milestones",
                "Action Items",
                "Risks",
                "Status Updates",
                "Meeting Notes",
                "_Reference",
                "_Validation",
            ]
            with ZipFile(BytesIO(exported.content)) as zf:
                names = set(zf.namelist())
                assert b"FF7C3AED" in zf.read("xl/styles.xml")
                assert any(name.startswith("xl/media/") for name in names)
                assert "xl/drawings/drawing1.xml" in names
                assert "xl/worksheets/_rels/sheet1.xml.rels" in names
                summary_sheet = zf.read("xl/worksheets/sheet2.xml")
                assert b"Revenue Plan - Base" in summary_sheet
                assert b"0.100000" in summary_sheet
                assert initiative_id in zf.read("xl/worksheets/sheet11.xml").decode()
                assert b"Stages" in zf.read("xl/worksheets/sheet12.xml")

            updated_name = f"Imported Acceptance Initiative Updated {uuid4()}"
            patched = _patched_initiative_workbook(
                exported.content,
                name=updated_name,
                summary="Updated through existing initiative workbook import.",
            )
            updated = client.post(
                f"/initiatives/{initiative_id}/import",
                headers=headers,
                files={"file": ("roundtrip.xlsx", patched, XLSX_MEDIA_TYPE)},
            )
            updated.raise_for_status()
            updated_data = updated.json()
            assert updated_data["id"] == initiative_id
            assert updated_data["name"] == updated_name
            assert updated_data["summary"] == "Updated through existing initiative workbook import."

            updated_financials = client.get(
                f"/initiatives/{initiative_id}/financials",
                headers=headers,
            )
            updated_financials.raise_for_status()
            updated_row = next(
                item
                for item in updated_financials.json()["entries"]
                if Decimal(item["revenue_uplift_base"]) == Decimal("33333.0000")
            )
            assert Decimal(updated_row["revenue_uplift_base"]) == Decimal("33333.0")

            wrong_ref = _patched_reference_value(exported.content, "initiative_id", str(uuid4()))
            mismatch = client.post(
                f"/initiatives/{initiative_id}/import",
                headers=headers,
                files={"file": ("wrong-reference.xlsx", wrong_ref, XLSX_MEDIA_TYPE)},
            )
            assert mismatch.status_code == 400
        finally:
            client.delete(f"/initiatives/{initiative_id}", headers=headers)


def test_real_api_initiative_intake_hitl_create_flow() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiative = {
            "name": f"Acceptance Intake Initiative {uuid4()}",
            "type": "cost_reduction",
            "impact_type": "recurring",
            "theme": "Acceptance automation",
            "country": "Singapore",
            "tag": "automation",
            "priority": "high",
            "summary": "Created by real API intake acceptance.",
            "value_logic": "Validate HITL suggestions through the real API.",
            "dependencies_text": "Seeded tenant data.",
            "planned_start": "2026-06-01",
            "planned_end": "2026-09-30",
        }

        suggestions_response = client.post(
            "/initiatives/intake/suggestions",
            headers=headers,
            json={"initiative": initiative, "conversation": ["Use deterministic acceptance data."]},
        )
        suggestions_response.raise_for_status()
        suggestions = suggestions_response.json()
        assert suggestions["trace_id"]
        assert suggestions["agent_status"] in {"generated", "deterministic_fallback"}
        assert len(suggestions["financial_entries"]) >= 1
        assert len(suggestions["cost_lines"]) >= 1
        assert len(suggestions["kpis"]) >= 3
        assert len(suggestions["risks"]) >= 3
        assert len(suggestions["milestones"]) >= 3

        suggestions["risks"][0]["accepted"] = False
        suggestions["kpis"][0]["name"] = "Acceptance modified KPI"
        created_response = client.post(
            "/initiatives/intake/create",
            headers=headers,
            json={"initiative": initiative, "suggestions": suggestions},
        )
        created_response.raise_for_status()
        created = created_response.json()
        initiative_id = created["id"]

        try:
            assert created["name"] == initiative["name"]
            assert created["counts"]["kpis_total"] >= 3
            assert created["counts"]["risks_open"] >= 2
            assert created["counts"]["milestones_total"] >= 3

            kpis = client.get(f"/initiatives/{initiative_id}/kpis", headers=headers)
            kpis.raise_for_status()
            assert any(item["name"] == "Acceptance modified KPI" for item in kpis.json()["items"])

            risks = client.get(f"/initiatives/{initiative_id}/risks", headers=headers)
            risks.raise_for_status()
            assert not any(
                item["description"] == suggestions["risks"][0]["description"]
                for item in risks.json()["items"]
            )

            financials = client.get(
                f"/initiatives/{initiative_id}/financials",
                headers=headers,
            )
            financials.raise_for_status()
            assert any(
                Decimal(item["gm_uplift_base"]) > Decimal("0")
                for item in financials.json()["entries"]
            )
        finally:
            client.delete(f"/initiatives/{initiative_id}", headers=headers)


def test_real_api_initiative_team_and_summary_persistence() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        users = client.get("/users", headers=headers)
        users.raise_for_status()
        user_ids = [user["id"] for user in users.json()["data"]]

        original = client.get(f"/initiatives/{initiative_id}", headers=headers)
        original.raise_for_status()
        original_data = original.json()
        original_owner = original_data["owner_id"]
        original_group_owner = original_data["group_owner_id"]
        original_summary = original_data["summary"]
        original_lessons = original_data["lessons_learned"]
        team_member_id: str | None = None

        existing_team = client.get(f"/initiatives/{initiative_id}/team", headers=headers)
        existing_team.raise_for_status()
        existing_user_ids = {item["user_id"] for item in existing_team.json()["data"]}
        user_id = next((uid for uid in user_ids if uid not in existing_user_ids), user_ids[0])

        try:
            owner_update = client.put(
                f"/initiatives/{initiative_id}",
                headers=headers,
                json={"owner_id": user_id, "group_owner_id": user_id},
            )
            owner_update.raise_for_status()
            owner_data = owner_update.json()
            assert owner_data["owner_id"] == user_id
            assert owner_data["group_owner_id"] == user_id

            team_add = client.post(
                f"/initiatives/{initiative_id}/team",
                headers=headers,
                json={"user_id": user_id, "role": "reviewer"},
            )
            team_add.raise_for_status()

            team = client.get(f"/initiatives/{initiative_id}/team", headers=headers)
            team.raise_for_status()
            member = next(item for item in team.json()["data"] if item["user_id"] == user_id)
            team_member_id = member["id"]
            assert member["role"] == "reviewer"

            summary_text = f"Acceptance final summary {uuid4()}"
            lessons_text = f"Acceptance lessons learned {uuid4()}"
            summary = client.patch(
                f"/initiatives/{initiative_id}/summary",
                headers=headers,
                json={"final_summary": summary_text, "lessons_learned": lessons_text},
            )
            summary.raise_for_status()
            summary_data = summary.json()
            assert summary_data["draft_status"] == "draft"
            assert summary_data["final_summary"] == summary_text
            assert summary_data["lessons_learned"] == lessons_text
            Decimal(summary_data["planned_value"])
            Decimal(summary_data["realized_value"])

            reloaded = client.get(f"/initiatives/{initiative_id}", headers=headers)
            reloaded.raise_for_status()
            assert reloaded.json()["summary"] == summary_text
            assert reloaded.json()["lessons_learned"] == lessons_text
        finally:
            if team_member_id:
                client.delete(
                    f"/initiatives/{initiative_id}/team/{team_member_id}",
                    headers=headers,
                )
            client.put(
                f"/initiatives/{initiative_id}",
                headers=headers,
                json={
                    "owner_id": original_owner,
                    "group_owner_id": original_group_owner,
                    "summary": original_summary,
                    "lessons_learned": original_lessons,
                },
            )


def test_real_api_status_update_compliance_and_nudge_flow() -> None:
    with _client() as client:
        headers = _auth_headers(client)
        users = client.get("/users", headers=headers)
        users.raise_for_status()
        owner_id = users.json()["data"][0]["id"]

        tracked = client.post(
            "/initiatives",
            headers=headers,
            json={
                "name": f"Acceptance Status Update {uuid4()}",
                "priority": "high",
                "country": "Singapore",
                "owner_id": owner_id,
            },
        )
        tracked.raise_for_status()
        tracked_id = tracked.json()["id"]

        silent = client.post(
            "/initiatives",
            headers=headers,
            json={
                "name": f"Acceptance Nuclear Status {uuid4()}",
                "priority": "medium",
                "country": "Singapore",
                "owner_id": owner_id,
            },
        )
        silent.raise_for_status()
        silent_id = silent.json()["id"]

        auto = client.post(
            "/initiatives",
            headers=headers,
            json={
                "name": f"Acceptance Daily Nudge Status {uuid4()}",
                "priority": "medium",
                "country": "Singapore",
                "owner_id": owner_id,
            },
        )
        auto.raise_for_status()
        auto_id = auto.json()["id"]

        try:
            generated = client.post(
                f"/initiatives/{tracked_id}/status-updates/generate-draft",
                headers=headers,
            )
            generated.raise_for_status()
            generated_data = generated.json()
            assert generated_data["summary"]
            assert generated_data["rag_status"] in {"green", "amber", "red"}
            assert "initiatives" in generated_data["sources"]

            draft = client.post(
                f"/initiatives/{tracked_id}/status-updates",
                headers=headers,
                json={
                    "rag_status": "amber",
                    "summary": "Draft status update from real acceptance.",
                    "achievements": "Created deterministic sample data.",
                    "issues": "None.",
                    "next_steps": "Submit the update.",
                    "is_draft": True,
                },
            )
            draft.raise_for_status()
            draft_id = draft.json()["id"]
            assert draft.json()["is_draft"] is True

            submitted = client.post(
                f"/initiatives/{tracked_id}/status-updates/{draft_id}/submit",
                headers=headers,
            )
            submitted.raise_for_status()
            submitted_data = submitted.json()
            assert submitted_data["is_draft"] is False
            assert submitted_data["submitted_at"] is not None

            compliance = client.get(
                "/portfolio/status-updates/compliance",
                headers=headers,
            )
            compliance.raise_for_status()
            compliance_data = compliance.json()
            assert compliance_data["summary"]["total"] >= 3
            assert compliance_data["summary"]["on_time"] >= 1
            assert compliance_data["summary"]["nuclear"] >= 1
            rows = compliance_data["initiatives"]
            tracked_row = next(item for item in rows if item["initiative_id"] == tracked_id)
            silent_row = next(item for item in rows if item["initiative_id"] == silent_id)
            assert tracked_row["status"] == "on_time"
            assert tracked_row["owner_name"] is not None
            assert tracked_row["days_since"] >= 0
            assert tracked_row["nudge_count"] == 0
            assert silent_row["status"] == "nuclear"
            assert silent_row["last_update_at"] is None
            assert silent_row["days_since"] == 999

            nudge = client.post(
                f"/initiatives/{silent_id}/nudge",
                headers=headers,
                json={"channel": "both"},
            )
            nudge.raise_for_status()
            nudge_data = nudge.json()
            assert nudge_data["success"] is True
            assert nudge_data["channel"] == "both"
            assert nudge_data["delivery_status"] in {"queued", "sent"}

            compliance_after = client.get(
                "/portfolio/status-updates/compliance",
                headers=headers,
            )
            compliance_after.raise_for_status()
            silent_after = next(
                item
                for item in compliance_after.json()["initiatives"]
                if item["initiative_id"] == silent_id
            )
            assert silent_after["nudge_count"] >= 1

            recent = client.get("/status-updates/portfolio", headers=headers)
            recent.raise_for_status()
            recent_update = next(item for item in recent.json() if item["id"] == draft_id)
            assert recent_update["initiative_name"] == tracked.json()["name"]

            nudges = client.get("/status-updates/nudges", headers=headers)
            nudges.raise_for_status()
            nudge_log = next(item for item in nudges.json() if item["id"] == nudge_data["nudge_id"])
            assert nudge_log["channel"] == "both"
            assert nudge_log["initiatives"]["name"] == silent.json()["name"]

            daily = client.post("/status-updates/nudges/run-daily", headers=headers)
            daily.raise_for_status()
            daily_data = daily.json()
            assert any(item["initiative_id"] == auto_id for item in daily_data)

            compliance_after_daily = client.get(
                "/portfolio/status-updates/compliance",
                headers=headers,
            )
            compliance_after_daily.raise_for_status()
            auto_after = next(
                item
                for item in compliance_after_daily.json()["initiatives"]
                if item["initiative_id"] == auto_id
            )
            assert auto_after["nudge_count"] >= 1
        finally:
            client.delete(f"/initiatives/{tracked_id}", headers=headers)
            client.delete(f"/initiatives/{silent_id}", headers=headers)
            client.delete(f"/initiatives/{auto_id}", headers=headers)


def test_real_api_governance_gate_submission_and_portfolio_health() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        created = client.post(
            "/initiatives",
            headers=headers,
            json={
                "name": f"Acceptance Governance {uuid4()}",
                "priority": "high",
                "country": "Singapore",
            },
        )
        created.raise_for_status()
        initiative_id = created.json()["id"]

        try:
            gates = client.get(f"/initiatives/{initiative_id}/gates", headers=headers)
            gates.raise_for_status()
            gates_data = gates.json()
            assert [gate["gate_number"] for gate in gates_data["gates"]] == [1, 2]
            assert gates_data["active_submission"] is None

            blocked_stage = client.put(
                f"/initiatives/{initiative_id}",
                headers=headers,
                json={"stage": "in_progress"},
            )
            assert blocked_stage.status_code == 400
            assert "Gate 1 must be approved" in blocked_stage.json()["detail"]

            criteria = client.get(
                f"/initiatives/{initiative_id}/gates/1/criteria",
                headers=headers,
            )
            criteria.raise_for_status()
            criteria_data = criteria.json()
            assert len(criteria_data) >= 1
            assert {"ticked", "ticked_by", "ticked_at"}.issubset(criteria_data[0])

            rejected_submit = client.post(
                f"/initiatives/{initiative_id}/gates/1/submit",
                headers=headers,
                json={
                    "criteria_snapshot": [
                        {**criteria_data[0], "ticked": False},
                    ],
                    "commentary": "Should not submit without any ticked criteria.",
                },
            )
            assert rejected_submit.status_code == 400

            portfolio_before = client.get("/portfolio/governance", headers=headers)
            portfolio_before.raise_for_status()
            before = portfolio_before.json()

            submitted = client.post(
                f"/initiatives/{initiative_id}/gates/1/submit",
                headers=headers,
                json={
                    "criteria_snapshot": [
                        {**criteria_data[0], "ticked": True},
                    ],
                    "commentary": "Ready for acceptance governance review.",
                },
            )
            submitted.raise_for_status()
            submission_data = submitted.json()
            submission_id = submission_data["id"]
            assert submission_data["decision"] == "pending"
            assert submission_data["criteria_snapshot"][0]["ticked_by"] is not None
            assert submission_data["criteria_snapshot"][0]["ticked_at"] is not None

            portfolio_pending = client.get("/portfolio/governance", headers=headers)
            portfolio_pending.raise_for_status()
            pending = portfolio_pending.json()
            assert pending["pending"] == before["pending"] + 1
            assert pending["health_score"].endswith(f"/{before['total_submissions'] + 1}")

            decided = client.post(
                f"/gates/submissions/{submission_id}/decide",
                headers=headers,
                json={"decision": "approved", "commentary": "Approved by acceptance."},
            )
            decided.raise_for_status()
            assert decided.json()["decision"] == "approved"

            detail = client.get(f"/initiatives/{initiative_id}", headers=headers)
            detail.raise_for_status()
            assert detail.json()["stage"] == "in_progress"

            blocked_complete = client.put(
                f"/initiatives/{initiative_id}",
                headers=headers,
                json={"stage": "complete"},
            )
            assert blocked_complete.status_code == 400
            assert "Gate 2 must be approved" in blocked_complete.json()["detail"]

            portfolio_after = client.get("/portfolio/governance", headers=headers)
            portfolio_after.raise_for_status()
            after = portfolio_after.json()
            assert after["approved"] == before["approved"] + 1
            assert after["health_score"].startswith(str(before["approved"] + 1))
        finally:
            client.delete(f"/initiatives/{initiative_id}", headers=headers)


def test_real_api_people_directory_profile_invite_and_pressure() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        users = client.get("/users", headers=headers)
        users.raise_for_status()
        user_rows = users.json()["items"]
        assert len(user_rows) >= 1
        user_id = user_rows[0]["id"]
        original_title = user_rows[0].get("title")

        filtered = client.get("/users", headers=headers, params={"search": user_rows[0]["email"]})
        filtered.raise_for_status()
        assert any(item["id"] == user_id for item in filtered.json()["items"])

        role_filtered = client.get(
            "/users",
            headers=headers,
            params={"role": user_rows[0]["role"], "status": user_rows[0]["status"]},
        )
        role_filtered.raise_for_status()
        assert any(item["id"] == user_id for item in role_filtered.json()["items"])

        profile = client.get(f"/users/{user_id}", headers=headers)
        profile.raise_for_status()
        profile_data = profile.json()
        assert "on_their_plate" in profile_data
        assert "pressure" in profile_data
        assert "last_login_at" in profile_data
        assert profile_data["status"] in {"active", "pending", "ghost", "deactivated"}
        assert isinstance(profile_data.get("workstreams", []), list)
        original_workstream_ids = [
            item["workstream_id"] for item in profile_data.get("workstreams", [])
        ]

        pressure = client.get(f"/users/{user_id}/pressure", headers=headers)
        pressure.raise_for_status()
        assert Decimal(pressure.json()["pressure_score"]) >= Decimal("0.0")

        updated = client.put(
            f"/users/{user_id}",
            headers=headers,
            json={"title": "Acceptance People Lead"},
        )
        updated.raise_for_status()
        assert updated.json()["title"] == "Acceptance People Lead"

        workstreams = client.get("/workstreams", headers=headers)
        workstreams.raise_for_status()
        workstream_rows = workstreams.json()["data"]
        invite_email = f"transmuter.acceptance+people.{uuid4().hex}@gmail.com"
        invited_id: str | None = None
        try:
            if workstream_rows:
                assigned = client.put(
                    f"/users/{user_id}/workstreams",
                    headers=headers,
                    json={"workstream_ids": [workstream_rows[0]["id"]]},
                )
                assigned.raise_for_status()
                assert (
                    assigned.json()["workstreams"][0]["workstream_id"] == workstream_rows[0]["id"]
                )

            invited = client.post(
                "/invites",
                headers=headers,
                json={
                    "email": invite_email,
                    "display_name": "Acceptance Invite",
                    "role": "initiative_owner",
                    "title": "Invited Owner",
                },
            )
            invited.raise_for_status()
            invited_data = invited.json()
            invited_id = invited_data["id"]
            assert invited_data["status"] == "pending"

            invites = client.get("/invites", headers=headers)
            invites.raise_for_status()
            assert any(item["email"] == invite_email for item in invites.json()["items"])

            revoked = client.post(
                f"/invites/{invited_id}/revoke",
                headers=headers,
            )
            revoked.raise_for_status()
            assert revoked.json()["status"] == "revoked"
            invited_id = None
        finally:
            if invited_id:
                client.post(f"/invites/{invited_id}/revoke", headers=headers)
            client.put(
                f"/users/{user_id}/workstreams",
                headers=headers,
                json={"workstream_ids": original_workstream_ids},
            )
            client.put(
                f"/users/{user_id}",
                headers=headers,
                json={"title": original_title},
            )


def test_real_api_initiative_overview_metadata_and_editing() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        original = client.get(f"/initiatives/{initiative_id}", headers=headers)
        original.raise_for_status()
        original_data = original.json()

        assert "business_unit_ids" in original_data
        assert "business_units" in original_data
        assert "pressure_breakdown" in original_data
        assert "team_members" in original_data
        assert "kpi_indicators" in original_data
        assert original_data["counts"]["milestones_total"] >= 0

        overview_summary = f"Acceptance overview summary {uuid4()}"
        overview_context = f"Acceptance overview context {uuid4()}"

        try:
            updated = client.put(
                f"/initiatives/{initiative_id}",
                headers=headers,
                json={
                    "summary": overview_summary,
                    "dependencies_text": overview_context,
                    "rag_status": "amber",
                    "actual_start": "2026-06-15",
                    "actual_end": "2026-10-31",
                },
            )
            updated.raise_for_status()
            updated_data = updated.json()
            assert updated_data["summary"] == overview_summary
            assert updated_data["dependencies_text"] == overview_context
            assert updated_data["stage"] == original_data["stage"]
            assert updated_data["rag_status"] == "amber"
            assert updated_data["actual_start"] == "2026-06-15"
            assert updated_data["actual_end"] == "2026-10-31"
        finally:
            client.put(
                f"/initiatives/{initiative_id}",
                headers=headers,
                json={
                    "summary": original_data["summary"],
                    "dependencies_text": original_data["dependencies_text"],
                    "rag_status": original_data["rag_status"],
                    "actual_start": original_data["actual_start"],
                    "actual_end": original_data["actual_end"],
                },
            )


def test_real_api_milestone_crud_pressure_dependencies_and_checklist() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        milestone_a_id: str | None = None
        milestone_b_id: str | None = None

        try:
            milestone_a = client.post(
                f"/initiatives/{initiative_id}/milestones",
                headers=headers,
                json={
                    "name": f"Acceptance Upstream {uuid4()}",
                    "description": "Acceptance upstream milestone",
                    "priority": "high",
                    "planned_start": "2030-01-01",
                    "planned_end": "2030-02-01",
                },
            )
            milestone_a.raise_for_status()
            milestone_a_id = milestone_a.json()["id"]

            milestone_b = client.post(
                f"/initiatives/{initiative_id}/milestones",
                headers=headers,
                json={
                    "name": f"Acceptance Downstream {uuid4()}",
                    "description": "Acceptance downstream milestone",
                    "priority": "medium",
                    "planned_start": "2030-02-02",
                    "planned_end": "2030-03-01",
                },
            )
            milestone_b.raise_for_status()
            milestone_b_id = milestone_b.json()["id"]

            ordered = client.put(
                f"/milestones/{milestone_a_id}",
                headers=headers,
                json={"sort_order": 10, "status": "in_progress"},
            )
            ordered.raise_for_status()
            assert ordered.json()["sort_order"] == 10

            checklist = client.post(
                f"/milestones/{milestone_b_id}/checklist",
                headers=headers,
                json={"text": "Acceptance checklist item", "sort_order": 0},
            )
            checklist.raise_for_status()
            checklist_id = checklist.json()["id"]

            detail = client.get(f"/milestones/{milestone_b_id}", headers=headers)
            detail.raise_for_status()
            assert detail.json()["checklist_total"] == 1
            assert Decimal(detail.json()["pressure_checklist"]) == Decimal("0.50")

            toggled = client.put(
                f"/milestones/{milestone_b_id}/checklist/{checklist_id}",
                headers=headers,
                json={"completed": True},
            )
            toggled.raise_for_status()
            assert toggled.json()["completed"] is True

            dependency = client.post(
                f"/milestones/{milestone_b_id}/dependencies",
                headers=headers,
                json={"upstream_milestone_id": milestone_a_id},
            )
            dependency.raise_for_status()
            dependency_id = dependency.json()["id"]

            portfolio_milestones = client.get("/portfolio/milestones", headers=headers)
            portfolio_milestones.raise_for_status()
            milestone_rows = portfolio_milestones.json()["items"]
            assert any(item["id"] == milestone_a_id for item in milestone_rows)
            assert portfolio_milestones.json()["stats"]["total"] >= len(milestone_rows)

            portfolio_dependencies = client.get("/portfolio/dependencies", headers=headers)
            portfolio_dependencies.raise_for_status()
            portfolio_dep_data = portfolio_dependencies.json()
            dependency_row = next(
                item for item in portfolio_dep_data["items"] if item["id"] == dependency_id
            )
            assert dependency_row["status"] == "on_track"
            assert portfolio_dep_data["stats"]["total"] >= 1
            assert any(node["id"] == milestone_a_id for node in portfolio_dep_data["nodes"])
            assert any(edge["id"] == dependency_id for edge in portfolio_dep_data["edges"])

            overdue = client.put(
                f"/milestones/{milestone_a_id}",
                headers=headers,
                json={"status": "overdue", "planned_end": "2026-01-01"},
            )
            overdue.raise_for_status()

            blocking_dependencies = client.get("/portfolio/dependencies", headers=headers)
            blocking_dependencies.raise_for_status()
            blocking_dep_data = blocking_dependencies.json()
            blocking_row = next(
                item for item in blocking_dep_data["items"] if item["id"] == dependency_id
            )
            assert blocking_row["status"] == "blocking"
            assert blocking_row["upstream_status"] == "overdue"
            assert blocking_dep_data["stats"]["blocking"] >= 1

            cycle = client.post(
                f"/milestones/{milestone_a_id}/dependencies",
                headers=headers,
                json={"upstream_milestone_id": milestone_b_id},
            )
            assert cycle.status_code == 400

            pressure = client.get(f"/milestones/{milestone_a_id}/pressure", headers=headers)
            pressure.raise_for_status()
            pressure_data = pressure.json()
            assert Decimal(pressure_data["blast_radius"]) >= Decimal("1.00")
            assert pressure_data["level"] in {"low", "medium", "high"}

            downstream_detail = client.get(f"/milestones/{milestone_b_id}", headers=headers)
            downstream_detail.raise_for_status()
            assert downstream_detail.json()["dependencies"][0]["upstream_name"]
        finally:
            if milestone_b_id:
                client.delete(f"/milestones/{milestone_b_id}", headers=headers)
            if milestone_a_id:
                client.delete(f"/milestones/{milestone_a_id}", headers=headers)


def test_real_api_kpi_crud_entries_and_portfolio_pulse() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        kpi_id: str | None = None

        try:
            created = client.post(
                f"/initiatives/{initiative_id}/kpis",
                headers=headers,
                json={
                    "name": f"Acceptance KPI {uuid4()}",
                    "type": "custom",
                    "frequency": "quarterly",
                    "unit": "%",
                },
            )
            created.raise_for_status()
            kpi_id = created.json()["id"]

            updated = client.put(
                f"/initiatives/{initiative_id}/kpis/{kpi_id}",
                headers=headers,
                json={"name": "Acceptance KPI Updated"},
            )
            updated.raise_for_status()
            assert updated.json()["name"] == "Acceptance KPI Updated"

            entries = client.put(
                f"/initiatives/{initiative_id}/kpis/{kpi_id}/entries",
                headers=headers,
                json=[
                    {
                        "year": 2030,
                        "quarter": 1,
                        "value_base": "75.0000",
                        "value_high": "90.0000",
                        "value_actual": "82.5000",
                    }
                ],
            )
            entries.raise_for_status()
            assert Decimal(entries.json()[0]["value_actual"]) == Decimal("82.5000")

            listed = client.get(f"/initiatives/{initiative_id}/kpis", headers=headers)
            listed.raise_for_status()
            item = next(item for item in listed.json()["items"] if item["id"] == kpi_id)
            assert item["health_status"] == "at_risk"

            pulse = client.get("/portfolio/kpi-pulse", headers=headers)
            pulse.raise_for_status()
            pulse_data = pulse.json()
            assert pulse_data["total_kpis"] >= 1
            Decimal(pulse_data["health_score"])
        finally:
            if kpi_id:
                client.delete(f"/initiatives/{initiative_id}/kpis/{kpi_id}", headers=headers)


def test_real_api_risk_crud_rating_filters_and_heatmap() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        risk_id: str | None = None

        try:
            created = client.post(
                f"/initiatives/{initiative_id}/risks",
                headers=headers,
                json={
                    "description": f"Acceptance Risk {uuid4()}",
                    "type": "operational",
                    "impact": "high",
                    "likelihood": "high",
                    "mitigation": "Acceptance mitigation plan",
                    "status": "open",
                    "escalated": True,
                },
            )
            created.raise_for_status()
            risk_id = created.json()["id"]
            assert created.json()["rating"] == "high"

            filtered = client.get("/portfolio/risks?rating=high", headers=headers)
            filtered.raise_for_status()
            assert any(item["id"] == risk_id for item in filtered.json()["items"])

            heatmap = client.get("/portfolio/risks/heatmap", headers=headers)
            heatmap.raise_for_status()
            assert heatmap.json()["total_open_risks"] >= 1

            updated = client.put(
                f"/initiatives/{initiative_id}/risks/{risk_id}",
                headers=headers,
                json={"impact": "low", "likelihood": "low", "escalated": False},
            )
            updated.raise_for_status()
            assert updated.json()["rating"] == "low"
            assert updated.json()["escalated"] is False

            closed = client.put(
                f"/initiatives/{initiative_id}/risks/{risk_id}",
                headers=headers,
                json={"status": "closed"},
            )
            closed.raise_for_status()
            assert closed.json()["status"] == "closed"
        finally:
            if risk_id:
                client.delete(f"/initiatives/{initiative_id}/risks/{risk_id}", headers=headers)


def test_real_api_financial_grid_save_reload_and_value_bridge() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_items = initiatives.json()["items"]
        initiative_id = initiative_items[0]["id"]
        for item in initiative_items:
            candidate = client.get(f"/initiatives/{item['id']}/financials", headers=headers)
            candidate.raise_for_status()
            if not candidate.json()["locked"]:
                initiative_id = item["id"]
                break

        grid = client.get(f"/initiatives/{initiative_id}/financials", headers=headers)
        grid.raise_for_status()
        assert grid.json()["locked"] is False
        entries = grid.json()["entries"]
        assert entries, "seeded initiative must include financial entries"
        period_keys = {(entry["year"], entry["quarter"], entry["month"]) for entry in entries}
        assert len(period_keys) == len(entries), "financial periods must be unique"

        original = next((entry for entry in entries if entry["month"] is not None), entries[0])
        selections = client.get(
            f"/initiatives/{initiative_id}/financials/selections",
            headers=headers,
        )
        selections.raise_for_status()
        selected_cost_keys = selections.json()["selected"]["cost_category_keys"]
        cost_category_key = selected_cost_keys[0] if selected_cost_keys else "implementation"
        cost_name = f"Acceptance Recurring Cost {uuid4()}"
        cost_line_id: str | None = None
        assumption_id: str | None = None
        update_entry = {
            "year": original["year"],
            "quarter": original["quarter"],
            "month": original["month"],
            "revenue_uplift_base": "123456.7800",
            "revenue_uplift_high": "223456.7800",
            "revenue_uplift_actual": "100000.0000",
            "gross_margin_base": "50000.0000",
            "gross_margin_high": "80000.0000",
            "gross_margin_actual": "45000.0000",
            "gm_uplift_base": "40000.0000",
            "gm_uplift_high": "65000.0000",
            "gm_uplift_actual": "35000.0000",
        }

        try:
            saved = client.put(
                f"/initiatives/{initiative_id}/financials",
                headers=headers,
                json={
                    "entries": [update_entry],
                    "cost_lines": [
                        {
                            "name": cost_name,
                            "category_key": cost_category_key,
                            "year": original["year"],
                            "quarter": original["quarter"],
                            "month": original["month"],
                            "amount_plan": "1250.0000",
                            "amount_actual": "1000.0000",
                            "is_recurring": True,
                        }
                    ],
                },
            )
            saved.raise_for_status()

            reloaded = client.get(f"/initiatives/{initiative_id}/financials", headers=headers)
            reloaded.raise_for_status()
            matching = [
                entry
                for entry in reloaded.json()["entries"]
                if entry["year"] == update_entry["year"]
                and entry["quarter"] == update_entry["quarter"]
                and entry["month"] == update_entry["month"]
            ]
            assert matching
            assert Decimal(matching[0]["revenue_uplift_base"]) == Decimal("123456.7800")
            assert Decimal(matching[0]["gm_uplift_actual"]) == Decimal("35000.0000")

            cost_lines = client.get(
                f"/initiatives/{initiative_id}/financials/cost-lines",
                headers=headers,
            )
            cost_lines.raise_for_status()
            created_cost = next(
                item for item in cost_lines.json()["items"] if item["name"] == cost_name
            )
            cost_line_id = created_cost["id"]
            assert Decimal(created_cost["amount_plan"]) == Decimal("1250.0000")
            assert Decimal(created_cost["amount_actual"]) == Decimal("1000.0000")

            bridge = client.get(
                f"/initiatives/{initiative_id}/financials/value-bridge",
                headers=headers,
            )
            bridge.raise_for_status()
            bridge_data = bridge.json()
            assert Decimal(bridge_data["base_case"]["gm_uplift"]) >= Decimal("40000.0000")
            assert Decimal(bridge_data["actual"]["costs_recurring"]) >= Decimal("1000.0000")

            scenario = client.get(
                f"/initiatives/{initiative_id}/financials/scenario-summary?scenario=high",
                headers=headers,
            )
            scenario.raise_for_status()
            scenario_data = scenario.json()
            assert scenario_data["scenario"] == "high"
            assert Decimal(scenario_data["gm_uplift"]) >= Decimal("65000.0000")
            assert Decimal(scenario_data["net_value"]) > Decimal("0")

            break_even = client.get(
                f"/initiatives/{initiative_id}/financials/break-even?scenario=base",
                headers=headers,
            )
            break_even.raise_for_status()
            break_even_data = break_even.json()
            assert break_even_data["scenario"] == "base"
            assert break_even_data["points"]
            assert all("cumulative_gm_uplift" in point for point in break_even_data["points"])
            Decimal(break_even_data["points"][0]["cumulative_costs"])

            assumption_comment = f"Acceptance assumption {uuid4()}"
            assumption = client.post(
                f"/initiatives/{initiative_id}/financials/assumptions",
                headers=headers,
                json={
                    "row_key": "gm_uplift_base",
                    "column_key": f"col_{original['year']}_q{original['quarter'] or 1}",
                    "comment": assumption_comment,
                },
            )
            assumption.raise_for_status()
            assumption_data = assumption.json()
            assumption_id = assumption_data["id"]
            assert assumption_data["comment"] == assumption_comment

            assumptions = client.get(
                f"/initiatives/{initiative_id}/financials/assumptions",
                headers=headers,
            )
            assumptions.raise_for_status()
            assert any(item["id"] == assumption_id for item in assumptions.json()["items"])

            updated_assumption = client.put(
                f"/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
                headers=headers,
                json={"comment": "Updated acceptance assumption"},
            )
            updated_assumption.raise_for_status()
            assert updated_assumption.json()["comment"] == "Updated acceptance assumption"
        finally:
            if assumption_id:
                client.delete(
                    f"/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
                    headers=headers,
                )
            restore = {key: original[key] for key in update_entry if key in original}
            client.put(
                f"/initiatives/{initiative_id}/financials",
                headers=headers,
                json={"entries": [restore], "cost_lines": []},
            )
            if cost_line_id:
                client.delete(
                    f"/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
                    headers=headers,
                )


def test_real_api_financial_configuration_category_reassignment_and_portfolio_rollup() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_id = initiatives.json()["items"][0]["id"]

        configuration = client.get("/admin/financial-configuration", headers=headers)
        configuration.raise_for_status()
        original_config = configuration.json()
        groups = original_config["groups"]
        items = original_config["items"]
        assert any(group["kind"] == "cost_category" for group in groups)
        assert any(item["key"] == "software" for item in items)

        group = next(group for group in groups if group["kind"] == "cost_category")
        replacement = next(
            item
            for item in items
            if item["item_type"] == "cost_category"
            and item["key"] != "other"
            and item.get("is_active", True)
        )
        category_key = f"acceptance_{uuid4().hex[:12]}"
        category_label = "Acceptance Reassign Category"
        cost_line_id: str | None = None
        amount_plan = Decimal("4321.0000")
        amount_actual = Decimal("3210.0000")
        year = 2026

        try:
            updated_config = client.put(
                "/admin/financial-configuration",
                headers=headers,
                json={
                    "groups": groups,
                    "items": [
                        *items,
                        {
                            "group_key": group["key"],
                            "key": category_key,
                            "label": category_label,
                            "item_type": "cost_category",
                            "system_metric_key": None,
                            "rollup_type": "one_off_cost",
                            "display_order": 999,
                            "is_system": False,
                            "is_active": True,
                        },
                    ],
                },
            )
            updated_config.raise_for_status()
            assert any(item["key"] == category_key for item in updated_config.json()["items"])

            created_cost = client.post(
                f"/initiatives/{initiative_id}/financials/cost-lines",
                headers=headers,
                json={
                    "name": f"Acceptance category reassignment {uuid4()}",
                    "year": year,
                    "quarter": 1,
                    "month": None,
                    "amount_plan": str(amount_plan),
                    "amount_actual": str(amount_actual),
                    "is_recurring": False,
                    "category_key": category_key,
                },
            )
            created_cost.raise_for_status()
            cost_line_id = created_cost.json()["id"]
            assert created_cost.json()["category_key"] == category_key

            portfolio = client.get(
                f"/portfolio/financials?granularity=quarterly&year={year}&category_key={category_key}",
                headers=headers,
            )
            portfolio.raise_for_status()
            portfolio_data = portfolio.json()
            category = next(
                row for row in portfolio_data["cost_breakdown"] if row["key"] == category_key
            )
            assert category["label"] == category_label
            assert Decimal(category["plan"]) >= amount_plan
            assert Decimal(category["actual"]) >= amount_actual
            assert any(
                row["period"] == f"{year}-Q1" and Decimal(row["one_off_costs_plan"]) >= amount_plan
                for row in portfolio_data["periods"]
            )

            contributors = client.get(
                (
                    "/portfolio/financials/contributors"
                    f"?granularity=quarterly&period={year}-Q1&year={year}"
                    f"&category_key={category_key}"
                ),
                headers=headers,
            )
            contributors.raise_for_status()
            assert any(
                line["category_key"] == category_key
                for contributor in contributors.json()["contributors"]
                for line in contributor["cost_lines"]
            )

            reassignment = client.post(
                "/admin/financial-configuration/cost-categories/delete",
                headers=headers,
                json={"category_key": category_key, "replacement_key": replacement["key"]},
            )
            reassignment.raise_for_status()
            assert reassignment.json()["reassigned"] >= 1

            cost_lines = client.get(
                f"/initiatives/{initiative_id}/financials/cost-lines",
                headers=headers,
            )
            cost_lines.raise_for_status()
            reassigned = next(
                item for item in cost_lines.json()["items"] if item["id"] == cost_line_id
            )
            assert reassigned["category_key"] == replacement["key"]
        finally:
            if cost_line_id:
                client.delete(
                    f"/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
                    headers=headers,
                )
            client.put("/admin/financial-configuration", headers=headers, json=original_config)


def test_real_api_financial_excel_export_import_roundtrip() -> None:
    with _client() as client:
        headers = _auth_headers(client)

        initiatives = client.get("/initiatives", headers=headers)
        initiatives.raise_for_status()
        initiative_items = initiatives.json()["items"]
        initiative_id = initiative_items[0]["id"]
        for item in initiative_items:
            candidate = client.get(f"/initiatives/{item['id']}/financials", headers=headers)
            candidate.raise_for_status()
            if not candidate.json()["locked"]:
                initiative_id = item["id"]
                break

        exported = client.get(
            f"/initiatives/{initiative_id}/financials/export.xlsx",
            headers=headers,
        )
        exported.raise_for_status()
        assert exported.headers["content-type"] == XLSX_MEDIA_TYPE
        with ZipFile(BytesIO(exported.content)) as zf:
            assert "xl/workbook.xml" in zf.namelist()

        workbook, period, original_entry, cost_name = _patched_financial_workbook(
            exported.content,
            revenue_uplift_base="98765.4321",
            gm_uplift_actual="12345.6789",
        )
        cost_line_id: str | None = None

        try:
            imported = client.post(
                f"/initiatives/{initiative_id}/financials/import.xlsx",
                headers=headers,
                files={"file": ("financials.xlsx", workbook, XLSX_MEDIA_TYPE)},
            )
            imported.raise_for_status()

            grid = client.get(f"/initiatives/{initiative_id}/financials", headers=headers)
            grid.raise_for_status()
            assert grid.json()["locked"] is False
            matching = [
                entry
                for entry in grid.json()["entries"]
                if entry["year"] == period["year"]
                and entry["quarter"] == period["quarter"]
                and entry["month"] == period["month"]
            ]
            assert matching
            assert Decimal(matching[0]["revenue_uplift_base"]) == Decimal("98765.4321")
            assert Decimal(matching[0]["gm_uplift_actual"]) == Decimal("12345.6789")

            cost_lines = client.get(
                f"/initiatives/{initiative_id}/financials/cost-lines",
                headers=headers,
            )
            cost_lines.raise_for_status()
            imported_cost = next(
                item for item in cost_lines.json()["items"] if item["name"] == cost_name
            )
            cost_line_id = imported_cost["id"]
            assert Decimal(imported_cost["amount_plan"]) == Decimal("3333.3300")
            assert Decimal(imported_cost["amount_actual"]) == Decimal("2222.2200")
        finally:
            client.put(
                f"/initiatives/{initiative_id}/financials",
                headers=headers,
                json={"entries": [original_entry], "cost_lines": []},
            )
            if cost_line_id:
                client.delete(
                    f"/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
                    headers=headers,
                )


def _patched_financial_workbook(
    data: bytes,
    *,
    revenue_uplift_base: str,
    gm_uplift_actual: str,
) -> tuple[bytes, dict[str, int | None], dict[str, str | int | None], str]:
    source = BytesIO(data)
    output = BytesIO()
    cost_name = f"Acceptance Excel Cost {uuid4()}"
    with ZipFile(source) as zin, ZipFile(output, "w", compression=ZIP_DEFLATED) as zout:
        period: dict[str, int | None] | None = None
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                content, period, original_entry = _patch_entries_sheet(
                    content,
                    revenue_uplift_base=revenue_uplift_base,
                    gm_uplift_actual=gm_uplift_actual,
                )
            elif item.filename == "xl/worksheets/sheet2.xml":
                assert period is not None
                content = _append_cost_line(content, period=period, cost_name=cost_name)
            zout.writestr(item, content)
    assert period is not None
    return output.getvalue(), period, original_entry, cost_name


def _patched_initiative_workbook(
    data: bytes,
    *,
    name: str,
    summary: str,
) -> bytes:
    output = BytesIO()
    with ZipFile(BytesIO(data)) as zin, ZipFile(output, "w", compression=ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                content = _patch_initiative_overview_sheet(content, name=name, summary=summary)
            elif item.filename.startswith("xl/worksheets/sheet"):
                content = _patch_import_benefits_sheet_if_present(content)
            zout.writestr(item, content)
    return output.getvalue()


def _patched_reference_value(data: bytes, key: str, value: str) -> bytes:
    output = BytesIO()
    with ZipFile(BytesIO(data)) as zin, ZipFile(output, "w", compression=ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == "xl/worksheets/sheet11.xml":
                content = _patch_reference_sheet(content, key=key, value=value)
            zout.writestr(item, content)
    return output.getvalue()


def _patch_initiative_overview_sheet(data: bytes, *, name: str, summary: str) -> bytes:
    ET.register_namespace("", SHEET_NS["main"])
    root = ET.fromstring(data)
    rows = root.findall("main:sheetData/main:row", SHEET_NS)
    headers = _row_values(rows[0])
    if "name" in headers:
        target = rows[1]
        _set_cell(target, headers.index("name") + 1, name)
        _set_cell(target, headers.index("summary") + 1, summary)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)
    for row in rows:
        values = _row_values(row)
        if values and values[0] == "Name":
            _set_cell(row, 2, name)
        if values and values[0] == "Description":
            _set_cell(row, 2, summary)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_reference_sheet(data: bytes, *, key: str, value: str) -> bytes:
    ET.register_namespace("", SHEET_NS["main"])
    root = ET.fromstring(data)
    rows = root.findall("main:sheetData/main:row", SHEET_NS)
    headers = _row_values(rows[0])
    key_index = headers.index("key") + 1
    value_index = headers.index("value") + 1
    for row in rows[1:]:
        if _row_values(row)[key_index - 1] == key:
            _set_cell(row, value_index, value)
            break
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_import_benefits_sheet_if_present(data: bytes) -> bytes:
    ET.register_namespace("", SHEET_NS["main"])
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return data
    rows = root.findall("main:sheetData/main:row", SHEET_NS)
    if len(rows) < 2:
        return data
    headers = _row_values(rows[0])
    if {"year", "month", "revenue_uplift_base"}.issubset(headers):
        target = rows[1]
        updates = {
            "year": "2030",
            "quarter": "",
            "month": "1",
            "revenue_uplift_base": "33333.0",
        }
        for header, value in updates.items():
            if header in headers:
                _set_cell(target, headers.index(header) + 1, value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    if not {"Name", "Lane", "FY26"}.issubset(headers):
        return data
    monthly_start = headers.index("FY26") + 5
    fy26_june_col = monthly_start + 5
    for row in rows[1:]:
        values = _row_values(row)
        if len(values) >= 2 and values[0] == "Revenue Uplift" and values[1] == "Plan Base":
            _set_cell(row, headers.index("FY26") + 1, "0.033333")
            _set_cell(row, fy26_june_col + 1, "0.033333")
            break
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_entries_sheet(
    data: bytes,
    *,
    revenue_uplift_base: str,
    gm_uplift_actual: str,
) -> tuple[bytes, dict[str, int | None], dict[str, str | int | None]]:
    ET.register_namespace("", SHEET_NS["main"])
    root = ET.fromstring(data)
    rows = root.findall("main:sheetData/main:row", SHEET_NS)
    headers = _row_values(rows[0])
    target = rows[1]
    values = _row_values(target)
    period = {
        "year": int(values[headers.index("year")]),
        "quarter": _optional_int(values[headers.index("quarter")]),
        "month": _optional_int(values[headers.index("month")]),
    }
    original = {
        header: (
            _optional_int(values[index])
            if header in {"quarter", "month"}
            else int(values[index])
            if header == "year"
            else None
            if header.endswith("_actual") and values[index] == ""
            else values[index]
        )
        for index, header in enumerate(headers)
    }
    _set_cell(target, headers.index("revenue_uplift_base") + 1, revenue_uplift_base)
    _set_cell(target, headers.index("gm_uplift_actual") + 1, gm_uplift_actual)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), period, original


def _append_cost_line(data: bytes, *, period: dict[str, int | None], cost_name: str) -> bytes:
    ET.register_namespace("", SHEET_NS["main"])
    root = ET.fromstring(data)
    sheet_data = root.find("main:sheetData", SHEET_NS)
    assert sheet_data is not None
    rows = sheet_data.findall("main:row", SHEET_NS)
    headers = _row_values(rows[0])
    values = {
        "name": cost_name,
        "year": str(period["year"]),
        "quarter": "" if period["quarter"] is None else str(period["quarter"]),
        "month": "" if period["month"] is None else str(period["month"]),
        "amount_plan": "3333.3300",
        "amount_actual": "2222.2200",
        "is_recurring": "true",
    }
    row_index = len(rows) + 1
    row = ET.SubElement(sheet_data, f"{{{SHEET_NS['main']}}}row", {"r": str(row_index)})
    for col_index, header in enumerate(headers, start=1):
        _add_inline_cell(row, col_index, row_index, values.get(header, ""))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _row_values(row: ET.Element) -> list[str]:
    return ["".join(cell.itertext()) for cell in row.findall("main:c", SHEET_NS)]


def _set_cell(row: ET.Element, col_index: int, value: str) -> None:
    row_index = int(row.attrib["r"])
    ref = f"{_column_name(col_index)}{row_index}"
    cell = next(
        (
            candidate
            for candidate in row.findall("main:c", SHEET_NS)
            if candidate.attrib.get("r") == ref
        ),
        None,
    )
    if cell is None:
        _add_inline_cell(row, col_index, row_index, value)
        return
    text = cell.find("main:is/main:t", SHEET_NS)
    assert text is not None
    text.text = value


def _add_inline_cell(row: ET.Element, col_index: int, row_index: int, value: str) -> None:
    cell = ET.SubElement(
        row,
        f"{{{SHEET_NS['main']}}}c",
        {"r": f"{_column_name(col_index)}{row_index}", "t": "inlineStr"},
    )
    inline = ET.SubElement(cell, f"{{{SHEET_NS['main']}}}is")
    text = ET.SubElement(inline, f"{{{SHEET_NS['main']}}}t")
    text.text = value


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def _optional_int(value: str) -> int | None:
    return int(value) if value else None
