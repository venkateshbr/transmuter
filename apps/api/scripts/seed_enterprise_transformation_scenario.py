"""
Seed a deterministic non-Ishirock enterprise transformation scenario.

Usage:
    cd apps/api
    TRANSMUTER_SEED_ENVIRONMENT=dev \
    TRANSMUTER_SEED_CONFIRMATION=seed-enterprise-transformation-dev \
    TRANSMUTER_SEED_ADMIN_PASSWORD=... \
      uv run python scripts/seed_enterprise_transformation_scenario.py
"""

from __future__ import annotations

import os
from calendar import monthrange
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from supabase import Client

load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")

from app.core.auth_metadata import build_auth_metadata_payload  # noqa: E402
from app.core.database import get_supabase_admin, get_supabase_schema  # noqa: E402
from app.domain.financials import WorkstreamTargetLockRequest  # noqa: E402
from app.services.dashboard_config import DashboardConfigService  # noqa: E402
from app.services.financial import FinancialService  # noqa: E402
from scripts.multi_tenant_transformation_profiles import (  # noqa: E402
    DEV_FIXTURE_EMAIL_DOMAINS,
)

ORG_NAME = os.environ.get("TRANSMUTER_SEED_ORG_NAME", "Acme Global Manufacturing")
ORG_SLUG = os.environ.get("TRANSMUTER_SEED_ORG_SLUG", "acme-transformation-lab")
ADMIN_EMAIL = os.environ.get(
    "TRANSMUTER_SEED_ADMIN_EMAIL",
    "admin@acme-transformation.qa.transmuter-dev.ishirock.tech",
)
ADMIN_PASSWORD = os.environ.get("TRANSMUTER_SEED_ADMIN_PASSWORD", "")
BASELINE_YEAR = 2026
SCENARIO_AS_OF_DATE = date(2028, 6, 30)
STATUS_CADENCE_AS_OF_DATE = date(2026, 7, 12)

DEV_APP_URL = "https://transmuter-dev.ishirock.tech"
DEV_SCHEMA = "transmuter_dev"
DEV_SUPABASE_URL = "https://supabase.ishirock.tech"
DEV_SEED_CONFIRMATION = "seed-enterprise-transformation-dev"
AUTH_FIXTURE_MARKER_KEY = "transmuter_fixture"
ORG_FIXTURE_MARKER_KEY = "qa_fixture"
DEFAULT_FIXTURE_OWNER = "enterprise-transformation-scenario"
OPTIONAL_RESET_TABLES = frozenset({"ai_copilot_actions"})

BASELINE_REVENUE = Decimal("20000000")
BASELINE_GROSS_MARGIN = Decimal("9000000")

MONEY = Decimal("0.0001")

InitiativeSeedRow = tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
]


def money(value: Decimal | int | str) -> str:
    return str(Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP))


def per_month(total: Decimal) -> Decimal:
    return (total / Decimal("12")).quantize(MONEY, rounding=ROUND_HALF_UP)


def now() -> str:
    return datetime.now(UTC).isoformat()


def reporting_year_months(reporting_year: int) -> list[tuple[int, int]]:
    """Return the platform's current reporting-year period coordinates."""
    return [(reporting_year, month) for month in range(1, 13)]


def reporting_year_bounds(reporting_year: int) -> tuple[date, date]:
    periods = reporting_year_months(reporting_year)
    start_year, start_month = periods[0]
    end_year, end_month = periods[-1]
    return (
        date(start_year, start_month, 1),
        date(end_year, end_month, monthrange(end_year, end_month)[1]),
    )


def reporting_year_actual_fraction(reporting_year: int) -> Decimal:
    if reporting_year < SCENARIO_AS_OF_DATE.year:
        return Decimal("1")
    if reporting_year > SCENARIO_AS_OF_DATE.year:
        return Decimal("0")
    return Decimal(SCENARIO_AS_OF_DATE.month) / Decimal("12")


def reporting_year_metric_totals(
    client: Client,
    tenant_id: str,
    metric_definition_id: str,
    scenario_id: str,
    reporting_year: int,
) -> dict[str, Decimal]:
    rows = (
        client.table("financial_metric_values")
        .select("initiative_id,value")
        .eq("tenant_id", tenant_id)
        .eq("metric_definition_id", metric_definition_id)
        .eq("scenario_id", scenario_id)
        .eq("year", reporting_year)
        .execute()
        .data
        or []
    )
    totals: dict[str, Decimal] = {}
    for row in rows:
        initiative_id = str(row["initiative_id"])
        totals[initiative_id] = totals.get(initiative_id, Decimal("0")) + Decimal(str(row["value"]))
    return totals


def assert_seed_target_allowed(environment: str, confirmation: str) -> None:
    target = environment.strip().lower()
    runtime_environment = (
        (os.environ.get("TRANSMUTER_ENVIRONMENT") or os.environ.get("ENVIRONMENT") or "")
        .strip()
        .lower()
    )
    schema = get_supabase_schema()
    app_url = (os.environ.get("APP_PUBLIC_URL") or "").rstrip("/")
    if target == "dev":
        if confirmation != DEV_SEED_CONFIRMATION:
            raise RuntimeError(
                f"Dev seed confirmation must exactly equal {DEV_SEED_CONFIRMATION!r}"
            )
        if runtime_environment not in {"dev", "development"}:
            raise RuntimeError("Dev seed requires the development runtime environment")
        supabase_target = (os.environ.get("SUPABASE_TARGET") or "").strip().lower()
        supabase_url = (
            os.environ.get("SUPABASE_LOCAL_URL") or os.environ.get("SUPABASE_URL") or ""
        ).rstrip("/")
        if (
            schema != DEV_SCHEMA
            or app_url != DEV_APP_URL
            or supabase_target != "local"
            or supabase_url != DEV_SUPABASE_URL
        ):
            raise RuntimeError(
                f"Dev seed requires schema {DEV_SCHEMA!r}, app URL {DEV_APP_URL!r}, "
                f"SUPABASE_TARGET=local, and endpoint {DEV_SUPABASE_URL!r}"
            )
        return
    raise RuntimeError("Seed environment must be explicitly set to dev")


def find_auth_user_by_email(client: Client, email: str) -> object | None:
    page = 1
    per_page = 100
    while True:
        users = client.auth.admin.list_users(page=page, per_page=per_page)
        if not users:
            return None
        for user in users:
            if (getattr(user, "email", "") or "").lower() == email.lower():
                return user
        if len(users) < per_page:
            return None
        page += 1


def find_auth_user_id_by_email(client: Client, email: str) -> str | None:
    user = find_auth_user_by_email(client, email)
    return str(user.id) if user else None  # type: ignore[attr-defined]


def assert_owned_auth_identity(
    client: Client,
    auth_user: object,
    *,
    email: str,
    tenant_id: str,
    role: str,
    fixture_owner: str,
) -> None:
    if bool(getattr(auth_user, "is_super_admin", False)):
        raise RuntimeError(f"Refusing fixture password reset for super-admin email {email!r}")
    app_metadata = getattr(auth_user, "app_metadata", None)
    if not isinstance(app_metadata, dict):
        raise RuntimeError(f"Existing auth email {email!r} has unreadable app metadata")
    allowed_scope_key = f"transmuter_authorization_{DEV_SCHEMA}"
    authorization_scope_keys = {
        key for key in app_metadata if key.startswith("transmuter_authorization_")
    }
    forbidden_keys = {"platform_admin", "tenant_id", "role"}
    if forbidden_keys.intersection(app_metadata):
        raise RuntimeError(f"Refusing fixture password reset for elevated/global email {email!r}")
    if authorization_scope_keys != {allowed_scope_key}:
        raise RuntimeError(f"Refusing fixture password reset for multi-scope email {email!r}")
    expected_authorization = {"tenant_id": tenant_id, "role": role}
    if app_metadata.get(allowed_scope_key) != expected_authorization:
        raise RuntimeError(f"Existing auth email {email!r} has mismatched dev authorization")
    expected_marker = {"owner": fixture_owner, "tenant_id": tenant_id}
    if app_metadata.get(AUTH_FIXTURE_MARKER_KEY) != expected_marker:
        raise RuntimeError(f"Existing auth email {email!r} is not owned by this fixture")
    user_metadata = getattr(auth_user, "user_metadata", None)
    if isinstance(user_metadata, dict) and {"tenant_id", "role"}.intersection(user_metadata):
        raise RuntimeError(f"Existing auth email {email!r} contains legacy user authorization")

    result = (
        client.table("users")
        .select("id,tenant_id,email,role")
        .eq("id", str(auth_user.id))  # type: ignore[attr-defined]
        .maybe_single()
        .execute()
    )
    row = result.data if result else None
    if (
        not row
        or str(row.get("tenant_id")) != tenant_id
        or str(row.get("email") or "").lower() != email.lower()
        or str(row.get("role")) != role
    ):
        raise RuntimeError(f"Existing auth email {email!r} does not match its platform user")


