"""
Dev seed script — Karya #30
Populates a fresh Transmuter Supabase project with realistic dev fixtures.

Usage:
    cd apps/api
    uv run python scripts/seed_dev.py

Idempotent: checks if org already exists before inserting.
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

from supabase import Client, create_client  # noqa: E402

# ── Constants ──────────────────────────────────────────────────────────────────

ORG_NAME = "Ishirock"
ORG_SLUG = "ishirock"

TODAY = date.today()


def d(days_from_today: int) -> str:
    return (TODAY + timedelta(days=days_from_today)).isoformat()


def dec(v: float) -> str:
    """Return Decimal-accurate string for monetary values."""
    return str(Decimal(str(v)))


def find_auth_user_id_by_email(c: Client, email: str) -> str | None:
    """Find an Auth user by email using the service-role admin API."""
    page = 1
    per_page = 100
    while True:
        users = c.auth.admin.list_users(page=page, per_page=per_page)
        if not users:
            return None
        for user in users:
            if getattr(user, "email", None) == email:
                return str(user.id)
        if len(users) < per_page:
            return None
        page += 1


def ensure_auth_user(c: Client, org_id: str, user: dict[str, object]) -> str:
    """Create or refresh a deterministic dev Auth user and return its user id."""
    email = str(user["email"])
    password = str(user["password"])
    role = str(user["role"])
    display_name = str(user["display_name"])

    existing_auth_id = find_auth_user_id_by_email(c, email)
    if existing_auth_id:
        c.auth.admin.update_user_by_id(existing_auth_id, {
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "tenant_id": org_id,
                "role": role,
                "display_name": display_name,
            },
        })
        return existing_auth_id

    auth_resp = c.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "tenant_id": org_id,
            "role": role,
            "display_name": display_name,
        },
    })
    return str(auth_resp.user.id)


# ── Seed Functions ─────────────────────────────────────────────────────────────


def seed_org(c: Client) -> str:
    existing = c.table("organizations").select("id").eq("slug", ORG_SLUG).execute()
    if existing.data:
        org_id = existing.data[0]["id"]
        print(f"  Org already exists: {org_id}")
        return org_id

    org_id = str(uuid4())
    c.table("organizations").insert({
        "id": org_id,
        "name": ORG_NAME,
        "slug": ORG_SLUG,
        "settings": {"nudge_overdue_days": 7, "nudge_nuclear_days": 14},
    }).execute()
    print(f"  Created org: {org_id}")
    return org_id


def seed_business_units(c: Client, org_id: str) -> dict[str, str]:
    bus = [
        {"name": "Group", "code": "GRP"},
        {"name": "Southeast Asia", "code": "SEA"},
    ]
    ids: dict[str, str] = {}
    for bu in bus:
        existing = (
            c.table("business_units")
            .select("id")
            .eq("tenant_id", org_id)
            .eq("code", bu["code"])
            .execute()
        )
        if existing.data:
            ids[bu["code"]] = existing.data[0]["id"]
            continue
        bid = str(uuid4())
        c.table("business_units").insert({"id": bid, "tenant_id": org_id, **bu}).execute()
        ids[bu["code"]] = bid
        print(f"  Created BU: {bu['name']}")
    return ids


def seed_workstreams(c: Client, org_id: str, bu_ids: dict[str, str]) -> dict[str, str]:
    wss = [
        {"name": "Group Productivity", "business_unit_id": bu_ids["GRP"]},
        {"name": "North Asia", "business_unit_id": bu_ids["SEA"]},
        {"name": "ERP (Finance)", "business_unit_id": bu_ids["GRP"]},
    ]
    ids: dict[str, str] = {}
    for ws in wss:
        existing = (
            c.table("workstreams")
            .select("id")
            .eq("tenant_id", org_id)
            .eq("name", ws["name"])
            .execute()
        )
        if existing.data:
            ids[ws["name"]] = existing.data[0]["id"]
            continue
        wid = str(uuid4())
        c.table("workstreams").insert({"id": wid, "tenant_id": org_id, **ws}).execute()
        ids[ws["name"]] = wid
        print(f"  Created workstream: {ws['name']}")
    return ids


def seed_users(c: Client, org_id: str, ws_ids: dict[str, str]) -> dict[str, str]:
    """
    Creates Supabase Auth users + platform user records.
    Returns a dict of label → user_id.
    """
    users_to_create = [
        # Transformation Office (admin)
        {
            "label": "admin1",
            "email": "admin@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Alex Chen",
            "title": "Head of Transformation",
            "role": "transformation_office",
            "workstreams": [],
        },
        {
            "label": "admin2",
            "email": "toffice@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Priya Sharma",
            "title": "Transformation Analyst",
            "role": "transformation_office",
            "workstreams": [],
        },
        # Initiative Owners
        {
            "label": "owner1",
            "email": "owner.revenue@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "James Wu",
            "title": "VP Commercial",
            "role": "initiative_owner",
            "workstreams": ["North Asia"],
        },
        {
            "label": "owner2",
            "email": "owner.ops@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Fatima Al-Rashid",
            "title": "Operations Director",
            "role": "initiative_owner",
            "workstreams": ["Group Productivity"],
        },
        {
            "label": "owner3",
            "email": "owner.erp@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Tom Nguyen",
            "title": "Finance Controller",
            "role": "initiative_owner",
            "workstreams": ["ERP (Finance)"],
        },
        {
            "label": "owner4",
            "email": "owner.hr@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Mei Lin",
            "title": "CHRO",
            "role": "initiative_owner",
            "workstreams": ["Group Productivity"],
        },
        {
            "label": "owner5",
            "email": "owner.compliance@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "David Park",
            "title": "Head of Compliance",
            "role": "initiative_owner",
            "workstreams": [],
        },
        # Workstream Leads
        {
            "label": "wslead1",
            "email": "lead.na@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Sofia Tanaka",
            "title": "North Asia Lead",
            "role": "workstream_lead",
            "workstreams": ["North Asia"],
        },
        {
            "label": "wslead2",
            "email": "lead.gp@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Carlos Rivera",
            "title": "Group Productivity Lead",
            "role": "workstream_lead",
            "workstreams": ["Group Productivity"],
        },
        {
            "label": "wslead3",
            "email": "lead.erp@ishirock.dev",
            "password": "Transmuter2026!",
            "display_name": "Nadia Kowalski",
            "title": "ERP Programme Lead",
            "role": "workstream_lead",
            "workstreams": ["ERP (Finance)"],
        },
    ]

    ids: dict[str, str] = {}

    for u in users_to_create:
        # Check if platform user already exists
        existing_platform = (
            c.table("users").select("id").eq("tenant_id", org_id).eq("email", u["email"]).execute()
        )
        if existing_platform.data:
            user_id = existing_platform.data[0]["id"]
            try:
                ensured_auth_id = ensure_auth_user(c, org_id, u)
                if ensured_auth_id != user_id:
                    print(
                        f"  WARNING: Auth/platform id mismatch for {u['email']} "
                        f"(platform={user_id}, auth={ensured_auth_id})"
                    )
            except Exception as e:
                print(f"  WARNING: Auth refresh failed for {u['email']} ({e})")
            ids[u["label"]] = user_id
            print(f"  User already exists: {u['email']} (auth refreshed)")
            continue

        try:
            user_id = ensure_auth_user(c, org_id, u)
        except Exception as e:
            print(f"  Auth ensure failed for {u['email']} ({e}) — skipping")
            continue

        # Create platform user record
        c.table("users").insert({
            "id": user_id,
            "tenant_id": org_id,
            "email": u["email"],
            "display_name": u["display_name"],
            "title": u["title"],
            "role": u["role"],
            "status": "active",
        }).execute()

        # Assign workstreams
        for ws_name in u["workstreams"]:
            if ws_name in ws_ids:
                c.table("user_workstreams").insert({
                    "tenant_id": org_id,
                    "user_id": user_id,
                    "workstream_id": ws_ids[ws_name],
                }).execute()

        ids[u["label"]] = user_id
        print(f"  Created user: {u['display_name']} <{u['email']}> ({u['role']})")

    return ids


def seed_initiatives(
    c: Client, org_id: str, ws_ids: dict[str, str], user_ids: dict[str, str]
) -> dict[str, str]:
    initiatives = [
        {
            "label": "rev_asia",
            "initiative_code": "TRN-001",
            "name": "North Asia Revenue Acceleration",
            "type": "revenue_growth",
            "impact_type": "recurring",
            "workstream_id": ws_ids["North Asia"],
            "owner_id": user_ids["owner1"],
            "priority": "high",
            "rag_status": "green",
            "stage": "in_progress",
            "country": "Group",
            "tag": "commercial",
            "summary": (
                "Accelerate revenue growth across North Asia markets through"
                " commercial excellence programs and key account management."
            ),
            "value_logic": (
                "Targeting 15% uplift in gross margin through improved pricing discipline"
                " and strategic account expansion in Japan, Korea, and China."
            ),
            "planned_start": d(-60),
            "planned_end": d(180),
            "actual_start": d(-55),
        },
        {
            "label": "cost_erp",
            "initiative_code": "TRN-002",
            "name": "ERP Consolidation & Automation",
            "type": "cost_reduction",
            "impact_type": "recurring",
            "workstream_id": ws_ids["ERP (Finance)"],
            "owner_id": user_ids["owner3"],
            "priority": "high",
            "rag_status": "amber",
            "stage": "in_progress",
            "country": "Group",
            "tag": "automation",
            "summary": (
                "Consolidate 4 legacy ERP systems into a single cloud platform,"
                " automating month-end close and AP/AR processes."
            ),
            "value_logic": (
                "Expected to reduce finance headcount equivalent by 8 FTEs and"
                " cut month-end close from 10 days to 3 days."
            ),
            "planned_start": d(-90),
            "planned_end": d(270),
            "actual_start": d(-85),
        },
        {
            "label": "prod_gp",
            "initiative_code": "TRN-003",
            "name": "Group Productivity: Remote Work Enablement",
            "type": "capability_building",
            "impact_type": "one_off",
            "workstream_id": ws_ids["Group Productivity"],
            "owner_id": user_ids["owner2"],
            "priority": "medium",
            "rag_status": "green",
            "stage": "scoping",
            "country": "Group",
            "tag": "other",
            "summary": (
                "Equip all 2,000+ employees with collaboration tools and upskilling"
                " programs to sustain hybrid work productivity."
            ),
            "value_logic": (
                "Target 10% improvement in employee NPS and 5% reduction in attrition,"
                " avoiding replacement cost of ~$8K per FTE."
            ),
            "planned_start": d(14),
            "planned_end": d(200),
        },
        {
            "label": "cost_offshoring",
            "initiative_code": "TRN-004",
            "name": "Back-Office Offshoring — Finance & HR",
            "type": "cost_reduction",
            "impact_type": "recurring",
            "workstream_id": ws_ids["Group Productivity"],
            "owner_id": user_ids["owner4"],
            "priority": "high",
            "rag_status": "red",
            "stage": "in_progress",
            "country": "Group",
            "tag": "offshoring",
            "summary": (
                "Transition transactional Finance and HR functions to a shared service centre."
            ),
            "value_logic": (
                "Labour arbitrage savings of ~$3.2M annually."
                " Break-even in month 14; full run-rate from month 18."
            ),
            "planned_start": d(-120),
            "planned_end": d(60),
            "actual_start": d(-110),
        },
        {
            "label": "compliance_data",
            "initiative_code": "TRN-005",
            "name": "Data Privacy & Regulatory Compliance Programme",
            "type": "compliance",
            "impact_type": "one_off",
            "workstream_id": ws_ids["ERP (Finance)"],
            "owner_id": user_ids["owner5"],
            "priority": "high",
            "rag_status": "amber",
            "stage": "in_progress",
            "country": "Group",
            "tag": "other",
            "summary": (
                "Achieve compliance with PDPA, GDPR, and regional data privacy regulations"
                " across all markets by Q3 2026."
            ),
            "value_logic": (
                "Avoid potential regulatory fines of up to $10M."
                " Enables expansion into regulated markets."
            ),
            "planned_start": d(-45),
            "planned_end": d(120),
            "actual_start": d(-40),
        },
    ]

    ids: dict[str, str] = {}
    for ini in initiatives:
        existing = (
            c.table("initiatives")
            .select("id")
            .eq("tenant_id", org_id)
            .eq("initiative_code", ini["initiative_code"])
            .execute()
        )
        if existing.data:
            ids[ini["label"]] = existing.data[0]["id"]
            print(f"  Initiative already exists: {ini['initiative_code']}")
            continue

        label = ini.pop("label")
        iid = str(uuid4())
        c.table("initiatives").insert({"id": iid, "tenant_id": org_id, **ini}).execute()
        ids[label] = iid
        print(f"  Created initiative: {ini['initiative_code']} — {ini['name']}")

    return ids


def seed_milestones(
    c: Client, org_id: str, init_ids: dict[str, str], user_ids: dict[str, str]
) -> None:
    milestones = [
        # TRN-001 milestones
        {"initiative": "rev_asia", "name": "Key Account Segmentation Complete", "status": "complete",
         "priority": "high", "owner": "owner1", "planned_start": d(-60), "planned_end": d(-20), "actual_end": d(-22)},
        {"initiative": "rev_asia", "name": "Pricing Framework Approved", "status": "complete",
         "priority": "high", "owner": "owner1", "planned_start": d(-30), "planned_end": d(10), "actual_end": d(8)},
        {"initiative": "rev_asia", "name": "Pilot in Japan — 3 accounts", "status": "in_progress",
         "priority": "high", "owner": "owner1", "planned_start": d(0), "planned_end": d(60)},
        {"initiative": "rev_asia", "name": "Korea & China Rollout", "status": "not_started",
         "priority": "medium", "owner": "owner1", "planned_start": d(61), "planned_end": d(150)},

        # TRN-002 milestones
        {"initiative": "cost_erp", "name": "Legacy System Audit Complete", "status": "complete",
         "priority": "high", "owner": "owner3", "planned_start": d(-90), "planned_end": d(-50), "actual_end": d(-48)},
        {"initiative": "cost_erp", "name": "Vendor Selection (Cloud ERP)", "status": "complete",
         "priority": "high", "owner": "owner3", "planned_start": d(-55), "planned_end": d(-20), "actual_end": d(-15)},
        {"initiative": "cost_erp", "name": "Data Migration Plan Approved", "status": "in_progress",
         "priority": "high", "owner": "owner3", "planned_start": d(-20), "planned_end": d(30)},
        {"initiative": "cost_erp", "name": "Parallel Run — Finance Module", "status": "not_started",
         "priority": "high", "owner": "owner3", "planned_start": d(31), "planned_end": d(120)},
        {"initiative": "cost_erp", "name": "Go-Live & Cutover", "status": "not_started",
         "priority": "high", "owner": "owner3", "planned_start": d(121), "planned_end": d(180)},

        # TRN-004 milestones (red initiative — some overdue)
        {"initiative": "cost_offshoring", "name": "Offshore Partner Selected", "status": "complete",
         "priority": "high", "owner": "owner4", "planned_start": d(-120), "planned_end": d(-90), "actual_end": d(-88)},
        {"initiative": "cost_offshoring", "name": "Knowledge Transfer — Finance", "status": "in_progress",
         "priority": "high", "owner": "owner4", "planned_start": d(-80), "planned_end": d(-20)},  # overdue
        {"initiative": "cost_offshoring", "name": "Knowledge Transfer — HR", "status": "not_started",
         "priority": "high", "owner": "owner4", "planned_start": d(-30), "planned_end": d(10)},   # overdue start

        # TRN-005 milestones
        {"initiative": "compliance_data", "name": "Data Mapping Across Markets", "status": "complete",
         "priority": "high", "owner": "owner5", "planned_start": d(-45), "planned_end": d(-10), "actual_end": d(-8)},
        {"initiative": "compliance_data", "name": "Privacy Impact Assessments", "status": "in_progress",
         "priority": "high", "owner": "owner5", "planned_start": d(-15), "planned_end": d(30)},
        {"initiative": "compliance_data", "name": "Staff Training Programme", "status": "not_started",
         "priority": "medium", "owner": "owner5", "planned_start": d(25), "planned_end": d(90)},
    ]

    for i, ms in enumerate(milestones):
        iid = init_ids.get(ms["initiative"])
        if not iid:
            continue
        existing = (
            c.table("milestones")
            .select("id")
            .eq("initiative_id", iid)
            .eq("name", ms["name"])
            .execute()
        )
        if existing.data:
            continue

        c.table("milestones").insert({
            "tenant_id": org_id,
            "initiative_id": iid,
            "name": ms["name"],
            "status": ms["status"],
            "priority": ms["priority"],
            "owner_id": user_ids.get(ms["owner"]),
            "sort_order": i,
            "planned_start": ms.get("planned_start"),
            "planned_end": ms.get("planned_end"),
            "actual_end": ms.get("actual_end"),
        }).execute()

    print(f"  Created {len(milestones)} milestones")


def seed_kpis_and_entries(
    c: Client, org_id: str, init_ids: dict[str, str]
) -> None:
    kpis = [
        # TRN-001
        {"initiative": "rev_asia", "name": "Gross Margin Uplift", "type": "gross_margin",
         "frequency": "quarterly", "unit": "USD",
         "entries": [
             {"year": 2026, "quarter": 1, "base": 800000, "high": 1200000, "actual": 920000},
             {"year": 2026, "quarter": 2, "base": 1000000, "high": 1500000},
             {"year": 2026, "quarter": 3, "base": 1200000, "high": 1800000},
         ]},
        {"initiative": "rev_asia", "name": "Key Account Revenue Growth %", "type": "operational",
         "frequency": "quarterly", "unit": "%",
         "entries": [
             {"year": 2026, "quarter": 1, "base": 10, "high": 15, "actual": 12},
             {"year": 2026, "quarter": 2, "base": 12, "high": 18},
         ]},

        # TRN-002
        {"initiative": "cost_erp", "name": "Finance FTE Reduction", "type": "operational",
         "frequency": "quarterly", "unit": "FTE",
         "entries": [
             {"year": 2026, "quarter": 3, "base": 4, "high": 6},
             {"year": 2026, "quarter": 4, "base": 8, "high": 10},
         ]},
        {"initiative": "cost_erp", "name": "Month-End Close Days", "type": "operational",
         "frequency": "quarterly", "unit": "Days",
         "entries": [
             {"year": 2026, "quarter": 3, "base": 6, "high": 4, "actual": None},
             {"year": 2026, "quarter": 4, "base": 4, "high": 3},
         ]},
    ]

    for kpi in kpis:
        iid = init_ids.get(kpi["initiative"])
        if not iid:
            continue
        existing = (
            c.table("kpis").select("id").eq("initiative_id", iid).eq("name", kpi["name"]).execute()
        )
        if existing.data:
            continue

        kid = str(uuid4())
        c.table("kpis").insert({
            "id": kid,
            "tenant_id": org_id,
            "initiative_id": iid,
            "name": kpi["name"],
            "type": kpi["type"],
            "frequency": kpi["frequency"],
            "unit": kpi["unit"],
        }).execute()

        for entry in kpi.get("entries", []):
            c.table("kpi_entries").insert({
                "tenant_id": org_id,
                "kpi_id": kid,
                "year": entry["year"],
                "quarter": entry["quarter"],
                "value_base": dec(entry["base"]),
                "value_high": dec(entry["high"]),
                "value_actual": dec(entry["actual"]) if entry.get("actual") else None,
            }).execute()

    print(f"  Created {len(kpis)} KPIs with entries")


def seed_risks(c: Client, org_id: str, init_ids: dict[str, str], user_ids: dict[str, str]) -> None:
    risks = [
        # TRN-001
        {"initiative": "rev_asia", "description": "Key account managers lack commercial negotiation skills",
         "type": "people", "impact": "high", "likelihood": "medium", "rating": "high",
         "owner": "owner1", "mitigation": "Enrol top 20 KAMs in 3-day commercial excellence bootcamp by end Q2"},
        {"initiative": "rev_asia", "description": "Competitor price undercutting in Korea market",
         "type": "financial", "impact": "medium", "likelihood": "high", "rating": "high",
         "owner": "owner1", "mitigation": "Monitor weekly via competitive intelligence dashboard"},

        # TRN-002
        {"initiative": "cost_erp", "description": "Legacy data quality issues delay migration timeline",
         "type": "technology", "impact": "high", "likelihood": "high", "rating": "high",
         "owner": "owner3", "mitigation": "Dedicated data cleansing sprint; 6-week buffer built into plan"},
        {"initiative": "cost_erp", "description": "Change resistance from finance team",
         "type": "people", "impact": "medium", "likelihood": "medium", "rating": "medium",
         "owner": "owner3", "mitigation": "Exec sponsor communications and change champion network"},

        # TRN-004 (red initiative — escalated risk)
        {"initiative": "cost_offshoring", "description": "Knowledge transfer taking 40% longer than planned",
         "type": "operational", "impact": "high", "likelihood": "high", "rating": "high",
         "owner": "owner4", "mitigation": "Extended parallel run; knowledge capture via Confluence wiki",
         "escalated": True, "status": "open"},
        {"initiative": "cost_offshoring", "description": "Offshore partner quality below SLA in first month",
         "type": "operational", "impact": "high", "likelihood": "medium", "rating": "high",
         "owner": "owner4", "mitigation": "Weekly quality review + penalty clause in contract", "escalated": True},

        # TRN-005
        {"initiative": "compliance_data", "description": "Regulatory interpretation varies across 8 markets",
         "type": "operational", "impact": "medium", "likelihood": "high", "rating": "high",
         "owner": "owner5", "mitigation": "Engage local legal counsel in each jurisdiction"},
    ]

    for risk in risks:
        iid = init_ids.get(risk["initiative"])
        if not iid:
            continue
        existing = (
            c.table("risks")
            .select("id")
            .eq("initiative_id", iid)
            .eq("description", risk["description"][:50])
            .execute()
        )
        if existing.data:
            continue
        c.table("risks").insert({
            "tenant_id": org_id,
            "initiative_id": iid,
            "description": risk["description"],
            "type": risk["type"],
            "impact": risk["impact"],
            "likelihood": risk["likelihood"],
            "rating": risk["rating"],
            "status": risk.get("status", "open"),
            "owner_id": user_ids.get(risk["owner"]),
            "mitigation": risk.get("mitigation"),
            "escalated": risk.get("escalated", False),
        }).execute()

    print(f"  Created {len(risks)} risks")


def seed_status_updates(
    c: Client, org_id: str, init_ids: dict[str, str], user_ids: dict[str, str]
) -> None:
    updates = [
        {"initiative": "rev_asia", "author": "owner1", "rag": "green", "days_ago": 5,
         "summary": "Japan pilot performing ahead of forecast. Q1 GM uplift of $920K vs $800K base case.",
         "achievements": "- Signed 2 new key accounts in Tokyo\n- Pricing framework adopted by all KAMs\n- Q1 actual GM uplift exceeded base case by 15%",
         "issues": "- Korea market entry delayed 3 weeks pending regulatory approval",
         "next_steps": "- Launch Korea pilot by end of month\n- Begin China account segmentation"},

        {"initiative": "cost_erp", "author": "owner3", "rag": "amber", "days_ago": 3,
         "summary": "Data migration plan approved but uncovered legacy data quality issues that may impact timeline.",
         "achievements": "- Vendor selection complete (Workday selected)\n- Migration plan signed off by CFO",
         "issues": "- 23% of GL data has duplicate or missing entries requiring cleansing\n- Finance team change resistance higher than expected",
         "next_steps": "- Kick off 6-week data cleansing sprint\n- Schedule change management workshops"},

        {"initiative": "cost_offshoring", "author": "owner4", "rag": "red", "days_ago": 2,
         "summary": "Programme at risk. KT taking significantly longer than planned. Timeline needs reassessment.",
         "achievements": "- Offshore partner onboarded and site operational",
         "issues": "- Finance KT 40% behind schedule due to undocumented processes\n- HR KT not started (was due to begin last week)\n- Quality metrics below SLA in week 1",
         "next_steps": "- Emergency steering committee call this week\n- Re-baseline timeline with sponsor approval"},

        {"initiative": "compliance_data", "author": "owner5", "rag": "amber", "days_ago": 7,
         "summary": "Privacy impact assessments underway. Complexity higher than scoped due to regulatory divergence across markets.",
         "achievements": "- Data mapping complete across all 8 markets\n- Local legal counsel engaged in SG, HK, MY",
         "issues": "- Thailand and Indonesia regulatory requirements differ significantly from initial assessment",
         "next_steps": "- Complete PIAs for remaining 5 markets by end of month\n- Escalate Thailand/Indonesia gaps to Steering Committee"},
    ]

    for upd in updates:
        iid = init_ids.get(upd["initiative"])
        if not iid:
            continue
        submitted_at = (TODAY - timedelta(days=upd["days_ago"])).isoformat()
        existing = (
            c.table("status_updates")
            .select("id")
            .eq("initiative_id", iid)
            .eq("is_draft", False)
            .execute()
        )
        if existing.data:
            continue
        c.table("status_updates").insert({
            "tenant_id": org_id,
            "initiative_id": iid,
            "author_id": user_ids.get(upd["author"]),
            "rag_status": upd["rag"],
            "summary": upd["summary"],
            "achievements": upd["achievements"],
            "issues": upd["issues"],
            "next_steps": upd.get("next_steps"),
            "is_draft": False,
            "submitted_at": submitted_at,
        }).execute()

    print(f"  Created {len(updates)} status updates")


def seed_gate_criteria(c: Client, org_id: str) -> None:
    """Load default G1/G2 criteria from gates.yaml into DB for this tenant."""
    import yaml  # type: ignore[import]

    gates_path = os.path.join(
        os.path.dirname(__file__), "../../../domain_packs/transmuter/gates.yaml"
    )
    with open(gates_path) as f:
        gates_config = yaml.safe_load(f)

    existing = (
        c.table("gate_criteria").select("id").eq("tenant_id", org_id).execute()
    )
    if existing.data:
        print(f"  Gate criteria already seeded ({len(existing.data)} rows)")
        return

    rows = []
    for gate_key, gate in gates_config["gates"].items():
        gate_num = int(gate_key[1])
        for i, criterion in enumerate(gate["criteria"]):
            rows.append({
                "tenant_id": org_id,
                "gate_number": gate_num,
                "criterion_id": criterion["id"],
                "label": criterion["label"],
                "guidance": criterion.get("guidance"),
                "sort_order": i,
                "is_active": criterion.get("default", True),
            })

    c.table("gate_criteria").insert(rows).execute()
    print(f"  Created {len(rows)} gate criteria (G1 + G2)")


def seed_financials(c: Client, org_id: str, init_ids: dict[str, str]) -> None:
    entries = [
        # TRN-001 — Revenue Growth
        {"initiative": "rev_asia", "year": 2026, "quarter": 1,
         "rev_base": 800000, "rev_high": 1200000, "rev_actual": 920000,
         "gm_base": 320000, "gm_high": 480000, "gm_actual": 368000},
        {"initiative": "rev_asia", "year": 2026, "quarter": 2,
         "rev_base": 1000000, "rev_high": 1500000,
         "gm_base": 400000, "gm_high": 600000},
        {"initiative": "rev_asia", "year": 2026, "quarter": 3,
         "rev_base": 1200000, "rev_high": 1800000,
         "gm_base": 480000, "gm_high": 720000},

        # TRN-002 — Cost Reduction
        {"initiative": "cost_erp", "year": 2026, "quarter": 3,
         "rev_base": 0, "rev_high": 0,
         "gm_base": 500000, "gm_high": 750000},
        {"initiative": "cost_erp", "year": 2026, "quarter": 4,
         "rev_base": 0, "rev_high": 0,
         "gm_base": 750000, "gm_high": 1100000},
    ]

    for e in entries:
        iid = init_ids.get(e["initiative"])
        if not iid:
            continue
        existing = (
            c.table("financial_entries")
            .select("id")
            .eq("initiative_id", iid)
            .eq("year", e["year"])
            .eq("quarter", e["quarter"])
            .execute()
        )
        if existing.data:
            continue
        c.table("financial_entries").insert({
            "tenant_id": org_id,
            "initiative_id": iid,
            "year": e["year"],
            "quarter": e["quarter"],
            "revenue_uplift_base": dec(e["rev_base"]),
            "revenue_uplift_high": dec(e["rev_high"]),
            "revenue_uplift_actual": dec(e["rev_actual"]) if e.get("rev_actual") else None,
            "gross_margin_base": dec(e["gm_base"]),
            "gross_margin_high": dec(e["gm_high"]),
            "gross_margin_actual": dec(e.get("gm_actual")) if e.get("gm_actual") else None,
        }).execute()

    # Cost lines for TRN-002
    cost_lines = [
        {"initiative": "cost_erp", "name": "ERP Licence & Implementation", "year": 2026, "quarter": 1,
         "amount_plan": 250000, "amount_actual": 260000, "is_recurring": False},
        {"initiative": "cost_erp", "name": "Data Migration Consultancy", "year": 2026, "quarter": 2,
         "amount_plan": 180000, "is_recurring": False},
        {"initiative": "cost_erp", "name": "Annual SaaS Licence", "year": 2026, "quarter": 3,
         "amount_plan": 120000, "is_recurring": True},
    ]
    for cl in cost_lines:
        iid = init_ids.get(cl["initiative"])
        if not iid:
            continue
        c.table("financial_cost_lines").insert({
            "tenant_id": org_id,
            "initiative_id": iid,
            "name": cl["name"],
            "year": cl["year"],
            "quarter": cl["quarter"],
            "amount_plan": dec(cl["amount_plan"]),
            "amount_actual": dec(cl["amount_actual"]) if cl.get("amount_actual") else None,
            "is_recurring": cl["is_recurring"],
        }).execute()

    print(f"  Created {len(entries)} financial entries + {len(cost_lines)} cost lines")


def seed_meetings(
    c: Client,
    org_id: str,
    ws_ids: dict[str, str],
    init_ids: dict[str, str],
    user_ids: dict[str, str],
) -> None:
    """Seed deterministic meeting data for real API and browser UI tests."""
    meetings = [
        {
            "label": "steering",
            "name": "Transformation Steering Committee",
            "workstream_id": None,
            "scope": "all",
            "recurrence": "weekly",
            "description": (
                "Weekly steering cadence for portfolio risks, value delivery, and decisions."
            ),
            "owner": "admin1",
            "attendees": ["admin1", "owner1", "owner3", "wslead1"],
            "initiatives": ["rev_asia", "cost_erp", "cost_offshoring"],
            "agenda": [
                {"text": "Portfolio value and RAG review", "initiative": None},
                {"text": "North Asia revenue acceleration blockers", "initiative": "rev_asia"},
                {"text": "ERP data migration risks", "initiative": "cost_erp"},
            ],
            "sessions": [
                {
                    "date": d(-7),
                    "status": "completed",
                    "notes": (
                        "Reviewed value delivery, ERP migration risks, and offshoring timeline."
                    ),
                    "has_transcript": True,
                    "ai_optimised": True,
                    "actions": [
                        {
                            "description": "Prepare ERP data cleansing recovery plan",
                            "assignee": "owner3",
                            "initiative": "cost_erp",
                            "priority": "high",
                            "status": "open",
                            "due_in_days": 5,
                        }
                    ],
                }
            ],
        },
        {
            "label": "north_asia",
            "name": "North Asia Workstream Review",
            "workstream_id": ws_ids.get("North Asia"),
            "scope": "workstream",
            "recurrence": "weekly",
            "description": (
                "Workstream review for North Asia growth initiatives and account execution."
            ),
            "owner": "wslead1",
            "attendees": ["wslead1", "owner1", "admin2"],
            "initiatives": ["rev_asia"],
            "agenda": [
                {"text": "Japan pilot account conversion", "initiative": "rev_asia"},
                {"text": "Korea launch dependency review", "initiative": "rev_asia"},
            ],
            "sessions": [
                {
                    "date": d(-3),
                    "status": "completed",
                    "notes": (
                        "Japan pilot remains ahead of base case. "
                        "Korea launch dependency needs legal input."
                    ),
                    "has_transcript": False,
                    "ai_optimised": False,
                    "actions": [
                        {
                            "description": "Confirm Korea launch regulatory checklist",
                            "assignee": "owner1",
                            "initiative": "rev_asia",
                            "priority": "medium",
                            "status": "in_progress",
                            "due_in_days": 7,
                        }
                    ],
                }
            ],
        },
    ]

    for meeting in meetings:
        existing = (
            c.table("meetings")
            .select("id")
            .eq("tenant_id", org_id)
            .eq("name", meeting["name"])
            .execute()
        )
        if existing.data:
            meeting_id = existing.data[0]["id"]
        else:
            inserted = c.table("meetings").insert({
                "tenant_id": org_id,
                "name": meeting["name"],
                "workstream_id": meeting["workstream_id"],
                "scope": meeting["scope"],
                "recurrence": meeting["recurrence"],
                "description": meeting["description"],
                "owner_id": user_ids.get(str(meeting["owner"])),
            }).execute()
            meeting_id = inserted.data[0]["id"]

        for attendee in meeting["attendees"]:
            user_id = user_ids.get(str(attendee))
            if not user_id:
                continue
            exists = (
                c.table("meeting_attendees")
                .select("id")
                .eq("tenant_id", org_id)
                .eq("meeting_id", meeting_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not exists.data:
                c.table("meeting_attendees").insert({
                    "tenant_id": org_id,
                    "meeting_id": meeting_id,
                    "user_id": user_id,
                }).execute()

        for initiative in meeting["initiatives"]:
            initiative_id = init_ids.get(str(initiative))
            if not initiative_id:
                continue
            exists = (
                c.table("meeting_initiatives")
                .select("id")
                .eq("tenant_id", org_id)
                .eq("meeting_id", meeting_id)
                .eq("initiative_id", initiative_id)
                .execute()
            )
            if not exists.data:
                c.table("meeting_initiatives").insert({
                    "tenant_id": org_id,
                    "meeting_id": meeting_id,
                    "initiative_id": initiative_id,
                }).execute()

        for sort_order, agenda in enumerate(meeting["agenda"], start=1):
            initiative_key = agenda.get("initiative")
            initiative_id = init_ids.get(str(initiative_key)) if initiative_key else None
            exists = (
                c.table("agenda_items")
                .select("id")
                .eq("tenant_id", org_id)
                .eq("meeting_id", meeting_id)
                .eq("text", agenda["text"])
                .execute()
            )
            if not exists.data:
                c.table("agenda_items").insert({
                    "tenant_id": org_id,
                    "meeting_id": meeting_id,
                    "initiative_id": initiative_id,
                    "text": agenda["text"],
                    "sort_order": sort_order,
                }).execute()

        for session in meeting["sessions"]:
            existing_session = (
                c.table("meeting_sessions")
                .select("id")
                .eq("tenant_id", org_id)
                .eq("meeting_id", meeting_id)
                .eq("session_date", session["date"])
                .execute()
            )
            if existing_session.data:
                session_id = existing_session.data[0]["id"]
            else:
                inserted = c.table("meeting_sessions").insert({
                    "tenant_id": org_id,
                    "meeting_id": meeting_id,
                    "session_date": session["date"],
                    "status": session["status"],
                    "has_transcript": session["has_transcript"],
                    "ai_optimised": session["ai_optimised"],
                    "notes": session["notes"],
                }).execute()
                session_id = inserted.data[0]["id"]

            for action in session["actions"]:
                exists = (
                    c.table("action_items")
                    .select("id")
                    .eq("tenant_id", org_id)
                    .eq("session_id", session_id)
                    .eq("description", action["description"])
                    .execute()
                )
                if exists.data:
                    continue
                c.table("action_items").insert({
                    "tenant_id": org_id,
                    "session_id": session_id,
                    "initiative_id": init_ids.get(str(action["initiative"])),
                    "description": action["description"],
                    "assignee_id": user_ids.get(str(action["assignee"])),
                    "priority": action["priority"],
                    "status": action["status"],
                    "due_date": d(int(action["due_in_days"])),
                }).execute()

    print(f"  Seeded {len(meetings)} meetings with agenda, sessions, and actions")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    c = create_client(url, key)
    print("\n=== Transmuter Dev Seed ===\n")

    print("1. Organization...")
    org_id = seed_org(c)

    print("\n2. Business Units...")
    bu_ids = seed_business_units(c, org_id)

    print("\n3. Workstreams...")
    ws_ids = seed_workstreams(c, org_id, bu_ids)

    print("\n4. Users...")
    user_ids = seed_users(c, org_id, ws_ids)

    if not user_ids:
        print("\nERROR: No users created — cannot seed initiatives.")
        sys.exit(1)

    print("\n5. Initiatives...")
    init_ids = seed_initiatives(c, org_id, ws_ids, user_ids)

    print("\n6. Milestones...")
    seed_milestones(c, org_id, init_ids, user_ids)

    print("\n7. KPIs & Entries...")
    seed_kpis_and_entries(c, org_id, init_ids)

    print("\n8. Risks...")
    seed_risks(c, org_id, init_ids, user_ids)

    print("\n9. Status Updates...")
    seed_status_updates(c, org_id, init_ids, user_ids)

    print("\n10. Gate Criteria...")
    seed_gate_criteria(c, org_id)

    print("\n11. Financials...")
    seed_financials(c, org_id, init_ids)

    print("\n12. Meetings...")
    seed_meetings(c, org_id, ws_ids, init_ids, user_ids)

    print("\n=== Seed complete ===")
    print(f"\n  Org ID   : {org_id}")
    print("  Admin    : admin@ishirock.dev / Transmuter2026!")
    print("  Owner    : owner.revenue@ishirock.dev / Transmuter2026!")
    print("  WS Lead  : lead.na@ishirock.dev / Transmuter2026!")
    print(f"\n  Initiatives: {len(init_ids)} seeded (TRN-001 through TRN-005)")


if __name__ == "__main__":
    main()
