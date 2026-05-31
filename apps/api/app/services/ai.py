from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from supabase import Client

from app.core.auth import CurrentUser
from app.core.observability import record_agent_run, start_agent_timer
from app.core.rbac import ROLE_TRANSFORMATION_OFFICE, can_view_all_initiatives
from app.domain.financials import CostLineCreate, FinancialEntryUpdate, FinancialGridUpdate
from app.domain.initiatives import InitiativeCreate
from app.domain.kpis import KPICreate
from app.domain.milestones import MilestoneCreate
from app.domain.risks import RiskCreate
from app.services.financial import FinancialService
from app.services.initiative import InitiativeService
from app.services.kpi import KPIService
from app.services.milestone import MilestoneService
from app.services.risk import RiskService


@dataclass(frozen=True)
class CopilotTool:
    name: str
    domain: str
    description: str
    operation: str
    permission: str
    source: str
    input_schema: dict[str, Any]
    examples: list[str]


@dataclass
class CopilotDraftAction:
    id: str
    tenant_id: str
    user_id: str
    action_type: str
    title: str
    description: str
    payload: dict[str, Any]
    created_at: datetime
    expires_at: datetime
    payload_hash: str
    plan: dict[str, Any]
    guardrails: list[dict[str, Any]]
    confirmed_at: datetime | None = None
    result: dict[str, Any] | None = None
    status: str = "draft"


@dataclass(frozen=True)
class CopilotPlan:
    intent: str
    operation: str
    tools: list[str]
    is_write: bool
    risk_level: str
    rationale: str


@dataclass
class CopilotSnapshot:
    initiatives: list[dict[str, Any]]
    users: list[dict[str, Any]]
    milestones: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    kpis: list[dict[str, Any]]
    kpi_entries: list[dict[str, Any]]
    financial_entries: list[dict[str, Any]]
    cost_lines: list[dict[str, Any]]
    status_updates: list[dict[str, Any]]
    meetings: list[dict[str, Any]]
    action_items: list[dict[str, Any]]
    milestone_dependencies: list[dict[str, Any]]
    initiative_dependencies: list[dict[str, Any]]


def _d(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: object) -> str:
    return format(_d(value).quantize(Decimal("0.0001")), "f")


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


