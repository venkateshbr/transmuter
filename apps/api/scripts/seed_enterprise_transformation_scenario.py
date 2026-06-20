"""
Seed a deterministic non-Ishirock enterprise transformation scenario.

Usage:
    cd apps/api
    uv run python scripts/seed_enterprise_transformation_scenario.py
"""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from supabase import Client

load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")

from app.core.database import get_supabase_admin  # noqa: E402
from app.services.financial import FinancialService  # noqa: E402

ORG_NAME = "Acme Global Manufacturing"
ORG_SLUG = "acme-transformation-lab"
ADMIN_EMAIL = "admin@acme-transformation.dev"
ADMIN_PASSWORD = "Transmuter2026!"
BASELINE_YEAR = 2026

BASELINE_REVENUE = Decimal("20000000")
BASELINE_GROSS_MARGIN = Decimal("9000000")

MONEY = Decimal("0.0001")


def money(value: Decimal | int | str) -> str:
    return str(Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP))


def per_month(total: Decimal) -> Decimal:
    return (total / Decimal("12")).quantize(MONEY, rounding=ROUND_HALF_UP)


def now() -> str:
    return datetime.now(UTC).isoformat()


def find_auth_user_id_by_email(client: Client, email: str) -> str | None:
    page = 1
    per_page = 100
    while True:
        users = client.auth.admin.list_users(page=page, per_page=per_page)
        if not users:
            return None
        for user in users:
            if getattr(user, "email", None) == email:
                return str(user.id)
        if len(users) < per_page:
            return None
        page += 1


def ensure_org(client: Client) -> str:
    existing = client.table("organizations").select("id,settings").eq("slug", ORG_SLUG).execute()
    settings = {
        "nudge_overdue_days": 7,
        "nudge_nuclear_days": 14,
        "bankable_plan_governance": {
            "approval_required": True,
            "approved_plan_only": True,
            "baseline_lock_gate_number": 2,
            "baseline_lock_on_approval": True,
        },
        "financial_reporting": {"fiscal_year_start_month": 1, "reporting_currency": "USD"},
    }
    if existing.data:
        org_id = str(existing.data[0]["id"])
        client.table("organizations").update(
            {"name": ORG_NAME, "settings": settings, "updated_at": now()}
        ).eq("id", org_id).execute()
        return org_id
    org_id = str(uuid4())
    client.table("organizations").insert(
        {"id": org_id, "name": ORG_NAME, "slug": ORG_SLUG, "settings": settings}
    ).execute()
    return org_id


def ensure_admin_user(client: Client, tenant_id: str) -> str:
    auth_id = find_auth_user_id_by_email(client, ADMIN_EMAIL)
    metadata = {
        "tenant_id": tenant_id,
        "role": "transformation_office",
        "display_name": "Morgan Patel",
    }
    if auth_id:
        client.auth.admin.update_user_by_id(
            auth_id,
            {
                "password": ADMIN_PASSWORD,
                "email_confirm": True,
                "user_metadata": metadata,
            },
        )
    else:
        created = client.auth.admin.create_user(
            {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "email_confirm": True,
                "user_metadata": metadata,
            }
        )
        auth_id = str(created.user.id)
    client.table("users").upsert(
        {
            "id": auth_id,
            "tenant_id": tenant_id,
            "email": ADMIN_EMAIL,
            "display_name": "Morgan Patel",
            "title": "VP, Enterprise Transformation",
            "department": "Transformation Office",
            "timezone": "UTC",
            "role": "transformation_office",
            "status": "active",
            "onboarding_completed": True,
            "updated_at": now(),
        },
        on_conflict="id",
    ).execute()
    return auth_id


def delete_tenant_rows(client: Client, tenant_id: str) -> None:
    tables = [
        "financial_initiative_annual_baselines",
        "financial_tenant_annual_baselines",
        "financial_benefit_line_validation_events",
        "benefit_realization_ledger",
        "bankable_plans",
        "gate_submissions",
        "financial_metric_values",
        "initiative_financial_scope",
        "financial_benefit_lines",
        "financial_cost_lines",
        "financial_bridge_rows",
        "financial_attribute_definitions",
        "financial_cost_categories",
        "financial_metric_definitions",
        "financial_scenarios",
        "financial_config_items",
        "financial_config_groups",
        "initiative_business_units",
        "initiative_team",
        "status_updates",
        "kpi_entries",
        "kpis",
        "risks",
        "milestones",
        "initiatives",
        "gate_criteria",
        "stage_gate_definitions",
        "workstreams",
        "business_units",
    ]
    for table in tables:
        try:
            client.table(table).delete().eq("tenant_id", tenant_id).execute()
        except Exception as exc:
            if "does not exist" not in str(exc):
                raise


