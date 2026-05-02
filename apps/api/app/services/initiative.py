"""Initiative service — business logic layer."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from supabase import Client

from app.domain.initiatives import (
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
from app.repositories.initiative import InitiativeRepository
from app.services.financial import FinancialService
from app.services.initiative_workbook import build_initiative_template, parse_initiative_template


class InitiativeService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = InitiativeRepository(client, tenant_id)
        self._fin = FinancialService(client, tenant_id)
        self._tenant_id = tenant_id

    def list_initiatives(
        self,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        stage: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        sort_by: str = "initiative_code",
        sort_desc: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> InitiativeListResponse:
        rows, total = self._repo.list(
            workstream_id=workstream_id,
            rag_status=rag_status,
            stage=stage,
            priority=priority,
            search=search,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            page_size=page_size,
        )
        items = [self._to_list_item(r) for r in rows]
        return InitiativeListResponse(items=items, total=total, page=page, page_size=page_size)

    def get_initiative(self, initiative_id: str) -> InitiativeDetail:
        row = self._repo.get(initiative_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
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
        # Generate unique code — retry up to 5 times on conflict
        for _ in range(5):
            code = self._repo.next_code()
            try:
                row = self._repo.create({
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
                    "value_logic": data.value_logic,
                    "dependencies_text": data.dependencies_text,
                    "planned_start": data.planned_start.isoformat() if data.planned_start else None,
                    "planned_end": data.planned_end.isoformat() if data.planned_end else None,
                    "rag_status": "green",
                    "stage": "scoping",
                })
                break
            except Exception as exc:
                if "unique" in str(exc).lower() and "initiative_code" in str(exc).lower():
                    continue
                raise
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique initiative code")

        return self.get_initiative(row["id"])

    def update_initiative(self, initiative_id: str, data: InitiativeUpdate) -> InitiativeDetail:
        self._assert_exists(initiative_id)
        patch = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
        # Serialize date fields
        for date_field in ("planned_start", "actual_start", "planned_end", "actual_end"):
            if date_field in patch and patch[date_field] is not None:
                patch[date_field] = patch[date_field].isoformat()
        # UUID fields
        for uuid_field in ("workstream_id", "owner_id", "group_owner_id"):
            if uuid_field in patch and patch[uuid_field] is not None:
                patch[uuid_field] = str(patch[uuid_field])
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._repo.update(initiative_id, patch)
        return self.get_initiative(initiative_id)

    def archive_initiative(self, initiative_id: str) -> InitiativeDetail:
        self._assert_exists(initiative_id)
        self._repo.archive(initiative_id)
        return self.get_initiative(initiative_id)

    def delete_initiative(self, initiative_id: str) -> None:
        self._assert_exists(initiative_id)
        self._repo.delete(initiative_id)

    def export_csv(self) -> str:
        return self._repo.export_csv()

    def export_template(self) -> bytes:
        return build_initiative_template()

    def preview_import(self, data: bytes) -> InitiativeCreate:
        return parse_initiative_template(data)

    def import_template(self, data: bytes, created_by: UUID) -> InitiativeDetail:
        parsed = parse_initiative_template(data)
        return self.create_initiative(parsed, created_by)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_exists(self, initiative_id: str) -> None:
        if not self._repo.get(initiative_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")

    @staticmethod
    def _to_list_item(row: dict) -> InitiativeListItem:  # type: ignore[type-arg]
        ws = row.get("workstreams") or {}
        owner = row.get("users") or {}
        return InitiativeListItem(
            id=row["id"],
            initiative_code=row["initiative_code"],
            name=row["name"],
            workstream_id=row.get("workstream_id"),
            workstream_name=ws.get("name") if isinstance(ws, dict) else None,
            owner_id=row.get("owner_id"),
            owner_name=owner.get("display_name") if isinstance(owner, dict) else None,
            type=row.get("type"),
            priority=row["priority"],
            rag_status=row["rag_status"],
            stage=row["stage"],
            country=row.get("country"),
            tag=row.get("tag"),
            planned_value_base=None,
            planned_value_high=None,
            actual_value=None,
            pressure_score=str(row["pressure_score"]) if row.get("pressure_score") is not None else None,
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
        bu = ws.get("business_units") if isinstance(ws, dict) else None
        sub = row.get("pressure_sub") or {}
        return InitiativeDetail(
            id=row["id"],
            initiative_code=row["initiative_code"],
            name=row["name"],
            workstream_id=row.get("workstream_id"),
            workstream_name=ws.get("name") if isinstance(ws, dict) else None,
            business_unit_id=ws.get("business_unit_id") if isinstance(ws, dict) else None,
            business_unit_name=bu.get("name") if isinstance(bu, dict) else None,
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
            value_logic=row.get("value_logic"),
            dependencies_text=row.get("dependencies_text"),
            planned_start=row.get("planned_start"),
            actual_start=row.get("actual_start"),
            planned_end=row.get("planned_end"),
            actual_end=row.get("actual_end"),
            pressure_score=str(row["pressure_score"]) if row.get("pressure_score") is not None else None,
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
        schedule = Decimal("2.0") # Base
        
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
            kpi_performance=Decimal("0"), # Placeholder
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
            breakdown.schedule * weights["schedule"] +
            breakdown.milestone_health * weights["milestone_health"] +
            breakdown.risk_exposure * weights["risk_exposure"] +
            breakdown.financial * weights["financial"] +
            breakdown.self_reported * weights["self_reported"]
        )
        
        return total_score.quantize(Decimal("0.1")), breakdown

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
            actual_entries = [entry for entry in kpi_entries if entry.get("value_actual") is not None]
            latest = sorted(
                actual_entries,
                key=lambda entry: (entry["year"], entry.get("quarter") or 5),
                reverse=True,
            )[0] if actual_entries else None
            latest_year = latest["year"] if latest else None

            def total_for(rows: list[dict], key: str) -> Decimal | None:
                values = [Decimal(str(row[key])) for row in rows if row.get(key) is not None]
                return sum(values, Decimal("0")) if values else None

            this_year_rows = [
                entry for entry in actual_entries
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
                    if this_year_rows else None,
                    all_time_actual=str(actual_total) if actual_total is not None else None,
                )
            )
        return indicators