class CopilotToolRegistry:
    """Curated, documented tools the copilot may use."""

    def __init__(self, client: Client, current_user: CurrentUser) -> None:
        self.client = client
        self.current_user = current_user
        self.tenant_id = str(current_user.tenant_id)

    def catalog(self) -> list[dict[str, Any]]:
        return [tool.__dict__ for tool in self._tools()]

    def build_snapshot(self) -> CopilotSnapshot:
        initiatives = self._query(
            "initiatives",
            (
                "id, initiative_code, name, owner_id, group_owner_id, workstream_id, "
                "type, impact_type, country, tag, priority, rag_status, stage, summary, "
                "value_logic, dependencies_text, planned_start, planned_end, actual_end, "
                "pressure_score, benefit_confidence, realization_status, archived_at"
            ),
        )
        if not can_view_all_initiatives(self.current_user.role):
            user_id = str(self.current_user.id)
            initiatives = [
                row
                for row in initiatives
                if row.get("owner_id") == user_id or row.get("group_owner_id") == user_id
            ]
        initiative_ids = {row["id"] for row in initiatives}

        users = self._query(
            "users",
            "id, display_name, role, title, department, market, status",
        )
        milestone_rows = self._filter_initiative_rows(
            self._query(
                "milestones",
                (
                    "id, initiative_id, name, description, owner_id, priority, status, "
                    "planned_start, planned_end, actual_end, pressure_score"
                ),
            ),
            initiative_ids,
        )
        risks = self._filter_initiative_rows(
            self._query(
                "risks",
                (
                    "id, initiative_id, description, type, impact, likelihood, rating, "
                    "status, owner_id, mitigation, escalated, created_at"
                ),
            ),
            initiative_ids,
        )
        kpis = self._filter_initiative_rows(
            self._query(
                "kpis",
                "id, initiative_id, name, type, category, frequency, unit",
            ),
            initiative_ids,
        )
        kpi_ids = {row["id"] for row in kpis}
        return CopilotSnapshot(
            initiatives=initiatives,
            users=users,
            milestones=milestone_rows,
            risks=risks,
            kpis=kpis,
            kpi_entries=[
                row for row in self._query("kpi_entries", "*") if row.get("kpi_id") in kpi_ids
            ],
            financial_entries=self._filter_initiative_rows(
                self._query("financial_entries", "*"),
                initiative_ids,
            ),
            cost_lines=self._filter_initiative_rows(
                self._query("financial_cost_lines", "*"),
                initiative_ids,
            ),
            status_updates=self._filter_initiative_rows(
                self._query(
                    "status_updates",
                    (
                        "id, initiative_id, author_id, rag_status, summary, achievements, "
                        "issues, next_steps, submitted_at, is_draft"
                    ),
                ),
                initiative_ids,
            ),
            meetings=self._query(
                "meetings",
                "id, name, workstream_id, scope, recurrence, description, owner_id, created_at",
            ),
            action_items=self._filter_initiative_rows(
                self._query(
                    "action_items",
                    (
                        "id, session_id, initiative_id, description, assignee_id, priority, "
                        "status, due_date, created_at"
                    ),
                ),
                initiative_ids,
                keep_unscoped=True,
            ),
            milestone_dependencies=self._query("milestone_dependencies", "*"),
            initiative_dependencies=self._filter_dependency_rows(
                self._query("initiative_dependencies", "*"),
                initiative_ids,
            ),
        )

    def _query(self, table: str, select: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.client.table(table)
                .select(select)
                .eq("tenant_id", self.tenant_id)
                .limit(1000)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Copilot data source unavailable: {table}",
            ) from exc

    @staticmethod
    def _filter_initiative_rows(
        rows: list[dict[str, Any]],
        initiative_ids: set[str],
        *,
        keep_unscoped: bool = False,
    ) -> list[dict[str, Any]]:
        return [
            row
            for row in rows
            if row.get("initiative_id") in initiative_ids
            or (keep_unscoped and row.get("initiative_id") is None)
        ]

    @staticmethod
    def _filter_dependency_rows(
        rows: list[dict[str, Any]],
        initiative_ids: set[str],
    ) -> list[dict[str, Any]]:
        return [
            row
            for row in rows
            if row.get("upstream_initiative_id") in initiative_ids
            or row.get("downstream_initiative_id") in initiative_ids
        ]

    @staticmethod
    def _tools() -> list[CopilotTool]:
        return [
            CopilotTool(
                "portfolio_snapshot",
                "portfolio",
                "Read tenant-scoped initiatives, health, status, ownership, and pressure context.",
                "read",
                "viewer",
                "initiatives, dashboard",
                {"query": "string", "filters": "optional portfolio filters"},
                ["Summarize the portfolio", "Which initiatives are red?"],
            ),
            CopilotTool(
                "financial_rollup",
                "financials",
                "Read and aggregate initiative financial entries and cost lines with Decimal math.",
                "read",
                "viewer",
                "financial_entries, financial_cost_lines, portfolio financial APIs",
                {"initiative": "optional string", "year": "optional integer"},
                ["What is the net value for HK CoSec?", "Show portfolio financial totals"],
            ),
            CopilotTool(
                "milestone_lookup",
                "milestones",
                "Read portfolio milestones, due dates, owners, status, pressure, and dependencies.",
                "read",
                "viewer",
                "milestones, milestone_dependencies",
                {"initiative": "optional string", "owner": "optional string", "date_range": "optional"},
                ["What milestones are due this month?", "Pending milestones for Alex Chen"],
            ),
            CopilotTool(
                "risk_lookup",
                "risks",
                "Read risk register, ratings, mitigations, escalations, and affected initiatives.",
                "read",
                "viewer",
                "risks",
                {"initiative": "optional string", "rating": "optional high|medium|low"},
                ["Show high risks", "Risks for ERP rollout"],
            ),
            CopilotTool(
                "kpi_lookup",
                "kpis",
                "Read KPIs and latest KPI entries across initiatives.",
                "read",
                "viewer",
                "kpis, kpi_entries",
                {"initiative": "optional string", "health": "optional"},
                ["Which KPIs are missing actuals?", "KPI status for Initiative ALQ-001"],
            ),
            CopilotTool(
                "meeting_action_lookup",
                "meetings",
                "Read meetings, agenda-related action items, owners, due dates, and open workload.",
                "read",
                "viewer",
                "meetings, action_items",
                {"owner": "optional string", "status": "optional"},
                ["Open action items", "What meetings are active?"],
            ),
            CopilotTool(
                "executive_reports",
                "reports",
                "Return executive report summaries and links to existing report/export endpoints.",
                "read",
                "viewer",
                "executive control report APIs",
                {"report": "owner-cockpit|executive-control-tower|investor-summary"},
                ["Generate an executive report", "Investor summary for 2026"],
            ),
            CopilotTool(
                "draft_initiative",
                "initiatives",
                "Draft a new initiative for explicit user confirmation before writing.",
                "write",
                "transformation_office",
                "InitiativeService.create_initiative",
                {"name": "string", "priority": "low|medium|high", "summary": "optional string"},
                ["Create an initiative called Vendor Consolidation"],
            ),
            CopilotTool(
                "draft_milestone",
                "milestones",
                "Draft a milestone on an existing initiative for confirmation.",
                "write",
                "transformation_office",
                "MilestoneService.create_milestone",
                {"initiative_id": "uuid", "name": "string", "planned_end": "optional date"},
                ["Add milestone Contract signed to HK CoSec by 2026-06-30"],
            ),
            CopilotTool(
                "draft_risk",
                "risks",
                "Draft an initiative risk for confirmation.",
                "write",
                "transformation_office",
                "RiskService.create_risk",
                {"initiative_id": "uuid", "description": "string", "impact": "optional"},
                ["Add a high risk to ERP rollout about adoption readiness"],
            ),
            CopilotTool(
                "draft_kpi",
                "kpis",
                "Draft a KPI on an initiative for confirmation.",
                "write",
                "transformation_office",
                "KPIService.create_kpi",
                {"initiative_id": "uuid", "name": "string", "unit": "optional string"},
                ["Add KPI cycle time to Onboarding Automation"],
            ),
            CopilotTool(
                "draft_financial_entry",
                "financials",
                "Draft a financial grid update or cost line for confirmation.",
                "write",
                "transformation_office",
                "FinancialService.update_financial_grid/create_cost_line",
                {"initiative_id": "uuid", "year": "integer", "amounts": "Decimal strings"},
                ["Add 50000 GM uplift base in 2026 Q2 to HK CoSec"],
            ),
        ]