def insert_business_units(client: Client, tenant_id: str) -> dict[str, str]:
    rows = [
        ("CORP", "Corporate"),
        ("COM", "Commercial"),
        ("OPS", "Operations"),
        ("TECH", "Technology"),
        ("SHR", "Shared Services"),
    ]
    result: dict[str, str] = {}
    for code, name in rows:
        row_id = str(uuid4())
        client.table("business_units").insert(
            {"id": row_id, "tenant_id": tenant_id, "code": code, "name": name}
        ).execute()
        result[code] = row_id
    return result


def insert_workstreams(client: Client, tenant_id: str, bus: dict[str, str]) -> dict[str, str]:
    rows = [
        ("Automation", bus["TECH"]),
        ("Offshoring & Operating Model", bus["SHR"]),
        ("Commercial Growth", bus["COM"]),
        ("ERP & Data Platform", bus["TECH"]),
        ("Procurement & Supply Chain", bus["OPS"]),
    ]
    result: dict[str, str] = {}
    for name, _bu_id in rows:
        row_id = str(uuid4())
        client.table("workstreams").insert(
            {
                "id": row_id,
                "tenant_id": tenant_id,
                "name": name,
            }
        ).execute()
        result[name] = row_id
    return result


def insert_stage_gates(client: Client, tenant_id: str) -> None:
    rows = [
        (1, "g1_identify_validate", "Gate 1: Identify to Validate", "identified", "validated"),
        (2, "g2_validate_plan", "Gate 2: Validate to Plan", "validated", "planned"),
        (3, "g3_plan_commit", "Gate 3: Plan to Commit", "planned", "committed"),
        (4, "g4_commit_execute", "Gate 4: Commit to Execute", "committed", "executing"),
        (5, "g5_execute_realize", "Gate 5: Execute to Realized", "executing", "realized"),
    ]
    client.table("stage_gate_definitions").insert(
        [
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "gate_number": gate,
                "key": key,
                "label": label,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "description": f"{label} control point for bankable transformation value.",
                "sort_order": gate * 10,
                "is_system": True,
                "approval_required": True,
                "approver_roles": ["transformation_office"],
                "require_all_criteria": True,
            }
            for gate, key, label, from_stage, to_stage in rows
        ]
    ).execute()


def insert_gate_criteria(client: Client, tenant_id: str) -> list[dict[str, str | int]]:
    rows: list[tuple[int, str, str, str]] = [
        (
            1,
            "g1-strategic-fit",
            "Strategic fit confirmed",
            "Initiative supports the enterprise transformation thesis and target operating model.",
        ),
        (
            1,
            "g1-value-hypothesis",
            "Value hypothesis documented",
            "Initial benefit type, value driver, and owner are documented.",
        ),
        (
            2,
            "g2-baseline-approved",
            "Baseline approved",
            "FY26 baseline allocation and measurement method are agreed.",
        ),
        (
            2,
            "g2-assumptions-documented",
            "Benefit assumptions documented",
            "Revenue, margin, savings, cost, and timing assumptions are captured.",
        ),
        (
            2,
            "g2-finance-validation",
            "Finance validation completed",
            "Finance has validated the benefit logic before bankable plan lock.",
        ),
        (
            3,
            "g3-delivery-plan",
            "Delivery plan approved",
            "Milestones, dependencies, budget, and owner accountability are approved.",
        ),
        (
            3,
            "g3-owner-sponsor",
            "Owner and sponsor assigned",
            "Business owner, sponsor, and transformation office owner are assigned.",
        ),
        (
            4,
            "g4-implementation-evidence",
            "Implementation evidence submitted",
            "Execution evidence confirms the initiative is live or materially complete.",
        ),
        (
            4,
            "g4-actuals-started",
            "Actuals collection started",
            "Benefit realization actuals are being captured in the ledger.",
        ),
        (
            5,
            "g5-benefits-accepted",
            "Benefits realized and accepted",
            "Realized value is accepted by the transformation office and business owner.",
        ),
    ]
    payload = [
        {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "gate_number": gate_number,
            "criterion_id": criterion_id,
            "label": label,
            "guidance": guidance,
            "sort_order": index * 10,
            "is_active": True,
        }
        for index, (gate_number, criterion_id, label, guidance) in enumerate(rows, start=1)
    ]
    client.table("gate_criteria").insert(payload).execute()
    return payload