def mark_auth_fixture_owner(
    client: Client,
    user_id: str,
    *,
    tenant_id: str,
    fixture_owner: str,
) -> None:
    response = client.auth.admin.get_user_by_id(user_id)
    user = getattr(response, "user", None)
    app_metadata = dict(getattr(user, "app_metadata", None) or {})
    app_metadata[AUTH_FIXTURE_MARKER_KEY] = {
        "owner": fixture_owner,
        "tenant_id": tenant_id,
    }
    client.auth.admin.update_user_by_id(user_id, {"app_metadata": app_metadata})
    verified = client.auth.admin.get_user_by_id(user_id)
    verified_user = getattr(verified, "user", None)
    verified_user_metadata = getattr(verified_user, "user_metadata", None)
    if isinstance(verified_user_metadata, dict) and {
        "tenant_id",
        "role",
    }.intersection(verified_user_metadata):
        raise RuntimeError("Fixture Auth user retained legacy user authorization")


def ensure_org(
    client: Client,
    *,
    org_name: str = ORG_NAME,
    org_slug: str = ORG_SLUG,
    reporting_currency: str = "USD",
    fiscal_year_start_month: int = 1,
    theme: str = "Enterprise gross margin and growth transformation",
    fixture_owner: str = DEFAULT_FIXTURE_OWNER,
) -> str:
    existing = client.table("organizations").select("id,settings").eq("slug", org_slug).execute()
    settings = {
        "nudge_overdue_days": 7,
        "nudge_nuclear_days": 14,
        "scenario_as_of_date": SCENARIO_AS_OF_DATE.isoformat(),
        "status_cadence_as_of_date": STATUS_CADENCE_AS_OF_DATE.isoformat(),
        "strategic_parameters": {
            "markets": ["Group", "Regional"],
            "themes": [theme],
            "tags": ["automation", "offshoring", "commercial", "other"],
        },
        "bankable_plan_governance": {
            "approval_required": True,
            "approved_plan_only": True,
            "initiative_plan_lock_gate_number": 2,
            "plan_lock_on_approval": True,
            "baseline_lock_gate_number": 2,
            "baseline_lock_on_approval": True,
        },
        "financial_reporting": {
            "fiscal_year_start_month": fiscal_year_start_month,
            "reporting_currency": reporting_currency,
        },
        ORG_FIXTURE_MARKER_KEY: {"owner": fixture_owner, "slug": org_slug},
    }
    if existing.data:
        org_id = str(existing.data[0]["id"])
        existing_settings = existing.data[0].get("settings") or {}
        expected_marker = {"owner": fixture_owner, "slug": org_slug}
        if existing_settings.get(ORG_FIXTURE_MARKER_KEY) != expected_marker:
            raise RuntimeError(f"Existing tenant {org_slug!r} is not owned by this fixture")
        settings = {**existing_settings, **settings}
        client.table("organizations").update(
            {
                "name": org_name,
                "settings": settings,
                "fiscal_year_start_month": fiscal_year_start_month,
                "reporting_currency": reporting_currency,
                "updated_at": now(),
            }
        ).eq("id", org_id).execute()
        return org_id
    org_id = str(uuid4())
    client.table("organizations").insert(
        {
            "id": org_id,
            "name": org_name,
            "slug": org_slug,
            "settings": settings,
            "fiscal_year_start_month": fiscal_year_start_month,
            "reporting_currency": reporting_currency,
        }
    ).execute()
    return org_id


def ensure_admin_user(
    client: Client,
    tenant_id: str,
    *,
    email: str = ADMIN_EMAIL,
    password: str = ADMIN_PASSWORD,
    display_name: str = "Enterprise Transformation Admin",
    title: str = "VP, Enterprise Transformation",
    fixture_owner: str = DEFAULT_FIXTURE_OWNER,
) -> str:
    auth_user = find_auth_user_by_email(client, email)
    created_auth_user = False
    if auth_user:
        assert_owned_auth_identity(
            client,
            auth_user,
            email=email,
            tenant_id=tenant_id,
            role="transformation_office",
            fixture_owner=fixture_owner,
        )
        auth_id = str(auth_user.id)  # type: ignore[attr-defined]
        metadata = build_auth_metadata_payload(
            auth_id,
            authorization={
                "tenant_id": tenant_id,
                "role": "transformation_office",
            },
            profile={"display_name": display_name},
            scope=get_supabase_schema(),
            preserve_legacy_user_authorization=False,
        )
        metadata["app_metadata"][AUTH_FIXTURE_MARKER_KEY] = {
            "owner": fixture_owner,
            "tenant_id": tenant_id,
        }
        client.auth.admin.update_user_by_id(
            auth_id,
            {
                "password": password,
                "email_confirm": True,
                **metadata,
            },
        )
    else:
        metadata = build_auth_metadata_payload(
            None,
            authorization={
                "tenant_id": tenant_id,
                "role": "transformation_office",
            },
            profile={"display_name": display_name},
            scope=get_supabase_schema(),
            preserve_legacy_user_authorization=False,
        )
        metadata["app_metadata"][AUTH_FIXTURE_MARKER_KEY] = {
            "owner": fixture_owner,
            "tenant_id": tenant_id,
        }
        created = client.auth.admin.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                **metadata,
            }
        )
        auth_id = str(created.user.id)
        created_auth_user = True
    try:
        client.table("users").upsert(
            {
                "id": auth_id,
                "tenant_id": tenant_id,
                "email": email,
                "display_name": display_name,
                "title": title,
                "department": "Transformation Office",
                "timezone": "UTC",
                "role": "transformation_office",
                "status": "active",
                "onboarding_completed": True,
                "updated_at": now(),
            },
            on_conflict="id",
        ).execute()
    except Exception:
        if created_auth_user:
            client.auth.admin.delete_user(auth_id)
        raise
    mark_auth_fixture_owner(
        client,
        auth_id,
        tenant_id=tenant_id,
        fixture_owner=fixture_owner,
    )
    return auth_id


def delete_tenant_rows(client: Client, tenant_id: str) -> None:
    tables = [
        "ai_copilot_actions",
        "tenant_dashboard_config",
        "shared_cost_allocation_audit_events",
        "shared_cost_allocation_exceptions",
        "shared_cost_allocations",
        "shared_cost_allocation_runs",
        "shared_cost_allocation_weights",
        "shared_cost_allocation_targets",
        "shared_cost_allocation_rules",
        "shared_cost_pool_periods",
        "shared_cost_pools",
        "shared_cost_reporting_settings",
        "meeting_artifacts",
        "meeting_external_events",
        "action_items",
        "meeting_session_attendees",
        "meeting_session_agenda_items",
        "meeting_sessions",
        "agenda_items",
        "meeting_initiatives",
        "meeting_attendees",
        "meeting_workstreams",
        "meetings",
        "initiative_dependencies",
        "initiative_value_realization_notes",
        "workstream_target_locks",
        "financial_forecasts",
        "financial_initiative_annual_baselines",
        "financial_tenant_annual_baselines",
        "financial_benefit_line_validation_events",
        "benefit_realization_ledger",
        "bankable_plans",
        "gate_submissions",
        "stage_gates",
        "financial_metric_values",
        "financial_cell_assumptions",
        "initiative_financial_selections",
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
        "milestone_dependencies",
        "milestone_checklist",
        "nudge_log",
        "status_updates",
        "kpi_entries",
        "kpis",
        "risks",
        "milestones",
        "initiatives",
        "gate_criteria",
        "stage_gate_definitions",
        "user_workstreams",
        "workstreams",
        "business_units",
    ]
    for table in tables:
        try:
            client.table(table).delete().eq("tenant_id", tenant_id).execute()
        except Exception as exc:
            if table not in OPTIONAL_RESET_TABLES or getattr(exc, "code", None) not in {
                "42P01",
                "PGRST205",
            }:
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


