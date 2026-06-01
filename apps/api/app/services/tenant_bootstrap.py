"""Tenant bootstrap defaults for blank organizations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml
from supabase import Client

DEFAULT_ORG_SETTINGS: dict[str, Any] = {
    "nudge_overdue_days": 7,
    "nudge_nuclear_days": 14,
    "strategic_parameters": {
        "markets": [],
        "themes": [],
        "tags": [],
    },
}

DEFAULT_FINANCIAL_GROUPS: list[dict[str, Any]] = [
    {
        "key": "revenue",
        "label": "Revenue",
        "kind": "metric",
        "rollup_type": None,
        "display_order": 10,
    },
    {
        "key": "gross_margin",
        "label": "Gross Margin",
        "kind": "metric",
        "rollup_type": None,
        "display_order": 20,
    },
    {
        "key": "savings",
        "label": "Savings",
        "kind": "metric",
        "rollup_type": None,
        "display_order": 40,
    },
    {
        "key": "benefits",
        "label": "Total Benefits",
        "kind": "calculation",
        "rollup_type": "benefit",
        "display_order": 50,
    },
    {
        "key": "implementation",
        "label": "One-off Costs",
        "kind": "cost_category",
        "rollup_type": "one_off_cost",
        "display_order": 10,
    },
    {
        "key": "operating",
        "label": "Recurring Costs",
        "kind": "cost_category",
        "rollup_type": "recurring_cost",
        "display_order": 20,
    },
    {
        "key": "uncategorized",
        "label": "Uncategorized",
        "kind": "cost_category",
        "rollup_type": None,
        "display_order": 90,
    },
    {
        "key": "one_off_costs",
        "label": "One-off Costs",
        "kind": "calculation",
        "rollup_type": "one_off_cost",
        "display_order": 55,
    },
    {
        "key": "net_value",
        "label": "Net Run-rate Impact",
        "kind": "calculation",
        "rollup_type": "net_value",
        "display_order": 60,
    },
    {
        "key": "payback_period",
        "label": "Payback Period",
        "kind": "calculation",
        "rollup_type": None,
        "display_order": 70,
    },
]

DEFAULT_FINANCIAL_ITEMS: list[dict[str, Any]] = [
    (
        "revenue",
        "revenue_uplift_base",
        "Revenue Uplift ($) (Base)",
        "metric",
        "revenue_uplift_base",
        "benefit",
        10,
    ),
    (
        "revenue",
        "revenue_uplift_high",
        "Revenue Uplift ($) (High)",
        "metric",
        "revenue_uplift_high",
        "benefit",
        20,
    ),
    (
        "revenue",
        "revenue_uplift_actual",
        "Revenue Uplift ($) (Actual)",
        "metric",
        "revenue_uplift_actual",
        "benefit",
        30,
    ),
    (
        "gross_margin",
        "gm_uplift_base",
        "Gross Margin Uplift ($) (Base)",
        "metric",
        "gm_uplift_base",
        "benefit",
        70,
    ),
    (
        "gross_margin",
        "gm_uplift_high",
        "Gross Margin Uplift ($) (High)",
        "metric",
        "gm_uplift_high",
        "benefit",
        80,
    ),
    (
        "gross_margin",
        "gm_uplift_actual",
        "Gross Margin Uplift ($) (Actual)",
        "metric",
        "gm_uplift_actual",
        "benefit",
        90,
    ),
    ("savings", "cost_savings", "Cost Savings ($)", "metric", None, "benefit", 10),
    (
        "implementation",
        "implementation",
        "Implementation / Project Cost",
        "cost_category",
        None,
        "one_off_cost",
        10,
    ),
    (
        "implementation",
        "technology_tooling",
        "Technology / Tooling",
        "cost_category",
        None,
        "one_off_cost",
        20,
    ),
    (
        "implementation",
        "external_consultants",
        "External Consultants",
        "cost_category",
        None,
        "one_off_cost",
        30,
    ),
    (
        "implementation",
        "training_change",
        "Training / Change Management",
        "cost_category",
        None,
        "one_off_cost",
        40,
    ),
    (
        "implementation",
        "other_one_off",
        "Other One-off Cost",
        "cost_category",
        None,
        "one_off_cost",
        90,
    ),
    (
        "operating",
        "software_subscriptions",
        "Software Subscriptions",
        "cost_category",
        None,
        "recurring_cost",
        10,
    ),
    (
        "operating",
        "support_maintenance",
        "Support / Maintenance",
        "cost_category",
        None,
        "recurring_cost",
        20,
    ),
    (
        "operating",
        "additional_headcount",
        "Additional Headcount",
        "cost_category",
        None,
        "recurring_cost",
        30,
    ),
    (
        "operating",
        "run_rate_operating",
        "Run-rate Operating Cost",
        "cost_category",
        None,
        "recurring_cost",
        40,
    ),
    ("operating", "maintenance", "Maintenance", "cost_category", None, "recurring_cost", 50),
    ("operating", "software", "Software / Licenses", "cost_category", None, "recurring_cost", 60),
    ("operating", "labor", "Labor / Operations", "cost_category", None, "recurring_cost", 70),
    ("uncategorized", "other", "Other", "cost_category", None, None, 99),
]


def _find_gates_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "domain_packs/transmuter/gates.yaml"
        if candidate.exists():
            return candidate
    return Path("/app/domain_packs/transmuter/gates.yaml")


class TenantBootstrapService:
    """Create system defaults for a new tenant without adding demo data."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def bootstrap_tenant(self, tenant_id: UUID | str) -> dict[str, int]:
        tid = str(tenant_id)
        return {
            "settings": self._bootstrap_settings(tid),
            "financial_groups": self._bootstrap_financial_groups(tid),
            "financial_items": self._bootstrap_financial_items(tid),
            "gate_criteria": self._bootstrap_gate_criteria(tid),
        }

    def _bootstrap_settings(self, tenant_id: str) -> int:
        row = (
            self._client.table("organizations")
            .select("id,settings")
            .eq("id", tenant_id)
            .maybe_single()
            .execute()
        )
        if not row or not row.data:
            return 0
        current = row.data.get("settings") or {}
        settings = self._merge_defaults(current, DEFAULT_ORG_SETTINGS)
        if settings == current:
            return 0
        self._client.table("organizations").update(
            {"settings": settings, "updated_at": datetime.now(UTC).isoformat()}
        ).eq("id", tenant_id).execute()
        return 1

    def _bootstrap_financial_groups(self, tenant_id: str) -> int:
        count = 0
        for index, group in enumerate(DEFAULT_FINANCIAL_GROUPS):
            payload = {
                "tenant_id": tenant_id,
                "key": group["key"],
                "label": group["label"],
                "kind": group["kind"],
                "rollup_type": group["rollup_type"],
                "display_order": group.get("display_order", index * 10),
                "is_system": True,
                "is_active": True,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            existing = (
                self._client.table("financial_config_groups")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("key", group["key"])
                .maybe_single()
                .execute()
            )
            if existing and existing.data:
                self._client.table("financial_config_groups").update(payload).eq(
                    "id", existing.data["id"]
                ).execute()
            else:
                self._client.table("financial_config_groups").insert(
                    {"id": str(uuid4()), **payload}
                ).execute()
                count += 1
        return count

    def _bootstrap_financial_items(self, tenant_id: str) -> int:
        groups = (
            self._client.table("financial_config_groups")
            .select("id,key")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        group_ids = {row["key"]: row["id"] for row in groups.data or []}
        count = 0
        for (
            group_key,
            key,
            label,
            item_type,
            system_metric_key,
            rollup_type,
            display_order,
        ) in DEFAULT_FINANCIAL_ITEMS:
            group_id = group_ids.get(group_key)
            if not group_id:
                continue
            payload = {
                "tenant_id": tenant_id,
                "group_id": group_id,
                "key": key,
                "label": label,
                "item_type": item_type,
                "system_metric_key": system_metric_key,
                "rollup_type": rollup_type,
                "display_order": display_order,
                "is_system": True,
                "is_active": True,
                "updated_at": datetime.now(UTC).isoformat(),
            }
            existing = (
                self._client.table("financial_config_items")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("key", key)
                .maybe_single()
                .execute()
            )
            if existing and existing.data:
                self._client.table("financial_config_items").update(payload).eq(
                    "id", existing.data["id"]
                ).execute()
            else:
                self._client.table("financial_config_items").insert(
                    {"id": str(uuid4()), **payload}
                ).execute()
                count += 1
        return count

    def _bootstrap_gate_criteria(self, tenant_id: str) -> int:
        with _find_gates_path().open() as handle:
            gates = yaml.safe_load(handle)["gates"]
        count = 0
        for gate_key, gate in gates.items():
            gate_number = int(str(gate_key).removeprefix("G"))
            for index, criterion in enumerate(gate.get("criteria", [])):
                if not criterion.get("default", True):
                    continue
                payload = {
                    "tenant_id": tenant_id,
                    "gate_number": gate_number,
                    "criterion_id": criterion["id"],
                    "label": criterion["label"],
                    "guidance": criterion.get("guidance"),
                    "sort_order": index,
                    "is_active": True,
                }
                existing = (
                    self._client.table("gate_criteria")
                    .select("id")
                    .eq("tenant_id", tenant_id)
                    .eq("gate_number", gate_number)
                    .eq("criterion_id", criterion["id"])
                    .maybe_single()
                    .execute()
                )
                if existing and existing.data:
                    self._client.table("gate_criteria").update(payload).eq(
                        "id", existing.data["id"]
                    ).execute()
                else:
                    self._client.table("gate_criteria").insert(
                        {"id": str(uuid4()), **payload}
                    ).execute()
                    count += 1
        return count

    def _merge_defaults(self, current: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        merged = {**current}
        for key, value in defaults.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                merged[key] = self._merge_defaults(merged[key], value)
        return merged