class AIService:
    def __init__(
        self,
        client: Client,
        current_user: CurrentUser,
        ledger_client: Client | None = None,
    ):
        self.client = client
        self.ledger_client = ledger_client or client
        self.current_user = current_user
        self.tenant_id = str(current_user.tenant_id)
        self.user_id = str(current_user.id)
        self.registry = CopilotToolRegistry(client, current_user)

    def tools(self) -> list[dict[str, Any]]:
        return self.registry.catalog()

    async def chat(
        self,
        query: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ground every copilot response in the curated tenant-scoped tool registry."""
        del conversation_id
        started_at = start_agent_timer()
        snapshot = self.registry.build_snapshot()
        plan = self._plan_query(query, snapshot, context or {})

        if plan.is_write:
            response = self._draft_action(query, snapshot, context or {}, plan)
        else:
            response = self._answer_query(query, snapshot, context or {}, plan)

        record_agent_run("portfolio_chat", self.tenant_id, "deterministic_tools", started_at)
        return response

    def confirm_action(self, action_id: str) -> dict[str, Any]:
        draft = self._load_action(action_id)
        if not draft or draft.tenant_id != self.tenant_id or draft.user_id != self.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
        if draft.status != "draft":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Action already used")
        if draft.expires_at < datetime.now(UTC):
            self._update_action_status(draft, "expired")
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Action expired")
        if self.current_user.role != ROLE_TRANSFORMATION_OFFICE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        if self._payload_hash(draft.action_type, draft.payload) != draft.payload_hash:
            self._update_action_status(draft, "failed", {"reason": "payload_hash_mismatch"})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Action integrity check failed",
            )
        guardrails = self._validate_action_payload(draft.action_type, draft.payload)
        if any(not item["passed"] for item in guardrails):
            self._update_action_status(
                draft,
                "failed",
                {"reason": "guardrail_revalidation_failed", "guardrails": guardrails},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action guardrail check failed",
            )

        result: Any
        action_type = draft.action_type
        payload = draft.payload
        if action_type == "create_initiative":
            result = InitiativeService(self.client, self.current_user.tenant_id, self.current_user.id).create_initiative(
                InitiativeCreate(**payload),
                self.current_user.id,
            )
        elif action_type == "create_milestone":
            result = MilestoneService(self.client, self.current_user.tenant_id, self.current_user.id).create_milestone(
                payload["initiative_id"],
                MilestoneCreate(**payload["data"]),
            )
        elif action_type == "create_risk":
            result = RiskService(self.client, self.current_user.tenant_id, self.current_user.id).create_risk(
                payload["initiative_id"],
                RiskCreate(**payload["data"]),
            )
        elif action_type == "create_kpi":
            result = KPIService(self.client, self.current_user.tenant_id, self.current_user.id).create_kpi(
                payload["initiative_id"],
                KPICreate(**payload["data"]),
            )
        elif action_type == "create_cost_line":
            result = FinancialService(self.client, self.current_user.tenant_id).create_cost_line(
                payload["initiative_id"],
                CostLineCreate(**payload["data"]),
            )
        elif action_type == "update_financial_entry":
            entry = FinancialEntryUpdate(**payload["data"])
            result = FinancialService(self.client, self.current_user.tenant_id).update_financial_grid(
                payload["initiative_id"],
                FinancialGridUpdate(entries=[entry]),
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action")

        draft.status = "confirmed"
        draft.confirmed_at = datetime.now(UTC)
        result_payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        draft.result = result_payload
        self._update_action_status(draft, "confirmed", result_payload)
        return {
            "action_id": action_id,
            "status": "confirmed",
            "message": f"Executed {draft.title}.",
            "result": result_payload,
        }

    def _answer_query(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
        plan: CopilotPlan,
    ) -> dict[str, Any]:
        query_l = query.lower()
        source_types: list[str] = []
        response: str
        confidence = 0.82

        if "tool" in query_l or "what can you do" in query_l or "knowledge" in query_l:
            source_types = ["ai_tools"]
            response = self._tools_answer()
            confidence = 0.98
        elif "report" in query_l or "brief" in query_l or "executive" in query_l:
            source_types = ["reports", "initiatives", "financials", "risks"]
            response = self._report_answer(snapshot)
        elif "financial" in query_l or "value" in query_l or "cost" in query_l or "gm " in query_l:
            source_types = ["financials", "initiatives"]
            response = self._financial_answer(query, snapshot, context)
        elif "milestone" in query_l or "due" in query_l or "deadline" in query_l:
            source_types = ["milestones", "initiatives", "users"]
            response = self._milestone_answer(query, snapshot, context)
        elif "risk" in query_l or "at-risk" in query_l or "at risk" in query_l or "escalat" in query_l:
            source_types = ["risks", "initiatives"]
            response = self._risk_answer(query, snapshot, context)
        elif "kpi" in query_l or "metric" in query_l:
            source_types = ["kpis", "initiatives"]
            response = self._kpi_answer(query, snapshot, context)
        elif "meeting" in query_l or "action" in query_l or "owner" in query_l or "user" in query_l:
            source_types = ["meetings", "action_items", "users", "initiatives"]
            response = self._people_meeting_answer(query, snapshot, context)
        elif self._find_initiative(query, snapshot, context):
            source_types = ["initiatives", "milestones", "risks", "financials", "action_items"]
            response = self._initiative_overview_answer(query, snapshot, context)
        else:
            source_types = ["initiatives", "milestones", "risks", "kpis", "financials"]
            response = self._portfolio_answer(snapshot)

        return {
            "response": response,
            "sources": self._sources(source_types, snapshot, response),
            "tool_trace": self._trace(source_types, snapshot, plan),
            "confidence": confidence,
            "proposed_actions": [],
            "plan": plan.__dict__,
        }

    def _draft_action(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
        plan: CopilotPlan,
    ) -> dict[str, Any]:
        query_l = query.lower()
        if self.current_user.role != ROLE_TRANSFORMATION_OFFICE:
            return {
                "response": "I can draft that, but your role does not allow portfolio writes. Ask a transformation office user to perform this action.",
                "sources": self._sources(["ai_tools"], snapshot, "Role does not allow writes."),
                "tool_trace": self._trace(["ai_tools"], snapshot, plan, rejected="role_guardrail"),
                "confidence": 0.93,
                "proposed_actions": [],
                "plan": plan.__dict__,
            }

        draft: CopilotDraftAction | None = None
        if "initiative" in query_l and ("create" in query_l or "new" in query_l):
            name = self._extract_name(query, ("called", "named", "initiative"))
            payload = {
                "name": name or "New AI drafted initiative",
                "priority": self._extract_priority(query_l),
                "summary": self._extract_after(query, "summary") or "Drafted by Transmuter Copilot.",
            }
            draft = self._store_action(
                "create_initiative",
                f"Create initiative: {payload['name']}",
                "Create a new scoping-stage initiative after confirmation.",
                payload,
                plan,
            )
        else:
            initiative = self._find_write_target_initiative(query, snapshot, context)
            if not initiative:
                return self._missing_initiative_response(snapshot, plan)
            if "milestone" in query_l:
                name = self._extract_name(query, ("called", "named", "milestone", "add"))
                payload = {
                    "initiative_id": initiative["id"],
                    "data": {
                        "name": name or "AI drafted milestone",
                        "priority": self._extract_priority(query_l),
                        "planned_end": self._extract_date(query),
                    },
                }
                draft = self._store_action(
                    "create_milestone",
                    f"Add milestone to {initiative['initiative_code']}",
                    f"Create milestone '{payload['data']['name']}' on {initiative['name']}.",
                    payload,
                    plan,
                )
            elif "risk" in query_l:
                description = self._extract_after(query, "risk") or self._extract_after(query, "about")
                payload = {
                    "initiative_id": initiative["id"],
                    "data": {
                        "description": description or "AI drafted risk",
                        "type": self._extract_risk_type(query_l),
                        "impact": self._extract_level(query_l) or "medium",
                        "likelihood": "medium",
                        "status": "open",
                        "mitigation": self._extract_after(query, "mitigation"),
                    },
                }
                draft = self._store_action(
                    "create_risk",
                    f"Add risk to {initiative['initiative_code']}",
                    f"Create a risk on {initiative['name']} after confirmation.",
                    payload,
                    plan,
                )
            elif "kpi" in query_l or "metric" in query_l:
                name = self._extract_name(query, ("called", "named", "kpi", "metric"))
                payload = {
                    "initiative_id": initiative["id"],
                    "data": {
                        "name": name or "AI drafted KPI",
                        "type": "custom",
                        "frequency": "quarterly",
                        "unit": self._extract_unit(query),
                    },
                }
                draft = self._store_action(
                    "create_kpi",
                    f"Add KPI to {initiative['initiative_code']}",
                    f"Create KPI '{payload['data']['name']}' on {initiative['name']}.",
                    payload,
                    plan,
                )
            elif "cost" in query_l or "cost line" in query_l:
                amount = self._extract_amount(query)
                payload = {
                    "initiative_id": initiative["id"],
                    "data": {
                        "name": self._extract_name(query, ("called", "named", "cost", "line")) or "AI drafted cost line",
                        "category_key": "other",
                        "year": self._extract_year(query) or date.today().year,
                        "quarter": self._extract_quarter(query),
                        "amount_plan": _money(amount),
                        "is_recurring": "recurring" in query_l,
                    },
                }
                draft = self._store_action(
                    "create_cost_line",
                    f"Add cost line to {initiative['initiative_code']}",
                    f"Create a cost line on {initiative['name']}.",
                    payload,
                    plan,
                )
            elif "financial" in query_l or "gm" in query_l or "uplift" in query_l or "value" in query_l:
                amount = self._extract_amount(query)
                payload = {
                    "initiative_id": initiative["id"],
                    "data": {
                        "year": self._extract_year(query) or date.today().year,
                        "quarter": self._extract_quarter(query),
                        "gm_uplift_base": _money(amount),
                        "gm_uplift_high": _money(amount),
                    },
                }
                draft = self._store_action(
                    "update_financial_entry",
                    f"Update financials for {initiative['initiative_code']}",
                    f"Upsert GM uplift values on {initiative['name']}.",
                    payload,
                    plan,
                )

        if not draft:
            return {
                "response": "I can help draft initiatives, milestones, risks, KPIs, cost lines, and financial entries. Please include the target initiative and the item to add.",
                "sources": self._sources(["ai_tools"], snapshot, "Unsupported draft request."),
                "tool_trace": self._trace(["ai_tools"], snapshot, plan, rejected="unsupported_action_guardrail"),
                "confidence": 0.72,
                "proposed_actions": [],
                "plan": plan.__dict__,
            }
        return {
            "response": f"I drafted this action and will only execute it after confirmation: {draft.title}.",
            "sources": self._sources(["ai_tools", "initiatives"], snapshot, draft.description),
            "tool_trace": self._trace(["ai_tools", "initiatives"], snapshot, plan),
            "confidence": 0.9,
            "proposed_actions": [self._action_payload(draft)],
            "plan": plan.__dict__,
        }

    def _portfolio_answer(self, snapshot: CopilotSnapshot) -> str:
        active = [row for row in snapshot.initiatives if not row.get("archived_at")]
        red = [row for row in active if row.get("rag_status") == "red"]
        amber = [row for row in active if row.get("rag_status") == "amber"]
        stages = self._counts(active, "stage")
        open_risks = [row for row in snapshot.risks if row.get("status") == "open"]
        open_actions = [row for row in snapshot.action_items if row.get("status") in {"open", "in_progress"}]
        return (
            f"The portfolio has {len(active)} active initiatives: {len(red)} red, {len(amber)} amber, "
            f"and {len(active) - len(red) - len(amber)} green. Stage mix: {self._count_text(stages)}. "
            f"I found {len(snapshot.milestones)} milestones, {len(open_risks)} open risks, "
            f"{len(snapshot.kpis)} KPIs, and {len(open_actions)} open action items."
        )

    def _risk_answer(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> str:
        initiative = self._find_initiative(query, snapshot, context)
        risks = snapshot.risks
        if initiative:
            risks = [row for row in risks if row.get("initiative_id") == initiative["id"]]
        if "high" in query.lower():
            risks = [row for row in risks if row.get("rating") == "high" or row.get("impact") == "high"]
        open_risks = [row for row in risks if row.get("status") == "open"]
        escalated = [row for row in open_risks if row.get("escalated")]
        top = sorted(open_risks, key=lambda r: (r.get("rating") != "high", r.get("created_at") or ""))[:5]
        lines = [
            f"{self._initiative_label(row.get('initiative_id'), snapshot)}: {row.get('description')} ({row.get('rating') or row.get('impact') or 'unrated'})"
            for row in top
        ]
        scope = f" for {initiative['initiative_code']}" if initiative else ""
        return (
            f"I found {len(open_risks)} open risks{scope}, including {len(escalated)} escalated. "
            + ("Top risks: " + "; ".join(lines) + "." if lines else "No matching open risks found.")
        )

    def _milestone_answer(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> str:
        query_l = query.lower()
        initiative = self._find_initiative(query, snapshot, context)
        owner = self._find_user(query, snapshot)
        milestones = snapshot.milestones
        if initiative:
            milestones = [row for row in milestones if row.get("initiative_id") == initiative["id"]]
        if owner:
            milestones = [row for row in milestones if row.get("owner_id") == owner["id"]]
        if "pending" in query_l or "open" in query_l or "incomplete" in query_l:
            milestones = [row for row in milestones if row.get("status") != "complete"]
        if "this week" in query_l:
            start = date.today()
            end = start + timedelta(days=7)
            milestones = [row for row in milestones if self._date_between(row.get("planned_end"), start, end)]
        elif "this month" in query_l or "month" in query_l:
            today = date.today()
            milestones = [
                row
                for row in milestones
                if self._date_in_month(row.get("planned_end"), today.year, today.month)
            ]
        if "count" in query_l or "how many" in query_l:
            return f"There are {len(milestones)} matching milestones."
        lines = [
            f"{row.get('name')} ({self._initiative_label(row.get('initiative_id'), snapshot)}, due {row.get('planned_end') or 'not set'}, {row.get('status')})"
            for row in sorted(milestones, key=lambda r: r.get("planned_end") or "9999-12-31")[:8]
        ]
        return (
            f"I found {len(milestones)} matching milestones. "
            + ("Key items: " + "; ".join(lines) + "." if lines else "No matching milestone records found.")
        )

    def _financial_answer(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> str:
        initiative = self._find_initiative(query, snapshot, context)
        initiative_ids = {initiative["id"]} if initiative else {row["id"] for row in snapshot.initiatives}
        entries = [row for row in snapshot.financial_entries if row.get("initiative_id") in initiative_ids]
        costs = [row for row in snapshot.cost_lines if row.get("initiative_id") in initiative_ids]
        year = self._extract_year(query)
        if year:
            entries = [row for row in entries if row.get("year") == year]
            costs = [row for row in costs if row.get("year") == year]

        gm_base = sum(_d(row.get("gm_uplift_base")) for row in entries)
        gm_actual = sum(_d(row.get("gm_uplift_actual")) for row in entries)
        recurring_cost = sum(_d(row.get("amount_plan")) for row in costs if row.get("is_recurring"))
        one_off_cost = sum(_d(row.get("amount_plan")) for row in costs if not row.get("is_recurring"))
        net_value = gm_base - recurring_cost
        scope = initiative["initiative_code"] if initiative else "the portfolio"
        year_text = f" in {year}" if year else ""
        return (
            f"For {scope}{year_text}, planned GM uplift is {_money(gm_base)}, actual GM uplift is {_money(gm_actual)}, "
            f"recurring planned costs are {_money(recurring_cost)}, one-off planned costs are {_money(one_off_cost)}, "
            f"and planned net value is {_money(net_value)}."
        )

    def _kpi_answer(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> str:
        initiative = self._find_initiative(query, snapshot, context)
        kpis = snapshot.kpis
        if initiative:
            kpis = [row for row in kpis if row.get("initiative_id") == initiative["id"]]
        entries_by_kpi: dict[str, list[dict[str, Any]]] = {}
        for entry in snapshot.kpi_entries:
            entries_by_kpi.setdefault(entry.get("kpi_id"), []).append(entry)
        no_actuals = [row for row in kpis if not any(e.get("value_actual") is not None for e in entries_by_kpi.get(row["id"], []))]
        lines = [
            f"{row.get('name')} ({self._initiative_label(row.get('initiative_id'), snapshot)}, {row.get('frequency')}, {row.get('unit') or 'unitless'})"
            for row in kpis[:6]
        ]
        return (
            f"I found {len(kpis)} KPIs"
            + (f" for {initiative['initiative_code']}" if initiative else "")
            + f"; {len(no_actuals)} have no actual values recorded. "
            + ("Examples: " + "; ".join(lines) + "." if lines else "No KPI records matched.")
        )

    def _people_meeting_answer(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> str:
        del context
        owner = self._find_user(query, snapshot)
        actions = snapshot.action_items
        milestones = snapshot.milestones
        if owner:
            actions = [row for row in actions if row.get("assignee_id") == owner["id"]]
            milestones = [row for row in milestones if row.get("owner_id") == owner["id"]]
        open_actions = [row for row in actions if row.get("status") in {"open", "in_progress"}]
        overdue_actions = [
            row for row in open_actions if self._parse_date(row.get("due_date")) and self._parse_date(row.get("due_date")) < date.today()
        ]
        open_milestones = [row for row in milestones if row.get("status") != "complete"]
        name = owner.get("display_name") if owner else "the portfolio"
        return (
            f"For {name}, I found {len(open_actions)} open action items, {len(overdue_actions)} overdue action items, "
            f"{len(open_milestones)} open milestones, and {len(snapshot.meetings)} meeting series in the tenant."
        )

    def _initiative_overview_answer(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> str:
        initiative = self._find_initiative(query, snapshot, context)
        if not initiative:
            return self._portfolio_answer(snapshot)
        open_milestones = [
            row for row in snapshot.milestones if row.get("initiative_id") == initiative["id"] and row.get("status") != "complete"
        ]
        open_risks = [
            row for row in snapshot.risks if row.get("initiative_id") == initiative["id"] and row.get("status") == "open"
        ]
        open_actions = [
            row for row in snapshot.action_items if row.get("initiative_id") == initiative["id"] and row.get("status") in {"open", "in_progress"}
        ]
        owner = self._user_label(initiative.get("owner_id"), snapshot)
        return (
            f"{initiative['initiative_code']} - {initiative['name']} is {initiative.get('stage')} with {initiative.get('rag_status')} RAG. "
            f"Owner: {owner}. Priority: {initiative.get('priority')}. "
            f"It has {len(open_milestones)} open milestones, {len(open_risks)} open risks, and {len(open_actions)} open action items. "
            f"Summary: {initiative.get('summary') or 'No summary recorded.'}"
        )

    def _report_answer(self, snapshot: CopilotSnapshot) -> str:
        base = self._portfolio_answer(snapshot)
        return (
            f"{base} Available report links: /reports/executive-control-tower?target_year={date.today().year}, "
            f"/reports/investor-summary?target_year={date.today().year}, "
            f"and /reports/owner-cockpit?target_year={date.today().year}. "
            "I can summarize them in chat and route you to existing exports; PDF/deck generation is not enabled in this v1."
        )

    def _tools_answer(self) -> str:
        domains = sorted({tool["domain"] for tool in self.tools()})
        return (
            "The copilot knowledge base has curated tools for "
            + ", ".join(domains)
            + ". Read tools answer from tenant-scoped data; write tools create a draft action that requires confirmation."
        )

    def _plan_query(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> CopilotPlan:
        query_l = query.lower()
        is_write = self._looks_like_write(query_l)
        if is_write:
            intent = "draft_write"
            operation = "draft_confirm"
            risk_level = "high"
            tools = ["ai_tools"]
            if "initiative" in query_l and ("create" in query_l or "new" in query_l):
                tools.append("draft_initiative")
            elif self._find_write_target_initiative(query, snapshot, context):
                if "milestone" in query_l:
                    tools.append("draft_milestone")
                elif "risk" in query_l:
                    tools.append("draft_risk")
                elif "kpi" in query_l or "metric" in query_l:
                    tools.append("draft_kpi")
                elif (
                    "cost" in query_l
                    or "financial" in query_l
                    or "gm" in query_l
                    or "uplift" in query_l
                ):
                    tools.append("draft_financial_entry")
        elif "report" in query_l or "brief" in query_l or "executive" in query_l:
            intent = "report"
            operation = "read"
            risk_level = "medium"
            tools = ["executive_reports", "portfolio_snapshot", "financial_rollup", "risk_lookup"]
        elif "financial" in query_l or "value" in query_l or "cost" in query_l or "gm " in query_l:
            intent = "answer"
            operation = "read"
            risk_level = "medium"
            tools = ["financial_rollup", "portfolio_snapshot"]
        elif "milestone" in query_l or "due" in query_l or "deadline" in query_l:
            intent = "answer"
            operation = "read"
            risk_level = "low"
            tools = ["milestone_lookup", "portfolio_snapshot"]
        elif "risk" in query_l or "at-risk" in query_l or "at risk" in query_l or "escalat" in query_l:
            intent = "answer"
            operation = "read"
            risk_level = "medium"
            tools = ["risk_lookup", "portfolio_snapshot"]
        elif "kpi" in query_l or "metric" in query_l:
            intent = "answer"
            operation = "read"
            risk_level = "low"
            tools = ["kpi_lookup", "portfolio_snapshot"]
        elif "meeting" in query_l or "action" in query_l or "owner" in query_l or "user" in query_l:
            intent = "answer"
            operation = "read"
            risk_level = "medium"
            tools = ["meeting_action_lookup", "portfolio_snapshot"]
        else:
            intent = "answer"
            operation = "read"
            risk_level = "low"
            tools = ["portfolio_snapshot"]
        return CopilotPlan(
            intent=intent,
            operation=operation,
            tools=tools,
            is_write=is_write,
            risk_level=risk_level,
            rationale="Keyword and context planner selected the minimum curated tool set.",
        )

    def _sources(
        self,
        source_types: list[str],
        snapshot: CopilotSnapshot,
        claim: str,
    ) -> list[dict[str, Any]]:
        labels = {
            "ai_tools": "AI tool knowledge base",
            "initiatives": "Portfolio initiatives",
            "milestones": "Milestones",
            "risks": "Risk register",
            "kpis": "KPIs",
            "financials": "Financial entries and cost lines",
            "users": "Tenant people directory",
            "meetings": "Meetings",
            "action_items": "Action items",
            "reports": "Executive reports",
        }
        sample_id = snapshot.initiatives[0]["id"] if snapshot.initiatives else None
        return [
            {
                "label": labels.get(source_type, source_type.replace("_", " ").title()),
                "source_type": source_type,
                "record_id": sample_id if source_type == "initiatives" else None,
                "url": self._source_url(source_type),
                "claim": claim[:500],
            }
            for source_type in dict.fromkeys(source_types)
        ]

    def _trace(
        self,
        source_types: list[str],
        snapshot: CopilotSnapshot,
        plan: CopilotPlan,
        *,
        rejected: str | None = None,
    ) -> list[dict[str, str]]:
        counts = {
            "initiatives": len(snapshot.initiatives),
            "milestones": len(snapshot.milestones),
            "risks": len(snapshot.risks),
            "kpis": len(snapshot.kpis),
            "financials": len(snapshot.financial_entries) + len(snapshot.cost_lines),
            "users": len(snapshot.users),
            "meetings": len(snapshot.meetings),
            "action_items": len(snapshot.action_items),
            "reports": 3,
            "ai_tools": len(self.tools()),
        }
        return [
            {
                "tool_name": source_type,
                "status": "rejected" if rejected else "completed",
                "summary": (
                    f"{rejected} blocked execution."
                    if rejected
                    else f"{plan.intent}/{plan.operation}: read {counts.get(source_type, 0)} tenant-scoped records."
                ),
                "source_type": source_type,
            }
            for source_type in dict.fromkeys(source_types)
        ]

    def _store_action(
        self,
        action_type: str,
        title: str,
        description: str,
        payload: dict[str, Any],
        plan: CopilotPlan,
    ) -> CopilotDraftAction:
        payload_hash = self._payload_hash(action_type, payload)
        guardrails = self._validate_action_payload(action_type, payload)
        if any(not item["passed"] for item in guardrails):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Draft action failed guardrail validation",
            )
        draft = CopilotDraftAction(
            id=str(uuid4()),
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action_type=action_type,
            title=title,
            description=description,
            payload=payload,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            payload_hash=payload_hash,
            plan=plan.__dict__,
            guardrails=guardrails,
        )
        self._persist_action(draft)
        return draft

    @staticmethod
    def _action_payload(draft: CopilotDraftAction) -> dict[str, Any]:
        return {
            "id": draft.id,
            "action_type": draft.action_type,
            "title": draft.title,
            "description": draft.description,
            "payload": draft.payload,
            "requires_confirmation": True,
            "status": draft.status,
            "expires_at": draft.expires_at.isoformat(),
            "payload_hash": draft.payload_hash,
            "plan": draft.plan,
            "guardrails": draft.guardrails,
        }

    @staticmethod
    def _payload_hash(action_type: str, payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            {
                "action_type": action_type,
                "payload": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _validate_action_payload(
        self,
        action_type: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        checks = [
            {
                "name": "tenant_scope",
                "passed": True,
                "message": "Action is scoped to the authenticated tenant.",
            },
            {
                "name": "requires_confirmation",
                "passed": True,
                "message": "Action remains draft until POST /ai/actions/{id}/confirm.",
            },
            {
                "name": "role_required",
                "passed": self.current_user.role == ROLE_TRANSFORMATION_OFFICE,
                "message": "Transformation office role is required for confirmed writes.",
            },
        ]
        if action_type != "create_initiative":
            checks.append(
                {
                    "name": "target_initiative",
                    "passed": bool(payload.get("initiative_id")),
                    "message": "Write action has a target initiative id.",
                }
            )
        if action_type in {"create_cost_line", "update_financial_entry"}:
            data = payload.get("data") or {}
            amount_fields = [
                key
                for key in (
                    "amount_plan",
                    "amount_actual",
                    "gm_uplift_base",
                    "gm_uplift_high",
                    "gm_uplift_actual",
                )
                if key in data
            ]
            checks.append(
                {
                    "name": "decimal_money",
                    "passed": all(str(_d(data.get(key))) == str(_d(str(data.get(key)))) for key in amount_fields),
                    "message": "Financial amounts are Decimal-compatible strings.",
                }
            )
        return checks

    def _persist_action(self, draft: CopilotDraftAction) -> None:
        row = {
            "id": draft.id,
            "tenant_id": draft.tenant_id,
            "user_id": draft.user_id,
            "action_type": draft.action_type,
            "title": draft.title,
            "description": draft.description,
            "payload": draft.payload,
            "payload_hash": draft.payload_hash,
            "plan": draft.plan,
            "guardrails": draft.guardrails,
            "status": draft.status,
            "expires_at": draft.expires_at.isoformat(),
            "created_at": draft.created_at.isoformat(),
        }
        try:
            self.ledger_client.table("ai_copilot_actions").insert(row).execute()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Action ledger is unavailable",
            ) from exc

    def _load_action(self, action_id: str) -> CopilotDraftAction | None:
        try:
            result = (
                self.ledger_client.table("ai_copilot_actions")
                .select("*")
                .eq("tenant_id", self.tenant_id)
                .eq("user_id", self.user_id)
                .eq("id", action_id)
                .maybe_single()
                .execute()
            )
            if result and result.data:
                row = result.data
                return CopilotDraftAction(
                    id=row["id"],
                    tenant_id=row["tenant_id"],
                    user_id=row["user_id"],
                    action_type=row["action_type"],
                    title=row["title"],
                    description=row["description"],
                    payload=row["payload"],
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                    expires_at=datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")),
                    payload_hash=row["payload_hash"],
                    plan=row.get("plan") or {},
                    guardrails=row.get("guardrails") or [],
                    confirmed_at=self._parse_datetime(row.get("confirmed_at")),
                    result=row.get("result"),
                    status=row["status"],
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Action ledger is unavailable",
            ) from exc
        return None

    def _update_action_status(
        self,
        draft: CopilotDraftAction,
        new_status: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        draft.status = new_status
        patch: dict[str, Any] = {
            "status": new_status,
            "confirmed_at": draft.confirmed_at.isoformat() if draft.confirmed_at else None,
            "result": result,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        try:
            (
                self.ledger_client.table("ai_copilot_actions")
                .update(patch)
                .eq("tenant_id", self.tenant_id)
                .eq("user_id", self.user_id)
                .eq("id", draft.id)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Action ledger update failed",
            ) from exc

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _looks_like_write(query_l: str) -> bool:
        write_verbs = ("create", "add", "update", "set", "change", "draft", "new")
        write_nouns = ("initiative", "milestone", "risk", "kpi", "metric", "financial", "cost", "uplift")
        return any(verb in query_l for verb in write_verbs) and any(noun in query_l for noun in write_nouns)

    def _find_initiative(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        context_id = context.get("initiative_id") or context.get("entity_id")
        if context_id:
            match = next((row for row in snapshot.initiatives if row["id"] == context_id), None)
            if match:
                return match
        q = _norm(query)
        best: tuple[int, dict[str, Any]] | None = None
        for row in snapshot.initiatives:
            hay = _norm(f"{row.get('initiative_code')} {row.get('name')} {row.get('summary')}")
            score = 0
            for token in q.split():
                if len(token) > 2 and token in hay:
                    score += 1
            if row.get("initiative_code") and _norm(row["initiative_code"]) in q:
                score += 4
            if score and (best is None or score > best[0]):
                best = (score, row)
        return best[1] if best and best[0] >= 2 else None

    def _find_write_target_initiative(
        self,
        query: str,
        snapshot: CopilotSnapshot,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        context_id = context.get("initiative_id") or context.get("entity_id")
        if context_id:
            return next((row for row in snapshot.initiatives if row["id"] == context_id), None)
        match = re.search(r"\b(?:to|for|on)\s+(.+)$", query, re.IGNORECASE)
        if not match:
            return None
        target_text = re.split(
            r"\b(?:with|about|by|due|called|named)\b",
            match.group(1),
            flags=re.IGNORECASE,
        )[0].strip()
        if not target_text:
            return None
        return self._find_initiative(target_text, snapshot, {})

    def _find_user(self, query: str, snapshot: CopilotSnapshot) -> dict[str, Any] | None:
        q = _norm(query)
        best: tuple[int, dict[str, Any]] | None = None
        for row in snapshot.users:
            name = _norm(row.get("display_name"))
            if not name:
                continue
            score = sum(1 for token in q.split() if len(token) > 2 and token in name)
            if score and (best is None or score > best[0]):
                best = (score, row)
        return best[1] if best else None

    def _missing_initiative_response(
        self,
        snapshot: CopilotSnapshot,
        plan: CopilotPlan,
    ) -> dict[str, Any]:
        examples = ", ".join(
            f"{row.get('initiative_code')} {row.get('name')}" for row in snapshot.initiatives[:3]
        )
        return {
            "response": "I need a target initiative before drafting that action."
            + (f" Examples I can see: {examples}." if examples else ""),
            "sources": self._sources(
                ["initiatives", "ai_tools"],
                snapshot,
                "Target initiative is required before drafting write actions.",
            ),
            "tool_trace": self._trace(
                ["initiatives", "ai_tools"],
                snapshot,
                plan,
                rejected="missing_target_guardrail",
            ),
            "confidence": 0.74,
            "proposed_actions": [],
            "plan": plan.__dict__,
        }

    @staticmethod
    def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get(key) or "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts

    @staticmethod
    def _count_text(counts: dict[str, int]) -> str:
        return ", ".join(f"{count} {key.replace('_', ' ')}" for key, count in sorted(counts.items())) or "none"

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    def _date_between(self, value: object, start: date, end: date) -> bool:
        parsed = self._parse_date(value)
        return bool(parsed and start <= parsed <= end)

    def _date_in_month(self, value: object, year: int, month: int) -> bool:
        parsed = self._parse_date(value)
        return bool(parsed and parsed.year == year and parsed.month == month)

    def _initiative_label(self, initiative_id: object, snapshot: CopilotSnapshot) -> str:
        initiative = next((row for row in snapshot.initiatives if row["id"] == initiative_id), None)
        if not initiative:
            return "Unscoped"
        return f"{initiative.get('initiative_code')} {initiative.get('name')}"

    def _user_label(self, user_id: object, snapshot: CopilotSnapshot) -> str:
        user = next((row for row in snapshot.users if row["id"] == user_id), None)
        return user.get("display_name") if user else "Unassigned"

    @staticmethod
    def _source_url(source_type: str) -> str | None:
        urls = {
            "initiatives": "/initiatives/pipeline",
            "milestones": "/progress",
            "risks": "/pmo/risks",
            "kpis": "/pmo/kpis",
            "financials": "/financials",
            "meetings": "/meetings",
            "action_items": "/progress",
            "reports": "/reports/executive-control-tower",
        }
        return urls.get(source_type)

    @staticmethod
    def _extract_name(query: str, markers: tuple[str, ...]) -> str | None:
        text = query.strip()
        for marker in markers:
            match = re.search(rf"\b{re.escape(marker)}\b\s+['\"]?([^'\".;]+)", text, re.IGNORECASE)
            if match:
                value = re.split(r"\b(to|for|by|with|on|in)\b", match.group(1), flags=re.IGNORECASE)[0]
                return value.strip(" .:-")[:300] or None
        return None

    @staticmethod
    def _extract_after(query: str, marker: str) -> str | None:
        match = re.search(rf"\b{re.escape(marker)}\b\s+(.+)$", query, re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip(" .")[:1000]

    @staticmethod
    def _extract_priority(query_l: str) -> str:
        for value in ("high", "medium", "low"):
            if value in query_l:
                return value
        return "medium"

    @staticmethod
    def _extract_level(query_l: str) -> str | None:
        for value in ("high", "medium", "low"):
            if value in query_l:
                return value
        return None

    @staticmethod
    def _extract_risk_type(query_l: str) -> str | None:
        for value in ("operational", "people", "financial", "technology"):
            if value in query_l:
                return value
        return None

    @staticmethod
    def _extract_unit(query: str) -> str | None:
        match = re.search(r"\b(unit|in)\s+([%a-zA-Z$]+)", query)
        return match.group(2)[:40] if match else None

    @staticmethod
    def _extract_date(query: str) -> str | None:
        match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", query)
        return match.group(1) if match else None

    @staticmethod
    def _extract_year(query: str) -> int | None:
        match = re.search(r"\b(20\d{2})\b", query)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_quarter(query: str) -> int | None:
        match = re.search(r"\bq([1-4])\b", query, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_amount(query: str) -> Decimal:
        match = re.search(r"([$]?\s*\d[\d,]*(?:\.\d+)?)\s*([kKmM])?", query)
        if not match:
            return Decimal("0")
        value = Decimal(match.group(1).replace("$", "").replace(",", "").strip())
        suffix = match.group(2)
        if suffix and suffix.lower() == "k":
            value *= Decimal("1000")
        if suffix and suffix.lower() == "m":
            value *= Decimal("1000000")
        return value