def insert_workstreams(client: Client, tenant_id: str) -> dict[str, str]:
    rows = [
        "Automation",
        "Offshoring & Operating Model",
        "Commercial Growth",
        "ERP & Data Platform",
        "Procurement & Supply Chain",
    ]
    result: dict[str, str] = {}
    for name in rows:
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
    client: Client,
    tenant_id: str,
    metric_ids: dict[str, str],
    user_id: str,
    *,
    baseline_year: int = BASELINE_YEAR,
    baseline_revenue: Decimal = BASELINE_REVENUE,
    baseline_gross_margin: Decimal = BASELINE_GROSS_MARGIN,
) -> None:
    client.table("financial_tenant_annual_baselines").insert(
        [
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "metric_definition_id": metric_ids["annual_revenue_baseline"],
                "baseline_year": baseline_year,
                "value": money(baseline_revenue),
                "note": f"FY{str(baseline_year)[-2:]} revenue baseline for the enterprise transformation.",
                "created_by": user_id,
                "updated_by": user_id,
            },
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "metric_definition_id": metric_ids["annual_gross_margin_baseline"],
                "baseline_year": baseline_year,
                "value": money(baseline_gross_margin),
                "note": f"FY{str(baseline_year)[-2:]} gross margin baseline.",
                "created_by": user_id,
                "updated_by": user_id,
            },
        ]
    ).execute()


INITIATIVES: list[InitiativeSeedRow] = [
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
    *,
    initiatives: Sequence[InitiativeSeedRow] = INITIATIVES,
    baseline_year: int = BASELINE_YEAR,
    organization_name: str = ORG_NAME,
    organization_slug: str = ORG_SLUG,
    theme: str = "Enterprise gross margin and growth transformation",
    country: str = "United States",
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
    milestone_dependency_rows: list[dict[str, object]] = []
    milestone_ids_by_code: dict[str, dict[str, str]] = {}
    for index, row in enumerate(initiatives, start=1):
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
                f"Finance validated against {organization_name} benefit assumptions."
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
                    "phasing": {"method": "monthly_even", "source": organization_slug},
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
                    "evidence_url": (
                        f"https://example.com/{organization_slug}/{code.lower()}-"
                        f"{metric_key}-evidence"
                    ),
                    "evidence_label": f"{organization_name} assumption pack",
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
                    "evidence_url": (
                        f"https://example.com/{organization_slug}/{code.lower()}-"
                        f"{metric_key}-evidence"
                    ),
                    "evidence_label": f"{organization_name} assumption pack",
                    "metadata": {"source": organization_slug},
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
                        "evidence_url": (
                            f"https://example.com/{organization_slug}/{code.lower()}-"
                            f"{metric_key}-evidence"
                        ),
                        "evidence_label": f"{organization_name} assumption pack",
                        "metadata": {"source": organization_slug},
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
                "theme": theme,
                "country": country,
                "tag": tag,
                "priority": "high" if index in {4, 6, 7} else "medium",
                "rag_status": "amber" if index in {5, 9} else "green",
                "stage": "executing",
                "benefit_confidence": str(96 - (index * 3)),
                "realization_status": ("at_risk" if index in {5, 9} else "partially_realized"),
                "variance_explanation": (
                    "Adoption and delivery timing are the primary variance drivers."
                    if index in {5, 9}
                    else "Delivery remains within the approved transformation tolerance."
                ),
                "summary": (
                    "Three-year enterprise initiative contributing to FY28 revenue growth, "
                    "gross margin expansion, and bankable run-rate value."
                ),
                "value_logic": (
                    f"Measured against FY{str(baseline_year)[-2:]} annual baseline metrics "
                    "with plan-only bankable value."
                ),
                "dependencies_text": "Dependent on enterprise data readiness, BU sponsorship, and change adoption.",
                "planned_start": "2026-01-01",
                "actual_start": "2026-01-15",
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
                    "baseline_year": baseline_year,
                    "value": money(init_baseline_revenue),
                    "note": (
                        f"Allocated FY{str(baseline_year)[-2:]} revenue baseline for "
                        "initiative measurement."
                    ),
                    "created_by": user_id,
                    "updated_by": user_id,
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "metric_definition_id": metric_ids["annual_gross_margin_baseline"],
                    "baseline_year": baseline_year,
                    "value": money(init_baseline_gm),
                    "note": (
                        f"Allocated FY{str(baseline_year)[-2:]} gross margin baseline for "
                        "initiative measurement."
                    ),
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
        for fiscal_year, scenarios in annual_values.items():
            for scenario_key, metrics in scenarios.items():
                for metric_key, annual_value in metrics.items():
                    monthly = per_month(annual_value)
                    for calendar_year, month in reporting_year_months(fiscal_year):
                        period_end = date(
                            calendar_year,
                            month,
                            monthrange(calendar_year, month)[1],
                        )
                        if scenario_key == "actual" and period_end > SCENARIO_AS_OF_DATE:
                            continue
                        metric_value_rows.append(
                            {
                                "id": str(uuid4()),
                                "tenant_id": tenant_id,
                                "initiative_id": initiative_id,
                                "metric_definition_id": metric_ids[metric_key],
                                "benefit_line_id": benefit_line_ids.get(metric_key),
                                "scenario_id": scenario_ids[scenario_key],
                                "year": calendar_year,
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
            actual_fraction = reporting_year_actual_fraction(year)
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
                        "amount_actual": money(
                            annual_amount * factor * Decimal("0.97") * actual_fraction
                        ),
                        "is_recurring": True,
                        "category_key": category,
                        "created_by": user_id,
                        "updated_by": user_id,
                        "created_at": now(),
                        "updated_at": now(),
                    }
                )
        baseline_milestone_id = str(uuid4())
        delivery_milestone_id = str(uuid4())
        realization_milestone_id = str(uuid4())
        milestone_ids_by_code[code] = {
            "baseline": baseline_milestone_id,
            "delivery": delivery_milestone_id,
            "realization": realization_milestone_id,
        }
        client.table("milestones").insert(
            [
                {
                    "id": baseline_milestone_id,
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": "Gate 2 baseline and business case confirmed",
                    "description": "Baseline metrics and bankable plan agreed with Finance.",
                    "owner_id": user_id,
                    "priority": "high",
                    "sort_order": 10,
                    "planned_start": "2026-01-01",
                    "actual_start": "2026-01-05",
                    "planned_end": "2026-03-31",
                    "actual_end": "2026-03-28",
                    "status": "complete",
                },
                {
                    "id": delivery_milestone_id,
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": "Operating-model release deployed",
                    "description": "Priority capabilities are deployed with adoption controls.",
                    "owner_id": user_id,
                    "priority": "high",
                    "sort_order": 20,
                    "planned_start": "2026-04-01",
                    "actual_start": "2026-04-08",
                    "planned_end": "2028-03-31" if index in {5, 9} else "2027-09-30",
                    "actual_end": None if index in {5, 9} else "2027-09-25",
                    "status": "overdue" if index in {5, 9} else "complete",
                },
                {
                    "id": realization_milestone_id,
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": "FY28 run-rate benefits activated",
                    "description": "Run-rate value is embedded into the operating plan.",
                    "owner_id": user_id,
                    "priority": "medium",
                    "sort_order": 30,
                    "planned_start": "2028-01-01",
                    "planned_end": "2028-12-15",
                    "status": "in_progress",
                },
            ]
        ).execute()
        client.table("milestone_checklist").insert(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "milestone_id": delivery_milestone_id,
                    "text": "Process owner acceptance recorded",
                    "completed": index not in {5, 9},
                    "sort_order": 10,
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "milestone_id": delivery_milestone_id,
                    "text": "Adoption evidence reviewed",
                    "completed": index not in {5, 9},
                    "sort_order": 20,
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "milestone_id": realization_milestone_id,
                    "text": "Finance realization sign-off complete",
                    "completed": False,
                    "sort_order": 10,
                },
            ]
        ).execute()
        milestone_dependency_rows.extend(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "upstream_milestone_id": baseline_milestone_id,
                    "downstream_milestone_id": delivery_milestone_id,
                    "dependency_type": "finish_to_start",
                    "lag_days": 0,
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "upstream_milestone_id": delivery_milestone_id,
                    "downstream_milestone_id": realization_milestone_id,
                    "dependency_type": "start_to_start",
                    "lag_days": 30,
                },
            ]
        )
    for upstream_code, downstream_code, lag_days in [
        ("ENT-004", "ENT-005", 14),
        ("ENT-006", "ENT-002", 7),
        ("ENT-010", "ENT-008", 0),
    ]:
        if upstream_code in milestone_ids_by_code and downstream_code in milestone_ids_by_code:
            milestone_dependency_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "upstream_milestone_id": milestone_ids_by_code[upstream_code]["delivery"],
                    "downstream_milestone_id": milestone_ids_by_code[downstream_code][
                        "realization"
                    ],
                    "dependency_type": "finish_to_start",
                    "lag_days": lag_days,
                }
            )
    if milestone_dependency_rows:
        client.table("milestone_dependencies").insert(milestone_dependency_rows).execute()
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