def insert_financial_config(client: Client, tenant_id: str) -> None:
    groups = [
        ("benefits", "Total Benefits", "calculation", "benefit", 10),
        ("recurring_costs", "Recurring Costs", "calculation", "recurring_cost", 20),
        ("one_off_costs", "One-off Costs", "calculation", "one_off_cost", 30),
        ("net_value", "Net Run-rate Impact", "calculation", "net_value", 40),
        ("revenue", "Revenue", "metric", None, 50),
        ("margin", "Gross Margin", "metric", None, 60),
        ("savings", "Savings", "metric", None, 70),
        ("implementation", "One-off Costs", "cost_category", None, 80),
        ("operating", "Recurring Costs", "cost_category", None, 90),
    ]
    group_ids: dict[str, str] = {}
    for key, label, kind, rollup_type, order in groups:
        group_id = str(uuid4())
        client.table("financial_config_groups").insert(
            {
                "id": group_id,
                "tenant_id": tenant_id,
                "key": key,
                "label": label,
                "kind": kind,
                "rollup_type": rollup_type,
                "display_order": order,
                "is_system": True,
                "is_active": True,
            }
        ).execute()
        group_ids[key] = group_id
    items = [
        ("revenue", "revenue_uplift", "Revenue Uplift", "metric", "benefit", 10),
        ("margin", "gm_uplift", "Gross Margin Uplift", "metric", "benefit", 20),
        ("savings", "cost_savings", "Cost Savings", "metric", "benefit", 30),
        (
            "implementation",
            "implementation",
            "Implementation / Project Cost",
            "cost_category",
            "one_off_cost",
            40,
        ),
        (
            "implementation",
            "technology_tooling",
            "Technology / Tooling",
            "cost_category",
            "one_off_cost",
            50,
        ),
        (
            "implementation",
            "external_consultants",
            "External Consultants",
            "cost_category",
            "one_off_cost",
            60,
        ),
        (
            "implementation",
            "training_change",
            "Training / Change Management",
            "cost_category",
            "one_off_cost",
            70,
        ),
        ("operating", "software", "Software / Licenses", "cost_category", "recurring_cost", 80),
        (
            "operating",
            "maintenance",
            "Support / Maintenance",
            "cost_category",
            "recurring_cost",
            90,
        ),
        ("operating", "labor", "People Support", "cost_category", "recurring_cost", 100),
    ]
    client.table("financial_config_items").insert(
        [
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "group_id": group_ids[group_key],
                "key": key,
                "label": label,
                "item_type": item_type,
                "system_metric_key": key if item_type == "metric" else None,
                "rollup_type": rollup_type,
                "display_order": order,
                "is_system": True,
                "is_active": True,
            }
            for group_key, key, label, item_type, rollup_type, order in items
        ]
    ).execute()


def insert_engine_config(
    client: Client, tenant_id: str, user_id: str
) -> tuple[dict[str, str], dict[str, str]]:
    scenarios = [
        ("baseline", "Baseline", "baseline", False, 0),
        ("plan_base", "Plan Base", "plan", True, 10),
        ("plan_high", "Plan High", "plan", False, 20),
        ("actual", "Actual", "actual", False, 30),
    ]
    scenario_ids: dict[str, str] = {}
    for key, label, kind, primary, order in scenarios:
        row_id = str(uuid4())
        client.table("financial_scenarios").insert(
            {
                "id": row_id,
                "tenant_id": tenant_id,
                "key": key,
                "label": label,
                "kind": kind,
                "is_primary": primary,
                "is_system": True,
                "is_active": True,
                "display_order": order,
            }
        ).execute()
        scenario_ids[key] = row_id

    metrics = [
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
            "all",
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
            "all",
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
            "all",
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
            "all",
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
            "all",
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
            "all",
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
            "all",
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
            "all",
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
            "all",
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
            "all",
        ),
    ]
    metric_ids: dict[str, str] = {}
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
        inputs,
        order,
        applies_to,
    ) in metrics:
        row_id = str(uuid4())
        client.table("financial_metric_definitions").insert(
            {
                "id": row_id,
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
                "formula_inputs": inputs,
                "precision": 4,
                "display_order": order,
                "applies_to": applies_to,
                "validation": {},
                "is_system": key in {"revenue_uplift", "gm_uplift", "cost_savings"},
                "is_active": True,
                "created_by": user_id,
                "updated_by": user_id,
            }
        ).execute()
        metric_ids[key] = row_id

    cost_categories = [
        ("implementation", "Implementation / Project Cost", "implementation", "one_off_cost", 10),
        ("technology_tooling", "Technology / Tooling", "implementation", "one_off_cost", 20),
        ("external_consultants", "External Consultants", "implementation", "one_off_cost", 30),
        ("training_change", "Training / Change Management", "implementation", "one_off_cost", 40),
        ("software", "Software / Licenses", "operating", "recurring_cost", 50),
        ("maintenance", "Support / Maintenance", "operating", "recurring_cost", 60),
        ("labor", "People Support", "operating", "recurring_cost", 70),
        ("other", "Other", "uncategorized", None, 999),
    ]
    cost_category_ids: dict[str, str] = {}
    for key, label, group_key, rollup_type, order in cost_categories:
        row_id = str(uuid4())
        client.table("financial_cost_categories").insert(
            {
                "id": row_id,
                "tenant_id": tenant_id,
                "key": key,
                "label": label,
                "group_key": group_key,
                "rollup_type": rollup_type,
                "display_order": order,
                "attributes": {},
                "is_system": True,
                "is_active": True,
            }
        ).execute()
        cost_category_ids[key] = row_id

    bridge_rows = [
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
        (
            "one_off_costs",
            "One-off Costs",
            "cost_set",
            [],
            ["implementation", "technology_tooling", "external_consultants", "training_change"],
            -1,
            50,
        ),
        ("net_value", "Net Value", "net", [], [], 1, 60),
    ]
    client.table("financial_bridge_rows").insert(
        [
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "key": key,
                "label": label,
                "row_kind": row_kind,
                "metric_definition_ids": [metric_ids[m] for m in metric_keys],
                "cost_category_ids": [cost_category_ids[c] for c in cost_keys],
                "cost_category_keys": cost_keys,
                "sign": sign,
                "display_order": order,
                "is_active": True,
            }
            for key, label, row_kind, metric_keys, cost_keys, sign, order in bridge_rows
        ]
    ).execute()
    return metric_ids, scenario_ids


