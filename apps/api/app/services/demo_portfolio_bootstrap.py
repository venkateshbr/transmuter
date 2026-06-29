"""Deterministic 10-initiative transformation portfolio bootstrap.

This module seeds a realistic multi-year transformation scenario that can be used
for dev registration/bootstrap flows and end-to-end browser testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from supabase import Client

SCENARIO_START = date(2026, 1, 1)
SCENARIO_END = date(2028, 12, 31)
QUARTER_STARTS = {
    1: (1, 1),
    2: (4, 1),
    3: (7, 1),
    4: (10, 1),
}


@dataclass(frozen=True)
class InitiativeSeed:
    label: str
    code: str
    name: str
    workstream: str
    kind: str
    impact_type: str
    priority: str
    rag_status: str
    stage: str
    country: str
    tag: str
    summary: str
    value_logic: str
    planned_start: date
    planned_end: date
    actual_start: date | None
    base_value: Decimal
    high_value: Decimal
    actual_value: Decimal | None
    benefit_confidence: Decimal
    realization_status: str


WORKSTREAMS = [
    ("foundation", "Transformation Foundation"),
    ("growth", "Revenue & Margin Growth"),
    ("operations", "Operations & Shared Services"),
]

INITIATIVES: list[InitiativeSeed] = [
    InitiativeSeed(
        label="pmo",
        code="TRN-001",
        name="Transformation PMO & Benefits Office",
        workstream="foundation",
        kind="governance",
        impact_type="one_off",
        priority="high",
        rag_status="green",
        stage="in_progress",
        country="Group",
        tag="governance",
        summary="Establishes the governance cadence, benefits discipline, and reporting standards for the portfolio.",
        value_logic="Creates the operating model that all other initiatives report through.",
        planned_start=SCENARIO_START,
        planned_end=date(2026, 12, 31),
        actual_start=SCENARIO_START,
        base_value=Decimal("50000"),
        high_value=Decimal("75000"),
        actual_value=Decimal("50000"),
        benefit_confidence=Decimal("95"),
        realization_status="committed",
    ),
    InitiativeSeed(
        label="erp",
        code="TRN-002",
        name="ERP Consolidation & Automation",
        workstream="foundation",
        kind="cost_reduction",
        impact_type="recurring",
        priority="high",
        rag_status="amber",
        stage="in_progress",
        country="Group",
        tag="automation",
        summary="Consolidates legacy finance systems and automates month-end close and AP/AR workflows.",
        value_logic="Unlocks future savings, consistent reporting, and downstream automation opportunities.",
        planned_start=date(2026, 1, 1),
        planned_end=date(2027, 6, 30),
        actual_start=date(2026, 4, 1),
        base_value=Decimal("250000"),
        high_value=Decimal("400000"),
        actual_value=Decimal("240000"),
        benefit_confidence=Decimal("88"),
        realization_status="forecasted",
    ),
    InitiativeSeed(
        label="compliance",
        code="TRN-003",
        name="Data Privacy & Regulatory Compliance Programme",
        workstream="foundation",
        kind="compliance",
        impact_type="one_off",
        priority="high",
        rag_status="green",
        stage="in_progress",
        country="Group",
        tag="other",
        summary="Privacy impact assessments, remediation, and training across the portfolio.",
        value_logic="Reduces execution risk and clears the path for later platform and AI rollouts.",
        planned_start=date(2026, 1, 1),
        planned_end=date(2026, 9, 30),
        actual_start=date(2026, 1, 1),
        base_value=Decimal("100000"),
        high_value=Decimal("150000"),
        actual_value=Decimal("100000"),
        benefit_confidence=Decimal("92"),
        realization_status="committed",
    ),
    InitiativeSeed(
        label="productivity",
        code="TRN-004",
        name="Group Productivity / Hybrid Ways of Working",
        workstream="foundation",
        kind="capability_building",
        impact_type="one_off",
        priority="medium",
        rag_status="green",
        stage="scoping",
        country="Group",
        tag="other",
        summary="Collaboration tools and operating norms to improve hybrid working productivity.",
        value_logic="Supports adoption of the transformation operating model and later automation releases.",
        planned_start=date(2026, 3, 1),
        planned_end=date(2027, 3, 31),
        actual_start=None,
        base_value=Decimal("125000"),
        high_value=Decimal("175000"),
        actual_value=None,
        benefit_confidence=Decimal("70"),
        realization_status="forecasted",
    ),
    InitiativeSeed(
        label="rev_asia",
        code="TRN-005",
        name="North Asia Revenue Acceleration",
        workstream="growth",
        kind="revenue_growth",
        impact_type="recurring",
        priority="high",
        rag_status="amber",
        stage="in_progress",
        country="North Asia",
        tag="commercial",
        summary="Pricing discipline, account segmentation, and key-account expansion for North Asia markets.",
        value_logic="Creates recurring revenue uplift with scenario sensitivity across base/high cases.",
        planned_start=date(2026, 2, 1),
        planned_end=date(2028, 6, 30),
        actual_start=date(2026, 4, 1),
        base_value=Decimal("450000"),
        high_value=Decimal("700000"),
        actual_value=Decimal("420000"),
        benefit_confidence=Decimal("84"),
        realization_status="forecasted",
    ),
    InitiativeSeed(
        label="offshoring",
        code="TRN-006",
        name="Back-office Offshoring (Finance & HR)",
        workstream="operations",
        kind="cost_reduction",
        impact_type="recurring",
        priority="high",
        rag_status="red",
        stage="in_progress",
        country="Group",
        tag="offshoring",
        summary="Moves transactional finance and HR work to a shared-service model with labour arbitrage savings.",
        value_logic="Strong candidate for bankable-plan locking and benefit-ledger tracking.",
        planned_start=date(2026, 1, 1),
        planned_end=date(2027, 12, 31),
        actual_start=date(2026, 7, 1),
        base_value=Decimal("320000"),
        high_value=Decimal("520000"),
        actual_value=Decimal("300000"),
        benefit_confidence=Decimal("90"),
        realization_status="at_risk",
    ),
    InitiativeSeed(
        label="procurement",
        code="TRN-007",
        name="Procurement Savings Wave",
        workstream="operations",
        kind="cost_reduction",
        impact_type="recurring",
        priority="high",
        rag_status="green",
        stage="in_progress",
        country="Group",
        tag="savings",
        summary="Vendor consolidation, contract renegotiation, and demand management for recurring savings.",
        value_logic="Captures quick wins in year 1 and compounds into year 2 and 3.",
        planned_start=date(2026, 4, 1),
        planned_end=date(2028, 12, 31),
        actual_start=date(2026, 10, 1),
        base_value=Decimal("210000"),
        high_value=Decimal("350000"),
        actual_value=Decimal("205000"),
        benefit_confidence=Decimal("82"),
        realization_status="forecasted",
    ),
    InitiativeSeed(
        label="pricing",
        code="TRN-008",
        name="Pricing & Discount Optimisation",
        workstream="growth",
        kind="revenue_growth",
        impact_type="recurring",
        priority="medium",
        rag_status="green",
        stage="scoping",
        country="Group",
        tag="commercial",
        summary="Pricing guardrails, discount governance, and margin improvement analytics.",
        value_logic="Improves margin mix with moderate implementation cost and strong visibility.",
        planned_start=date(2026, 6, 1),
        planned_end=date(2028, 9, 30),
        actual_start=date(2027, 1, 1),
        base_value=Decimal("180000"),
        high_value=Decimal("260000"),
        actual_value=None,
        benefit_confidence=Decimal("76"),
        realization_status="forecasted",
    ),
    InitiativeSeed(
        label="supply_chain",
        code="TRN-009",
        name="Supply Chain Control Tower",
        workstream="operations",
        kind="operational",
        impact_type="recurring",
        priority="high",
        rag_status="amber",
        stage="in_progress",
        country="Group",
        tag="data",
        summary="Visibility, inventory optimisation, and service-level improvement across the supply chain.",
        value_logic="Balances service, inventory, and risk with strong control-tower reporting needs.",
        planned_start=date(2027, 1, 1),
        planned_end=date(2028, 12, 31),
        actual_start=date(2027, 4, 1),
        base_value=Decimal("290000"),
        high_value=Decimal("420000"),
        actual_value=Decimal("270000"),
        benefit_confidence=Decimal("78"),
        realization_status="partially_realized",
    ),
    InitiativeSeed(
        label="ai_service_desk",
        code="TRN-010",
        name="AI Service Desk Automation",
        workstream="operations",
        kind="automation",
        impact_type="recurring",
        priority="medium",
        rag_status="green",
        stage="scoping",
        country="Group",
        tag="automation",
        summary="Ticket deflection, knowledge automation, and service productivity improvements.",
        value_logic="Demonstrates the next wave of automation benefits and post-go-live realization.",
        planned_start=date(2027, 3, 1),
        planned_end=date(2028, 12, 31),
        actual_start=date(2027, 7, 1),
        base_value=Decimal("160000"),
        high_value=Decimal("300000"),
        actual_value=Decimal("150000"),
        benefit_confidence=Decimal("74"),
        realization_status="forecasted",
    ),
]


def _quarter_date(year: int, quarter: int) -> tuple[date, date]:
    month, day = QUARTER_STARTS[quarter]
    start = date(year, month, day)
    if quarter == 4:
        end = date(year, 12, 31)
    else:
        next_month = QUARTER_STARTS[quarter + 1][0]
        end = date(year, next_month, 1) - timedelta(days=1)
    return start, end


def _dec(value: Decimal | float | int | None) -> str | None:
    if value is None:
        return None
    return f"{Decimal(str(value)):.4f}"


def _quarter_multiplier(initiative: InitiativeSeed, year: int, quarter: int) -> Decimal:
    offset = (year - 2026) * 4 + (quarter - 1)
    if initiative.kind == "governance":
        return Decimal("1") + Decimal(offset) * Decimal("0.03")
    if initiative.kind in {"revenue_growth", "automation"}:
        return Decimal("1") + Decimal(offset) * Decimal("0.06")
    if initiative.kind == "cost_reduction":
        return Decimal("1") + Decimal(offset) * Decimal("0.05")
    return Decimal("1") + Decimal(offset) * Decimal("0.04")


def _financial_row(
    initiative: InitiativeSeed, year: int, quarter: int
) -> dict[str, str | int | None]:
    multiplier = _quarter_multiplier(initiative, year, quarter)
    revenue_base = (
        initiative.base_value * multiplier
        if initiative.kind in {"revenue_growth", "automation"}
        else Decimal("0")
    )
    revenue_high = (
        initiative.high_value * multiplier
        if initiative.kind in {"revenue_growth", "automation"}
        else Decimal("0")
    )
    actual_available = (
        initiative.actual_start is not None
        and date(year, *_quarter_date(year, quarter)[0].timetuple()[1:3]) >= initiative.actual_start
    )
    actual_factor = (
        Decimal("0.96")
        if initiative.kind == "revenue_growth"
        else Decimal("0.93")
        if initiative.kind == "cost_reduction"
        else Decimal("0.90")
    )
    revenue_actual = revenue_base * actual_factor if actual_available and revenue_base > 0 else None
    gm_base = (initiative.base_value * Decimal("0.80")) * multiplier
    gm_high = (initiative.high_value * Decimal("0.80")) * multiplier
    gm_actual = gm_base * actual_factor if actual_available else None

    if initiative.kind == "cost_reduction":
        gm_base = initiative.base_value * multiplier
        gm_high = initiative.high_value * multiplier
        gm_actual = gm_base * actual_factor if actual_available else None

    if initiative.kind == "governance":
        gm_base = initiative.base_value * multiplier
        gm_high = initiative.high_value * multiplier
        gm_actual = gm_base if actual_available else None

    return {
        "year": year,
        "quarter": quarter,
        "revenue_uplift_base": _dec(revenue_base),
        "revenue_uplift_high": _dec(revenue_high),
        "revenue_uplift_actual": _dec(revenue_actual),
        "gross_margin_base": _dec(gm_base),
        "gross_margin_high": _dec(gm_high),
        "gross_margin_actual": _dec(gm_actual),
        "gm_uplift_base": _dec(gm_base),
        "gm_uplift_high": _dec(gm_high),
        "gm_uplift_actual": _dec(gm_actual),
    }


def _db_type(kind: str) -> str:
    return {
        "governance": "capability_building",
        "automation": "capability_building",
        "revenue_growth": "revenue_growth",
        "cost_reduction": "cost_reduction",
        "compliance": "compliance",
        "capability_building": "capability_building",
        "operational": "capability_building",
    }.get(kind, "capability_building")


def bootstrap_demo_portfolio(client: Client, tenant_id: str, owner_user_id: str) -> dict[str, int]:
    """Seed the deterministic multi-year demo portfolio for a tenant."""
    _seed_bankable_plan_governance(client, tenant_id)
    workstream_ids = _seed_workstreams(client, tenant_id)
    initiative_ids = _seed_initiatives(client, tenant_id, workstream_ids, owner_user_id)
    _seed_milestones(client, tenant_id, initiative_ids, owner_user_id)
    _seed_financial_entries(client, tenant_id, initiative_ids)
    _seed_cost_lines(client, tenant_id, initiative_ids)
    _seed_bankable_plan_locks(client, tenant_id, initiative_ids, owner_user_id)
    _seed_workstream_target_locks(client, tenant_id, initiative_ids, workstream_ids, owner_user_id)
    _seed_dependencies(client, tenant_id, initiative_ids, owner_user_id)
    _seed_benefit_ledger(client, tenant_id, initiative_ids)
    _seed_initiative_controls(client, tenant_id, initiative_ids)
    return {
        "workstreams": len(workstream_ids),
        "initiatives": len(initiative_ids),
    }


def _seed_bankable_plan_governance(client: Client, tenant_id: str) -> None:
    org = (
        client.table("organizations")
        .select("settings")
        .eq("id", tenant_id)
        .maybe_single()
        .execute()
    )
    settings = (org.data or {}).get("settings") or {}
    settings["bankable_plan_governance"] = {
        **(settings.get("bankable_plan_governance") or {}),
        "initiative_plan_lock_gate_number": 3,
        "plan_lock_on_approval": True,
        "allow_rebaseline": True,
        "rebaseline_roles": ["transformation_office", "finance_lead", "pmo_lead"],
        "workstream_lock_cadence": "one_off",
        "initiative_inclusion_cutoff": "approved_at_lte_lock_date",
        "valuation_method": "run_rate",
        "locked_value_basis": "net_run_rate",
        "workstream_target_versioning": True,
    }
    client.table("organizations").update({"settings": settings}).eq("id", tenant_id).execute()


def _seed_workstreams(client: Client, tenant_id: str) -> dict[str, str]:
    rows = {}
    for key, name in WORKSTREAMS:
        existing = (
            client.table("workstreams")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("name", name)
            .execute()
        )
        if existing.data:
            rows[key] = existing.data[0]["id"]
            continue
        row_id = str(uuid4())
        client.table("workstreams").insert(
            {"id": row_id, "tenant_id": tenant_id, "name": name}
        ).execute()
        rows[key] = row_id
    return rows


def _seed_initiatives(
    client: Client,
    tenant_id: str,
    workstream_ids: dict[str, str],
    owner_user_id: str,
) -> dict[str, str]:
    rows: dict[str, str] = {}
    for initiative in INITIATIVES:
        existing = (
            client.table("initiatives")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("initiative_code", initiative.code)
            .execute()
        )
        payload = {
            "tenant_id": tenant_id,
            "initiative_code": initiative.code,
            "name": initiative.name,
            "workstream_id": workstream_ids[initiative.workstream],
            "owner_id": owner_user_id,
            "priority": initiative.priority,
            "rag_status": initiative.rag_status,
            "stage": initiative.stage,
            "country": initiative.country,
            "tag": initiative.tag,
            "type": _db_type(initiative.kind),
            "impact_type": initiative.impact_type,
            "summary": initiative.summary,
            "value_logic": initiative.value_logic,
            "planned_start": initiative.planned_start.isoformat(),
            "planned_end": initiative.planned_end.isoformat(),
            "actual_start": initiative.actual_start.isoformat()
            if initiative.actual_start
            else None,
            "actual_end": None,
            "benefit_confidence": str(initiative.benefit_confidence),
            "realization_status": initiative.realization_status,
            "variance_explanation": initiative.value_logic,
        }
        if existing.data:
            initiative_id = existing.data[0]["id"]
            client.table("initiatives").update(payload).eq("id", initiative_id).execute()
        else:
            initiative_id = str(uuid4())
            client.table("initiatives").insert({"id": initiative_id, **payload}).execute()
        rows[initiative.label] = initiative_id
    return rows


def _seed_milestones(
    client: Client,
    tenant_id: str,
    initiative_ids: dict[str, str],
    owner_user_id: str,
) -> None:
    for index, initiative in enumerate(INITIATIVES):
        iid = initiative_ids[initiative.label]
        milestone_specs = [
            (
                "Charter / design",
                initiative.planned_start,
                initiative.planned_start + timedelta(days=45),
                initiative.actual_start,
                initiative.actual_start + timedelta(days=30) if initiative.actual_start else None,
                "complete" if initiative.actual_start else "not_started",
            ),
            (
                "Build / pilot",
                initiative.planned_start + timedelta(days=60),
                initiative.planned_start + timedelta(days=150),
                initiative.actual_start + timedelta(days=30) if initiative.actual_start else None,
                initiative.actual_start + timedelta(days=120) if initiative.actual_start else None,
                "in_progress" if initiative.actual_start else "not_started",
            ),
            (
                "Rollout / benefit lock-in",
                initiative.planned_start + timedelta(days=180),
                initiative.planned_end,
                None,
                None,
                "not_started",
            ),
        ]
        for sort_order, (
            name,
            planned_start,
            planned_end,
            actual_start,
            actual_end,
            status,
        ) in enumerate(milestone_specs):
            existing = (
                client.table("milestones")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("initiative_id", iid)
                .eq("name", name)
                .execute()
            )
            payload = {
                "tenant_id": tenant_id,
                "initiative_id": iid,
                "name": name,
                "description": f"{initiative.name} — {name.lower()}",
                "owner_id": owner_user_id,
                "priority": initiative.priority,
                "status": status,
                "sort_order": sort_order + index * 10,
                "planned_start": planned_start.isoformat(),
                "planned_end": planned_end.isoformat(),
                "actual_start": actual_start.isoformat() if actual_start else None,
                "actual_end": actual_end.isoformat() if actual_end else None,
                "pressure_score": "0.0000" if status == "complete" else "55.0000",
                "pressure_blast_radius": "0.1000",
                "pressure_dep_urgency": "0.2000",
                "pressure_cluster": "0.2000",
                "pressure_slack": "0.2000",
                "pressure_checklist": "0.2000",
                "pressure_self_status": "0.2000",
                "pressure_updated_at": None,
            }
            if existing.data:
                client.table("milestones").update(payload).eq(
                    "id", existing.data[0]["id"]
                ).execute()
            else:
                client.table("milestones").insert({"id": str(uuid4()), **payload}).execute()


def _seed_financial_entries(client: Client, tenant_id: str, initiative_ids: dict[str, str]) -> None:
    for initiative in INITIATIVES:
        iid = initiative_ids[initiative.label]
        for year in (2026, 2027, 2028):
            for quarter in (1, 2, 3, 4):
                existing = (
                    client.table("financial_entries")
                    .select("id")
                    .eq("tenant_id", tenant_id)
                    .eq("initiative_id", iid)
                    .eq("year", year)
                    .eq("quarter", quarter)
                    .execute()
                )
                row = _financial_row(initiative, year, quarter)
                payload = {
                    "tenant_id": tenant_id,
                    "initiative_id": iid,
                    **row,
                }
                if existing.data:
                    client.table("financial_entries").update(payload).eq(
                        "id", existing.data[0]["id"]
                    ).execute()
                else:
                    client.table("financial_entries").insert(
                        {"id": str(uuid4()), **payload}
                    ).execute()


def _seed_cost_lines(client: Client, tenant_id: str, initiative_ids: dict[str, str]) -> None:
    cost_lines = [
        (
            "erp",
            "ERP Licence & Implementation",
            "implementation",
            2026,
            1,
            Decimal("250000"),
            Decimal("260000"),
            False,
        ),
        (
            "offshoring",
            "Shared Service Transition",
            "implementation",
            2026,
            3,
            Decimal("180000"),
            Decimal("175000"),
            False,
        ),
        (
            "procurement",
            "Vendor Renegotiation Workstream",
            "operating",
            2026,
            4,
            Decimal("90000"),
            Decimal("85000"),
            True,
        ),
        (
            "ai_service_desk",
            "AI Knowledge Base Build",
            "implementation",
            2027,
            2,
            Decimal("120000"),
            Decimal("110000"),
            False,
        ),
    ]
    for (
        label,
        name,
        category_key,
        year,
        quarter,
        amount_plan,
        amount_actual,
        recurring,
    ) in cost_lines:
        iid = initiative_ids[label]
        existing = (
            client.table("financial_cost_lines")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("initiative_id", iid)
            .eq("name", name)
            .execute()
        )
        payload = {
            "tenant_id": tenant_id,
            "initiative_id": iid,
            "name": name,
            "category_key": category_key,
            "year": year,
            "quarter": quarter,
            "amount_plan": _dec(amount_plan),
            "amount_actual": _dec(amount_actual),
            "is_recurring": recurring,
        }
        if existing.data:
            client.table("financial_cost_lines").update(payload).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            client.table("financial_cost_lines").insert({"id": str(uuid4()), **payload}).execute()


def _seed_bankable_plan_locks(
    client: Client,
    tenant_id: str,
    initiative_ids: dict[str, str],
    owner_user_id: str,
) -> None:
    for initiative in INITIATIVES:
        if initiative.stage == "scoping":
            continue
        iid = initiative_ids[initiative.label]
        approved_at = initiative.actual_start or initiative.planned_start
        submission = (
            client.table("gate_submissions")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("initiative_id", iid)
            .eq("gate_number", 3)
            .eq("decision", "approved")
            .execute()
        )
        submission_payload = {
            "tenant_id": tenant_id,
            "initiative_id": iid,
            "gate_number": 3,
            "submitted_by_id": owner_user_id,
            "submitted_at": approved_at.isoformat(),
            "decision": "approved",
            "decided_by_id": owner_user_id,
            "decided_at": approved_at.isoformat(),
            "commentary": "Seeded demo approval for initiative plan lock.",
            "criteria_snapshot": [
                {
                    "criterion_id": "demo-bankable-plan",
                    "label": "Bankable plan ready",
                    "ticked": True,
                    "ticked_by": owner_user_id,
                    "ticked_at": approved_at.isoformat(),
                }
            ],
        }
        if submission.data:
            submission_id = submission.data[0]["id"]
            client.table("gate_submissions").update(submission_payload).eq(
                "id", submission_id
            ).execute()
        else:
            submission_id = str(uuid4())
            client.table("gate_submissions").insert(
                {"id": submission_id, **submission_payload}
            ).execute()

        existing_plan = (
            client.table("bankable_plans")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("initiative_id", iid)
            .eq("version", 1)
            .execute()
        )
        snapshot = {
            "entries": [],
            "cost_lines": [],
            "metric_values": [],
            "selections": {"metric_keys": [], "cost_category_keys": []},
            "financial_mode": {
                "key": "bankable_locked",
                "label": "Locked bankable plan",
                "description": "Seeded immutable baseline for demo portfolio.",
                "locked": True,
                "scenarios": ["approval"],
            },
            "summary": {
                "net_value_plan": _dec(initiative.base_value),
                "net_value_actual": _dec(initiative.actual_value),
                "benefit_run_rate": _dec(initiative.base_value),
                "cost_run_rate": "0.0000",
            },
        }
        plan_payload = {
            "tenant_id": tenant_id,
            "initiative_id": iid,
            "version": 1,
            "trigger_type": "approval",
            "trigger_submission_id": submission_id,
            "locked_by_id": owner_user_id,
            "locked_at": approved_at.isoformat(),
            "locked_reason": "Seeded demo approval for initiative plan lock.",
            "snapshot": snapshot,
        }
        if existing_plan.data:
            client.table("bankable_plans").update(plan_payload).eq(
                "id", existing_plan.data[0]["id"]
            ).execute()
        else:
            client.table("bankable_plans").insert({"id": str(uuid4()), **plan_payload}).execute()


def _seed_workstream_target_locks(
    client: Client,
    tenant_id: str,
    initiative_ids: dict[str, str],
    workstream_ids: dict[str, str],
    owner_user_id: str,
) -> None:
    lock_date = date(2026, 12, 31)
    for workstream_key, workstream_id in workstream_ids.items():
        workstream_initiatives = [
            initiative for initiative in INITIATIVES if initiative.workstream == workstream_key
        ]
        included = [
            initiative for initiative in workstream_initiatives if initiative.stage != "scoping"
        ]
        excluded = [
            initiative for initiative in workstream_initiatives if initiative.stage == "scoping"
        ]
        plan_total = sum((initiative.base_value for initiative in included), Decimal("0"))
        actual_total = sum(
            (initiative.actual_value or Decimal("0") for initiative in included), Decimal("0")
        )
        snapshot = {
            "workstream_id": workstream_id,
            "workstream_name": next(
                (name for key, name in WORKSTREAMS if key == workstream_key), workstream_key
            ),
            "lock_date": lock_date.isoformat(),
            "settings": {
                "initiative_plan_lock_gate_number": 3,
                "plan_lock_on_approval": True,
                "allow_rebaseline": True,
                "rebaseline_roles": ["transformation_office", "finance_lead", "pmo_lead"],
                "workstream_lock_cadence": "one_off",
                "initiative_inclusion_cutoff": "approved_at_lte_lock_date",
                "valuation_method": "run_rate",
                "locked_value_basis": "net_run_rate",
                "workstream_target_versioning": True,
            },
            "included": [
                {
                    "initiative_id": initiative_ids[initiative.label],
                    "initiative_code": initiative.code,
                    "name": initiative.name,
                    "stage": initiative.stage,
                    "approved_at": (
                        initiative.actual_start or initiative.planned_start
                    ).isoformat(),
                    "bankable_plan_version": 1,
                    "value_source": "bankable_plan",
                    "net_run_rate_value": _dec(initiative.base_value),
                    "actual_value": _dec(initiative.actual_value),
                }
                for initiative in included
            ],
            "excluded": [
                {
                    "initiative_id": initiative_ids[initiative.label],
                    "initiative_code": initiative.code,
                    "name": initiative.name,
                    "stage": initiative.stage,
                    "approved_at": None,
                    "bankable_plan_version": None,
                    "value_source": "current_financials_preview",
                    "net_run_rate_value": _dec(initiative.base_value),
                    "actual_value": _dec(initiative.actual_value),
                }
                for initiative in excluded
            ],
            "locked_run_rate_value": _dec(plan_total),
            "plan_total": _dec(plan_total),
            "actual_total": _dec(actual_total),
            "variance": _dec(actual_total - plan_total),
        }
        existing = (
            client.table("workstream_target_locks")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("workstream_id", workstream_id)
            .eq("version", 1)
            .execute()
        )
        payload = {
            "tenant_id": tenant_id,
            "workstream_id": workstream_id,
            "version": 1,
            "lock_date": lock_date.isoformat(),
            "locked_at": lock_date.isoformat(),
            "locked_by_id": owner_user_id,
            "lock_cadence": "one_off",
            "cutoff_rule": "approved_at_lte_lock_date",
            "valuation_method": "run_rate",
            "locked_value_basis": "net_run_rate",
            "included_initiative_ids": [
                initiative_ids[initiative.label] for initiative in included
            ],
            "excluded_initiative_ids": [
                initiative_ids[initiative.label] for initiative in excluded
            ],
            "locked_run_rate_value": _dec(plan_total),
            "plan_total": _dec(plan_total),
            "actual_total": _dec(actual_total),
            "variance": _dec(actual_total - plan_total),
            "snapshot": snapshot,
        }
        if existing.data:
            client.table("workstream_target_locks").update(payload).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            client.table("workstream_target_locks").insert(
                {"id": str(uuid4()), **payload}
            ).execute()


def _seed_dependencies(
    client: Client,
    tenant_id: str,
    initiative_ids: dict[str, str],
    owner_user_id: str,
) -> None:
    dependencies = [
        ("pmo", "erp", "enables", "active", "medium", "TRN-002 depends on governance cadence."),
        (
            "pmo",
            "rev_asia",
            "enables",
            "active",
            "medium",
            "TRN-005 depends on benefits governance.",
        ),
        (
            "erp",
            "offshoring",
            "blocks",
            "blocking",
            "high",
            "ERP stabilisation is required before offshoring scale-up.",
        ),
        (
            "compliance",
            "supply_chain",
            "requires_decision",
            "at_risk",
            "high",
            "Privacy controls must be final before the control tower can scale.",
        ),
        (
            "productivity",
            "ai_service_desk",
            "informs",
            "active",
            "low",
            "Productivity rollout improves adoption of the AI desk.",
        ),
        (
            "procurement",
            "pricing",
            "enables",
            "active",
            "medium",
            "Savings and pricing governance reinforce each other.",
        ),
        (
            "offshoring",
            "procurement",
            "blocks",
            "at_risk",
            "high",
            "Shared-services model influences procurement execution.",
        ),
    ]
    for upstream_label, downstream_label, dep_type, status, severity, note in dependencies:
        upstream = initiative_ids[upstream_label]
        downstream = initiative_ids[downstream_label]
        existing = (
            client.table("initiative_dependencies")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("upstream_initiative_id", upstream)
            .eq("downstream_initiative_id", downstream)
            .eq("dependency_type", dep_type)
            .execute()
        )
        payload = {
            "tenant_id": tenant_id,
            "upstream_initiative_id": upstream,
            "downstream_initiative_id": downstream,
            "dependency_type": dep_type,
            "status": status,
            "severity": severity,
            "owner_id": owner_user_id,
            "due_date": (SCENARIO_START + timedelta(days=90)).isoformat(),
            "resolution_notes": note,
        }
        if existing.data:
            client.table("initiative_dependencies").update(payload).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            client.table("initiative_dependencies").insert(
                {"id": str(uuid4()), **payload}
            ).execute()


def _seed_benefit_ledger(client: Client, tenant_id: str, initiative_ids: dict[str, str]) -> None:
    ledger_initiatives = ["offshoring", "procurement", "ai_service_desk"]
    for label in ledger_initiatives:
        iid = initiative_ids[label]
        for month_index in range(1, 13):
            period_start = date(2027, month_index, 1)
            if month_index == 12:
                period_end = date(2027, 12, 31)
            else:
                period_end = date(2027, month_index + 1, 1) - timedelta(days=1)
            bankable_plan_amount = Decimal("10000") + Decimal(month_index * 250)
            actual_amount = bankable_plan_amount * Decimal("0.92")
            existing = (
                client.table("benefit_realization_ledger")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("initiative_id", iid)
                .eq("period_granularity", "monthly")
                .eq("period_start", period_start.isoformat())
                .execute()
            )
            payload = {
                "tenant_id": tenant_id,
                "initiative_id": iid,
                "period_granularity": "monthly",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "bankable_plan_amount": _dec(bankable_plan_amount),
                "actual_amount": _dec(actual_amount),
                "description": f"{label.replace('_', ' ').title()} realization month {month_index}",
            }
            if existing.data:
                client.table("benefit_realization_ledger").update(payload).eq(
                    "id", existing.data[0]["id"]
                ).execute()
            else:
                client.table("benefit_realization_ledger").insert(
                    {"id": str(uuid4()), **payload}
                ).execute()


def _seed_initiative_controls(
    client: Client, tenant_id: str, initiative_ids: dict[str, str]
) -> None:
    controls = {
        "pmo": ("95.00", "committed", "Portfolio governance is fully established."),
        "erp": ("84.00", "forecasted", "ERP cutover drives the remaining delivery risk."),
        "offshoring": ("72.00", "at_risk", "Savings are sensitive to transition timing."),
        "ai_service_desk": (
            "68.00",
            "partially_realized",
            "Knowledge automation adoption is ramping.",
        ),
    }
    for label, (confidence, status, explanation) in controls.items():
        iid = initiative_ids[label]
        client.table("initiatives").update(
            {
                "benefit_confidence": confidence,
                "realization_status": status,
                "variance_explanation": explanation,
            }
        ).eq("tenant_id", tenant_id).eq("id", iid).execute()