def insert_initiative_controls(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    *,
    initiatives: Sequence[InitiativeSeedRow] = INITIATIVES,
    currency: str = "USD",
) -> None:
    kpi_rows: list[dict[str, object]] = []
    kpi_entry_rows: list[dict[str, object]] = []
    risk_rows: list[dict[str, object]] = []
    status_rows: list[dict[str, object]] = []
    risk_types = ("operational", "people", "financial", "technology")

    for index, seed in enumerate(initiatives, start=1):
        code, name = seed[0], seed[1]
        initiative_id = initiative_ids[code]
        value_kpi_id = str(uuid4())
        adoption_kpi_id = str(uuid4())
        kpi_rows.extend(
            [
                {
                    "id": value_kpi_id,
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": f"{name} value delivery",
                    "type": "gross_margin",
                    "category": "Value realization",
                    "frequency": "quarterly",
                    "unit": currency,
                },
                {
                    "id": adoption_kpi_id,
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "name": f"{name} adoption rate",
                    "type": "operational",
                    "category": "Delivery adoption",
                    "frequency": "quarterly",
                    "unit": "%",
                },
            ]
        )

        annual_values = {
            2026: (seed[10] + seed[12]) * Decimal("0.35"),
            2027: seed[10] + seed[12],
            2028: seed[11] + seed[13],
        }
        for year, annual_value in annual_values.items():
            for quarter in range(1, 5):
                quarter_end_year = year
                quarter_end_month = quarter * 3
                quarter_end = date(
                    quarter_end_year,
                    quarter_end_month,
                    monthrange(quarter_end_year, quarter_end_month)[1],
                )
                is_future = quarter_end > SCENARIO_AS_OF_DATE
                target = annual_value / Decimal("4")
                performance = Decimal("1.03") if index % 3 == 0 else Decimal("0.91")
                actual = target * performance
                if is_future:
                    actual_value: str | None = None
                else:
                    actual_value = money(actual)
                kpi_entry_rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "kpi_id": value_kpi_id,
                        "year": year,
                        "quarter": quarter,
                        "value_base": money(target),
                        "value_high": money(target * Decimal("1.15")),
                        "value_actual": actual_value,
                    }
                )
                adoption_base = Decimal(20 + ((year - 2026) * 30) + (quarter * 5))
                adoption_base = min(adoption_base, Decimal("95"))
                adoption_actual = adoption_base + (
                    Decimal("3") if index % 4 == 0 else Decimal("-4")
                )
                kpi_entry_rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "kpi_id": adoption_kpi_id,
                        "year": year,
                        "quarter": quarter,
                        "value_base": money(adoption_base),
                        "value_high": money(min(adoption_base + Decimal("8"), Decimal("100"))),
                        "value_actual": (
                            None if is_future else money(max(adoption_actual, Decimal("0")))
                        ),
                    }
                )

        high_risk = index in {4, 5, 9}
        risk_rows.extend(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "description": f"{name} delivery capacity may delay the committed release sequence.",
                    "type": risk_types[(index - 1) % len(risk_types)],
                    "impact": "high" if high_risk else "medium",
                    "likelihood": "high" if index in {5, 9} else "medium",
                    "rating": "high" if high_risk else "medium",
                    "status": "open",
                    "owner_id": user_id,
                    "mitigation": "Review critical-path capacity weekly and escalate decisions within five days.",
                    "escalated": index in {5, 9},
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "description": f"{name} adoption may lag the benefit realization curve.",
                    "type": "people",
                    "impact": "medium",
                    "likelihood": "low" if index % 2 == 0 else "medium",
                    "rating": "low" if index % 2 == 0 else "medium",
                    "status": "closed" if index % 4 == 0 else "open",
                    "owner_id": user_id,
                    "mitigation": "Track adoption by business unit and activate targeted coaching.",
                    "escalated": False,
                },
            ]
        )

        status_age_days = 22 if index in {5, 9} else 4
        latest_date = (
            f"{(STATUS_CADENCE_AS_OF_DATE - timedelta(days=status_age_days)).isoformat()}"
            "T09:00:00+00:00"
        )
        draft_date = f"{(STATUS_CADENCE_AS_OF_DATE - timedelta(days=2)).isoformat()}T09:00:00+00:00"
        status_rows.extend(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "author_id": user_id,
                    "rag_status": "amber" if high_risk else "green",
                    "summary": f"{name} completed its latest delivery checkpoint.",
                    "achievements": "Financial assumptions and delivery evidence were refreshed.",
                    "issues": (
                        "Capacity and dependency decisions remain open."
                        if high_risk
                        else "No material issue outside approved tolerance."
                    ),
                    "next_steps": "Close the next milestone and update benefit evidence.",
                    "is_draft": False,
                    "submitted_at": latest_date,
                    "created_at": latest_date,
                    "updated_at": latest_date,
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "author_id": user_id,
                    "rag_status": "amber" if high_risk else "green",
                    "summary": f"Draft next-period update for {name}.",
                    "achievements": "Quarterly evidence collection has started.",
                    "issues": "Draft pending owner review.",
                    "next_steps": "Submit after the next workstream review.",
                    "is_draft": True,
                    "submitted_at": None,
                    "created_at": draft_date,
                    "updated_at": draft_date,
                },
            ]
        )

    client.table("kpis").insert(kpi_rows).execute()
    for start in range(0, len(kpi_entry_rows), 500):
        client.table("kpi_entries").insert(kpi_entry_rows[start : start + 500]).execute()
    client.table("risks").insert(risk_rows).execute()
    client.table("status_updates").insert(status_rows).execute()


def insert_initiative_financial_scope(
    client: Client,
    tenant_id: str,
    initiative_ids: dict[str, str],
    metric_ids: dict[str, str],
) -> None:
    cost_categories = (
        client.table("financial_cost_categories")
        .select("id,key")
        .eq("tenant_id", tenant_id)
        .execute()
        .data
        or []
    )
    selected_metric_keys = set(metric_ids)
    selected_cost_keys = {
        "implementation",
        "technology_tooling",
        "external_consultants",
        "training_change",
        "software",
        "maintenance",
        "labor",
    }
    selection_rows: list[dict[str, object]] = []
    scope_rows: list[dict[str, object]] = []
    for initiative_id in initiative_ids.values():
        for metric_key, metric_id in metric_ids.items():
            is_active = metric_key in selected_metric_keys
            selection_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "item_key": metric_key,
                    "item_type": "metric",
                    "is_active": is_active,
                }
            )
            scope_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "scope_type": "metric_definition",
                    "metric_definition_id": metric_id,
                    "is_active": is_active,
                }
            )
        for category in cost_categories:
            category_key = str(category["key"])
            is_active = category_key in selected_cost_keys
            selection_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "item_key": category_key,
                    "item_type": "cost_category",
                    "is_active": is_active,
                }
            )
            scope_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "scope_type": "cost_category",
                    "cost_category_id": str(category["id"]),
                    "is_active": is_active,
                }
            )
    client.table("initiative_financial_selections").insert(selection_rows).execute()
    client.table("initiative_financial_scope").insert(scope_rows).execute()


