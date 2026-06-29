from __future__ import annotations

import os
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers() -> dict[str, str]:
    credentials = [
        (
            os.environ.get("TRANSMUTER_TEST_EMAIL", "admin@ishirock.dev"),
            os.environ.get("TRANSMUTER_TEST_PASSWORD", "Transmuter2026!"),
        ),
        ("admin@acme3-transformation.dev", "Transmuter2026!"),
        ("admin@acme-transformation.dev", "Transmuter2026!"),
    ]
    response = None
    for email, password in dict.fromkeys(credentials):
        response = client.post("/auth/login", json={"email": email, "password": password})
        if response.is_success:
            return {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert response is not None
    response.raise_for_status()
    return {}


def _first_initiative(headers: dict[str, str]) -> str:
    response = client.get("/initiatives", headers=headers)
    response.raise_for_status()
    return response.json()["items"][0]["id"]


def _first_user(headers: dict[str, str]) -> str:
    response = client.get("/users", headers=headers)
    response.raise_for_status()
    return response.json()["items"][0]["id"]


def test_real_team_routes_cover_member_lifecycle_and_guards() -> None:
    headers = _headers()
    initiative_id = _first_initiative(headers)
    user_id = _first_user(headers)

    team = client.get(f"/initiatives/{initiative_id}/team", headers=headers)
    team.raise_for_status()

    member_id: str | None = None
    try:
        added = client.post(
            f"/initiatives/{initiative_id}/team",
            headers=headers,
            json={"user_id": user_id, "role": f"qa_reviewer_{uuid4().hex[:8]}"},
        )
        added.raise_for_status()
        member_id = added.json()["data"]["id"]

        reloaded = client.get(f"/initiatives/{initiative_id}/team", headers=headers)
        reloaded.raise_for_status()
        assert any(item["id"] == member_id for item in reloaded.json()["data"])

        missing_user = client.post(
            f"/initiatives/{initiative_id}/team",
            headers=headers,
            json={"user_id": "ffffffff-ffff-ffff-ffff-ffffffffffff", "role": "reviewer"},
        )
        assert missing_user.status_code == 404
    finally:
        if member_id:
            removed = client.delete(
                f"/initiatives/{initiative_id}/team/{member_id}",
                headers=headers,
            )
            assert removed.status_code == 200

    missing_member = client.delete(
        f"/initiatives/{initiative_id}/team/ffffffff-ffff-ffff-ffff-ffffffffffff",
        headers=headers,
    )
    assert missing_member.status_code == 404


def test_real_financial_routes_cover_grid_costs_assumptions_and_rollups() -> None:
    headers = _headers()
    initiative_id = _first_initiative(headers)

    grid = client.get(f"/initiatives/{initiative_id}/financials", headers=headers)
    grid.raise_for_status()
    entry = grid.json()["entries"][0]

    selections = client.get(f"/initiatives/{initiative_id}/financials/selections", headers=headers)
    selections.raise_for_status()
    selected = selections.json()["selected"]
    category_key = (selected["cost_category_keys"] or ["implementation"])[0]

    cost_line_id: str | None = None
    assumption_id: str | None = None
    try:
        saved = client.put(
            f"/initiatives/{initiative_id}/financials",
            headers=headers,
            json={
                "entries": [
                    {
                        "year": entry["year"],
                        "quarter": entry["quarter"],
                        "month": entry["month"],
                        "revenue_uplift_base": "11111.0000",
                        "revenue_uplift_high": "22222.0000",
                        "gm_uplift_base": "3333.0000",
                        "gm_uplift_high": "4444.0000",
                        "gm_uplift_actual": "2222.0000",
                    }
                ]
            },
        )
        saved.raise_for_status()

        created_cost = client.post(
            f"/initiatives/{initiative_id}/financials/cost-lines",
            headers=headers,
            json={
                "name": f"Route coverage cost {uuid4()}",
                "category_key": category_key,
                "year": entry["year"],
                "quarter": entry["quarter"],
                "month": entry["month"],
                "amount_plan": "555.0000",
                "amount_actual": "444.0000",
                "is_recurring": True,
            },
        )
        created_cost.raise_for_status()
        cost_line_id = created_cost.json()["id"]

        updated_cost = client.put(
            f"/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
            headers=headers,
            json={"amount_actual": "445.0000"},
        )
        updated_cost.raise_for_status()
        assert updated_cost.json()["amount_actual"] == "445.0000"

        costs = client.get(f"/initiatives/{initiative_id}/financials/cost-lines", headers=headers)
        costs.raise_for_status()
        assert any(item["id"] == cost_line_id for item in costs.json()["items"])

        for path in (
            f"/initiatives/{initiative_id}/financials/value-bridge",
            f"/initiatives/{initiative_id}/financials/scenario-summary?scenario=actual",
            f"/initiatives/{initiative_id}/financials/break-even?scenario=base",
            "/portfolio/value-bridge",
            f"/portfolio/value-ramp?granularity=quarterly&run_rate_year={entry['year']}",
            f"/portfolio/financials?granularity=quarterly&year={entry['year']}",
            f"/portfolio/financials/contributors?granularity=quarterly&period={entry['year']}-Q1&year={entry['year']}",
            "/financial-configuration",
            "/admin/financial-configuration",
        ):
            response = client.get(path, headers=headers)
            response.raise_for_status()

        assumption = client.post(
            f"/initiatives/{initiative_id}/financials/assumptions",
            headers=headers,
            json={
                "row_key": "gm_uplift_base",
                "column_key": f"{entry['year']}-Q{entry['quarter'] or 1}",
                "comment": "Route coverage assumption",
            },
        )
        assumption.raise_for_status()
        assumption_id = assumption.json()["id"]

        listed = client.get(
            f"/initiatives/{initiative_id}/financials/assumptions",
            headers=headers,
        )
        listed.raise_for_status()
        assert any(item["id"] == assumption_id for item in listed.json()["items"])

        updated_assumption = client.put(
            f"/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
            headers=headers,
            json={"comment": "Updated route coverage assumption"},
        )
        updated_assumption.raise_for_status()
        assert updated_assumption.json()["comment"] == "Updated route coverage assumption"
    finally:
        if assumption_id:
            client.delete(
                f"/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
                headers=headers,
            )
        if cost_line_id:
            client.delete(
                f"/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
                headers=headers,
            )


def test_real_executive_control_routes_cover_reports_and_shared_costs() -> None:
    headers = _headers()

    dependencies = client.get("/initiative-dependencies", headers=headers)
    dependencies.raise_for_status()

    config = client.get("/shared-costs/config", headers=headers)
    config.raise_for_status()
    config_data = config.json()
    assert any(item["key"] == "equal_split" for item in config_data["allocation_methods"])
    assert "reporting_settings" in config_data

    settings = client.get("/shared-costs/reporting-settings", headers=headers)
    settings.raise_for_status()
    restored_settings = client.put(
        "/shared-costs/reporting-settings",
        headers=headers,
        json=settings.json(),
    )
    restored_settings.raise_for_status()

    pools = client.get("/shared-cost-pools", headers=headers)
    pools.raise_for_status()
    pool_items = pools.json()["items"]
    assert pool_items
    pool_id = pool_items[0]["id"]
    target_year = pool_items[0]["year"]

    for path in (
        f"/shared-cost-pools/{pool_id}/periods",
        f"/shared-cost-pools/{pool_id}/allocation-rules",
        f"/shared-cost-pools/{pool_id}/allocation-runs",
        "/shared-cost-allocations",
        f"/reports/executive-control-tower?target_year={target_year}",
        f"/reports/investor-summary?target_year={target_year}",
        f"/reports/owner-cockpit?target_year={target_year}",
    ):
        response = client.get(path, headers=headers)
        response.raise_for_status()

    rules = client.get(f"/shared-cost-pools/{pool_id}/allocation-rules", headers=headers)
    rule_items = rules.json()
    if rule_items:
        preview = client.post(
            f"/shared-cost-pools/{pool_id}/allocation-runs/preview",
            headers=headers,
            json={"rule_id": rule_items[0]["id"], "scenario": "plan"},
        )
        preview.raise_for_status()
        preview_data = preview.json()
        assert "reconciliation" in preview_data
        assert "allocations" in preview_data

    initiative_id = _first_initiative(headers)
    notes = client.get(
        f"/initiatives/{initiative_id}/value-realization-notes",
        headers=headers,
    )
    notes.raise_for_status()

    missing_pool = client.post(
        "/shared-cost-pools/ffffffff-ffff-ffff-ffff-ffffffffffff",
        headers=headers,
        json={"name": "Missing", "year": 2026, "amount_plan": "1.0000"},
    )
    assert missing_pool.status_code in {404, 405, 422}


def test_real_initiative_template_preview_and_intake_routes() -> None:
    headers = _headers()
    imported_initiative_id: str | None = None
    intake_initiative_id: str | None = None

    try:
        template = client.get("/initiatives/template", headers=headers)
        template.raise_for_status()
        assert template.headers["content-type"] == (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        preview = client.post(
            "/initiatives/import/preview",
            headers=headers,
            files={
                "file": (
                    "template.xlsx",
                    template.content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        preview.raise_for_status()
        assert preview.json()["validation_errors"] == []

        imported = client.post(
            "/initiatives/import",
            headers=headers,
            files={
                "file": (
                    "template.xlsx",
                    template.content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        imported.raise_for_status()
        imported_initiative_id = imported.json()["id"]

        initiative_payload = {
            "name": f"Route Coverage Intake {uuid4()}",
            "type": "cost_reduction",
            "impact_type": "recurring",
            "theme": "Route coverage",
            "country": "Singapore",
            "priority": "medium",
            "summary": "Route coverage intake summary.",
            "value_logic": "Validate deterministic intake suggestions.",
            "planned_start": "2026-06-01",
            "planned_end": "2026-09-30",
        }
        suggestions = client.post(
            "/initiatives/intake/suggestions",
            headers=headers,
            json={"initiative": initiative_payload, "conversation": []},
        )
        suggestions.raise_for_status()
        suggestion_payload = suggestions.json()
        assert suggestion_payload["financial_entries"] == []
        assert suggestion_payload["cost_lines"] == []
        assert suggestion_payload["kpis"]

        extracted = client.post(
            "/initiatives/intake/extract",
            headers=headers,
            json={
                "text": (
                    "Initiative: Route coverage extraction. Type: cost reduction. "
                    "Priority: medium. Market: Singapore. Complete by September 2026."
                )
            },
        )
        extracted.raise_for_status()
        assert extracted.json()["draft"]["type"] == "cost_reduction"

        kpis = client.post(
            "/initiatives/intake/kpis",
            headers=headers,
            json={
                "initiative_type": "cost_reduction",
                "initiative_name": "Route coverage extraction",
                "value_logic": "Reduce operating cost with reviewable evidence.",
            },
        )
        kpis.raise_for_status()
        assert kpis.json()["suggestions"]

        risks = client.post(
            "/initiatives/intake/risks",
            headers=headers,
            json={
                "initiative_draft": {
                    "name": "Route coverage extraction",
                    "type": "cost_reduction",
                    "dependencies": "Finance validation",
                }
            },
        )
        risks.raise_for_status()
        assert risks.json()["risks"]

        created_from_intake = client.post(
            "/initiatives/intake/create",
            headers=headers,
            json={"initiative": initiative_payload, "suggestions": suggestion_payload},
        )
        created_from_intake.raise_for_status()
        intake_initiative_id = created_from_intake.json()["id"]
    finally:
        for initiative_id in (intake_initiative_id, imported_initiative_id):
            if initiative_id:
                client.delete(f"/initiatives/{initiative_id}", headers=headers)


def test_real_initiative_crud_summary_export_and_status_update_routes() -> None:
    headers = _headers()
    initiative_id: str | None = None
    update_id: str | None = None

    try:
        created = client.post(
            "/initiatives",
            headers=headers,
            json={
                "name": f"Route Coverage CRUD {uuid4()}",
                "type": "capability_building",
                "impact_type": "one_off",
                "theme": "Route coverage",
                "country": "Singapore",
                "priority": "low",
                "summary": "Temporary route coverage initiative.",
                "planned_start": "2026-07-01",
                "planned_end": "2026-08-31",
            },
        )
        created.raise_for_status()
        initiative_id = created.json()["id"]

        detail = client.get(f"/initiatives/{initiative_id}", headers=headers)
        detail.raise_for_status()

        updated = client.put(
            f"/initiatives/{initiative_id}",
            headers=headers,
            json={"priority": "medium", "summary": "Updated route coverage summary."},
        )
        updated.raise_for_status()
        assert updated.json()["priority"] == "medium"

        for path in (
            "/initiatives/export",
            f"/initiatives/{initiative_id}/export",
            f"/initiatives/{initiative_id}/summary",
        ):
            response = client.get(path, headers=headers)
            response.raise_for_status()

        summary = client.patch(
            f"/initiatives/{initiative_id}/summary",
            headers=headers,
            json={
                "final_summary": "Route coverage closure summary.",
                "lessons_learned": "Keep temporary QA data isolated.",
            },
        )
        summary.raise_for_status()
        assert summary.json()["final_summary"] == "Route coverage closure summary."

        draft_suggestion = client.post(
            f"/initiatives/{initiative_id}/status-updates/generate-draft",
            headers=headers,
        )
        draft_suggestion.raise_for_status()
        assert draft_suggestion.json()["sources"]

        ai_context = client.get(f"/initiatives/{initiative_id}/ai-context", headers=headers)
        ai_context.raise_for_status()
        assert ai_context.json()["initiative_id"] == initiative_id

        created_update = client.post(
            f"/initiatives/{initiative_id}/status-updates",
            headers=headers,
            json={
                "rag_status": "green",
                "summary": "Route coverage draft status update.",
                "achievements": "Draft created through the real route.",
                "is_draft": True,
            },
        )
        created_update.raise_for_status()
        update_id = created_update.json()["id"]

        draft = client.get(f"/initiatives/{initiative_id}/status-updates/draft", headers=headers)
        draft.raise_for_status()
        assert draft.json()["id"] == update_id

        patched = client.put(
            f"/initiatives/{initiative_id}/status-updates/{update_id}",
            headers=headers,
            json={"next_steps": "Submit through the real route."},
        )
        patched.raise_for_status()
        assert patched.json()["next_steps"] == "Submit through the real route."

        submitted = client.post(
            f"/initiatives/{initiative_id}/status-updates/{update_id}/submit",
            headers=headers,
        )
        submitted.raise_for_status()
        assert submitted.json()["is_draft"] is False

        history = client.get(f"/initiatives/{initiative_id}/status-updates", headers=headers)
        history.raise_for_status()
        assert any(item["id"] == update_id for item in history.json()["items"])

        archived = client.post(f"/initiatives/{initiative_id}/archive", headers=headers)
        archived.raise_for_status()
        assert archived.json()["archived_at"]
    finally:
        if update_id and initiative_id:
            client.delete(
                f"/initiatives/{initiative_id}/status-updates/{update_id}",
                headers=headers,
            )
        if initiative_id:
            client.delete(f"/initiatives/{initiative_id}", headers=headers)