def insert_tenant_baselines(
    client: Client, tenant_id: str, metric_ids: dict[str, str], user_id: str
) -> None:
    client.table("financial_tenant_annual_baselines").insert(
        [
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "metric_definition_id": metric_ids["annual_revenue_baseline"],
                "baseline_year": BASELINE_YEAR,
                "value": money(BASELINE_REVENUE),
                "note": "FY26 revenue baseline for the enterprise transformation.",
                "created_by": user_id,
                "updated_by": user_id,
            },
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "metric_definition_id": metric_ids["annual_gross_margin_baseline"],
                "baseline_year": BASELINE_YEAR,
                "value": money(BASELINE_GROSS_MARGIN),
                "note": "FY26 gross margin baseline at 45%.",
                "created_by": user_id,
                "updated_by": user_id,
            },
        ]
    ).execute()


INITIATIVES = [
    (
        "ENT-001",
        "Transformation PMO & Benefits Office",
        "Corporate",
        "Automation",
        "other",
        "capability_building",
        Decimal("500000"),
        Decimal("225000"),
        Decimal("0"),
        Decimal("0"),
        Decimal("50000"),
        Decimal("100000"),
        Decimal("0"),
        Decimal("0"),
        Decimal("250000"),
        Decimal("125000"),
    ),
    (
        "ENT-002",
        "Finance Process Automation",
        "Shared Services",
        "Automation",
        "automation",
        "cost_reduction",
        Decimal("1600000"),
        Decimal("720000"),
        Decimal("0"),
        Decimal("0"),
        Decimal("225000"),
        Decimal("450000"),
        Decimal("300000"),
        Decimal("650000"),
        Decimal("300000"),
        Decimal("75000"),
    ),
    (
        "ENT-003",
        "Customer Onboarding Automation",
        "Commercial",
        "Automation",
        "automation",
        "revenue_growth",
        Decimal("2200000"),
        Decimal("990000"),
        Decimal("400000"),
        Decimal("700000"),
        Decimal("260000"),
        Decimal("500000"),
        Decimal("100000"),
        Decimal("150000"),
        Decimal("280000"),
        Decimal("55000"),
    ),
    (
        "ENT-004",
        "Back-office Finance & HR Offshoring",
        "Shared Services",
        "Offshoring & Operating Model",
        "offshoring",
        "cost_reduction",
        Decimal("2000000"),
        Decimal("900000"),
        Decimal("0"),
        Decimal("0"),
        Decimal("400000"),
        Decimal("800000"),
        Decimal("550000"),
        Decimal("1000000"),
        Decimal("220000"),
        Decimal("100000"),
    ),
    (
        "ENT-005",
        "Enterprise Data Platform",
        "Technology",
        "ERP & Data Platform",
        "automation",
        "capability_building",
        Decimal("1200000"),
        Decimal("540000"),
        Decimal("200000"),
        Decimal("450000"),
        Decimal("180000"),
        Decimal("400000"),
        Decimal("100000"),
        Decimal("200000"),
        Decimal("500000"),
        Decimal("150000"),
    ),
    (
        "ENT-006",
        "Pricing & Discount Optimization",
        "Commercial",
        "Commercial Growth",
        "commercial",
        "revenue_growth",
        Decimal("3000000"),
        Decimal("1350000"),
        Decimal("700000"),
        Decimal("1100000"),
        Decimal("520000"),
        Decimal("1050000"),
        Decimal("0"),
        Decimal("0"),
        Decimal("250000"),
        Decimal("50000"),
    ),
    (
        "ENT-007",
        "Sales Coverage Expansion",
        "Commercial",
        "Commercial Growth",
        "commercial",
        "revenue_growth",
        Decimal("3400000"),
        Decimal("1530000"),
        Decimal("500000"),
        Decimal("950000"),
        Decimal("300000"),
        Decimal("650000"),
        Decimal("0"),
        Decimal("0"),
        Decimal("200000"),
        Decimal("70000"),
    ),
    (
        "ENT-008",
        "Procurement Vendor Consolidation",
        "Operations",
        "Procurement & Supply Chain",
        "offshoring",
        "cost_reduction",
        Decimal("2300000"),
        Decimal("1035000"),
        Decimal("0"),
        Decimal("0"),
        Decimal("280000"),
        Decimal("550000"),
        Decimal("450000"),
        Decimal("800000"),
        Decimal("200000"),
        Decimal("40000"),
    ),
    (
        "ENT-009",
        "Supply Chain Control Tower",
        "Operations",
        "Procurement & Supply Chain",
        "automation",
        "cost_avoidance",
        Decimal("2400000"),
        Decimal("1080000"),
        Decimal("100000"),
        Decimal("300000"),
        Decimal("200000"),
        Decimal("450000"),
        Decimal("250000"),
        Decimal("450000"),
        Decimal("180000"),
        Decimal("65000"),
    ),
    (
        "ENT-010",
        "AI Service Desk Automation",
        "Technology",
        "Automation",
        "automation",
        "cost_reduction",
        Decimal("1400000"),
        Decimal("630000"),
        Decimal("100000"),
        Decimal("500000"),
        Decimal("205000"),
        Decimal("450000"),
        Decimal("250000"),
        Decimal("500000"),
        Decimal("120000"),
        Decimal("70000"),
    ),
]