def insert_bankable_plan_and_realization_demo(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    gate_criteria: list[dict[str, str | int]],
    metric_ids: dict[str, str],
    scenario_ids: dict[str, str],
    *,
    initiatives: Sequence[InitiativeSeedRow] = INITIATIVES,
    organization_name: str = ORG_NAME,
    value_scale: Decimal = Decimal("1"),
) -> None:
    service = FinancialService(client, tenant_id)  # type: ignore[arg-type]
    gate_dates = {
        1: ("2026-02-15T09:00:00+00:00", "2026-02-18T09:00:00+00:00"),
        2: ("2026-04-12T09:00:00+00:00", "2026-04-16T09:00:00+00:00"),
        3: ("2026-06-10T09:00:00+00:00", "2026-06-14T09:00:00+00:00"),
        4: ("2027-09-20T09:00:00+00:00", "2027-09-25T09:00:00+00:00"),
    }
    submission_rows: list[dict[str, object]] = []
    plan_lock_submission_ids: dict[str, str] = {}
    for code, initiative_id in initiative_ids.items():
        for gate_number in range(1, 5):
            submitted_at, decided_at = gate_dates[gate_number]
            submission_id = str(uuid4())
            if gate_number == 2:
                plan_lock_submission_ids[code] = submission_id
            criteria_snapshot = [
                {
                    "id": row["id"],
                    "criterion_id": row["criterion_id"],
                    "label": row["label"],
                    "guidance": row.get("guidance"),
                    "sort_order": row.get("sort_order", 0),
                    "ticked": True,
                    "ticked_by": user_id,
                    "ticked_at": submitted_at,
                }
                for row in gate_criteria
                if row["gate_number"] == gate_number
            ]
            submission_rows.append(
                {
                    "id": submission_id,
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "gate_number": gate_number,
                    "submission_type": "stage_gate",
                    "submitted_by_id": user_id,
                    "submitted_at": submitted_at,
                    "decision": "approved",
                    "decided_by_id": user_id,
                    "decided_at": decided_at,
                    "commentary": (f"Seeded {organization_name} Gate {gate_number} approval."),
                    "criteria_snapshot": criteria_snapshot,
                }
            )
    client.table("gate_submissions").insert(submission_rows).execute()

    for code, initiative_id in initiative_ids.items():
        plan = service.lock_bankable_plan_from_approval(
            initiative_id,
            plan_lock_submission_ids[code],
            user_id,
            locked_reason=(
                f"Seeded Gate 2 approval for {organization_name} acceptance bankable plan."
            ),
        )
        client.table("bankable_plans").update({"locked_at": gate_dates[2][1]}).eq(
            "tenant_id", tenant_id
        ).eq("id", plan.id).execute()

    rebaseline_initiative_id = initiative_ids["ENT-005"]
    reporting_2028_periods = set(reporting_year_months(2028))
    rebaseline_values = (
        client.table("financial_metric_values")
        .select("id,year,month,value")
        .eq("tenant_id", tenant_id)
        .eq("initiative_id", rebaseline_initiative_id)
        .eq("metric_definition_id", metric_ids["gm_uplift"])
        .eq("scenario_id", scenario_ids["plan_base"])
        .execute()
        .data
        or []
    )
    for value_row in rebaseline_values:
        if (int(value_row["year"]), int(value_row["month"])) not in reporting_2028_periods:
            continue
        client.table("financial_metric_values").update(
            {"value": money(Decimal(str(value_row["value"])) * Decimal("1.08"))}
        ).eq("tenant_id", tenant_id).eq("id", value_row["id"]).execute()

    requested_snapshot = service.get_bankable_plan_snapshot(rebaseline_initiative_id)
    rebaseline_submission_id = str(uuid4())
    client.table("gate_submissions").insert(
        {
            "id": rebaseline_submission_id,
            "tenant_id": tenant_id,
            "initiative_id": rebaseline_initiative_id,
            "gate_number": 2,
            "submission_type": "bankable_plan_rebaseline",
            "submitted_by_id": user_id,
            "submitted_at": "2028-04-10T09:00:00+00:00",
            "decision": "approved",
            "decided_by_id": user_id,
            "decided_at": "2028-04-16T09:00:00+00:00",
            "commentary": (
                f"Governed rebaseline for {initiatives[4][1]} after validated scope and "
                "adoption assumptions changed."
            ),
            "criteria_snapshot": [
                {
                    "id": "rebaseline-reason",
                    "criterion_id": "rebaseline-reason",
                    "label": "Rebaseline reason documented",
                    "ticked": True,
                    "ticked_by": user_id,
                    "ticked_at": "2028-04-10T09:00:00+00:00",
                },
                {
                    "id": "dashboard-impact-reviewed",
                    "criterion_id": "dashboard-impact-reviewed",
                    "label": "Dashboard and board-pack impact reviewed",
                    "ticked": True,
                    "ticked_by": user_id,
                    "ticked_at": "2028-04-10T09:00:00+00:00",
                },
            ],
            "requested_bankable_plan_version": 2,
            "requested_snapshot": requested_snapshot.model_dump(mode="json"),
        }
    ).execute()
    rebaseline_plan = service.rebaseline_bankable_plan(
        rebaseline_initiative_id,
        user_id,
        reason=(
            f"Approved governed rebaseline for {initiatives[4][1]} after validated scope "
            "and adoption assumptions changed."
        ),
        trigger_submission_id=rebaseline_submission_id,
    )
    client.table("bankable_plans").update({"locked_at": "2028-04-16T09:00:00+00:00"}).eq(
        "tenant_id", tenant_id
    ).eq("id", rebaseline_plan.id).execute()

    rows = []
    initiative_seed_by_code = {row[0]: row for row in initiatives}
    for code, initiative_id in initiative_ids.items():
        seed = initiative_seed_by_code[code]
        gm_2027 = seed[10]
        gm_2028 = seed[11]
        savings_2027 = seed[12]
        savings_2028 = seed[13]
        rebaselined_gm_2028 = gm_2028 * (Decimal("1.08") if code == "ENT-005" else Decimal("1"))
        yearly = {
            2027: {
                "plan": gm_2027 + savings_2027,
                "actual": (gm_2027 * Decimal("0.86")) + (savings_2027 * Decimal("0.82")),
            },
            2028: {
                "plan": rebaselined_gm_2028 + savings_2028,
                "actual": (gm_2028 * Decimal("0.90")) + (savings_2028 * Decimal("0.88")),
            },
        }
        for fiscal_year, amounts in yearly.items():
            plan_monthly = per_month(amounts["plan"])
            actual_monthly = per_month(amounts["actual"])
            for calendar_year, month in reporting_year_months(fiscal_year):
                last_day = monthrange(calendar_year, month)[1]
                period_end = date(calendar_year, month, last_day)
                actual_amount = (
                    actual_monthly if period_end <= SCENARIO_AS_OF_DATE else Decimal("0")
                )
                rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "initiative_id": initiative_id,
                        "period_granularity": "monthly",
                        "period_start": f"{calendar_year}-{month:02d}-01",
                        "period_end": f"{calendar_year}-{month:02d}-{last_day:02d}",
                        "bankable_plan_amount": money(plan_monthly),
                        "actual_amount": money(actual_amount),
                        "description": (
                            f"Seeded {organization_name} FY{fiscal_year} monthly realization "
                            f"for {code} as of {SCENARIO_AS_OF_DATE.isoformat()}."
                        ),
                    }
                )
    for start in range(0, len(rows), 500):
        client.table("benefit_realization_ledger").insert(rows[start : start + 500]).execute()

    note_rows = [
        {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "initiative_id": initiative_ids["ENT-002"],
            "author_id": user_id,
            "note_type": "realization",
            "period_label": "FY2028",
            "planned_value": money(Decimal("1450000") * value_scale),
            "actual_value": money(
                Decimal("1285000") * value_scale * reporting_year_actual_fraction(2028)
            ),
            "explanation": (
                "Commercial execution remains above baseline, but adoption timing "
                "is the main variance to monitor in the next steering cycle."
            ),
        },
        {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "initiative_id": initiative_ids["ENT-005"],
            "author_id": user_id,
            "note_type": "allocation",
            "period_label": "FY2028",
            "planned_value": money(Decimal("650000") * value_scale),
            "actual_value": money(
                Decimal("585000") * value_scale * reporting_year_actual_fraction(2028)
            ),
            "explanation": (
                "Enterprise Data Platform carries a material share of group "
                "technology platform costs because it benefits most from the "
                "central data and tooling pool."
            ),
        },
        {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "initiative_id": initiative_ids["ENT-010"],
            "author_id": user_id,
            "note_type": "board_note",
            "period_label": "FY2028",
            "planned_value": money(Decimal("900000") * value_scale),
            "actual_value": money(
                Decimal("792000") * value_scale * reporting_year_actual_fraction(2028)
            ),
            "explanation": (
                "Collaboration tooling value is tracking behind plan in the first "
                "half because shared services adoption is slower than expected."
            ),
        },
    ]
    client.table("initiative_value_realization_notes").insert(note_rows).execute()


