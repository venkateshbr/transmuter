"""Initiative service — business logic layer."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from supabase import Client

from app.core.auth import CurrentUser
from app.core.rbac import can_view_all_initiatives
from app.domain.financials import FinancialGridUpdate, FinancialSummary
from app.domain.initiative_intake import (
    InitiativeIntakeCreate,
    InitiativeWorkbookPreview,
)
from app.domain.initiatives import (
    InitiativeBusinessUnit,
    InitiativeCounts,
    InitiativeCreate,
    InitiativeDetail,
    InitiativeKPIIndicator,
    InitiativeListItem,
    InitiativeListResponse,
    InitiativeTeamMember,
    InitiativeUpdate,
    PressureBreakdown,
)
from app.domain.kpis import KPICreate, KPIEntryUpsert
from app.domain.milestones import MilestoneCreate
from app.domain.risks import RiskCreate
from app.domain.status_updates import StatusUpdateCreate
from app.repositories.audit import AuditRepository
from app.repositories.business_unit import BusinessUnitRepository
from app.repositories.initiative import InitiativeRepository
from app.repositories.people import PeopleRepository
from app.repositories.status_update import StatusUpdateRepository
from app.repositories.workstream import WorkstreamRepository
from app.services.financial import FinancialService
from app.services.initiative_workbook import (
    build_initiative_export,
    build_initiative_template,
    build_preview,
    parse_initiative_template,
    parse_workbook_overview_metadata,
    parse_workbook_reference,
)
from app.services.kpi import KPIService
from app.services.milestone import MilestoneService
from app.services.risk import RiskService
from app.services.status_update import StatusUpdateService


class InitiativeService:
    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID | None = None) -> None:
        self._client = client
        self._repo = InitiativeRepository(client, tenant_id)
        self._audit = AuditRepository(client, tenant_id)
        self._fin = FinancialService(client, tenant_id)
        self._tenant_id = tenant_id
        self._user_id = str(user_id) if user_id else None

    def list_initiatives(
        self,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        stage: str | None = None,
        priority: str | None = None,
        tag: str | None = None,
        search: str | None = None,
        sort_by: str = "initiative_code",
        sort_desc: bool = False,
        page: int = 1,
        page_size: int = 50,
        current_user: CurrentUser | None = None,
    ) -> InitiativeListResponse:
        owner_user_id = (
            str(current_user.id)
            if current_user and current_user.role == "initiative_owner"
            else None
        )
        rows, total = self._repo.list(
            business_unit_ids=self._split_filter_values(business_unit_id),
            workstream_ids=self._split_filter_values(workstream_id),
            rag_statuses=self._split_filter_values(rag_status),
            stages=self._split_filter_values(stage),
            priorities=self._split_filter_values(priority),
            tags=self._split_filter_values(tag),
            search=search,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            page_size=page_size,
            owner_user_id=owner_user_id,
        )
        items = [self._to_list_item(r, self._fin.get_financial_summary(str(r["id"]))) for r in rows]
        return InitiativeListResponse(items=items, total=total, page=page, page_size=page_size)

    @staticmethod
    def _split_filter_values(value: str | None) -> list[str] | None:
        if not value:
            return None
        values = [part.strip() for part in value.split(",") if part.strip()]
        return values or None

    def get_initiative(
        self,
        initiative_id: str,
        current_user: CurrentUser | None = None,
    ) -> InitiativeDetail:
        row = self._repo.get(initiative_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found"
            )
        if current_user and not can_view_all_initiatives(current_user.role):
            user_id = str(current_user.id)
            if row.get("owner_id") != user_id and row.get("group_owner_id") != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found"
                )
        counts = self._repo.get_counts(initiative_id)
        fin_summary = self._fin.get_financial_summary(initiative_id)
        team_members = self._get_team_members(initiative_id)
        kpi_indicators = self._get_kpi_indicators(initiative_id)

        # Calculate dynamic pressure
        pressure_score, pressure_breakdown = self._calculate_pressure(row, counts, fin_summary)
        row["pressure_score"] = pressure_score
        row["pressure_sub"] = pressure_breakdown.model_dump() if pressure_breakdown else None

        return self._to_detail(row, counts, fin_summary, team_members, kpi_indicators)

    def create_initiative(self, data: InitiativeCreate, created_by: UUID) -> InitiativeDetail:
        self._assert_tenant_ready_for_creation()
        business_unit_ids = [str(bu_id) for bu_id in data.business_unit_ids]
        # Generate unique code — retry up to 5 times on conflict
        for _ in range(5):
            code = self._repo.next_code()
            try:
                row = self._repo.create(
                    {
                        "id": str(uuid4()),
                        "tenant_id": str(self._tenant_id),
                        "initiative_code": code,
                        "name": data.name,
                        "workstream_id": str(data.workstream_id) if data.workstream_id else None,
                        "owner_id": str(data.owner_id) if data.owner_id else None,
                        "group_owner_id": str(data.group_owner_id) if data.group_owner_id else None,
                        "type": data.type,
                        "impact_type": data.impact_type,
                        "theme": data.theme,
                        "country": data.country,
                        "tag": data.tag,
                        "priority": data.priority,
                        "summary": data.summary,
                        "context_problem": data.context_problem,
                        "value_logic": data.value_logic,
                        "dependencies_text": data.dependencies_text,
                        "benefit_confidence": str(data.benefit_confidence),
                        "realization_status": data.realization_status,
                        "variance_explanation": data.variance_explanation,
                        "planned_start": data.planned_start.isoformat()
                        if data.planned_start
                        else None,
                        "planned_end": data.planned_end.isoformat() if data.planned_end else None,
                        "rag_status": "green",
                        "stage": self._initial_stage(),
                    }
                )
                break
            except Exception as exc:
                if "unique" in str(exc).lower() and "initiative_code" in str(exc).lower():
                    continue
                raise
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique initiative code")

        self._repo.replace_business_units(row["id"], business_unit_ids)
        self._fin.initialize_default_selections(row["id"])
        initiative = self.get_initiative(row["id"])
        self._audit_change(
            "create", "initiative", row["id"], after_data=initiative.model_dump(mode="json")
        )
        return initiative

    def update_initiative(self, initiative_id: str, data: InitiativeUpdate) -> InitiativeDetail:
        existing = self._repo.get(initiative_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found"
            )
        patch = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
        business_unit_ids = patch.pop("business_unit_ids", None)
        if "stage" in patch and patch["stage"] is not None:
            self._assert_stage_transition_allowed(
                initiative_id,
                str(existing["stage"]),
                str(patch["stage"]),
            )
        # Serialize date fields
        for date_field in ("planned_start", "actual_start", "planned_end", "actual_end"):
            if date_field in patch and patch[date_field] is not None:
                patch[date_field] = patch[date_field].isoformat()
        # UUID fields
        for uuid_field in ("workstream_id", "owner_id", "group_owner_id"):
            if uuid_field in patch and patch[uuid_field] is not None:
                patch[uuid_field] = str(patch[uuid_field])
        if "benefit_confidence" in patch and patch["benefit_confidence"] is not None:
            patch["benefit_confidence"] = str(patch["benefit_confidence"])
        patch["updated_at"] = datetime.now(UTC).isoformat()
        self._repo.update(initiative_id, patch)
        if business_unit_ids is not None:
            self._repo.replace_business_units(
                initiative_id,
                [str(bu_id) for bu_id in business_unit_ids],
            )
        initiative = self.get_initiative(initiative_id)
        self._audit_change(
            "update",
            "initiative",
            initiative_id,
            before_data=existing,
            after_data=initiative.model_dump(mode="json"),
        )
        return initiative

    def archive_initiative(self, initiative_id: str) -> InitiativeDetail:
        existing = self._assert_exists(initiative_id)
        self._repo.archive(initiative_id)
        initiative = self.get_initiative(initiative_id)
        self._audit_change(
            "archive",
            "initiative",
            initiative_id,
            before_data=existing,
            after_data=initiative.model_dump(mode="json"),
        )
        return initiative

    def delete_initiative(self, initiative_id: str) -> None:
        existing = self._assert_exists(initiative_id)
        self._repo.delete(initiative_id)
        self._audit_change("delete", "initiative", initiative_id, before_data=existing)

    def export_csv(self, current_user: CurrentUser | None = None) -> str:
        owner_user_id = (
            str(current_user.id)
            if current_user and current_user.role == "initiative_owner"
            else None
        )
        return self._repo.export_csv(owner_user_id=owner_user_id)

    def export_template(self) -> bytes:
        return build_initiative_template()

    def export_initiative_workbook(self, initiative_id: str) -> bytes:
        initiative = self.get_initiative(initiative_id)
        financials = self._fin.get_financial_grid(initiative_id)
        costs = self._fin.list_cost_lines(initiative_id)
        kpis = KPIService(self._client, self._tenant_id).list_kpis(initiative_id)
        risks = RiskService(self._client, self._tenant_id).list_risks(initiative_id)
        milestones = MilestoneService(self._client, self._tenant_id).list_milestones(initiative_id)
        status_updates = StatusUpdateRepository(self._client, self._tenant_id).list_history(
            initiative_id
        )
        meeting_notes = self._list_meeting_notes(initiative_id)

        return build_initiative_export(
            overview_rows=[self._overview_export_row(initiative)],
            benefit_rows=[
                [
                    str(row.year),
                    str(row.quarter or ""),
                    str(row.month or ""),
                    row.revenue_uplift_base,
                    row.revenue_uplift_high,
                    row.revenue_uplift_actual or "",
                    row.gross_margin_base,
                    row.gross_margin_high,
                    row.gross_margin_actual or "",
                    row.gm_uplift_base,
                    row.gm_uplift_high,
                    row.gm_uplift_actual or "",
                ]
                for row in financials.entries
            ],
            cost_rows=[
                [
                    row.name,
                    str(row.year),
                    str(row.quarter or ""),
                    str(row.month or ""),
                    row.amount_plan,
                    row.amount_actual or "",
                    "true" if row.is_recurring else "false",
                ]
                for row in costs.items
            ],
            kpi_rows=[
                [
                    kpi.name,
                    kpi.type,
                    kpi.category or "",
                    kpi.frequency,
                    kpi.unit or "",
                    str(entry.year),
                    str(entry.quarter or ""),
                    entry.value_base or "",
                    entry.value_high or "",
                    entry.value_actual or "",
                ]
                for kpi in kpis.items
                for entry in (kpi.entries or [None])
                if entry is not None
            ],
            risk_rows=[
                [
                    risk.description,
                    risk.type or "",
                    risk.impact or "",
                    risk.likelihood or "",
                    risk.mitigation or "",
                ]
                for risk in risks.items
            ],
            milestone_rows=[
                [
                    milestone.name,
                    milestone.description or "",
                    milestone.priority,
                    milestone.planned_start or "",
                    milestone.planned_end or "",
                ]
                for milestone in milestones.items
            ],
            status_update_rows=[
                [
                    row.get("submitted_at") or "",
                    row.get("rag_status") or "",
                    row.get("summary") or "",
                    row.get("achievements") or "",
                    row.get("issues") or "",
                    row.get("next_steps") or "",
                    (row.get("users") or {}).get("display_name") or "",
                ]
                for row in status_updates
            ],
            meeting_note_rows=[
                [
                    row.get("session_date") or "",
                    (row.get("meetings") or {}).get("name") or "",
                    row.get("notes") or "",
                    row.get("status") or "",
                ]
                for row in meeting_notes
            ],
            reference_rows=[
                ["initiative_id", str(initiative.id)],
                ["initiative_code", initiative.initiative_code],
                ["export_version", "1"],
                ["exported_by", "Transmuter"],
            ],
        )

    def preview_import(self, data: bytes) -> InitiativeWorkbookPreview:
        return build_preview(parse_initiative_template(data))

    def import_template(self, data: bytes, created_by: UUID) -> InitiativeDetail:
        self._assert_tenant_ready_for_creation()
        parsed = parse_initiative_template(data)
        if parsed.validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[error.model_dump() for error in parsed.validation_errors],
            )
        overview = self._apply_workbook_metadata(parsed.overview, parsed.metadata, created_by)
        created = self.create_initiative(overview, created_by)
        initiative_id = str(created.id)
        if parsed.financial_entries or parsed.cost_lines:
            writer = (
                self._fin.replace_financial_grid
                if parsed.metadata.get("format") == "alchemist"
                else self._fin.update_financial_grid
            )
            writer(
                initiative_id,
                FinancialGridUpdate(
                    entries=parsed.financial_entries,
                    cost_lines=parsed.cost_lines,
                ),
            )
        kpi_service = KPIService(self._client, self._tenant_id)
        for kpi in parsed.kpis:
            created_kpi = kpi_service.create_kpi(initiative_id, self._as_kpi_create(kpi))
            if kpi.entries:
                kpi_service.upsert_entries(
                    initiative_id,
                    created_kpi.id,
                    kpi.entries,
                )
        risk_service = RiskService(self._client, self._tenant_id)
        for risk in parsed.risks:
            risk_service.create_risk(initiative_id, risk)
        milestone_service = MilestoneService(self._client, self._tenant_id)
        for milestone in parsed.milestones:
            if not milestone.owner_id:
                milestone.owner_id = str(created_by)
            milestone_service.create_milestone(initiative_id, milestone)
        self._import_status_updates(initiative_id, parsed.status_updates, created_by)
        return self.get_initiative(initiative_id)

    def import_into_existing_initiative(
        self,
        initiative_id: str,
        data: bytes,
        updated_by: UUID | None = None,
    ) -> InitiativeDetail:
        self._assert_exists(initiative_id)
        reference = parse_workbook_reference(data)
        referenced_id = reference.get("initiative_id")
        if referenced_id and referenced_id != initiative_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workbook reference does not match initiative_id",
            )

        parsed = parse_initiative_template(data)
        if parsed.validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[error.model_dump() for error in parsed.validation_errors],
            )

        overview = self._apply_workbook_metadata(parsed.overview, parsed.metadata, updated_by)
        overview_patch = overview.model_dump(exclude_none=True)
        metadata = parse_workbook_overview_metadata(data)
        for field in ("stage", "rag_status"):
            if metadata.get(field):
                overview_patch[field] = metadata[field]
        self.update_initiative(initiative_id, InitiativeUpdate(**overview_patch))

        if parsed.financial_entries or parsed.cost_lines:
            writer = (
                self._fin.replace_financial_grid
                if parsed.metadata.get("format") == "alchemist"
                else self._fin.update_financial_grid
            )
            writer(
                initiative_id,
                FinancialGridUpdate(
                    entries=parsed.financial_entries,
                    cost_lines=parsed.cost_lines,
                ),
            )
        if parsed.status_updates:
            self._import_status_updates(initiative_id, parsed.status_updates, updated_by)
        return self.get_initiative(initiative_id)

    def _apply_workbook_metadata(
        self,
        overview: InitiativeCreate,
        metadata: dict,
        fallback_user_id: UUID | None,
    ) -> InitiativeCreate:
        if not metadata:
            return overview

        patch = overview.model_dump()
        business_unit_ids = self._ensure_business_unit_ids(metadata)
        if business_unit_ids:
            patch["business_unit_ids"] = business_unit_ids
        workstream_id = self._ensure_workstream_id(metadata)
        if workstream_id:
            patch["workstream_id"] = workstream_id

        owner_id = self._resolve_user_id(metadata.get("owner_name"))
        group_owner_id = self._resolve_user_id(metadata.get("group_owner_name"))
        if not owner_id and fallback_user_id:
            owner_id = str(fallback_user_id)
        if not group_owner_id and fallback_user_id:
            group_owner_id = str(fallback_user_id)
        if owner_id:
            patch["owner_id"] = owner_id
        if group_owner_id:
            patch["group_owner_id"] = group_owner_id

        return InitiativeCreate(**patch)

    def _ensure_business_unit_ids(self, metadata: dict) -> list[str]:
        names = metadata.get("business_unit_names") or []
        cleaned_names = list(
            dict.fromkeys([str(item).strip() for item in names if str(item).strip()])
        )
        if not cleaned_names:
            return []
        repo = BusinessUnitRepository(self._client, self._tenant_id)
        existing_by_name = {row.get("name", "").lower(): row for row in repo.list()}
        business_unit_ids: list[str] = []
        for name in cleaned_names:
            existing = existing_by_name.get(name.lower())
            if existing:
                business_unit_ids.append(existing["id"])
                continue
            created = repo.create({"name": name, "code": self._business_unit_code(name)})
            if created.get("id"):
                business_unit_ids.append(created["id"])
        return business_unit_ids

    def _ensure_workstream_id(self, metadata: dict) -> str | None:
        name = str(metadata.get("workstream_name") or "").strip()
        if not name:
            return None
        repo = WorkstreamRepository(self._client, self._tenant_id)
        workstreams = repo.list()
        existing = next(
            (row for row in workstreams if row.get("name", "").lower() == name.lower()), None
        )
        if existing:
            return existing["id"]
        created = repo.create({"name": name})
        return created.get("id")

    def _resolve_user_id(self, display_name: str | None) -> str | None:
        name = str(display_name or "").strip().lower()
        if not name:
            return None
        users = PeopleRepository(self._client, self._tenant_id).list_users(status="active")
        exact = next(
            (row for row in users if str(row.get("display_name") or "").strip().lower() == name),
            None,
        )
        if exact:
            return exact["id"]
        tokens = {part for part in name.split() if part}
        if not tokens:
            return None
        return next(
            (
                row["id"]
                for row in users
                if tokens.issubset(set(str(row.get("display_name") or "").strip().lower().split()))
            ),
            None,
        )

    def _import_status_updates(
        self,
        initiative_id: str,
        rows: list[dict],
        author_id: UUID | None,
    ) -> None:
        if not rows:
            return
        existing = StatusUpdateService(self._client, self._tenant_id, author_id).list_history(
            initiative_id
        )
        existing_summaries = {item.summary for item in existing.items}
        service = StatusUpdateService(self._client, self._tenant_id, author_id)
        for row in rows:
            if row.get("summary") in existing_summaries:
                continue
            service.create_update(initiative_id, StatusUpdateCreate(**row))

    def _business_unit_code(self, name: str) -> str:
        code = "".join(ch for ch in name.upper() if ch.isalnum())
        return code[:8] or "BU"

    def _list_meeting_notes(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        links = (
            self._client.table("meeting_initiatives")
            .select("meeting_id")
            .eq("tenant_id", str(self._tenant_id))
            .eq("initiative_id", initiative_id)
            .execute()
        )
        meeting_ids = [row["meeting_id"] for row in links.data or [] if row.get("meeting_id")]
        if not meeting_ids:
            return []
        sessions = (
            self._client.table("meeting_sessions")
            .select("session_date, notes, status, meetings(name)")
            .eq("tenant_id", str(self._tenant_id))
            .in_("meeting_id", meeting_ids)
            .order("session_date", desc=True)
            .execute()
        )
        return sessions.data or []

    @staticmethod
    def _overview_export_row(initiative: InitiativeDetail) -> list[str]:
        return [
            initiative.name,
            initiative.stage,
            initiative.rag_status,
            initiative.workstream_name or "",
            "",
            "",
            initiative.type or "",
            initiative.impact_type or "",
            initiative.theme or "",
            initiative.country or "",
            initiative.tag or "",
            initiative.priority,
            initiative.summary or "",
            initiative.context_problem or "",
            initiative.value_logic or "",
            initiative.dependencies_text or "",
            str(initiative.planned_start or ""),
            str(initiative.planned_end or ""),
        ]

    def create_from_intake(
        self,
        data: InitiativeIntakeCreate,
        created_by: UUID,
    ) -> InitiativeDetail:
        self._assert_tenant_ready_for_creation()
        created = self.create_initiative(data.initiative, created_by)
        initiative_id = str(created.id)
        suggestions = data.suggestions
        if not suggestions:
            return created

        accepted_entries = [item for item in suggestions.financial_entries if item.accepted]
        accepted_costs = [item for item in suggestions.cost_lines if item.accepted]
        if accepted_entries or accepted_costs:
            self._fin.update_financial_grid(
                initiative_id,
                FinancialGridUpdate(entries=accepted_entries, cost_lines=accepted_costs),
            )

        kpi_service = KPIService(self._client, self._tenant_id)
        for kpi in [item for item in suggestions.kpis if item.accepted]:
            created_kpi = kpi_service.create_kpi(initiative_id, self._as_kpi_create(kpi))
            if kpi.entries:
                kpi_service.upsert_entries(
                    initiative_id,
                    created_kpi.id,
                    self._kpi_entries_with_initial_actuals(kpi.entries),
                )

        risk_service = RiskService(self._client, self._tenant_id)
        for risk in [item for item in suggestions.risks if item.accepted]:
            risk_service.create_risk(initiative_id, self._as_risk_create(risk))

        milestone_service = MilestoneService(self._client, self._tenant_id)
        for milestone in [item for item in suggestions.milestones if item.accepted]:
            milestone_service.create_milestone(initiative_id, self._as_milestone_create(milestone))
        return self.get_initiative(initiative_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_exists(self, initiative_id: str) -> None:
        if not self._repo.get(initiative_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found"
            )

    def _assert_tenant_ready_for_creation(self) -> None:
        required_tables = {
            "business_units": "business units",
            "workstreams": "workstreams",
            "financial_metric_definitions": "financial metric definitions",
            "financial_scenarios": "financial scenarios",
            "financial_cost_categories": "financial cost categories",
            "stage_gate_definitions": "stage gates",
            "gate_criteria": "gate criteria",
        }
        missing = [
            label for table, label in required_tables.items() if not self._table_has_rows(table)
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Tenant setup is incomplete. Configure "
                    f"{', '.join(missing)} before creating initiatives."
                ),
            )

    def _table_has_rows(self, table: str) -> bool:
        result = (
            self._client.table(table)
            .select("id", count="exact")
            .eq("tenant_id", str(self._tenant_id))
            .execute()
        )
        return bool(result.count and result.count > 0)

    def _assert_stage_transition_allowed(
        self,
        initiative_id: str,
        current_stage: str,
        requested_stage: str,
    ) -> None:
        definitions = self._stage_gate_definitions()
        stage_order = self._stage_order(definitions)
        if requested_stage == current_stage:
            return
        if requested_stage not in stage_order or current_stage not in stage_order:
            return

        current_index = stage_order.index(current_stage)
        requested_index = stage_order.index(requested_stage)
        if requested_index <= current_index:
            return

        for stage_index in range(current_index + 1, requested_index + 1):
            gate_number = int(definitions[stage_index - 1]["gate_number"])
            if not self._repo.has_approved_gate_submission(initiative_id, gate_number):
                gate_label = definitions[stage_index - 1].get("label") or f"Gate {gate_number}"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{gate_label} must be approved before advancing "
                        f"to {stage_order[stage_index]}."
                    ),
                )

    def _initial_stage(self) -> str:
        definitions = self._stage_gate_definitions()
        return str(definitions[0]["from_stage"]) if definitions else "scoping"

    def _stage_gate_definitions(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._client.table("stage_gate_definitions")
            .select("gate_number,label,from_stage,to_stage,is_active,sort_order")
            .eq("tenant_id", str(self._tenant_id))
            .eq("is_active", True)
            .order("gate_number")
            .execute()
        )
        return result.data or []

    @staticmethod
    def _stage_order(definitions: list[dict]) -> list[str]:  # type: ignore[type-arg]
        stages: list[str] = []
        for definition in definitions:
            for key in ("from_stage", "to_stage"):
                value = str(definition.get(key) or "").strip()
                if value and value not in stages:
                    stages.append(value)
        return stages

    @staticmethod
    def _as_kpi_create(data: object) -> KPICreate:
        fields = {"name", "type", "category", "frequency", "unit"}
        raw = data.model_dump(include=fields) if hasattr(data, "model_dump") else data
        return KPICreate.model_validate(raw)

    @staticmethod
    def _kpi_entries_with_initial_actuals(entries: list[KPIEntryUpsert]) -> list[KPIEntryUpsert]:
        normalized: list[KPIEntryUpsert] = []
        for entry in entries:
            if entry.value_actual is not None:
                normalized.append(entry)
                continue
            normalized.append(
                entry.model_copy(update={"value_actual": entry.value_base or entry.value_high})
            )
        return normalized

    @staticmethod
    def _as_risk_create(data: object) -> RiskCreate:
        fields = {
            "description",
            "type",
            "impact",
            "likelihood",
            "status",
            "owner_id",
            "mitigation",
            "escalated",
        }
        raw = data.model_dump(include=fields) if hasattr(data, "model_dump") else data
        return RiskCreate.model_validate(raw)

    @staticmethod
    def _as_milestone_create(data: object) -> MilestoneCreate:
        fields = {
            "name",
            "description",
            "owner_id",
            "priority",
            "planned_start",
            "planned_end",
        }
        raw = data.model_dump(include=fields) if hasattr(data, "model_dump") else data
        return MilestoneCreate.model_validate(raw)

    @staticmethod
    @staticmethod
    def _net_value(
        benefit: str | None,
        cost: str | None,
        *,
        require_benefit: bool = False,
    ) -> str | None:
        if require_benefit and benefit is None:
            return None
        return str(Decimal(benefit or "0") - Decimal(cost or "0"))

    @staticmethod
    def _business_units(row: dict) -> list[InitiativeBusinessUnit]:  # type: ignore[type-arg]
        items: list[InitiativeBusinessUnit] = []
        seen: set[str] = set()
        for link in row.get("initiative_business_units") or []:
            business_unit = link.get("business_units") if isinstance(link, dict) else None
            bu_id = (
                business_unit.get("id")
                if isinstance(business_unit, dict)
                else link.get("business_unit_id")
            )
            name = business_unit.get("name") if isinstance(business_unit, dict) else None
            if not bu_id or str(bu_id) in seen:
                continue
            seen.add(str(bu_id))
            items.append(InitiativeBusinessUnit(id=bu_id, name=name or "Business Unit"))
        return items

    @classmethod
    def _to_list_item(
        cls,
        row: dict,  # type: ignore[type-arg]
        fin: FinancialSummary | None = None,
    ) -> InitiativeListItem:
        ws = row.get("workstreams") or {}
        owner = row.get("users") or {}
        business_units = cls._business_units(row)
        return InitiativeListItem(
            id=row["id"],
            initiative_code=row["initiative_code"],
            name=row["name"],
            workstream_id=row.get("workstream_id"),
            workstream_name=ws.get("name") if isinstance(ws, dict) else None,
            business_unit_ids=[item.id for item in business_units],
            business_units=business_units,
            owner_id=row.get("owner_id"),
            owner_name=owner.get("display_name") if isinstance(owner, dict) else None,
            type=row.get("type"),
            priority=row["priority"],
            rag_status=row["rag_status"],
            stage=row["stage"],
            country=row.get("country"),
            tag=row.get("tag"),
            planned_value_base=cls._net_value(
                fin.gm_uplift_plan_base if fin else None,
                fin.costs_plan if fin else None,
            )
            if fin
            else None,
            planned_value_high=cls._net_value(
                fin.gm_uplift_plan_high if fin else None,
                fin.costs_plan if fin else None,
            )
            if fin
            else None,
            actual_value=cls._net_value(
                fin.gm_uplift_actual if fin else None,
                fin.costs_actual if fin else None,
                require_benefit=True,
            )
            if fin
            else None,
            pressure_score=str(row["pressure_score"])
            if row.get("pressure_score") is not None
            else None,
            archived_at=row.get("archived_at"),
        )

    @staticmethod
    def _to_detail(
        row: dict,
        counts: dict,
        fin: FinancialSummary | None = None,
        team_members: list[InitiativeTeamMember] | None = None,
        kpi_indicators: list[InitiativeKPIIndicator] | None = None,
    ) -> InitiativeDetail:  # type: ignore[type-arg]
        ws = row.get("workstreams") or {}
        sub = row.get("pressure_sub") or {}
        business_units = InitiativeService._business_units(row)
        return InitiativeDetail(
            id=row["id"],
            initiative_code=row["initiative_code"],
            name=row["name"],
            workstream_id=row.get("workstream_id"),
            workstream_name=ws.get("name") if isinstance(ws, dict) else None,
            business_unit_ids=[item.id for item in business_units],
            business_units=business_units,
            owner_id=row.get("owner_id"),
            owner_name=row.get("_owner_name"),
            group_owner_id=row.get("group_owner_id"),
            group_owner_name=row.get("_group_owner_name"),
            type=row.get("type"),
            impact_type=row.get("impact_type"),
            theme=row.get("theme"),
            country=row.get("country"),
            tag=row.get("tag"),
            priority=row["priority"],
            rag_status=row["rag_status"],
            stage=row["stage"],
            summary=row.get("summary"),
            lessons_learned=row.get("lessons_learned"),
            context_problem=row.get("context_problem"),
            value_logic=row.get("value_logic"),
            dependencies_text=row.get("dependencies_text"),
            benefit_confidence=str(row.get("benefit_confidence") or "50.00"),
            realization_status=row.get("realization_status") or "not_started",
            variance_explanation=row.get("variance_explanation"),
            planned_start=row.get("planned_start"),
            actual_start=row.get("actual_start"),
            planned_end=row.get("planned_end"),
            actual_end=row.get("actual_end"),
            pressure_score=str(row["pressure_score"])
            if row.get("pressure_score") is not None
            else None,
            pressure_breakdown=PressureBreakdown(**sub) if sub else None,
            counts=InitiativeCounts(**counts),
            team_members=team_members or [],
            kpi_indicators=kpi_indicators or [],
            financial_summary=fin,
            archived_at=row.get("archived_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _calculate_pressure(
        self, row: dict, counts: dict, fin: FinancialSummary
    ) -> tuple[Decimal, PressureBreakdown]:
        """Dynamically calculate pressure score based on various health factors."""
        from decimal import Decimal

        # 1. Schedule Pressure (0-10)
        # Higher if close to end date or overdue
        schedule = Decimal("2.0")  # Base

        # 2. Milestone Health (0-10)
        # Higher if overdue milestones exist
        ms_total = counts.get("milestones_total", 0)
        ms_overdue = counts.get("milestones_overdue", 0)
        ms_health = Decimal("0")
        if ms_total > 0:
            ms_health = (Decimal(str(ms_overdue)) / Decimal(str(ms_total))) * 10

        # 3. Risk Exposure (0-10)
        # Higher if high-rating risks exist
        risks_total = counts.get("risks_open", 0)
        risks_high = counts.get("risks_high", 0)
        risk_exp = Decimal("0")
        if risks_total > 0:
            risk_exp = (Decimal(str(risks_high)) / Decimal(str(risks_total))) * 10

        # 4. Financial Pressure (0-10)
        # Higher if actual cost > plan or actual benefit < plan
        fin_press = Decimal("0")
        try:
            plan_val = Decimal(fin.gm_uplift_plan_base)
            act_val = Decimal(fin.gm_uplift_actual or "0")
            if plan_val > 0 and act_val < plan_val:
                fin_press = ((plan_val - act_val) / plan_val) * 10
        except:
            pass

        # 5. Self-Reported (from row)
        self_reported = Decimal(str(row.get("pressure_score") or "0"))

        breakdown = PressureBreakdown(
            schedule=schedule.quantize(Decimal("0.1")),
            milestone_health=ms_health.quantize(Decimal("0.1")),
            risk_exposure=risk_exp.quantize(Decimal("0.1")),
            kpi_performance=Decimal("0"),  # Placeholder
            financial=fin_press.quantize(Decimal("0.1")),
            self_reported=self_reported.quantize(Decimal("0.1")),
        )

        # Weighted average
        weights = {
            "schedule": Decimal("0.2"),
            "milestone_health": Decimal("0.2"),
            "risk_exposure": Decimal("0.2"),
            "financial": Decimal("0.3"),
            "self_reported": Decimal("0.1"),
        }

        total_score = (
            breakdown.schedule * weights["schedule"]
            + breakdown.milestone_health * weights["milestone_health"]
            + breakdown.risk_exposure * weights["risk_exposure"]
            + breakdown.financial * weights["financial"]
            + breakdown.self_reported * weights["self_reported"]
        )

        return total_score.quantize(Decimal("0.1")), breakdown

    def _audit_change(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        *,
        before_data: dict | None = None,  # type: ignore[type-arg]
        after_data: dict | None = None,  # type: ignore[type-arg]
    ) -> None:
        if not self._user_id:
            return
        self._audit.log_change(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=self._user_id,
            before_data=before_data,
            after_data=after_data,
        )

    def _get_team_members(self, initiative_id: str) -> list[InitiativeTeamMember]:
        rows = self._repo.get_team_members(initiative_id)
        members = []
        for row in rows:
            user = row.get("users") or {}
            members.append(
                InitiativeTeamMember(
                    id=row["id"],
                    user_id=row["user_id"],
                    role=row["role"],
                    display_name=user.get("display_name") if isinstance(user, dict) else None,
                    email=user.get("email") if isinstance(user, dict) else None,
                )
            )
        return members

    def _get_kpi_indicators(self, initiative_id: str) -> list[InitiativeKPIIndicator]:
        kpis, entries = self._repo.get_kpi_indicator_rows(initiative_id)
        entries_by_kpi: dict[str, list[dict]] = {row["id"]: [] for row in kpis}
        for entry in entries:
            entries_by_kpi.setdefault(entry["kpi_id"], []).append(entry)

        indicators: list[InitiativeKPIIndicator] = []
        for kpi in kpis[:6]:
            kpi_entries = entries_by_kpi.get(kpi["id"], [])
            actual_entries = [
                entry for entry in kpi_entries if entry.get("value_actual") is not None
            ]
            latest = (
                sorted(
                    actual_entries,
                    key=lambda entry: (entry["year"], entry.get("quarter") or 5),
                    reverse=True,
                )[0]
                if actual_entries
                else None
            )
            latest_year = latest["year"] if latest else None

            def total_for(rows: list[dict], key: str) -> Decimal | None:
                values = [Decimal(str(row[key])) for row in rows if row.get(key) is not None]
                return sum(values, Decimal("0")) if values else None

            this_year_rows = [
                entry
                for entry in actual_entries
                if latest_year is not None and entry["year"] == latest_year
            ]
            actual_total = total_for(actual_entries, "value_actual")
            base_total = total_for(kpi_entries, "value_base")

            health = "no_data"
            if latest and latest.get("value_actual") is not None:
                actual = Decimal(str(latest["value_actual"]))
                base = Decimal(str(latest.get("value_base") or "0"))
                high = Decimal(str(latest.get("value_high") or base))
                if actual >= high:
                    health = "on_track"
                elif actual >= base:
                    health = "at_risk"
                else:
                    health = "critical"
            elif actual_total is not None and base_total is not None:
                health = "on_track" if actual_total >= base_total else "critical"

            indicators.append(
                InitiativeKPIIndicator(
                    id=kpi["id"],
                    name=kpi["name"],
                    unit=kpi.get("unit"),
                    health_status=health,
                    this_quarter_actual=str(latest["value_actual"]) if latest else None,
                    this_year_actual=str(total_for(this_year_rows, "value_actual"))
                    if this_year_rows
                    else None,
                    all_time_actual=str(actual_total) if actual_total is not None else None,
                )
            )
        return indicators