def insert_initiatives(
    client: Client,
    tenant_id: str,
    user_id: str,
    business_units: dict[str, str],
    workstreams: dict[str, str],
    metric_ids: dict[str, str],
    scenario_ids: dict[str, str],
) -> dict[str, str]:
    bu_by_name = {
        "Corporate": business_units["CORP"],
        "Commercial": business_units["COM"],
        "Operations": business_units["OPS"],
        "Technology": business_units["TECH"],
        "Shared Services": business_units["SHR"],
    }
    initiative_ids: dict[str, str] = {}
    benefit_line_rows = []
    benefit_line_validation_event_rows = []
    metric_value_rows = []
    cost_rows = []
    baseline_rows = []
    for index, row in enumerate(INITIATIVES, start=1):
        (
            code,
            name,
            bu_name,
            ws_name,
            tag,
            initiative_type,
            init_baseline_revenue,
            init_baseline_gm,
            rev_2027,
            rev_2028,
            gm_2027,
            gm_2028,
            savings_2027,
            savings_2028,
            one_time,
            recurring_2028,
        ) = row
        initiative_id = str(uuid4())
        initiative_ids[code] = initiative_id
        benefit_line_ids: dict[str, str] = {}
        for metric_key, label, description, benefit_class in [
            (
                "revenue_uplift",
                f"{code} revenue uplift",
                "Incremental revenue created by the initiative.",
                "revenue",
            ),
            (
                "gm_uplift",
                f"{code} gross margin uplift",
                "Gross margin improvement created by the initiative.",
                "margin",
            ),
            (
                "cost_savings",
                f"{code} cost savings",
                "Run-rate savings created by the initiative.",
                "savings",
            ),
        ]:
            benefit_line_id = str(uuid4())
            benefit_line_ids[metric_key] = benefit_line_id
            validation_status = "finance_validated"
            validation_comment = (
                "Finance validated against ACME benefit model and source assumptions."
            )
            rejection_reason = None
            if index in {5, 8} and metric_key == "revenue_uplift":
                validation_status = "submitted"
                validation_comment = "Submitted for Finance review with commercial owner evidence."
            elif index == 9 and metric_key == "cost_savings":
                validation_status = "rejected"
                validation_comment = "Rejected pending updated vendor baseline evidence."
                rejection_reason = validation_comment
            elif index == 10 and metric_key == "revenue_uplift":
                validation_status = "draft"
                validation_comment = None
            risk_adjustment = "90.00"
            risk_rating = "medium"
            if benefit_class == "revenue":
                risk_adjustment = "80.00"
                risk_rating = "high" if index in {5, 8, 10} else "medium"
            elif benefit_class == "savings":
                risk_adjustment = "95.00"
                risk_rating = "low" if index not in {9} else "high"
            benefit_line_rows.append(
                {
                    "id": benefit_line_id,
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "metric_definition_id": metric_ids[metric_key],
                    "name": label,
                    "description": description,
                    "impact_type": "recurring",
                    "timing": "FY27-FY28 ramp to run-rate",
                    "confidence": "85.00" if benefit_class != "revenue" else "80.00",
                    "phasing": {"method": "monthly_even", "source": "acme_seed"},
                    "attributes": {
                        "benefit_class": benefit_class,
                        "evidence": "Seeded board-demo assumption pack",
                    },
                    "validation_status": validation_status,
                    "submitted_at": now(),
                    "submitted_by": user_id,
                    "validated_at": now()
                    if validation_status in {"finance_validated", "rejected"}
                    else None,
                    "validated_by": user_id
                    if validation_status in {"finance_validated", "rejected"}
                    else None,
                    "validation_comment": validation_comment,
                    "evidence_url": f"https://example.com/acme/{code.lower()}-{metric_key}-evidence",
                    "evidence_label": "ACME assumption pack",
                    "rejection_reason": rejection_reason,
                    "realization_owner_id": user_id,
                    "handoff_status": "handoff_complete"
                    if validation_status == "finance_validated"
                    else "owner_assigned",
                    "handoff_due_date": "2028-03-31",
                    "risk_rating": risk_rating,
                    "risk_adjustment_pct": risk_adjustment,
                    "show_in_summary": True,
                    "display_order": len(benefit_line_rows) + 10,
                    "created_by": user_id,
                    "updated_by": user_id,
                    "created_at": now(),
                    "updated_at": now(),
                }
            )
            benefit_line_validation_event_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "benefit_line_id": benefit_line_id,
                    "event_type": "submit",
                    "actor_user_id": user_id,
                    "comment": "Submitted seeded benefit line for Finance validation.",
                    "evidence_url": f"https://example.com/acme/{code.lower()}-{metric_key}-evidence",
                    "evidence_label": "ACME assumption pack",
                    "metadata": {"source": "acme_seed"},
                    "created_at": now(),
                }
            )
            if validation_status in {"finance_validated", "rejected"}:
                benefit_line_validation_event_rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "initiative_id": initiative_id,
                        "benefit_line_id": benefit_line_id,
                        "event_type": "validate"
                        if validation_status == "finance_validated"
                        else "reject",
                        "actor_user_id": user_id,
                        "comment": validation_comment,
                        "evidence_url": f"https://example.com/acme/{code.lower()}-{metric_key}-evidence",
                        "evidence_label": "ACME assumption pack",
                        "metadata": {"source": "acme_seed"},
                        "created_at": now(),
                    }
                )
        client.table("initiatives").insert(
            {
                "id": initiative_id,
                "tenant_id": tenant_id,
                "initiative_code": code,
                "name": name,
                "workstream_id": workstreams[ws_name],
                "owner_id": user_id,
                "group_owner_id": user_id,
                "type": initiative_type,
                "impact_type": "recurring",
                "theme": "Enterprise gross margin and growth transformation",
                "country": "United States",
                "tag": tag,
                "priority": "high" if index in {4, 6, 7} else "medium",
                "rag_status": "amber" if index in {5, 9} else "green",
                "stage": "executing",
                "summary": (
                    "Two-year enterprise initiative contributing to FY28 revenue growth, "
                    "gross margin expansion, and bankable run-rate value."
                ),
                "value_logic": "Measured against FY26 annual baseline metrics with plan-only bankable value.",
                "dependencies_text": "Dependent on enterprise data readiness, BU sponsorship, and change adoption.",
                "planned_start": "2027-01-01",
                "planned_end": "2028-12-31",
                "created_at": now(),
                "updated_at": now(),
            }
        ).execute()
        client.table("initiative_business_units").insert(
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "initiative_id": initiative_id,
                "business_unit_id": bu_by_name[bu_name],
            }
        ).execute()
        baseline_rows.extend(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "metric_definition_id": metric_ids["annual_revenue_baseline"],
                    "baseline_year": BASELINE_YEAR,
                    "value": money(init_baseline_revenue),
                    "note": "Allocated FY26 revenue baseline for initiative measurement.",
                    "created_by": user_id,
                    "updated_by": user_id,
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "metric_definition_id": metric_ids["annual_gross_margin_baseline"],
                    "baseline_year": BASELINE_YEAR,
                    "value": money(init_baseline_gm),
                    "note": "Allocated FY26 gross margin baseline for initiative measurement.",
                    "created_by": user_id,
                    "updated_by": user_id,
                },
            ]
        )

        annual_values = {
            2026: {
                "baseline": {
                    "annual_revenue_baseline": init_baseline_revenue,
                    "annual_gross_margin_baseline": init_baseline_gm,
                }
            },
            2027: {
                "plan_base": {
                    "revenue_uplift": rev_2027,
                    "gm_uplift": gm_2027,
                    "cost_savings": savings_2027,
                },
                "plan_high": {
                    "revenue_uplift": rev_2027 * Decimal("1.15"),
                    "gm_uplift": gm_2027 * Decimal("1.12"),
                    "cost_savings": savings_2027 * Decimal("1.10"),
                },
                "actual": {
                    "revenue_uplift": rev_2027 * Decimal("0.88"),
                    "gm_uplift": gm_2027 * Decimal("0.86"),
                    "cost_savings": savings_2027 * Decimal("0.82"),
                },
            },
            2028: {
                "plan_base": {
                    "revenue_uplift": rev_2028,
                    "gm_uplift": gm_2028,
                    "cost_savings": savings_2028,
                },
                "plan_high": {
                    "revenue_uplift": rev_2028 * Decimal("1.12"),
                    "gm_uplift": gm_2028 * Decimal("1.10"),
                    "cost_savings": savings_2028 * Decimal("1.08"),
                },
                "actual": {
                    "revenue_uplift": rev_2028 * Decimal("0.92"),
                    "gm_uplift": gm_2028 * Decimal("0.90"),
                    "cost_savings": savings_2028 * Decimal("0.88"),
                },
            },
        }
        for year, scenarios in annual_values.items():
            for scenario_key, metrics in scenarios.items():
                for metric_key, annual_value in metrics.items():
                    monthly = per_month(annual_value)
                    for month in range(1, 13):
                        metric_value_rows.append(
                            {
                                "id": str(uuid4()),
                                "tenant_id": tenant_id,
                                "initiative_id": initiative_id,
                                "metric_definition_id": metric_ids[metric_key],
                                "benefit_line_id": benefit_line_ids.get(metric_key),
                                "scenario_id": scenario_ids[scenario_key],
                                "year": year,
                                "month": month,
                                "value": money(monthly),
                                "status": "approved",
                                "note": f"Seeded {scenario_key} {metric_key} for steering committee scenario.",
                                "created_by": user_id,
                                "updated_by": user_id,
                            }
                        )
        one_time_categories = [
            ("implementation", one_time * Decimal("0.45")),
            ("technology_tooling", one_time * Decimal("0.35")),
            ("training_change", one_time * Decimal("0.20")),
        ]
        for category, amount in one_time_categories:
            cost_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": f"{category.replace('_', ' ').title()} setup",
                    "year": 2027,
                    "quarter": None,
                    "amount_plan": money(amount),
                    "amount_actual": money(amount * Decimal("0.95")),
                    "is_recurring": False,
                    "category_key": category,
                    "created_by": user_id,
                    "updated_by": user_id,
                    "created_at": now(),
                    "updated_at": now(),
                }
            )
        recurring_categories = [
            ("software", recurring_2028 * Decimal("0.40")),
            ("maintenance", recurring_2028 * Decimal("0.35")),
            ("labor", recurring_2028 * Decimal("0.25")),
        ]
        for year, factor in [(2027, Decimal("0.50")), (2028, Decimal("1.00"))]:
            for category, annual_amount in recurring_categories:
                cost_rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "initiative_id": initiative_id,
                        "name": f"{category.title()} run support",
                        "year": year,
                        "quarter": None,
                        "amount_plan": money(annual_amount * factor),
                        "amount_actual": money(annual_amount * factor * Decimal("0.97")),
                        "is_recurring": True,
                        "category_key": category,
                        "created_by": user_id,
                        "updated_by": user_id,
                        "created_at": now(),
                        "updated_at": now(),
                    }
                )
        client.table("milestones").insert(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": "Gate 2 baseline and business case confirmed",
                    "description": "Baseline metrics and bankable plan agreed with Finance.",
                    "owner_id": user_id,
                    "priority": "high",
                    "sort_order": 10,
                    "planned_start": "2027-01-01",
                    "planned_end": "2027-03-31",
                    "actual_end": "2027-03-28",
                    "status": "complete",
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": "FY28 run-rate benefits activated",
                    "description": "Run-rate value embedded into operating plan.",
                    "owner_id": user_id,
                    "priority": "high",
                    "sort_order": 20,
                    "planned_start": "2028-01-01",
                    "planned_end": "2028-12-15",
                    "status": "in_progress",
                },
            ]
        ).execute()
    client.table("financial_initiative_annual_baselines").insert(baseline_rows).execute()
    client.table("financial_benefit_lines").insert(benefit_line_rows).execute()
    client.table("financial_benefit_line_validation_events").insert(
        benefit_line_validation_event_rows
    ).execute()
    for start in range(0, len(metric_value_rows), 500):
        client.table("financial_metric_values").insert(
            metric_value_rows[start : start + 500]
        ).execute()
    client.table("financial_cost_lines").insert(cost_rows).execute()
    return initiative_ids