def insert_forecasts_and_workstream_targets(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    workstreams: dict[str, str],
    *,
    initiatives: Sequence[InitiativeSeedRow] = INITIATIVES,
) -> None:
    forecast_rows: list[dict[str, object]] = []
    seed_by_code = {row[0]: row for row in initiatives}
    for code, initiative_id in initiative_ids.items():
        seed = seed_by_code[code]
        forecast_rows.extend(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "line_type": "metric",
                    "line_key": "gm_uplift",
                    "year": 2028,
                    "quarter": None,
                    "month": None,
                    "amount_forecast": money(seed[11] * Decimal("0.94")),
                    "notes": "Current outlook after delivery and adoption risk adjustments.",
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "line_type": "metric",
                    "line_key": "cost_savings",
                    "year": 2028,
                    "quarter": None,
                    "month": None,
                    "amount_forecast": money(seed[13] * Decimal("0.91")),
                    "notes": "Current savings outlook relative to the locked plan.",
                },
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "initiative_id": initiative_id,
                    "line_type": "cost",
                    "line_key": "software",
                    "year": 2028,
                    "quarter": None,
                    "month": None,
                    "amount_forecast": money(seed[15] * Decimal("0.40") * Decimal("1.03")),
                    "notes": "Forecast recurring platform cost including current run-rate variance.",
                },
            ]
        )
    client.table("financial_forecasts").insert(forecast_rows).execute()

    service = FinancialService(client, tenant_id)  # type: ignore[arg-type]
    request = WorkstreamTargetLockRequest(lock_date=SCENARIO_AS_OF_DATE)
    for workstream_id in workstreams.values():
        service.lock_workstream_target(workstream_id, request, user_id)


def insert_shared_cost_demo(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    metric_ids: dict[str, str],
    scenario_ids: dict[str, str],
    *,
    reporting_currency: str = "USD",
    organization_name: str = ORG_NAME,
    value_scale: Decimal = Decimal("1"),
) -> None:
    categories = {
        row["key"]: row["id"]
        for row in client.table("financial_cost_categories")
        .select("id,key")
        .eq("tenant_id", tenant_id)
        .execute()
        .data
        or []
    }
    reporting_period_start, reporting_period_end = reporting_year_bounds(2028)
    gm_plan_by_initiative = reporting_year_metric_totals(
        client,
        tenant_id,
        metric_ids["gm_uplift"],
        scenario_ids["plan_base"],
        2028,
    )
    actual_fraction = reporting_year_actual_fraction(2028)

    def allocate_by_shares(
        pool_id: str,
        rule_id: str,
        run_id: str,
        codes: list[str],
        shares: list[Decimal],
        basis_values: list[Decimal],
        amount_plan: Decimal,
        amount_actual: Decimal,
        allocation_method: str,
        basis_label: str,
        basis_metric_definition_id: str | None,
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        remaining_plan = amount_plan
        remaining_actual = amount_actual
        for index, code in enumerate(codes):
            share = shares[index]
            ideal_plan = (amount_plan * share).quantize(MONEY, rounding=ROUND_HALF_UP)
            ideal_actual = (amount_actual * share).quantize(MONEY, rounding=ROUND_HALF_UP)
            if index == len(codes) - 1:
                plan = remaining_plan
                actual = remaining_actual
            else:
                plan = ideal_plan
                actual = ideal_actual
                remaining_plan -= plan
                remaining_actual -= actual
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "run_id": run_id,
                    "pool_id": pool_id,
                    "rule_id": rule_id,
                    "initiative_id": initiative_ids[code],
                    "allocation_basis": allocation_method,
                    "basis_value": money(basis_values[index]),
                    "allocated_plan": money(plan),
                    "allocated_actual": money(actual),
                    "period_start": reporting_period_start.isoformat(),
                    "period_end": reporting_period_end.isoformat(),
                    "scenario_id": scenario_ids["plan_base"],
                    "basis_metric_definition_id": basis_metric_definition_id,
                    "basis_label": basis_label,
                    "allocation_share": str(share.quantize(Decimal("0.00000001"))),
                    "rounding_adjustment": money(plan - ideal_plan),
                    "explanation": (
                        f"{code} receives "
                        f"{(share * Decimal('100')).quantize(Decimal('0.01'))}% of the pool "
                        f"using {basis_label}."
                    ),
                    "exception_flags": {},
                }
            )
        return rows

    scenarios = [
        {
            "name": "Group technology and data platform",
            "description": "Shared data, cloud, AI, and integration platform costs used by transformation initiatives.",
            "category_key": "software",
            "amount_plan": Decimal("650000") * value_scale,
            "amount_actual": Decimal("585000") * value_scale * actual_fraction,
            "method": "benefit_weighted",
            "driver_metric_definition_id": metric_ids["gm_uplift"],
            "target_codes": ["ENT-002", "ENT-005", "ENT-006", "ENT-009", "ENT-010"],
            "basis": "Gross Margin Uplift",
            "shares": None,
        },
        {
            "name": "Transformation PMO and benefits office",
            "description": "Central governance and benefits-office run cost allocated across the bankable portfolio.",
            "category_key": "labor",
            "amount_plan": Decimal("400000") * value_scale,
            "amount_actual": Decimal("360000") * value_scale * actual_fraction,
            "method": "equal_split",
            "target_codes": list(initiative_ids.keys()),
            "basis": "Equal split",
            "shares": None,
        },
        {
            "name": "Shared change and training support",
            "description": "Shared adoption, training, and change-support capacity for process-heavy initiatives.",
            "category_key": "training_change",
            "amount_plan": Decimal("220000") * value_scale,
            "amount_actual": Decimal("198000") * value_scale * actual_fraction,
            "method": "manual_amount",
            "target_codes": ["ENT-002", "ENT-004", "ENT-005", "ENT-010"],
            "basis": "Manual amount",
            "manual_amounts": {
                "ENT-002": Decimal("55000") * value_scale,
                "ENT-004": Decimal("70000") * value_scale,
                "ENT-005": Decimal("55000") * value_scale,
                "ENT-010": Decimal("40000") * value_scale,
            },
            "shares": None,
        },
        {
            "name": "Central advisory and vendor support",
            "description": "Central advisory support allocated to workstreams that used the transformation vendor.",
            "category_key": "external_consultants",
            "amount_plan": Decimal("180000") * value_scale,
            "amount_actual": Decimal("162000") * value_scale * actual_fraction,
            "method": "fixed_percentage",
            "target_codes": ["ENT-005", "ENT-008", "ENT-009"],
            "basis": "Fixed percentage",
            "shares": [Decimal("0.40"), Decimal("0.35"), Decimal("0.25")],
        },
    ]

    client.table("shared_cost_reporting_settings").upsert(
        {
            "tenant_id": tenant_id,
            "include_in_executive_control_tower": True,
            "include_in_dashboard_executive_brief": True,
            "include_in_portfolio_financials": False,
            "include_in_initiative_financials": True,
            "include_in_bankable_plan": False,
            "posting_mode": "report_only",
        },
        on_conflict="tenant_id",
    ).execute()

    for scenario in scenarios:
        pool_id = str(uuid4())
        rule_id = str(uuid4())
        run_id = str(uuid4())
        amount_plan = scenario["amount_plan"]
        amount_actual = scenario["amount_actual"]
        category_key = str(scenario["category_key"])
        client.table("shared_cost_pools").insert(
            {
                "id": pool_id,
                "tenant_id": tenant_id,
                "name": scenario["name"],
                "description": scenario["description"],
                "category_key": category_key,
                "cost_category_id": categories.get(category_key),
                "scenario_id": scenario_ids["plan_base"],
                "year": 2028,
                "amount_plan": money(amount_plan),
                "amount_actual": money(amount_actual),
                "is_recurring": True,
                "status": "active",
                "period_grain": "annual",
                "reporting_treatment": "report_only",
                "currency_code": reporting_currency,
                "owner_id": user_id,
            }
        ).execute()
        client.table("shared_cost_pool_periods").insert(
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "pool_id": pool_id,
                "scenario_id": scenario_ids["plan_base"],
                "year": 2028,
                "period_start": reporting_period_start.isoformat(),
                "period_end": reporting_period_end.isoformat(),
                "amount_plan": money(amount_plan),
                "amount_actual": money(amount_actual),
                "status": "locked",
            }
        ).execute()
        client.table("shared_cost_allocation_rules").insert(
            {
                "id": rule_id,
                "tenant_id": tenant_id,
                "pool_id": pool_id,
                "name": f"{scenario['basis']} allocation",
                "allocation_method": scenario["method"],
                "filters": {},
                "weights": {},
                "is_active": True,
                "version": 1,
                "policy_status": "locked",
                "driver_metric_definition_id": scenario.get("driver_metric_definition_id"),
                "driver_scenario_id": scenario_ids["plan_base"],
                "driver_period_mode": "fiscal_year",
                "missing_basis_behavior": "fail",
                "is_locked": True,
            }
        ).execute()
        target_rows = [
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "rule_id": rule_id,
                "target_mode": "include",
                "dimension_type": "initiative",
                "dimension_value": initiative_ids[code],
                "label": code,
            }
            for code in scenario["target_codes"]
        ]
        client.table("shared_cost_allocation_targets").insert(target_rows).execute()

        weights = []
        if scenario["method"] == "manual_amount":
            for code, manual_amount in scenario["manual_amounts"].items():
                weights.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "rule_id": rule_id,
                        "initiative_id": initiative_ids[code],
                        "manual_amount": money(manual_amount),
                        "label": code,
                    }
                )
        elif scenario["method"] == "fixed_percentage":
            for code, share in zip(scenario["target_codes"], scenario["shares"], strict=True):
                weights.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "rule_id": rule_id,
                        "initiative_id": initiative_ids[code],
                        "percentage": money(share * Decimal("100")),
                        "label": code,
                    }
                )
        if weights:
            client.table("shared_cost_allocation_weights").insert(weights).execute()

        codes = scenario["target_codes"]
        shares = scenario.get("shares")
        method = str(scenario["method"])
        if shares is None and method == "benefit_weighted":
            basis_values = [
                gm_plan_by_initiative.get(initiative_ids[code], Decimal("0")) for code in codes
            ]
            total = sum(basis_values, Decimal("0"))
            if total <= 0:
                raise RuntimeError(
                    "Benefit-weighted allocation requires positive FY2028 GM plan values"
                )
            shares = [basis / total for basis in basis_values]
        elif shares is None and method == "equal_split":
            basis_values = [Decimal("1") for _code in codes]
            shares = [Decimal("1") / Decimal(len(codes)) for _code in codes]
        elif shares is None and method == "manual_amount":
            basis_values = [scenario["manual_amounts"][code] for code in codes]
            shares = [basis / amount_plan for basis in basis_values]
        else:
            basis_values = [share * Decimal("100") for share in shares]
        allocation_rows = allocate_by_shares(
            pool_id,
            rule_id,
            run_id,
            codes,
            shares,
            basis_values,
            amount_plan,
            amount_actual,
            method,
            str(scenario["basis"]),
            scenario.get("driver_metric_definition_id"),
        )
        client.table("shared_cost_allocation_runs").insert(
            {
                "id": run_id,
                "tenant_id": tenant_id,
                "pool_id": pool_id,
                "rule_id": rule_id,
                "scenario": "plan",
                "scenario_id": scenario_ids["plan_base"],
                "status": "locked",
                "run_type": "posting",
                "rule_version": 1,
                "period_start": reporting_period_start.isoformat(),
                "period_end": reporting_period_end.isoformat(),
                "total_amount_plan": money(amount_plan),
                "total_amount_actual": money(amount_actual),
                "input_snapshot": {
                    "seeded": True,
                    "pool": scenario["name"],
                    "allocation_method": method,
                    "basis_values": [money(value) for value in basis_values],
                    "allocation_shares": [
                        str(share.quantize(Decimal("0.00000001"))) for share in shares
                    ],
                },
                "exception_summary": {"count": 0, "blocking": 0, "exceptions": []},
                "approved_by": user_id,
                "approved_at": now(),
                "locked_by": user_id,
                "locked_at": now(),
                "created_by": user_id,
                "reporting_treatment": "report_only",
            }
        ).execute()
        client.table("shared_cost_allocations").insert(allocation_rows).execute()
        client.table("shared_cost_allocation_audit_events").insert(
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "pool_id": pool_id,
                "rule_id": rule_id,
                "run_id": run_id,
                "actor_id": user_id,
                "event_type": "seeded_locked_run",
                "message": f"Seeded {organization_name} shared-cost locked allocation run.",
                "after_state": {"pool": scenario["name"], "amount_plan": money(amount_plan)},
            }
        ).execute()


