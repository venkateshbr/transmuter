"""Tenant bootstrap shell defaults for blank organizations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from supabase import Client

from app.services.dashboard_config import DashboardConfigService

DEFAULT_ORG_SETTINGS: dict[str, Any] = {
    "nudge_overdue_days": 7,
    "nudge_nuclear_days": 14,
    "strategic_parameters": {
        "markets": [],
        "themes": [],
        "tags": [],
    },
}

STARTER_SCENARIOS = [
    ("baseline", "Baseline", "baseline", False, 0),
    ("plan_base", "Plan Base", "plan", True, 10),
    ("plan_high", "Plan High", "plan", False, 20),
    ("actual", "Actual", "actual", False, 30),
]

STARTER_METRICS = [
    (
        "annual_revenue_baseline",
        "Annual Revenue Baseline",
        "baseline",
        "currency",
        "neutral",
        "last",
        None,
        False,
        None,
        None,
        [],
        10,
    ),
    (
        "annual_gross_margin_baseline",
        "Annual Gross Margin Baseline",
        "baseline",
        "currency",
        "neutral",
        "last",
        None,
        False,
        None,
        None,
        [],
        20,
    ),
    (
        "revenue_uplift",
        "Revenue Uplift",
        "revenue",
        "currency",
        "increase_good",
        "sum",
        "benefit",
        True,
        "revenue",
        None,
        [],
        30,
    ),
    (
        "gm_uplift",
        "Gross Margin Uplift",
        "margin",
        "currency",
        "increase_good",
        "sum",
        "benefit",
        True,
        "margin",
        None,
        [],
        40,
    ),
    (
        "cost_savings",
        "Cost Savings",
        "savings",
        "currency",
        "increase_good",
        "sum",
        "benefit",
        True,
        "savings",
        None,
        [],
        50,
    ),
    (
        "target_revenue",
        "Target Revenue",
        "revenue",
        "currency",
        "increase_good",
        "formula",
        None,
        False,
        None,
        "baseline_annual_revenue_baseline + revenue_uplift",
        ["baseline_annual_revenue_baseline", "revenue_uplift"],
        60,
    ),
    (
        "target_gross_margin",
        "Target Gross Margin",
        "margin",
        "currency",
        "increase_good",
        "formula",
        None,
        False,
        None,
        "baseline_annual_gross_margin_baseline + gm_uplift",
        ["baseline_annual_gross_margin_baseline", "gm_uplift"],
        70,
    ),
    (
        "revenue_growth_pct",
        "Revenue Growth %",
        "revenue",
        "percent",
        "increase_good",
        "formula",
        None,
        False,
        None,
        "revenue_uplift / baseline_annual_revenue_baseline * 100",
        ["revenue_uplift", "baseline_annual_revenue_baseline"],
        80,
    ),
    (
        "gross_margin_run_rate_pct",
        "Gross Margin Run-rate %",
        "margin",
        "percent",
        "increase_good",
        "formula",
        None,
        False,
        None,
        "target_gross_margin / target_revenue * 100",
        ["target_gross_margin", "target_revenue"],
        90,
    ),
    (
        "gm_improvement_pct",
        "Gross Margin Improvement %",
        "margin",
        "percent",
        "increase_good",
        "formula",
        None,
        False,
        None,
        "gm_uplift / baseline_annual_gross_margin_baseline * 100",
        ["gm_uplift", "baseline_annual_gross_margin_baseline"],
        100,
    ),
]

STARTER_COST_CATEGORIES = [
    ("implementation", "Implementation / Project Cost", "implementation", "one_off_cost", 10),
    ("technology_tooling", "Technology / Tooling", "implementation", "one_off_cost", 20),
    ("external_consultants", "External Consultants", "implementation", "one_off_cost", 30),
    ("training_change", "Training / Change Management", "implementation", "one_off_cost", 40),
    ("software", "Software / Licenses", "operating", "recurring_cost", 50),
    ("maintenance", "Support / Maintenance", "operating", "recurring_cost", 60),
    ("labor", "People Support", "operating", "recurring_cost", 70),
    ("other", "Other", "uncategorized", None, 999),
]

STARTER_BRIDGE_ROWS = [
    ("revenue", "Revenue Uplift", "metric_set", ["revenue_uplift"], [], 1, 10),
    ("margin", "Gross Margin Uplift", "metric_set", ["gm_uplift"], [], 1, 20),
    ("savings", "Cost Savings", "metric_set", ["cost_savings"], [], 1, 30),
    (
        "recurring_costs",
        "Recurring Costs",
        "cost_set",
        [],
        ["software", "maintenance", "labor"],
        -1,
        40,
    ),
    ("net_run_rate_value", "Net Run-rate Value", "net", [], [], 1, 50),
    (
        "one_off_investment",
        "One-off Investment",
        "cost_set",
        [],
        ["implementation", "technology_tooling", "external_consultants", "training_change"],
        -1,
        60,
    ),
]


class TenantBootstrapService:
    """Create the minimal tenant shell without business-specific configuration."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def bootstrap_tenant(self, tenant_id: UUID | str) -> dict[str, int]:
        tid = str(tenant_id)
        return {
            "settings": self._bootstrap_settings(tid),
            **self._bootstrap_financial_engine(tid),
            "dashboards": DashboardConfigService(self._client, tid).ensure_defaults(),
            "gate_criteria": 0,
            "stage_gate_definitions": 0,
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

    def _merge_defaults(self, current: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        merged = {**current}
        for key, value in defaults.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                merged[key] = self._merge_defaults(merged[key], value)
        return merged

    def _bootstrap_financial_engine(self, tenant_id: str) -> dict[str, int]:
        counts = {
            "financial_scenarios": self._bootstrap_scenarios(tenant_id),
            "financial_metric_definitions": self._bootstrap_metrics(tenant_id),
            "financial_cost_categories": self._bootstrap_cost_categories(tenant_id),
            "financial_bridge_rows": self._bootstrap_bridge_rows(tenant_id),
        }
        return counts

    def _bootstrap_scenarios(self, tenant_id: str) -> int:
        existing = self._existing_keys("financial_scenarios", tenant_id)
        rows = []
        now = datetime.now(UTC).isoformat()
        for key, label, kind, is_primary, order in STARTER_SCENARIOS:
            if key in existing:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "key": key,
                    "label": label,
                    "kind": kind,
                    "is_primary": is_primary,
                    "is_system": True,
                    "is_active": True,
                    "display_order": order,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        if rows:
            self._client.table("financial_scenarios").insert(rows).execute()
        return len(rows)

    def _bootstrap_metrics(self, tenant_id: str) -> int:
        existing = self._existing_keys("financial_metric_definitions", tenant_id)
        rows = []
        now = datetime.now(UTC).isoformat()
        for (
            key,
            label,
            group_key,
            value_type,
            direction,
            aggregation,
            rollup_type,
            is_benefit,
            benefit_class,
            formula,
            formula_inputs,
            order,
        ) in STARTER_METRICS:
            if key in existing:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "key": key,
                    "label": label,
                    "group_key": group_key,
                    "value_type": value_type,
                    "direction": direction,
                    "aggregation": aggregation,
                    "rollup_type": rollup_type,
                    "is_benefit": is_benefit,
                    "benefit_class": benefit_class,
                    "formula": formula,
                    "formula_inputs": formula_inputs,
                    "precision": 4,
                    "display_order": order,
                    "applies_to": "all",
                    "validation": {},
                    "is_system": True,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        if rows:
            self._client.table("financial_metric_definitions").insert(rows).execute()
        return len(rows)

    def _bootstrap_cost_categories(self, tenant_id: str) -> int:
        existing = self._existing_keys("financial_cost_categories", tenant_id)
        rows = []
        now = datetime.now(UTC).isoformat()
        for key, label, group_key, rollup_type, order in STARTER_COST_CATEGORIES:
            if key in existing:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "key": key,
                    "label": label,
                    "group_key": group_key,
                    "rollup_type": rollup_type,
                    "display_order": order,
                    "attributes": {},
                    "is_system": True,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        if rows:
            self._client.table("financial_cost_categories").insert(rows).execute()
        return len(rows)

    def _bootstrap_bridge_rows(self, tenant_id: str) -> int:
        existing = self._existing_keys("financial_bridge_rows", tenant_id)
        metrics = self._id_by_key("financial_metric_definitions", tenant_id)
        categories = self._id_by_key("financial_cost_categories", tenant_id)
        rows = []
        now = datetime.now(UTC).isoformat()
        for key, label, row_kind, metric_keys, cost_keys, sign, order in STARTER_BRIDGE_ROWS:
            if key in existing:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "key": key,
                    "label": label,
                    "row_kind": row_kind,
                    "metric_definition_ids": [
                        metrics[item] for item in metric_keys if item in metrics
                    ],
                    "cost_category_ids": [
                        categories[item] for item in cost_keys if item in categories
                    ],
                    "cost_category_keys": cost_keys,
                    "sign": sign,
                    "display_order": order,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        if rows:
            self._client.table("financial_bridge_rows").insert(rows).execute()
        return len(rows)

    def _existing_keys(self, table: str, tenant_id: str) -> set[str]:
        result = self._client.table(table).select("key").eq("tenant_id", tenant_id).execute()
        return {str(row["key"]) for row in result.data or []}

    def _id_by_key(self, table: str, tenant_id: str) -> dict[str, str]:
        result = self._client.table(table).select("id,key").eq("tenant_id", tenant_id).execute()
        return {str(row["key"]): str(row["id"]) for row in result.data or []}