def insert_bankable_plan_and_realization_demo(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    gate_criteria: list[dict[str, str | int]],
) -> None:
    service = FinancialService(client, tenant_id)  # type: ignore[arg-type]
    criteria_snapshot = [
        {
            "criterion_id": row["criterion_id"],
            "label": row["label"],
            "ticked": True,
            "ticked_by": user_id,
            "ticked_at": now(),
        }
        for row in gate_criteria
        if row["gate_number"] == 2
    ]
    submission_rows = []
    submission_ids: dict[str, str] = {}
    for code, initiative_id in initiative_ids.items():
        submission_id = str(uuid4())
        submission_ids[code] = submission_id
        submission_rows.append(
            {
                "id": submission_id,
                "tenant_id": tenant_id,
                "initiative_id": initiative_id,
                "gate_number": 2,
                "submitted_by_id": user_id,
                "submitted_at": now(),
                "decision": "approved",
                "decided_by_id": user_id,
                "decided_at": now(),
                "commentary": "Seeded ACME Gate 2 approval for bankable plan lock.",
                "criteria_snapshot": criteria_snapshot,
            }
        )
    client.table("gate_submissions").insert(submission_rows).execute()

    for code, initiative_id in initiative_ids.items():
        service.lock_bankable_plan_from_approval(
            initiative_id,
            submission_ids[code],
            user_id,
            locked_reason="Seeded Gate 2 approval for ACME board-demo bankable plan.",
        )
    service.rebaseline_bankable_plan(
        initiative_ids["ENT-005"],
        user_id,
        reason=(
            "Seeded rebaseline example for Enterprise Data Platform after delivery "
            "timing and tooling assumptions were refreshed."
        ),
    )

    rows = []
    initiative_seed_by_code = {row[0]: row for row in INITIATIVES}
    for code, initiative_id in initiative_ids.items():
        seed = initiative_seed_by_code[code]
        gm_2027 = seed[10]
        gm_2028 = seed[11]
        savings_2027 = seed[12]
        savings_2028 = seed[13]
        yearly = {
            2027: {
                "plan": gm_2027 + savings_2027,
                "actual": (gm_2027 * Decimal("0.86")) + (savings_2027 * Decimal("0.82")),
            },
            2028: {
                "plan": gm_2028 + savings_2028,
                "actual": (gm_2028 * Decimal("0.90")) + (savings_2028 * Decimal("0.88")),
            },
        }
        for year, amounts in yearly.items():
            plan_monthly = per_month(amounts["plan"])
            actual_monthly = per_month(amounts["actual"])
            for month in range(1, 13):
                last_day = monthrange(year, month)[1]
                rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "initiative_id": initiative_id,
                        "period_granularity": "monthly",
                        "period_start": f"{year}-{month:02d}-01",
                        "period_end": f"{year}-{month:02d}-{last_day:02d}",
                        "bankable_plan_amount": money(plan_monthly),
                        "actual_amount": money(actual_monthly),
                        "description": (
                            f"Seeded ACME {year} monthly realization for {code}; "
                            "actuals mirror financial-engine actual scenario."
                        ),
                    }
                )
    for start in range(0, len(rows), 500):
        client.table("benefit_realization_ledger").insert(rows[start : start + 500]).execute()