def insert_initiative_dependencies(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    workstreams: dict[str, str],
) -> None:
    dependency_specs = [
        (
            "ENT-004",
            "ENT-005",
            "blocks",
            "blocking",
            "high",
            "2028-03-31",
            "Upstream operating-model readiness must stabilize before the downstream cutover.",
        ),
        (
            "ENT-006",
            "ENT-002",
            "requires_decision",
            "at_risk",
            "high",
            "2028-02-28",
            "A portfolio data and design decision gates the downstream rollout.",
        ),
        (
            "ENT-010",
            "ENT-008",
            "enables",
            "active",
            "medium",
            "2028-04-15",
            "Enabling capability adoption is required before downstream value capture.",
        ),
    ]
    dependency_rows = []
    for (
        upstream_code,
        downstream_code,
        dep_type,
        status,
        severity,
        due_date,
        notes,
    ) in dependency_specs:
        dependency_rows.append(
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "upstream_initiative_id": initiative_ids[upstream_code],
                "downstream_initiative_id": initiative_ids[downstream_code],
                "dependency_type": dep_type,
                "status": status,
                "severity": severity,
                "owner_id": user_id,
                "due_date": due_date,
                "resolution_notes": notes,
            }
        )
    client.table("initiative_dependencies").insert(dependency_rows).execute()


def insert_meeting_demo(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    workstreams: dict[str, str],
) -> None:
    meeting_specs = [
        {
            "name": "Transformation Steering Committee",
            "workstream_id": None,
            "scope": "all",
            "recurrence": "weekly",
            "day_of_week": 1,
            "start_time": "09:00",
            "duration_minutes": 75,
            "description": "Executive cadence for value delivery, dependencies, shared costs, and gate decisions.",
            "initiatives": ["ENT-002", "ENT-004", "ENT-005", "ENT-006", "ENT-010"],
            "agenda": [
                ("Portfolio value and bankable plan movement", None),
                ("Shared-cost allocation and burdened value bridge", "ENT-005"),
                ("ERP dependency and procurement cutover decision", "ENT-004"),
            ],
            "session_date": "2028-02-12",
            "notes": "Reviewed FY2028 value bridge, locked shared-cost runs, and two high dependency risks.",
            "action": (
                "Validate procurement cutover readiness against ERP data migration dependency",
                "ENT-005",
                "high",
                "2028-02-23",
            ),
        },
        {
            "name": "North Asia Workstream Review",
            "workstream_id": workstreams["Commercial Growth"],
            "scope": "workstream",
            "recurrence": "weekly",
            "day_of_week": 3,
            "start_time": "14:00",
            "duration_minutes": 60,
            "description": "Regional commercial execution review for growth and pricing initiatives.",
            "initiatives": ["ENT-002", "ENT-003"],
            "agenda": [
                ("Distributor segmentation lift and account conversion", "ENT-002"),
                ("Pricing analytics adoption blockers", "ENT-003"),
            ],
            "session_date": "2028-02-14",
            "notes": "Commercial Growth reviewed adoption blockers and pricing analytics rollout risks.",
            "action": (
                "Confirm North Asia account conversion evidence for next benefits review",
                "ENT-002",
                "medium",
                "2028-02-26",
            ),
        },
    ]

    for meeting in meeting_specs:
        meeting_id = str(uuid4())
        attendee_id = str(uuid4())
        session_id = str(uuid4())
        client.table("meetings").insert(
            {
                "id": meeting_id,
                "tenant_id": tenant_id,
                "name": meeting["name"],
                "workstream_id": meeting["workstream_id"],
                "scope": meeting["scope"],
                "recurrence": meeting["recurrence"],
                "day_of_week": meeting["day_of_week"],
                "start_time": meeting["start_time"],
                "timezone": "UTC",
                "duration_minutes": meeting["duration_minutes"],
                "description": meeting["description"],
                "owner_id": user_id,
            }
        ).execute()
        client.table("meeting_attendees").insert(
            {
                "id": attendee_id,
                "tenant_id": tenant_id,
                "meeting_id": meeting_id,
                "user_id": user_id,
            }
        ).execute()
        client.table("meeting_initiatives").insert(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "meeting_id": meeting_id,
                    "initiative_id": initiative_ids[code],
                }
                for code in meeting["initiatives"]
            ]
        ).execute()
        agenda_rows = []
        for sort_order, (text, code) in enumerate(meeting["agenda"], start=1):
            agenda_rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "meeting_id": meeting_id,
                    "initiative_id": initiative_ids[code] if code else None,
                    "text": text,
                    "sort_order": sort_order,
                }
            )
        client.table("agenda_items").insert(agenda_rows).execute()
        client.table("meeting_sessions").insert(
            {
                "id": session_id,
                "tenant_id": tenant_id,
                "meeting_id": meeting_id,
                "session_date": meeting["session_date"],
                "status": "completed",
                "has_transcript": True,
                "ai_optimised": True,
                "transcript_text": meeting["notes"],
                "notes": meeting["notes"],
            }
        ).execute()
        client.table("meeting_session_attendees").insert(
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "meeting_id": meeting_id,
                "session_id": session_id,
                "source_meeting_attendee_id": attendee_id,
                "user_id": user_id,
            }
        ).execute()
        client.table("meeting_session_agenda_items").insert(
            [
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "meeting_id": meeting_id,
                    "session_id": session_id,
                    "source_agenda_item_id": row["id"],
                    "initiative_id": row["initiative_id"],
                    "text": row["text"],
                    "sort_order": row["sort_order"],
                }
                for row in agenda_rows
            ]
        ).execute()
        action_text, action_code, priority, due_date = meeting["action"]
        client.table("action_items").insert(
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "session_id": session_id,
                "initiative_id": initiative_ids[action_code],
                "description": action_text,
                "assignee_id": user_id,
                "priority": priority,
                "status": "open",
                "due_date": due_date,
            }
        ).execute()


