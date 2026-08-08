"""Real API acceptance for dependency-aware financial metric deletion."""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest

from app.testing.credentials import fixture_credentials

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REAL_ACCEPTANCE") != "1",
    reason="real API acceptance requires a running API and RUN_REAL_ACCEPTANCE=1",
)

BASE_URL = os.environ.get("TRANSMUTER_API_BASE_URL", "http://localhost:8000")


def _auth_headers(client: httpx.Client) -> dict[str, str]:
    email, password = fixture_credentials()
    response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _metric_payload(key: str, label: str, *, formula: str | None = None) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "value_type": "currency" if formula is None else "percent",
        "direction": "increase_good",
        "aggregation": "sum" if formula is None else "formula",
        "is_benefit": formula is None,
        "benefit_class": "other" if formula is None else None,
        "formula": formula,
        "formula_inputs": [] if formula is None else [key.removesuffix("_ratio")],
        "precision": 4,
        "display_order": 9999,
        "applies_to": "opt_in",
        "validation": {},
        "is_system": True,
        "is_active": True,
    }


def test_real_metric_delete_reports_formula_dependency_then_deletes() -> None:
    suffix = uuid4().hex[:10]
    target_key = f"delete_acceptance_{suffix}"
    formula_key = f"{target_key}_ratio"
    created_ids: list[tuple[str, str]] = []

    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        headers = _auth_headers(client)
        try:
            target = client.post(
                "/admin/financial-engine/metrics",
                headers=headers,
                json=_metric_payload(target_key, "Deletion acceptance target"),
            )
            target.raise_for_status()
            target_data = target.json()
            assert target_data["is_system"] is False
            created_ids.append((target_data["id"], target_key))

            formula_payload = _metric_payload(
                formula_key,
                "Deletion acceptance formula",
                formula=target_key,
            )
            formula_payload["formula_inputs"] = [target_key]
            formula = client.post(
                "/admin/financial-engine/metrics",
                headers=headers,
                json=formula_payload,
            )
            formula.raise_for_status()
            formula_data = formula.json()
            created_ids.append((formula_data["id"], formula_key))

            impact = client.get(
                f"/admin/financial-engine/metrics/{target_data['id']}/deletion-impact",
                headers=headers,
            )
            impact.raise_for_status()
            assert impact.json()["can_delete"] is False
            assert impact.json()["blockers"]["formula_dependencies"]["count"] == 1

            blocked = client.request(
                "DELETE",
                f"/admin/financial-engine/metrics/{target_data['id']}",
                headers=headers,
                json={"confirmation_key": target_key},
            )
            assert blocked.status_code == 409
            assert blocked.json()["detail"]["impact"]["blocker_total"] == 1

            delete_formula = client.request(
                "DELETE",
                f"/admin/financial-engine/metrics/{formula_data['id']}",
                headers=headers,
                json={"confirmation_key": formula_key},
            )
            assert delete_formula.status_code == 204
            created_ids.remove((formula_data["id"], formula_key))

            refreshed = client.get(
                f"/admin/financial-engine/metrics/{target_data['id']}/deletion-impact",
                headers=headers,
            )
            refreshed.raise_for_status()
            assert refreshed.json()["can_delete"] is True

            delete_target = client.request(
                "DELETE",
                f"/admin/financial-engine/metrics/{target_data['id']}",
                headers=headers,
                json={"confirmation_key": target_key},
            )
            assert delete_target.status_code == 204
            created_ids.remove((target_data["id"], target_key))

            missing = client.get(
                f"/admin/financial-engine/metrics/{target_data['id']}/deletion-impact",
                headers=headers,
            )
            assert missing.status_code == 404
        finally:
            for metric_id, key in reversed(created_ids):
                client.request(
                    "DELETE",
                    f"/admin/financial-engine/metrics/{metric_id}",
                    headers=headers,
                    json={"confirmation_key": key},
                )