def main() -> None:
    client = get_supabase_admin()
    tenant_id = ensure_org(client)
    user_id = ensure_admin_user(client, tenant_id)
    delete_tenant_rows(client, tenant_id)
    business_units = insert_business_units(client, tenant_id)
    workstreams = insert_workstreams(client, tenant_id, business_units)
    insert_stage_gates(client, tenant_id)
    gate_criteria = insert_gate_criteria(client, tenant_id)
    insert_financial_config(client, tenant_id)
    metric_ids, scenario_ids = insert_engine_config(client, tenant_id, user_id)
    insert_tenant_baselines(client, tenant_id, metric_ids, user_id)
    initiative_ids = insert_initiatives(
        client,
        tenant_id,
        user_id,
        business_units,
        workstreams,
        metric_ids,
        scenario_ids,
    )
    insert_bankable_plan_and_realization_demo(
        client,
        tenant_id,
        user_id,
        initiative_ids,
        gate_criteria,
    )
    print("Seeded enterprise transformation scenario")
    print(f"  tenant_id: {tenant_id}")
    print(f"  login: {ADMIN_EMAIL}")
    print(f"  initiatives: {len(initiative_ids)}")
    print("  gate criteria: seeded")
    print("  bankable plans: seeded")
    print("  benefit ledger: seeded")
    print(f"  FY26 revenue baseline: {money(BASELINE_REVENUE)}")
    print(f"  FY26 gross margin baseline: {money(BASELINE_GROSS_MARGIN)}")
    print("  FY28 plan target revenue uplift: 4000000.0000")
    print("  FY28 plan target gross margin uplift: 5400000.0000")


if __name__ == "__main__":
    main()