def insert_operating_cadence_demo(
    client: Client,
    tenant_id: str,
    user_id: str,
    initiative_ids: dict[str, str],
    workstreams: dict[str, str],
) -> None:
    insert_initiative_dependencies(client, tenant_id, user_id, initiative_ids, workstreams)
    insert_meeting_demo(client, tenant_id, user_id, initiative_ids, workstreams)


def seed_enterprise_transformation_scenario(
    client: Client,
    *,
    seed_environment: str = "",
    seed_confirmation: str = "",
    fixture_owner: str,
    org_name: str = ORG_NAME,
    org_slug: str = ORG_SLUG,
    admin_email: str = ADMIN_EMAIL,
    admin_password: str = ADMIN_PASSWORD,
    admin_display_name: str = "Enterprise Transformation Admin",
    admin_title: str = "VP, Enterprise Transformation",
    baseline_year: int = BASELINE_YEAR,
    baseline_revenue: Decimal = BASELINE_REVENUE,
    baseline_gross_margin: Decimal = BASELINE_GROSS_MARGIN,
    reporting_currency: str = "USD",
    fiscal_year_start_month: int = 1,
    theme: str = "Enterprise gross margin and growth transformation",
    country: str = "United States",
    initiatives: Sequence[InitiativeSeedRow] = INITIATIVES,
    value_scale: Decimal = Decimal("1"),
    include_meetings: bool = True,
) -> dict[str, object]:
    assert_seed_target_allowed(seed_environment, seed_confirmation)
    if len(admin_password) < 12:
        raise RuntimeError("Seed admin password must be explicitly set to at least 12 characters")
    email_parts = admin_email.lower().split("@")
    if (
        len(email_parts) != 2
        or not email_parts[0]
        or email_parts[1] not in DEV_FIXTURE_EMAIL_DOMAINS
    ):
        raise RuntimeError("Seed admin email must use an approved dev QA domain")
    if len(initiatives) != 10:
        raise ValueError("Enterprise transformation scenario requires exactly 10 initiatives")
    expected_codes = [f"ENT-{index:03d}" for index in range(1, 11)]
    if [row[0] for row in initiatives] != expected_codes:
        raise ValueError("Enterprise transformation scenario requires ENT-001 through ENT-010")
    currency = reporting_currency.upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("Reporting currency must be a three-letter ISO-style code")
    if not 1 <= fiscal_year_start_month <= 12:
        raise ValueError("Fiscal year start month must be between 1 and 12")

    tenant_id = ensure_org(
        client,
        org_name=org_name,
        org_slug=org_slug,
        reporting_currency=currency,
        fiscal_year_start_month=fiscal_year_start_month,
        theme=theme,
        fixture_owner=fixture_owner,
    )
    user_id = ensure_admin_user(
        client,
        tenant_id,
        email=admin_email,
        password=admin_password,
        display_name=admin_display_name,
        title=admin_title,
        fixture_owner=fixture_owner,
    )
    delete_tenant_rows(client, tenant_id)
    business_units = insert_business_units(client, tenant_id)
    workstreams = insert_workstreams(client, tenant_id)
    insert_stage_gates(client, tenant_id)
    gate_criteria = insert_gate_criteria(client, tenant_id)
    insert_financial_config(client, tenant_id)
    metric_ids, scenario_ids = insert_engine_config(client, tenant_id, user_id)
    insert_tenant_baselines(
        client,
        tenant_id,
        metric_ids,
        user_id,
        baseline_year=baseline_year,
        baseline_revenue=baseline_revenue,
        baseline_gross_margin=baseline_gross_margin,
    )
    initiative_ids = insert_initiatives(
        client,
        tenant_id,
        user_id,
        business_units,
        workstreams,
        metric_ids,
        scenario_ids,
        initiatives=initiatives,
        baseline_year=baseline_year,
        organization_name=org_name,
        organization_slug=org_slug,
        theme=theme,
        country=country,
    )
    insert_initiative_financial_scope(client, tenant_id, initiative_ids, metric_ids)
    insert_initiative_controls(
        client,
        tenant_id,
        user_id,
        initiative_ids,
        initiatives=initiatives,
        currency=currency,
    )
    insert_bankable_plan_and_realization_demo(
        client,
        tenant_id,
        user_id,
        initiative_ids,
        gate_criteria,
        metric_ids,
        scenario_ids,
        initiatives=initiatives,
        organization_name=org_name,
        value_scale=value_scale,
    )
    insert_forecasts_and_workstream_targets(
        client,
        tenant_id,
        user_id,
        initiative_ids,
        workstreams,
        initiatives=initiatives,
    )
    insert_shared_cost_demo(
        client,
        tenant_id,
        user_id,
        initiative_ids,
        metric_ids,
        scenario_ids,
        reporting_currency=currency,
        organization_name=org_name,
        value_scale=value_scale,
    )
    DashboardConfigService(client, tenant_id).enable_all_defaults()
    insert_initiative_dependencies(client, tenant_id, user_id, initiative_ids, workstreams)
    if include_meetings:
        insert_meeting_demo(client, tenant_id, user_id, initiative_ids, workstreams)

    return {
        "tenant_id": tenant_id,
        "admin_user_id": user_id,
        "initiative_ids": initiative_ids,
        "initiative_count": len(initiative_ids),
        "meetings_included": include_meetings,
    }


def main() -> None:
    include_meetings = os.environ.get("TRANSMUTER_SEED_INCLUDE_MEETINGS", "1").lower() not in {
        "0",
        "false",
        "no",
    }
    result = seed_enterprise_transformation_scenario(
        get_supabase_admin(),
        seed_environment=os.environ.get("TRANSMUTER_SEED_ENVIRONMENT", ""),
        seed_confirmation=os.environ.get("TRANSMUTER_SEED_CONFIRMATION", ""),
        fixture_owner=DEFAULT_FIXTURE_OWNER,
        include_meetings=include_meetings,
    )
    print("Seeded enterprise transformation scenario")
    print(f"  tenant_id: {result['tenant_id']}")
    print(f"  login: {ADMIN_EMAIL}")
    print(f"  initiatives: {result['initiative_count']}")
    print("  gate criteria: seeded")
    print("  bankable plans: seeded")
    print("  benefit ledger: seeded")
    print("  shared cost pools: seeded")
    print(f"  meetings: {'seeded' if include_meetings else 'excluded'}")
    print(f"  FY26 revenue baseline: {money(BASELINE_REVENUE)}")
    print(f"  FY26 gross margin baseline: {money(BASELINE_GROSS_MARGIN)}")
    print("  FY28 plan target revenue uplift: 4000000.0000")
    print("  FY28 plan target gross margin uplift: 5400000.0000")


if __name__ == "__main__":
    main()
