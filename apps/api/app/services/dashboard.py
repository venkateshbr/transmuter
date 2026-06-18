from decimal import Decimal
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
        priority: str | None = None,
        tag: str | None = None,
        target_year: int | None = None,
    ) -> dict[str, Any]:
        # 1. Initiatives & Filters
        owner_user_id = str(user_id) if role == "initiative_owner" else None
        all_inits = self.repo.get_initiatives_for_dashboard(owner_user_id=owner_user_id)
        business_unit_ids = self._split_filter_values(business_unit_id)
        workstream_ids = self._split_filter_values(workstream_id)
        rag_statuses = self._split_filter_values(rag_status)
        priorities = self._split_filter_values(priority)
        tags = self._split_filter_values(tag)
        filtered_inits = [
            i
            for i in all_inits
            if self._matches_filters(
                i, business_unit_ids, workstream_ids, rag_statuses, priorities, tags
            )
        ]
        initiative_ids = {i["id"] for i in filtered_inits}

        # 2. Aggregates
        total_initiatives = len(filtered_inits)
        at_risk = len([i for i in filtered_inits if i["rag_status"] == "red"])

        stage_definitions = self.repo.get_stage_gate_definitions()
        stage_options = self._stage_options(stage_definitions, all_inits)
        pipeline_by_stage = {
            stage["id"]: len([i for i in filtered_inits if i["stage"] == stage["id"]])
            for stage in stage_options
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
        metric_values, costs, metric_definitions, scenarios = self.repo.get_financial_summary_data()
        fin_entries = self._configurable_financial_entries(
            metric_values,
            metric_definitions,
            scenarios,
        )
        value_matrix = self._calculate_value_matrix(filtered_inits, fin_entries, costs, target_year)
        value_bridge = self._calculate_value_bridge(
            fin_entries,
            costs,
            initiative_ids,
            value_matrix.get("selected_year"),
        )

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
        workstream_targets = self._calculate_workstream_targets(
            wss, self.repo.get_workstream_target_locks()
        )
        stage_gate_waterline = self._calculate_stage_gate_waterline(
            workstream_targets,
            value_matrix,
            stage_definitions,
        )
        rag_values = sorted({i.get("rag_status") for i in all_inits if i.get("rag_status")})
        priority_values = self._ordered_values(
            {i.get("priority") for i in all_inits if i.get("priority")},
            ["high", "medium", "low"],
        )
        tag_values = sorted({i.get("tag") for i in all_inits if i.get("tag")})

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
            "workstream_targets": workstream_targets,
            "stage_gate_waterline": stage_gate_waterline,
            "recent_activity": recent_activity,
            "available_filters": {
                "business_units": bus,
                "workstreams": wss,
                "stages": stage_options,
                "rag_statuses": [{"id": v, "name": v.title()} for v in rag_values],
                "priorities": [{"id": v, "name": v.title()} for v in priority_values],
                "tags": [{"id": v, "name": self._label(v)} for v in tag_values],
            },
        }

    def generate_executive_summary(
        self,
        user_id: UUID,
        role: str,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        priority: str | None = None,
        tag: str | None = None,
        target_year: int | None = None,
    ) -> dict[str, Any]:
        data = self.get_dashboard_data(
            user_id=user_id,
            role=role,
            business_unit_id=business_unit_id,
            workstream_id=workstream_id,
            rag_status=rag_status,
            priority=priority,
            tag=tag,
            target_year=target_year,
        )
        summary = data["summary"]
        value = data["value_bridge"]
        kpi = data["kpi_pulse"]
        risks = data["risk_heatmap"]
        at_risk_items = [
            item
            for item in data.get("recent_activity", [])
            if item.get("rag_status") in {"red", "amber"}
        ][:5]
        actions = []
        if summary["at_risk"]:
            actions.append(
                f"Review {summary['at_risk']} red initiatives before the next steering forum."
            )
        if summary["pending_approvals"]:
            actions.append(f"Resolve {summary['pending_approvals']} pending gate approvals.")
        if kpi.get("missing_base"):
            actions.append(
                f"Refresh recovery actions for {kpi['missing_base']} KPIs missing base case."
            )
        if not actions:
            actions.append("Continue weekly portfolio cadence and refresh value evidence.")
        return {
            "portfolio_health": {
                "total_initiatives": summary["total_initiatives"],
                "at_risk": summary["at_risk"],
                "pending_approvals": summary["pending_approvals"],
                "kpi_health_score": kpi.get("health_score", "0.0"),
            },
            "financial_overview": {
                "benefits_base": value.get("benefits_base", "0.0000"),
                "benefits_high": value.get("benefits_high", "0.0000"),
                "benefits_actual": value.get("benefits_actual", "0.0000"),
                "costs_plan": value.get("costs_plan", "0.0000"),
                "costs_actual": value.get("costs_actual", "0.0000"),
                "net_base": value.get("net_base", "0.0000"),
                "net_actual": value.get("net_actual", "0.0000"),
            },
            "top_initiatives": data.get("value_matrix", {})
            .get("totals", {})
            .get("total", {})
            .get("initiatives", [])[:5],
            "at_risk_items": at_risk_items,
            "key_risks": risks,
            "recommended_actions": actions,
        }

    def generate_executive_summary_pdf(
        self,
        user_id: UUID,
        role: str,
        business_unit_id: str | None = None,
        workstream_id: str | None = None,
        rag_status: str | None = None,
        priority: str | None = None,
        tag: str | None = None,
        target_year: int | None = None,
    ) -> bytes:
        summary = self.generate_executive_summary(
            user_id=user_id,
            role=role,
            business_unit_id=business_unit_id,
            workstream_id=workstream_id,
            rag_status=rag_status,
            priority=priority,
            tag=tag,
            target_year=target_year,
        )
        self._trace_executive_summary(summary)
        return _simple_pdf(_summary_lines(summary))

    def _trace_executive_summary(self, summary: dict[str, Any]) -> None:
        try:
            from app.core.observability import get_langfuse

            langfuse = get_langfuse()
            if not langfuse:
                return
            with langfuse.start_as_current_observation(
                name="executive_summary_generation",
                as_type="agent",
                input={"dashboard_context": summary["portfolio_health"]},
                metadata={"source": "dashboard_export"},
            ):
                langfuse.update_current_span(output=summary)
            langfuse.flush()
        except Exception:
            return

    def _matches_filters(
        self,
        row: dict[str, Any],
        bu_ids: set[str],
        ws_ids: set[str],
        rag_statuses: set[str],
        priorities: set[str],
        tags: set[str],
    ) -> bool:
        row_bu_ids = {
            str(link.get("business_unit_id"))
            for link in row.get("initiative_business_units") or []
            if link.get("business_unit_id")
        }
        if bu_ids and not (row_bu_ids & bu_ids):
            return False
        if ws_ids and row.get("workstream_id") not in ws_ids:
            return False
        if rag_statuses and row.get("rag_status") not in rag_statuses:
            return False
        if priorities and row.get("priority") not in priorities:
            return False
        return not tags or row.get("tag") in tags

    @staticmethod
    def _split_filter_values(value: str | None) -> set[str]:
        if not value:
            return set()
        return {part.strip() for part in value.split(",") if part.strip()}

    def _calculate_workstream_targets(
        self,
        workstreams: list[dict[str, Any]],
        locks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        def _dec(value: object) -> Decimal:
            return Decimal(str(value)) if value is not None else Decimal("0")

        def _money(value: Decimal) -> str:
            return str(value.quantize(Decimal("0.0001")))

        latest_by_workstream: dict[str, dict[str, Any]] = {}
        for row in locks:
            latest_by_workstream[str(row.get("workstream_id"))] = row
        workstream_name = {str(row["id"]): row.get("name") for row in workstreams}
        items = []
        for workstream_id, row in latest_by_workstream.items():
            target = _dec(row.get("locked_run_rate_value"))
            actual = _dec(row.get("actual_total"))
            items.append(
                {
                    "workstream_id": workstream_id,
                    "workstream_name": workstream_name.get(workstream_id) or "Workstream",
                    "version": row.get("version"),
                    "lock_date": row.get("lock_date"),
                    "locked_at": row.get("locked_at"),
                    "locked_run_rate_value": _money(target),
                    "actual_total": _money(actual),
                    "variance": _money(actual - target),
                }
            )
        total_target = sum(
            (_dec(row.get("locked_run_rate_value")) for row in latest_by_workstream.values()),
            Decimal("0"),
        )
        total_actual = sum(
            (_dec(row.get("actual_total")) for row in latest_by_workstream.values()), Decimal("0")
        )
        return {
            "items": sorted(items, key=lambda item: item["workstream_name"]),
            "locked_workstreams": len(items),
            "locked_run_rate_value": _money(total_target),
            "actual_total": _money(total_actual),
            "variance": _money(total_actual - total_target),
        }

    def _calculate_stage_gate_waterline(
        self,
        workstream_targets: dict[str, Any],
        value_matrix: dict[str, Any],
        stage_definitions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        def _dec(value: object) -> Decimal:
            return Decimal(str(value)) if value is not None else Decimal("0")

        def _money(value: Decimal) -> str:
            return str(value.quantize(Decimal("0.0001")))

        target_by_workstream = {
            str(row.get("workstream_id")): row
            for row in workstream_targets.get("items", [])
            if row.get("workstream_id")
        }
        stage_order = self._stage_order(stage_definitions or [])
        items: list[dict[str, Any]] = []
        totals = {
            "l1": Decimal("0"),
            "l2": Decimal("0"),
            "l3": Decimal("0"),
            "l4": Decimal("0"),
            "l5": Decimal("0"),
            "locked_plan": Decimal("0"),
        }

        for row in value_matrix.get("rows", []):
            workstream_id = row.get("workstream_id")
            target = target_by_workstream.get(str(workstream_id)) if workstream_id else None
            locked_plan = _dec(target.get("locked_run_rate_value")) if target else Decimal("0")
            l5 = _dec(target.get("actual_total")) if target else Decimal("0")
            l4 = max(locked_plan - l5, Decimal("0"))
            below = {"l1": Decimal("0"), "l2": Decimal("0"), "l3": Decimal("0")}
            locked_ids = {
                str(item.get("id"))
                for item in (row.get("total") or {}).get("initiatives", [])
                if target
                and locked_plan > Decimal("0")
                and self._is_terminal_stage(str(item.get("stage") or ""), stage_order)
            }

            for initiative in (row.get("total") or {}).get("initiatives", []):
                initiative_value = max(_dec(initiative.get("net_value_base")), Decimal("0"))
                if str(initiative.get("id")) in locked_ids:
                    continue
                bucket = self._stage_waterline_bucket(
                    str(initiative.get("stage") or ""),
                    stage_order,
                )
                below[bucket] += initiative_value

            item = {
                "label": row.get("workstream_name") or "Workstream",
                "workstream_id": workstream_id,
                "l1": _money(below["l1"]),
                "l2": _money(below["l2"]),
                "l3": _money(below["l3"]),
                "l4": _money(l4),
                "l5": _money(l5),
                "locked_plan": _money(locked_plan),
                "above_waterline": _money(l4 + l5),
                "below_waterline": _money(below["l1"] + below["l2"] + below["l3"]),
            }
            items.append(item)
            for key in ("l1", "l2", "l3"):
                totals[key] += below[key]
            totals["l4"] += l4
            totals["l5"] += l5
            totals["locked_plan"] += locked_plan

        above = totals["l4"] + totals["l5"]
        below_total = totals["l1"] + totals["l2"] + totals["l3"]
        return {
            "basis": "net_run_rate",
            "x_axis": "workstream",
            "items": sorted(items, key=lambda item: item["label"]),
            "totals": {
                "l1": _money(totals["l1"]),
                "l2": _money(totals["l2"]),
                "l3": _money(totals["l3"]),
                "l4": _money(totals["l4"]),
                "l5": _money(totals["l5"]),
                "locked_plan": _money(totals["locked_plan"]),
                "above_waterline": _money(above),
                "below_waterline": _money(below_total),
                "variance": _money(above - totals["locked_plan"]),
            },
        }

    @staticmethod
    def _ordered_values(values: set[str], preferred_order: list[str]) -> list[str]:
        ordered = [value for value in preferred_order if value in values]
        ordered.extend(sorted(values - set(preferred_order)))
        return ordered

    def _stage_options(
        self,
        stage_definitions: list[dict[str, Any]],
        initiatives: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        seen: set[str] = set()

        for stage_id in self._stage_order(stage_definitions):
            options.append({"id": stage_id, "name": self._label(stage_id)})
            seen.add(stage_id)

        for stage_id in self._ordered_values(
            {str(row.get("stage")) for row in initiatives if row.get("stage")},
            ["identified", "scoping", "planning", "in_execution", "complete", "realized"],
        ):
            if stage_id in seen:
                continue
            options.append({"id": stage_id, "name": self._label(stage_id)})
            seen.add(stage_id)

        if not options:
            options = [
                {"id": "scoping", "name": "Scoping"},
                {"id": "in_progress", "name": "In Progress"},
                {"id": "complete", "name": "Complete"},
            ]

        return options

    @staticmethod
    def _stage_order(stage_definitions: list[dict[str, Any]]) -> list[str]:
        stages: list[str] = []
        ordered = sorted(
            stage_definitions,
            key=lambda row: (int(row.get("gate_number") or 0), str(row.get("label") or "")),
        )
        for row in ordered:
            for key in ("from_stage", "to_stage"):
                stage_id = str(row.get(key) or "").strip()
                if stage_id and stage_id not in stages:
                    stages.append(stage_id)
        return stages

    @staticmethod
    def _is_terminal_stage(stage: str, stage_order: list[str]) -> bool:
        normalized = stage.strip().lower()
        terminal_names = {"complete", "completed", "realized", "realised", "done", "closed"}
        if normalized in terminal_names:
            return True
        return bool(stage_order and stage == stage_order[-1])

    def _stage_waterline_bucket(self, stage: str, stage_order: list[str]) -> str:
        normalized = stage.strip().lower()
        if not stage_order:
            if normalized in {"scoping", "identified", "idea", "ideation"}:
                return "l1"
            if self._is_terminal_stage(stage, stage_order):
                return "l2"
            return "l3"
        if stage not in stage_order:
            return "l3"
        if self._is_terminal_stage(stage, stage_order):
            return "l2"
        if len(stage_order) <= 2:
            return "l1"
        ratio = Decimal(stage_order.index(stage)) / Decimal(len(stage_order) - 1)
        if ratio < Decimal("0.34"):
            return "l1"
        if ratio < Decimal("0.67"):
            return "l2"
        return "l3"

    @staticmethod
    def _label(value: str) -> str:
        return value.replace("_", " ").replace("-", " ").title()

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
        target_year: int | None = None,
    ) -> dict[str, str]:
        def _dec(value: object) -> Decimal:
            return Decimal(str(value)) if value is not None else Decimal("0")

        def _money(value: Decimal) -> str:
            return str(value.quantize(Decimal("0.0001")))

        scoped_entries = [
            e
            for e in entries
            if (not initiative_ids or e.get("initiative_id") in initiative_ids)
            and (target_year is None or e.get("year") == target_year)
        ]
        scoped_costs = [
            c
            for c in costs
            if (not initiative_ids or c.get("initiative_id") in initiative_ids)
            and (target_year is None or c.get("year") == target_year)
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

    def _configurable_financial_entries(
        self,
        metric_values: list[dict[str, Any]],
        metric_definitions: list[dict[str, Any]],
        scenarios: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        def _dec(value: object) -> Decimal:
            return Decimal(str(value)) if value is not None else Decimal("0")

        suffix_by_key = {"plan_base": "base", "plan_high": "high", "actual": "actual"}
        scenario_suffix_by_id: dict[str, str] = {}
        for row in scenarios:
            if not row.get("is_active", True):
                continue
            suffix = suffix_by_key.get(str(row.get("key")))
            if suffix and row.get("id"):
                scenario_suffix_by_id[str(row["id"])] = suffix

        definitions_by_id = {
            str(row["id"]): row
            for row in metric_definitions
            if row.get("is_active", True) and row.get("aggregation") != "formula"
        }
        grouped: dict[tuple[str, int, int | None, int | None], dict[str, Any]] = {}

        for row in metric_values:
            definition = definitions_by_id.get(str(row.get("metric_definition_id")))
            suffix = scenario_suffix_by_id.get(str(row.get("scenario_id")))
            if not definition or not suffix or not definition.get("is_benefit"):
                continue
            initiative_id = row.get("initiative_id")
            year = row.get("year")
            if not initiative_id or year is None:
                continue
            month = int(row["month"]) if row.get("month") is not None else None
            quarter = (
                int(row["quarter"])
                if row.get("quarter") is not None
                else (((month - 1) // 3) + 1 if month is not None else None)
            )
            key = (
                str(initiative_id),
                int(year),
                quarter,
                month,
            )
            entry = grouped.setdefault(
                key,
                {
                    "initiative_id": str(initiative_id),
                    "year": int(year),
                    "quarter": quarter,
                    "month": month,
                    "revenue_uplift_base": Decimal("0"),
                    "revenue_uplift_high": Decimal("0"),
                    "revenue_uplift_actual": Decimal("0"),
                    "gm_uplift_base": Decimal("0"),
                    "gm_uplift_high": Decimal("0"),
                    "gm_uplift_actual": Decimal("0"),
                },
            )
            amount = _dec(row.get("value"))
            benefit_class = str(definition.get("benefit_class") or "").lower()
            metric_key = str(definition.get("key") or "")
            if benefit_class == "revenue" or metric_key == "revenue_uplift":
                entry[f"revenue_uplift_{suffix}"] += amount
            else:
                entry[f"gm_uplift_{suffix}"] += amount

        return list(grouped.values())

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
                    "business_unit_name": self._business_unit_summary(initiative),
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

    @staticmethod
    def _business_unit_summary(initiative: dict[str, Any]) -> str | None:
        names = []
        for link in initiative.get("initiative_business_units") or []:
            business_unit = link.get("business_units") if isinstance(link, dict) else None
            if isinstance(business_unit, dict) and business_unit.get("name"):
                names.append(str(business_unit["name"]))
        unique_names = list(dict.fromkeys(names))
        if not unique_names:
            return None
        if len(unique_names) == 1:
            return unique_names[0]
        return f"{len(unique_names)} business units"

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


def _summary_lines(summary: dict[str, Any]) -> list[str]:
    health = summary["portfolio_health"]
    financial = summary["financial_overview"]
    lines = [
        "Transmuter Executive Summary",
        f"Initiatives: {health['total_initiatives']}",
        f"At risk: {health['at_risk']}",
        f"Pending approvals: {health['pending_approvals']}",
        f"KPI health score: {health['kpi_health_score']}%",
        f"Benefits base: {financial['benefits_base']}",
        f"Benefits high: {financial['benefits_high']}",
        f"Benefits actual: {financial['benefits_actual']}",
        f"Costs plan: {financial['costs_plan']}",
        f"Net base: {financial['net_base']}",
        f"Net actual: {financial['net_actual']}",
        "Recommended actions:",
    ]
    lines.extend(f"- {item}" for item in summary["recommended_actions"])
    return lines


def _simple_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 18 Tf", "72 760 Td", f"({_pdf_escape(lines[0])}) Tj"]
    content_lines.extend(["/F1 11 Tf"])
    for line in lines[1:]:
        content_lines.append("0 -18 Td")
        content_lines.append(f"({_pdf_escape(line[:110])}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(pdf)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
