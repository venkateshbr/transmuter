from decimal import Decimal
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.repositories.dashboard import DashboardRepository


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self.repo = repository

    def get_dashboard_data(
        self,
        user_id: UUID,
        role: str,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        target_year: int | None = None,
    ) -> dict[str, Any]:
        # 1. Initiatives & Filters
        owner_user_id = str(user_id) if role == "initiative_owner" else None
        all_inits = self.repo.get_initiatives_for_dashboard(owner_user_id=owner_user_id)
        filtered_inits = [
            i
            for i in all_inits
            if self._matches_filters(i, business_unit_id, workstream_id, rag_status)
        ]
        initiative_ids = {i["id"] for i in filtered_inits}

        # 2. Aggregates
        total_initiatives = len(filtered_inits)
        at_risk = len([i for i in filtered_inits if i["rag_status"] == "red"])

        pipeline_by_stage = {
            "scoping": len([i for i in filtered_inits if i["stage"] == "scoping"]),
            "in_progress": len([i for i in filtered_inits if i["stage"] == "in_progress"]),
            "complete": len([i for i in filtered_inits if i["stage"] == "complete"]),
        }

        rag_breakdown = {
            "red": at_risk,
            "amber": len([i for i in filtered_inits if i["rag_status"] == "amber"]),
            "green": len([i for i in filtered_inits if i["rag_status"] == "green"]),
        }

        # 3. Pressure
        scores = [
            float(i["pressure_score"]) for i in filtered_inits if i["pressure_score"] is not None
        ]
        avg_pressure = sum(scores) / len(scores) if scores else 0

        # 4. Risks Heatmap
        risks = self.repo.get_risks_for_heatmap()
        risk_heatmap = {}
        for r in risks:
            if initiative_ids and r.get("initiative_id") not in initiative_ids:
                continue
            key = f"{r['impact']}_{r['likelihood']}"
            risk_heatmap[key] = risk_heatmap.get(key, 0) + 1

        # 5. KPIs
        kpis, entries = self.repo.get_kpi_data()
        kpi_pulse = self._calculate_kpi_pulse(kpis, entries, initiative_ids)

        # 6. Financials
        fin_entries, costs = self.repo.get_financial_summary_data()
        value_bridge = self._calculate_value_bridge(fin_entries, costs, initiative_ids)
        value_matrix = self._calculate_value_matrix(filtered_inits, fin_entries, costs, target_year)

        # 7. Other data
        my_milestones = self.repo.get_my_milestones(user_id)
        # Filter milestones by initiative if dashboard is filtered
        if initiative_ids:
            my_milestones = [m for m in my_milestones if m.get("initiative_id") in initiative_ids][
                :5
            ]

        pending_count = self.repo.get_pending_approvals_count()

        all_actions = self.repo.get_my_actions(user_id)
        closed_statuses = {"done", "complete", "completed", "closed"}
        my_actions = [
            a
            for a in all_actions
            if a.get("status") not in closed_statuses
            and (not initiative_ids or a.get("initiative_id") in initiative_ids)
        ][:5]

        recent_activity = [
            a
            for a in self.repo.get_recent_activity()
            if not initiative_ids or a.get("initiative_id") in initiative_ids
        ][:5]

        bus, wss = self.repo.get_filter_options()
        rag_values = sorted({i.get("rag_status") for i in all_inits if i.get("rag_status")})

        return {
            "summary": {
                "total_initiatives": total_initiatives,
                "at_risk": at_risk,
                "pending_approvals": pending_count,
            },
            "pipeline_by_stage": pipeline_by_stage,
            "rag_breakdown": rag_breakdown,
            "my_milestones": my_milestones,
            "portfolio_pressure": {
                "score": avg_pressure,
                "label": "Low"
                if avg_pressure < 3.4
                else "Medium"
                if avg_pressure < 6.7
                else "High",
            },
            "risk_heatmap": risk_heatmap,
            "my_actions": my_actions,
            "kpi_pulse": kpi_pulse,
            "value_bridge": value_bridge,
            "value_matrix": value_matrix,
            "recent_activity": recent_activity,
            "available_filters": {
                "business_units": bus,
                "workstreams": wss,
                "rag_statuses": [{"id": v, "name": v.title()} for v in rag_values],
            },
        }

    def get_dashboard_slice(
        self,
        key: str,
        user_id: UUID,
        role: str,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        target_year: int | None = None,
    ) -> Any:
        data = self.get_dashboard_data(
            user_id=user_id,
            role=role,
            business_unit_id=business_unit_id,
            workstream_id=workstream_id,
            rag_status=rag_status,
            target_year=target_year,
        )
        return data[key]

    def get_pipeline_by_stage_detail(
        self,
        user_id: UUID,
        role: str,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
    ) -> dict[str, Any]:
        owner_user_id = str(user_id) if role == "initiative_owner" else None
        initiatives = [
            i
            for i in self.repo.get_initiatives_for_dashboard(owner_user_id=owner_user_id)
            if self._matches_filters(i, business_unit_id, workstream_id, rag_status)
        ]
        entries, costs = self.repo.get_financial_summary_data()
        return self._calculate_pipeline_by_stage_detail(initiatives, entries, costs)

    def generate_executive_summary_pdf(
        self,
        user_id: UUID,
        role: str,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        target_year: int | None = None,
    ) -> bytes:
        summary = self.generate_executive_summary(
            user_id=user_id,
            role=role,
            business_unit_id=business_unit_id,
            workstream_id=workstream_id,
            rag_status=rag_status,
            target_year=target_year,
        )
        self._trace_executive_summary(summary)
        return _render_summary_pdf(summary)

    def generate_executive_summary(
        self,
        user_id: UUID,
        role: str,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        target_year: int | None = None,
    ) -> dict[str, Any]:
        data = self.get_dashboard_data(
            user_id=user_id,
            role=role,
            business_unit_id=business_unit_id,
            workstream_id=workstream_id,
            rag_status=rag_status,
            target_year=target_year,
        )
        owner_user_id = str(user_id) if role == "initiative_owner" else None
        initiatives = [
            item
            for item in self.repo.get_initiatives_for_dashboard(owner_user_id=owner_user_id)
            if self._matches_filters(item, business_unit_id, workstream_id, rag_status)
        ]
        initiative_ids = {item["id"] for item in initiatives}
        risks = [
            item
            for item in self.repo.get_open_risks_detail()
            if not initiative_ids or item.get("initiative_id") in initiative_ids
        ]

        top_initiatives = sorted(
            initiatives,
            key=lambda item: Decimal(str(item.get("pressure_score") or "0")),
            reverse=True,
        )[:5]
        at_risk = [
            item for item in initiatives if item.get("rag_status") in {"red", "amber"}
        ][:5]

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "filters": {
                "business_unit_id": business_unit_id,
                "workstream_id": workstream_id,
                "rag_status": rag_status,
                "target_year": target_year,
            },
            "portfolio_health": {
                "total_initiatives": data["summary"]["total_initiatives"],
                "at_risk": data["summary"]["at_risk"],
                "pending_approvals": data["summary"]["pending_approvals"],
                "pressure_score": round(float(data["portfolio_pressure"]["score"]), 1),
                "pressure_label": data["portfolio_pressure"]["label"],
                "rag_breakdown": data["rag_breakdown"],
                "pipeline_by_stage": data["pipeline_by_stage"],
            },
            "top_initiatives": [_initiative_summary(item) for item in top_initiatives],
            "at_risk_items": [_initiative_summary(item) for item in at_risk],
            "financial_overview": data["value_bridge"],
            "kpi_pulse": {
                key: data["kpi_pulse"].get(key)
                for key in ("total_kpis", "hitting_base", "missing_base", "no_actuals", "health_score")
            },
            "key_risks": [_risk_summary(item) for item in risks[:5]],
            "recommended_actions": _recommended_actions(data, at_risk, risks),
        }

    def _trace_executive_summary(self, summary: dict[str, Any]) -> None:
        try:
            from app.core.observability import get_langfuse

            langfuse = get_langfuse()
            if not langfuse:
                return
            health = summary["portfolio_health"]
            with langfuse.start_as_current_observation(
                name="executive-summary-generation",
                input={
                    "filters": summary["filters"],
                    "total_initiatives": health["total_initiatives"],
                    "at_risk": health["at_risk"],
                },
                tags=["executive-summary", "dashboard"],
            ) as observation:
                observation.update(
                    output={
                        "sections": [
                            "portfolio_health",
                            "top_initiatives",
                            "at_risk_items",
                            "financial_overview",
                            "key_risks",
                            "recommended_actions",
                        ],
                    }
                )
        except Exception:
            return

    def _matches_filters(
        self,
        row: dict[str, Any],
        bu_id: str | None,
        ws_id: str | None,
        rag: str | None,
    ) -> bool:
        ws = row.get("workstreams") or {}
        if bu_id and ws.get("business_unit_id") != bu_id:
            return False
        if ws_id and row.get("workstream_id") != ws_id:
            return False
        return not rag or row.get("rag_status") == rag

    def _calculate_kpi_pulse(
        self,
        kpis: list[dict[str, Any]],
        entries: list[dict[str, Any]],
        initiative_ids: set[str],
    ) -> dict[str, Any]:
        scoped_kpis = [
            k for k in kpis if not initiative_ids or k.get("initiative_id") in initiative_ids
        ]
        entries_by_kpi: dict[str, list[dict[str, Any]]] = {}
        for e in entries:
            entries_by_kpi.setdefault(e["kpi_id"], []).append(e)

        hitting = 0
        missing = 0
        no_data = 0
        items: list[dict[str, Any]] = []

        for k in scoped_kpis:
            actual_entries = [
                e for e in entries_by_kpi.get(k["id"], []) if e.get("value_actual") is not None
            ]
            latest = (
                sorted(
                    actual_entries,
                    key=lambda e: (e.get("year") or 0, e.get("quarter") or 5),
                    reverse=True,
                )[0]
                if actual_entries
                else None
            )

            if not latest:
                no_data += 1
                status = "no_data"
            elif Decimal(str(latest.get("value_actual"))) >= Decimal(str(latest.get("value_base"))):
                hitting += 1
                status = "on_track"
            else:
                missing += 1
                status = "at_risk"

            items.append(
                {
                    "id": k["id"],
                    "name": k["name"],
                    "unit": k.get("unit"),
                    "initiative": k.get("initiatives"),
                    "status": status,
                    "actual": str(latest.get("value_actual")) if latest else None,
                    "base": str(latest.get("value_base")) if latest else None,
                }
            )

        tracked = hitting + missing
        health = (
            Decimal("0") if tracked == 0 else (Decimal(hitting) / Decimal(tracked)) * Decimal("100")
        )

        return {
            "total_kpis": len(scoped_kpis),
            "hitting_base": hitting,
            "missing_base": missing,
            "no_actuals": no_data,
            "health_score": str(health.quantize(Decimal("0.1"))),
            "items": items[:5],
        }

    def _calculate_value_bridge(
        self,
        entries: list[dict[str, Any]],
        costs: list[dict[str, Any]],
        initiative_ids: set[str],
    ) -> dict[str, str]:
        def _dec(value: object) -> Decimal:
            return Decimal(str(value)) if value is not None else Decimal("0")

        def _money(value: Decimal) -> str:
            return str(value.quantize(Decimal("0.0001")))

        scoped_entries = [
            e for e in entries if not initiative_ids or e.get("initiative_id") in initiative_ids
        ]
        scoped_costs = [
            c for c in costs if not initiative_ids or c.get("initiative_id") in initiative_ids
        ]

        benefits_base = sum((_dec(e.get("gm_uplift_base")) for e in scoped_entries), Decimal("0"))
        benefits_high = sum((_dec(e.get("gm_uplift_high")) for e in scoped_entries), Decimal("0"))
        benefits_actual = sum(
            (_dec(e.get("gm_uplift_actual")) for e in scoped_entries), Decimal("0")
        )
        costs_plan = sum((_dec(c.get("amount_plan")) for c in scoped_costs), Decimal("0"))
        costs_actual = sum((_dec(c.get("amount_actual")) for c in scoped_costs), Decimal("0"))

        return {
            "benefits_base": _money(benefits_base),
            "benefits_high": _money(benefits_high),
            "benefits_actual": _money(benefits_actual),
            "costs_plan": _money(costs_plan),
            "costs_actual": _money(costs_actual),
            "net_base": _money(benefits_base - costs_plan),
            "net_high": _money(benefits_high - costs_plan),
            "net_actual": _money(benefits_actual - costs_actual),
        }

    def _calculate_pipeline_by_stage_detail(
        self,
        initiatives: list[dict[str, Any]],
        entries: list[dict[str, Any]],
        costs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        def _dec(value: object) -> Decimal:
            return Decimal(str(value)) if value is not None else Decimal("0")

        def _money(value: Decimal) -> str:
            return str(value.quantize(Decimal("0.0001")))

        initiative_ids_by_stage: dict[str, set[str]] = {
            "scoping": set(),
            "in_progress": set(),
            "complete": set(),
        }
        for initiative in initiatives:
            stage = initiative.get("stage") or "scoping"
            initiative_ids_by_stage.setdefault(stage, set()).add(initiative["id"])

        result: dict[str, Any] = {}
        for stage, ids in initiative_ids_by_stage.items():
            scoped_entries = [e for e in entries if e.get("initiative_id") in ids]
            scoped_costs = [c for c in costs if c.get("initiative_id") in ids]
            benefits_base = sum((_dec(e.get("gm_uplift_base")) for e in scoped_entries), Decimal("0"))
            benefits_high = sum((_dec(e.get("gm_uplift_high")) for e in scoped_entries), Decimal("0"))
            benefits_actual = sum(
                (_dec(e.get("gm_uplift_actual")) for e in scoped_entries), Decimal("0")
            )
            costs_plan = sum((_dec(c.get("amount_plan")) for c in scoped_costs), Decimal("0"))
            costs_actual = sum((_dec(c.get("amount_actual")) for c in scoped_costs), Decimal("0"))
            result[stage] = {
                "count": len(ids),
                "benefits_base": _money(benefits_base),
                "benefits_high": _money(benefits_high),
                "benefits_actual": _money(benefits_actual),
                "costs_plan": _money(costs_plan),
                "costs_actual": _money(costs_actual),
                "net_base": _money(benefits_base - costs_plan),
                "net_high": _money(benefits_high - costs_plan),
                "net_actual": _money(benefits_actual - costs_actual),
            }
        return result

    def _calculate_value_matrix(
        self,
        initiatives: list[dict[str, Any]],
        entries: list[dict[str, Any]],
        costs: list[dict[str, Any]],
        target_year: int | None,
    ) -> dict[str, Any]:
        def _dec(value: object) -> Decimal:
            return Decimal(str(value)) if value is not None else Decimal("0")

        def _money(value: Decimal) -> str:
            return str(value.quantize(Decimal("0.0001")))

        def _label(value: str | None, fallback: str) -> str:
            return (value or fallback).replace("_", " ").title()

        scoped_ids = {i["id"] for i in initiatives}
        scoped_entries = [e for e in entries if e.get("initiative_id") in scoped_ids]
        scoped_costs = [c for c in costs if c.get("initiative_id") in scoped_ids]
        available_years = sorted(
            {int(e["year"]) for e in [*scoped_entries, *scoped_costs] if e.get("year") is not None}
        )
        selected_year = (
            target_year
            if target_year in available_years
            else (max(available_years) if available_years else target_year)
        )

        tags = ["automation", "offshoring", "commercial", "other"]
        for initiative in initiatives:
            tag = initiative.get("tag") or "other"
            if tag not in tags:
                tags.append(tag)

        row_lookup: dict[str, dict[str, Any]] = {}
        for initiative in initiatives:
            ws = initiative.get("workstreams") or {}
            workstream_id = initiative.get("workstream_id") or "unassigned"
            if workstream_id not in row_lookup:
                row_lookup[workstream_id] = {
                    "workstream_id": None if workstream_id == "unassigned" else workstream_id,
                    "workstream_name": ws.get("name") or "Unassigned",
                    "business_unit_name": (ws.get("business_units") or {}).get("name"),
                    "cells": {tag: self._empty_matrix_cell(tag) for tag in tags},
                    "total": self._empty_matrix_cell("total"),
                }

        if not row_lookup:
            row_lookup["empty"] = {
                "workstream_id": None,
                "workstream_name": "No active initiatives",
                "business_unit_name": None,
                "cells": {tag: self._empty_matrix_cell(tag) for tag in tags},
                "total": self._empty_matrix_cell("total"),
            }

        entries_by_initiative: dict[str, list[dict[str, Any]]] = {}
        for entry in scoped_entries:
            if selected_year is not None and entry.get("year") != selected_year:
                continue
            entries_by_initiative.setdefault(entry["initiative_id"], []).append(entry)

        costs_by_initiative: dict[str, list[dict[str, Any]]] = {}
        for cost in scoped_costs:
            if selected_year is not None and cost.get("year") != selected_year:
                continue
            costs_by_initiative.setdefault(cost["initiative_id"], []).append(cost)

        initiative_values: dict[str, dict[str, Decimal]] = {}
        for initiative_id in scoped_ids:
            initiative_entries = entries_by_initiative.get(initiative_id, [])
            annual_rows = [e for e in initiative_entries if e.get("quarter") is None]
            rows_to_sum = annual_rows or initiative_entries
            initiative_costs = costs_by_initiative.get(initiative_id, [])
            annual_costs = [c for c in initiative_costs if c.get("quarter") is None]
            costs_to_sum = annual_costs or initiative_costs
            recurring_plan = sum(
                (_dec(c.get("amount_plan")) for c in costs_to_sum if c.get("is_recurring")),
                Decimal("0"),
            )
            recurring_actual = sum(
                (_dec(c.get("amount_actual")) for c in costs_to_sum if c.get("is_recurring")),
                Decimal("0"),
            )
            one_time_plan = sum(
                (_dec(c.get("amount_plan")) for c in costs_to_sum if not c.get("is_recurring")),
                Decimal("0"),
            )
            one_time_actual = sum(
                (_dec(c.get("amount_actual")) for c in costs_to_sum if not c.get("is_recurring")),
                Decimal("0"),
            )
            gm_base = sum((_dec(e.get("gm_uplift_base")) for e in rows_to_sum), Decimal("0"))
            gm_high = sum((_dec(e.get("gm_uplift_high")) for e in rows_to_sum), Decimal("0"))
            gm_actual = sum((_dec(e.get("gm_uplift_actual")) for e in rows_to_sum), Decimal("0"))
            initiative_values[initiative_id] = {
                "base": gm_base,
                "high": gm_high,
                "actual": gm_actual,
                "gross_margin_base": gm_base,
                "gross_margin_high": gm_high,
                "gross_margin_actual": gm_actual,
                "recurring_costs_plan": recurring_plan,
                "recurring_costs_actual": recurring_actual,
                "one_time_costs_plan": one_time_plan,
                "one_time_costs_actual": one_time_actual,
                "net_value_base": gm_base - recurring_plan - one_time_plan,
                "net_value_high": gm_high - recurring_plan - one_time_plan,
                "net_value_actual": gm_actual - recurring_actual - one_time_actual,
            }

        for initiative in initiatives:
            values = initiative_values.get(
                initiative["id"],
                {
                    "base": Decimal("0"),
                    "high": Decimal("0"),
                    "actual": Decimal("0"),
                    "gross_margin_base": Decimal("0"),
                    "gross_margin_high": Decimal("0"),
                    "gross_margin_actual": Decimal("0"),
                    "recurring_costs_plan": Decimal("0"),
                    "recurring_costs_actual": Decimal("0"),
                    "one_time_costs_plan": Decimal("0"),
                    "one_time_costs_actual": Decimal("0"),
                    "net_value_base": Decimal("0"),
                    "net_value_high": Decimal("0"),
                    "net_value_actual": Decimal("0"),
                },
            )
            tag = initiative.get("tag") or "other"
            workstream_id = initiative.get("workstream_id") or "unassigned"
            row = row_lookup[workstream_id]
            cell = row["cells"].setdefault(tag, self._empty_matrix_cell(tag))
            if not any(
                values[field]
                for field in (
                    "gross_margin_base",
                    "gross_margin_high",
                    "gross_margin_actual",
                    "recurring_costs_plan",
                    "recurring_costs_actual",
                    "one_time_costs_plan",
                    "one_time_costs_actual",
                )
            ):
                continue
            self._add_initiative_to_cell(cell, initiative, values)
            self._add_initiative_to_cell(row["total"], initiative, values)

        total_cells = {tag: self._empty_matrix_cell(tag) for tag in tags}
        grand_total = self._empty_matrix_cell("total")
        for row in row_lookup.values():
            for tag in tags:
                cell = row["cells"].setdefault(tag, self._empty_matrix_cell(tag))
                self._finalize_matrix_cell(cell, _money)
                self._merge_matrix_cell(total_cells[tag], cell)
            self._finalize_matrix_cell(row["total"], _money)
            self._merge_matrix_cell(grand_total, row["total"])

        for cell in total_cells.values():
            self._finalize_matrix_cell(cell, _money)
        self._finalize_matrix_cell(grand_total, _money)

        return {
            "selected_year": selected_year,
            "available_years": available_years,
            "tags": [{"id": tag, "label": _label(tag, tag)} for tag in tags],
            "rows": sorted(row_lookup.values(), key=lambda r: r["workstream_name"]),
            "totals": {"cells": total_cells, "total": grand_total},
        }

    def _empty_matrix_cell(self, tag: str) -> dict[str, Any]:
        return {
            "tag": tag,
            "base": Decimal("0"),
            "high": Decimal("0"),
            "actual": Decimal("0"),
            "initiative_count": 0,
            "initiatives": [],
        }

    def _add_initiative_to_cell(
        self,
        cell: dict[str, Any],
        initiative: dict[str, Any],
        values: dict[str, Decimal],
    ) -> None:
        cell["base"] += values["base"]
        cell["high"] += values["high"]
        cell["actual"] += values["actual"]
        cell["initiative_count"] += 1
        cell["initiatives"].append(
            {
                "id": initiative["id"],
                "name": initiative["name"],
                "initiative_code": initiative.get("initiative_code"),
                "stage": initiative.get("stage"),
                "rag_status": initiative.get("rag_status"),
                "base": values["base"],
                "high": values["high"],
                "actual": values["actual"],
                "gross_margin_base": values["gross_margin_base"],
                "gross_margin_high": values["gross_margin_high"],
                "gross_margin_actual": values["gross_margin_actual"],
                "recurring_costs_plan": values["recurring_costs_plan"],
                "recurring_costs_actual": values["recurring_costs_actual"],
                "one_time_costs_plan": values["one_time_costs_plan"],
                "one_time_costs_actual": values["one_time_costs_actual"],
                "net_value_base": values["net_value_base"],
                "net_value_high": values["net_value_high"],
                "net_value_actual": values["net_value_actual"],
            }
        )

    def _merge_matrix_cell(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        target["base"] += Decimal(str(source["base"]))
        target["high"] += Decimal(str(source["high"]))
        target["actual"] += Decimal(str(source["actual"]))
        target["initiative_count"] += int(source["initiative_count"])
        target["initiatives"].extend(source["initiatives"])

    def _finalize_matrix_cell(self, cell: dict[str, Any], money_formatter: Any) -> None:
        cell["base"] = money_formatter(Decimal(str(cell["base"])))
        cell["high"] = money_formatter(Decimal(str(cell["high"])))
        cell["actual"] = money_formatter(Decimal(str(cell["actual"])))
        for initiative in cell["initiatives"]:
            for field in (
                "base",
                "high",
                "actual",
                "gross_margin_base",
                "gross_margin_high",
                "gross_margin_actual",
                "recurring_costs_plan",
                "recurring_costs_actual",
                "one_time_costs_plan",
                "one_time_costs_actual",
                "net_value_base",
                "net_value_high",
                "net_value_actual",
            ):
                initiative[field] = money_formatter(Decimal(str(initiative[field])))


def _initiative_summary(item: dict[str, Any]) -> dict[str, Any]:
    workstream = item.get("workstreams") or {}
    return {
        "id": item.get("id"),
        "code": item.get("initiative_code"),
        "name": item.get("name"),
        "stage": item.get("stage"),
        "rag_status": item.get("rag_status"),
        "pressure_score": item.get("pressure_score"),
        "workstream": workstream.get("name"),
        "business_unit": (workstream.get("business_units") or {}).get("name"),
    }


def _risk_summary(item: dict[str, Any]) -> dict[str, Any]:
    initiative = item.get("initiatives") or {}
    return {
        "id": item.get("id"),
        "description": item.get("description"),
        "type": item.get("type"),
        "impact": item.get("impact"),
        "likelihood": item.get("likelihood"),
        "rating": item.get("rating"),
        "initiative": initiative.get("name"),
        "initiative_code": initiative.get("initiative_code"),
    }


def _recommended_actions(
    data: dict[str, Any],
    at_risk: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = []
    if at_risk:
        actions.append(
            f"Run executive intervention on {len(at_risk)} red/amber initiatives this week."
        )
    if risks:
        actions.append(f"Review top {min(len(risks), 5)} open risks and confirm mitigation owners.")
    if int(data["summary"].get("pending_approvals") or 0) > 0:
        actions.append("Clear pending gate approvals to unblock delivery decisions.")
    kpi_pulse = data.get("kpi_pulse") or {}
    if int(kpi_pulse.get("missing_base") or 0) > 0:
        actions.append("Ask initiative owners to recover KPIs currently missing base.")
    if not actions:
        actions.append("Maintain current cadence and monitor for emerging delivery pressure.")
    return actions


def _render_summary_pdf(summary: dict[str, Any]) -> bytes:
    lines = _summary_lines(summary)
    pages = [lines[index : index + 48] for index in range(0, len(lines), 48)] or [[]]
    objects: list[bytes] = []

    def add_object(value: bytes) -> int:
        objects.append(value)
        return len(objects)

    catalog_id = add_object(b"")
    pages_id = add_object(b"")
    page_ids: list[int] = []
    for page_lines in pages:
        content = _page_content(page_lines)
        content_id = add_object(
            b"<< /Length "
            + str(len(content)).encode("ascii")
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        )
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
                f"/BaseFont /Helvetica >> >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        page_ids.append(page_id)

    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
    ).encode("ascii")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def _summary_lines(summary: dict[str, Any]) -> list[str]:
    health = summary["portfolio_health"]
    financials = summary["financial_overview"]
    kpis = summary["kpi_pulse"]
    lines = [
        "Transmuter Executive Summary",
        f"Generated: {summary['generated_at']}",
        "",
        "Portfolio Health",
        f"- Total initiatives: {health['total_initiatives']}",
        f"- Red initiatives: {health['at_risk']}",
        f"- Pending approvals: {health['pending_approvals']}",
        f"- Pressure: {health['pressure_score']} ({health['pressure_label']})",
        f"- RAG mix: {health['rag_breakdown']}",
        f"- Pipeline: {health['pipeline_by_stage']}",
        "",
        "Financial Overview",
        f"- Benefits base: {financials.get('benefits_base', '0.0000')}",
        f"- Benefits actual: {financials.get('benefits_actual', '0.0000')}",
        f"- Costs plan: {financials.get('costs_plan', '0.0000')}",
        f"- Costs actual: {financials.get('costs_actual', '0.0000')}",
        f"- Net base: {financials.get('net_base', '0.0000')}",
        f"- Net actual: {financials.get('net_actual', '0.0000')}",
        "",
        "KPI Pulse",
        f"- Total KPIs: {kpis.get('total_kpis', 0)}",
        f"- Hitting base: {kpis.get('hitting_base', 0)}",
        f"- Missing base: {kpis.get('missing_base', 0)}",
        f"- Health score: {kpis.get('health_score', '0.0')}%",
        "",
        "Top Initiatives",
        *_bullet_initiatives(summary["top_initiatives"]),
        "",
        "At-Risk Items",
        *_bullet_initiatives(summary["at_risk_items"]),
        "",
        "Key Risks",
        *_bullet_risks(summary["key_risks"]),
        "",
        "Recommended Actions",
        *[f"- {action}" for action in summary["recommended_actions"]],
    ]
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap_line(line, 90))
    return wrapped


def _bullet_initiatives(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- None in current filter scope."]
    return [
        "- {code} {name}: {rag_status}, {stage}, pressure {pressure_score}".format(
            code=item.get("code") or "",
            name=item.get("name") or "Untitled",
            rag_status=item.get("rag_status") or "unknown",
            stage=item.get("stage") or "unknown",
            pressure_score=item.get("pressure_score") or "n/a",
        ).strip()
        for item in items
    ]


def _bullet_risks(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- No open risks in current filter scope."]
    return [
        "- {description} ({impact}/{likelihood}) [{initiative}]".format(
            description=item.get("description") or "Open risk",
            impact=item.get("impact") or "unknown",
            likelihood=item.get("likelihood") or "unknown",
            initiative=item.get("initiative") or "Portfolio",
        )
        for item in items
    ]


def _wrap_line(line: str, width: int) -> list[str]:
    text = line.encode("latin-1", errors="replace").decode("latin-1")
    if len(text) <= width:
        return [text]
    words = text.split()
    rows: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            rows.append(current)
            current = word
        else:
            current = candidate
    if current:
        rows.append(current)
    return rows


def _page_content(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "54 748 Td", "15 TL"]
    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
