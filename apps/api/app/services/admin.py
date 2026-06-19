"""Admin service — organization settings and governance configuration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.config import settings
from app.repositories.audit import AuditRepository
from app.repositories.governance import GovernanceRepository
from app.repositories.organization import OrganizationRepository
from app.services.billing import stripe_price_configuration

PORTFOLIO_CLEANUP_TABLES = [
    "action_items",
    "meeting_artifacts",
    "meeting_external_events",
    "meeting_session_agenda_items",
    "meeting_session_attendees",
    "agenda_items",
    "meeting_sessions",
    "meeting_initiatives",
    "meeting_attendees",
    "meeting_workstreams",
    "meetings",
    "gate_submissions",
    "stage_gates",
    "nudge_log",
    "status_updates",
    "financial_forecasts",
    "benefit_realization_ledger",
    "bankable_plans",
    "financial_initiative_annual_baselines",
    "financial_cost_lines",
    "financial_metric_values",
    "financial_benefit_lines",
    "financial_cell_assumptions",
    "risks",
    "kpi_entries",
    "kpis",
    "milestone_dependencies",
    "milestone_checklist",
    "milestones",
    "initiative_business_units",
    "initiative_team",
    "initiatives",
]

PRESERVED_PORTFOLIO_CLEANUP_OBJECTS = [
    "organization",
    "users",
    "billing",
    "business_units",
    "workstreams",
    "gate_criteria",
    "audit_logs",
]


class AdminService:
    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID | None = None) -> None:
        self._org_repo = OrganizationRepository(client, tenant_id)
        self._gov_repo = GovernanceRepository(client, tenant_id)
        self._audit_repo = AuditRepository(client, tenant_id)
        self._c = client
        self._tid = str(tenant_id)
        self._user_id = str(user_id) if user_id else None

    # ── Organization Settings ──────────────────────────────────────

    def get_settings(self) -> dict[str, Any]:
        org = self._org_repo.get_organization()
        if not org:
            return {}
        return {
            "name": org["name"],
            "logo_url": org.get("logo_url"),
            "settings": org.get("settings", {}),
        }

    def get_billing_status(self) -> dict[str, Any]:
        org = self._org_repo.get_organization()
        settings = (org or {}).get("settings") or {}
        billing = settings.get("billing") or {}
        subscription_response = (
            self._c.table("tenant_subscriptions")
            .select(
                "*, subscription_plans("
                "code,name,amount_cents,currency,billing_interval,stripe_price_id,"
                "user_limit_min,user_limit_max)"
            )
            .eq("tenant_id", self._tid)
            .maybe_single()
            .execute()
        )
        subscription = subscription_response.data if subscription_response else None
        plan = (subscription or {}).get("subscription_plans") or {}
        active_users = (
            self._c.table("users")
            .select("id", count="exact")
            .eq("tenant_id", self._tid)
            .eq("status", "active")
            .execute()
        )
        return {
            "provider": billing.get("provider", "stripe"),
            "subscription_status": (subscription or {}).get("status")
            or billing.get("subscription_status", "not_configured"),
            "checkout_status": (subscription or {}).get("checkout_status")
            or billing.get("checkout_status"),
            "payment_status": (subscription or {}).get("payment_status")
            or billing.get("payment_status"),
            "planned_user_count": (subscription or {}).get("planned_user_count")
            or billing.get("planned_user_count"),
            "active_user_count": active_users.count or 0,
            "price_per_user_cents": billing.get("price_per_user_cents"),
            "amount_cents": plan.get("amount_cents") or billing.get("amount_cents"),
            "currency": plan.get("currency") or billing.get("currency", "usd"),
            "billing_interval": plan.get("billing_interval")
            or billing.get("billing_interval", "month"),
            "plan_code": plan.get("code") or billing.get("plan_code"),
            "plan_name": plan.get("name") or billing.get("plan_name"),
            "stripe_price_id": plan.get("stripe_price_id"),
            "stripe_customer_id": (subscription or {}).get("stripe_customer_id")
            or billing.get("customer_id"),
            "stripe_subscription_id": (subscription or {}).get("stripe_subscription_id")
            or billing.get("subscription_id"),
            "stripe_checkout_session_id": (subscription or {}).get("stripe_checkout_session_id")
            or billing.get("checkout_session_id"),
            "last_event_at": (subscription or {}).get("updated_at") or billing.get("last_event_at"),
            "stripe_price_configuration": stripe_price_configuration(),
        }

    def get_launch_readiness(self) -> dict[str, Any]:
        checks = [
            self._check("supabase_url", bool(settings.supabase_url), "Supabase URL is configured."),
            self._check(
                "supabase_service_key",
                bool(settings.supabase_service_key),
                "Supabase service key is configured.",
            ),
            self._check(
                "jwt_secret",
                len(settings.jwt_secret) >= 32,
                "JWT secret is at least 32 characters.",
            ),
            self._check(
                "payment_provider",
                settings.payment_provider == "stripe",
                "Stripe is the active payment provider.",
            ),
            self._check(
                "stripe_secret_key",
                settings.stripe_secret_key.startswith("sk_"),
                "Stripe secret key is configured.",
            ),
            self._check(
                "stripe_publishable_key",
                settings.stripe_publishable_key.startswith("pk_"),
                "Stripe publishable key is configured.",
            ),
            self._check(
                "stripe_webhook_secret",
                settings.stripe_webhook_secret.startswith("whsec_"),
                "Stripe webhook secret is configured.",
            ),
            self._check(
                "stripe_price_team_monthly",
                bool(settings.stripe_price_team_monthly),
                "Team monthly Stripe Price ID is configured.",
            ),
            self._check(
                "stripe_price_team_annual",
                bool(settings.stripe_price_team_annual),
                "Team annual Stripe Price ID is configured.",
            ),
            self._check(
                "stripe_price_business_monthly",
                bool(settings.stripe_price_business_monthly),
                "Business monthly Stripe Price ID is configured.",
            ),
            self._check(
                "stripe_price_business_annual",
                bool(settings.stripe_price_business_annual),
                "Business annual Stripe Price ID is configured.",
            ),
            self._check(
                "encryption_key",
                bool(settings.encryption_key),
                "Encryption key is configured.",
            ),
            self._check(
                "openrouter_api_key",
                bool(settings.openrouter_api_key),
                "OpenRouter key is configured for AI.",
            ),
        ]
        for table in (
            "organizations",
            "users",
            "initiatives",
            "financial_metric_values",
            "financial_cost_lines",
            "kpis",
            "risks",
            "milestones",
            "meetings",
            "action_items",
            "subscription_plans",
            "signup_intents",
            "tenant_subscriptions",
        ):
            checks.append(self._table_check(table))

        billing = self.get_billing_status()
        checks.append(
            self._check(
                "tenant_billing_status",
                billing.get("subscription_status") not in {None, "", "not_configured"},
                "Tenant billing status has been initialized.",
                severity="warning",
            )
        )
        blockers = [
            check for check in checks if check["severity"] == "blocker" and not check["passed"]
        ]
        warnings = [
            check for check in checks if check["severity"] == "warning" and not check["passed"]
        ]
        return {
            "ready": not blockers,
            "blockers": len(blockers),
            "warnings": len(warnings),
            "checks": checks,
        }

    def get_setup_status(self) -> dict[str, Any]:
        gate_criteria_status = self._gate_criteria_completeness()
        counts = {
            "business_units": self._count_tenant_rows("business_units"),
            "workstreams": self._count_tenant_rows("workstreams"),
            "users": self._count_users(),
            "stage_gate_definitions": self._count_tenant_rows("stage_gate_definitions"),
            "financial_metric_definitions": self._count_tenant_rows("financial_metric_definitions"),
            "financial_scenarios": self._count_tenant_rows("financial_scenarios"),
            "financial_cost_categories": self._count_tenant_rows("financial_cost_categories"),
            "gate_criteria": self._count_tenant_rows("gate_criteria"),
            "active_stage_gates": gate_criteria_status["active_stage_gates"],
            "active_gate_criteria": gate_criteria_status["active_gate_criteria"],
            "gates_with_criteria": gate_criteria_status["gates_with_criteria"],
            "gates_missing_criteria": gate_criteria_status["gates_missing_criteria"],
            "initiatives": self._count_tenant_rows("initiatives"),
        }
        checks = [
            {
                "key": "organization",
                "label": "Organization settings",
                "complete": bool(self._org_repo.get_organization()),
            },
            {
                "key": "business_units",
                "label": "Business units",
                "complete": counts["business_units"] > 0,
            },
            {
                "key": "workstreams",
                "label": "Workstreams",
                "complete": counts["workstreams"] > 0,
            },
            {
                "key": "financial_config",
                "label": "Financial configuration",
                "complete": counts["financial_metric_definitions"] > 0
                and counts["financial_scenarios"] > 0
                and counts["financial_cost_categories"] > 0,
            },
            {
                "key": "stage_gates",
                "label": "Stage gates",
                "complete": counts["stage_gate_definitions"] > 0,
            },
            {
                "key": "gate_criteria",
                "label": "Gate criteria",
                "complete": gate_criteria_status["complete"],
                "details": gate_criteria_status,
            },
            {
                "key": "users",
                "label": "Users",
                "complete": counts["users"] > 0,
            },
        ]
        completed = len([check for check in checks if check["complete"]])
        return {
            "complete": completed == len(checks),
            "completed": completed,
            "total": len(checks),
            "counts": counts,
            "checks": checks,
        }

    def _gate_criteria_completeness(self) -> dict[str, Any]:
        gates_result = (
            self._c.table("stage_gate_definitions")
            .select("gate_number,is_active")
            .eq("tenant_id", self._tid)
            .eq("is_active", True)
            .execute()
        )
        criteria_result = (
            self._c.table("gate_criteria")
            .select("gate_number,is_active")
            .eq("tenant_id", self._tid)
            .eq("is_active", True)
            .execute()
        )
        active_gate_numbers = {
            int(row["gate_number"])
            for row in gates_result.data or []
            if row.get("gate_number") is not None
        }
        criteria_gate_numbers = {
            int(row["gate_number"])
            for row in criteria_result.data or []
            if row.get("gate_number") is not None
        }
        missing_gate_numbers = sorted(active_gate_numbers - criteria_gate_numbers)
        return {
            "complete": bool(active_gate_numbers) and not missing_gate_numbers,
            "active_stage_gates": len(active_gate_numbers),
            "active_gate_criteria": len(criteria_result.data or []),
            "gates_with_criteria": len(active_gate_numbers & criteria_gate_numbers),
            "gates_missing_criteria": len(missing_gate_numbers),
            "missing_gate_numbers": missing_gate_numbers,
        }

    def update_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        patch = {}
        if "name" in data:
            patch["name"] = data["name"]
        if "logo_url" in data:
            patch["logo_url"] = data["logo_url"]
        if "settings" in data:
            patch["settings"] = data["settings"]

        patch["updated_at"] = datetime.now(UTC).isoformat()
        return self._org_repo.update_organization(patch)

    def reset_strategic_parameter_references(
        self,
        parameter_type: str,
        value: str,
    ) -> dict[str, Any]:
        field_by_parameter = {
            "market": "country",
            "theme": "theme",
            "tag": "tag",
        }
        field = field_by_parameter.get(parameter_type)
        if not field:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported strategic parameter type",
            )

        result = (
            self._c.table("initiatives")
            .update({field: None})
            .eq("tenant_id", self._tid)
            .eq(field, value)
            .execute()
        )
        reset_count = len(result.data or [])
        if self._user_id:
            self._audit_repo.log(
                "update",
                "strategic_parameter_references",
                self._tid,
                self._user_id,
                {
                    "parameter_type": parameter_type,
                    "value": value,
                    "field": field,
                    "reset_count": reset_count,
                },
            )
        return {
            "parameter_type": parameter_type,
            "value": value,
            "field": field,
            "reset_count": reset_count,
        }

    # ── Governance Criteria ────────────────────────────────────────

    def list_gate_criteria(self, gate_number: int | None = None) -> dict[str, Any]:
        items = self._gov_repo.list_criteria(gate_number)
        return {"items": items, "total": len(items)}

    def upsert_gate_criterion(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._gov_repo.upsert_criterion(data)

    def delete_gate_criterion(self, criterion_id: str) -> None:
        self._gov_repo.delete_criterion(criterion_id)

    # ── Portfolio Cleanup ─────────────────────────────────────────

    def get_portfolio_cleanup_preview(self) -> dict[str, Any]:
        org = self._require_organization()
        table_counts = self._portfolio_cleanup_table_counts()
        return {
            "tenant_id": self._tid,
            "tenant_slug": org["slug"],
            "tenant_name": org["name"],
            "object_counts": self._portfolio_cleanup_object_counts(table_counts),
            "table_counts": table_counts,
            "preserved_objects": PRESERVED_PORTFOLIO_CLEANUP_OBJECTS,
        }

    def delete_portfolio_data(self, confirm_slug: str) -> dict[str, Any]:
        org = self._require_organization()
        if confirm_slug != org["slug"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation slug does not match tenant slug",
            )

        deletion_counts: dict[str, int] = {}
        for table in PORTFOLIO_CLEANUP_TABLES:
            deletion_counts[table] = self._delete_tenant_rows(table)

        if self._user_id:
            self._audit_repo.log(
                "delete",
                "portfolio_cleanup",
                self._tid,
                self._user_id,
                {
                    "deleted_rows": deletion_counts,
                    "object_counts": self._portfolio_cleanup_object_counts(deletion_counts),
                    "preserved_objects": PRESERVED_PORTFOLIO_CLEANUP_OBJECTS,
                },
            )

        return {
            "deleted": True,
            "tenant_id": self._tid,
            "tenant_slug": org["slug"],
            "tenant_name": org["name"],
            "deleted_rows": deletion_counts,
            "object_counts": self._portfolio_cleanup_object_counts(deletion_counts),
            "preserved_objects": PRESERVED_PORTFOLIO_CLEANUP_OBJECTS,
        }

    def list_meeting_cleanup_candidates(self) -> dict[str, Any]:
        response = (
            self._c.table("meetings")
            .select("id, name, recurrence, created_at, users!meetings_owner_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .order("created_at", desc=True)
            .execute()
        )
        items = []
        for meeting in response.data or []:
            meeting_id = meeting["id"]
            counts = self._meeting_cleanup_counts([meeting_id])
            items.append(
                {
                    **meeting,
                    "dependent_count": sum(counts.values()),
                    "cleanup_counts": counts,
                }
            )
        return {"items": items, "total": len(items)}

    def delete_selected_meetings(
        self,
        meeting_ids: list[str],
        confirm_phrase: str,
    ) -> dict[str, Any]:
        if confirm_phrase.strip() != "DELETE MEETINGS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match",
            )

        normalized_ids = list(
            dict.fromkeys([str(item) for item in meeting_ids if str(item).strip()])
        )
        if not normalized_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Select at least one meeting to delete",
            )

        existing = (
            self._c.table("meetings")
            .select("id, name")
            .eq("tenant_id", self._tid)
            .in_("id", normalized_ids)
            .execute()
        )
        existing_rows = existing.data or []
        existing_ids = [row["id"] for row in existing_rows]
        missing_ids = [
            meeting_id for meeting_id in normalized_ids if meeting_id not in existing_ids
        ]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more selected meetings were not found",
            )

        counts = self._meeting_cleanup_counts(existing_ids)
        linked_records = self._meeting_artifact_linked_records(existing_ids, exclusive_only=True)
        self._c.table("meetings").delete().eq("tenant_id", self._tid).in_(
            "id", existing_ids
        ).execute()

        if linked_records["risk"]:
            self._delete_by_ids("risks", linked_records["risk"])
        if linked_records["action_item"]:
            self._delete_by_ids("action_items", linked_records["action_item"])

        if self._user_id:
            self._audit_repo.log(
                "delete",
                "meeting_cleanup",
                self._tid,
                self._user_id,
                {
                    "meeting_ids": existing_ids,
                    "meeting_names": [row.get("name") for row in existing_rows],
                    "deleted_rows": counts,
                    "linked_records": {
                        "risk": len(linked_records["risk"]),
                        "action_item": len(linked_records["action_item"]),
                    },
                },
            )

        return {
            "deleted": True,
            "meeting_ids": existing_ids,
            "deleted_meetings": existing_rows,
            "deleted_rows": counts,
            "linked_records": {
                "risk": len(linked_records["risk"]),
                "action_item": len(linked_records["action_item"]),
            },
        }

    # ── Audit Logs ───────────────────────────────────────────────

    def list_audit_logs(self, limit: int = 100) -> dict[str, Any]:
        items = self._audit_repo.list_logs(limit)
        return {"items": items, "total": len(items)}

    @staticmethod
    def _check(
        code: str,
        passed: bool,
        message: str,
        *,
        severity: str = "blocker",
    ) -> dict[str, Any]:
        return {
            "code": code,
            "passed": passed,
            "message": message,
            "severity": severity,
        }

    def _table_check(self, table: str) -> dict[str, Any]:
        try:
            self._c.table(table).select("*").limit(1).execute()
            return self._check(f"table_{table}", True, f"{table} table is queryable.")
        except Exception:
            return self._check(f"table_{table}", False, f"{table} table is not queryable.")

    def _require_organization(self) -> dict[str, Any]:
        org = self._org_repo.get_organization()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return org

    def _portfolio_cleanup_table_counts(self) -> dict[str, int]:
        return {table: self._count_tenant_rows(table) for table in PORTFOLIO_CLEANUP_TABLES}

    def _count_tenant_rows(self, table: str) -> int:
        try:
            response = (
                self._c.table(table)
                .select("id", count="exact")
                .eq("tenant_id", self._tid)
                .execute()
            )
        except Exception as exc:
            if self._is_missing_table(exc, table):
                return 0
            raise
        return response.count or 0

    def _count_users(self) -> int:
        response = (
            self._c.table("users")
            .select("id", count="exact")
            .eq("tenant_id", self._tid)
            .neq("status", "deactivated")
            .execute()
        )
        return response.count or 0

    def _delete_tenant_rows(self, table: str) -> int:
        count = self._count_tenant_rows(table)
        if count == 0:
            return 0
        try:
            self._c.table(table).delete().eq("tenant_id", self._tid).execute()
        except Exception as exc:
            if self._is_missing_table(exc, table):
                return 0
            raise
        return count

    @staticmethod
    def _is_missing_table(exc: Exception, table_name: str) -> bool:
        text = str(exc)
        return table_name in text and (
            "Could not find the table" in text or "does not exist" in text or "schema cache" in text
        )

    @staticmethod
    def _portfolio_cleanup_object_counts(table_counts: dict[str, int]) -> dict[str, int]:
        groups = {
            "initiatives": ["initiatives", "initiative_team"],
            "financials": [
                "financial_cost_lines",
                "financial_metric_values",
                "financial_benefit_lines",
                "financial_cell_assumptions",
                "financial_forecasts",
                "benefit_realization_ledger",
                "bankable_plans",
            ],
            "kpis": ["kpis", "kpi_entries"],
            "risks": ["risks"],
            "milestones": ["milestones", "milestone_checklist", "milestone_dependencies"],
            "meetings": [
                "meetings",
                "meeting_attendees",
                "meeting_initiatives",
                "meeting_workstreams",
                "meeting_external_events",
                "meeting_artifacts",
                "meeting_session_agenda_items",
                "meeting_session_attendees",
                "meeting_sessions",
                "agenda_items",
            ],
            "action_items": ["action_items"],
            "governance": ["gate_submissions", "stage_gates"],
            "status_updates": ["status_updates", "nudge_log"],
        }
        return {
            key: sum(table_counts.get(table, 0) for table in tables)
            for key, tables in groups.items()
        }

    def _meeting_cleanup_counts(self, meeting_ids: list[str]) -> dict[str, int]:
        tables = [
            "meetings",
            "meeting_attendees",
            "meeting_initiatives",
            "meeting_workstreams",
            "meeting_external_events",
            "meeting_artifacts",
            "meeting_session_agenda_items",
            "meeting_session_attendees",
            "meeting_sessions",
            "agenda_items",
        ]
        counts = {table: self._count_rows_for_meetings(table, meeting_ids) for table in tables}
        session_ids = self._session_ids_for_meetings(meeting_ids)
        counts["action_items"] = self._count_rows_for_sessions("action_items", session_ids)
        linked = self._meeting_artifact_linked_records(meeting_ids, exclusive_only=True)
        counts["linked_risks"] = len(linked["risk"])
        counts["linked_action_items"] = len(linked["action_item"])
        return counts

    def _meeting_artifact_linked_records(
        self,
        meeting_ids: list[str],
        *,
        exclusive_only: bool = False,
    ) -> dict[str, list[str]]:
        if not meeting_ids:
            return {"risk": [], "action_item": []}
        response = (
            self._c.table("meeting_artifacts")
            .select("linked_record_type, linked_record_id")
            .eq("tenant_id", self._tid)
            .in_("meeting_id", meeting_ids)
            .execute()
        )
        records = {"risk": [], "action_item": []}
        for row in response.data or []:
            linked_type = row.get("linked_record_type")
            linked_id = row.get("linked_record_id")
            if linked_type in records and linked_id:
                records[linked_type].append(str(linked_id))
        return {
            key: self._exclusive_linked_record_ids(key, list(dict.fromkeys(values)), meeting_ids)
            if exclusive_only
            else list(dict.fromkeys(values))
            for key, values in records.items()
        }

    def _exclusive_linked_record_ids(
        self,
        linked_type: str,
        linked_ids: list[str],
        selected_meeting_ids: list[str],
    ) -> list[str]:
        if not linked_ids:
            return []
        response = (
            self._c.table("meeting_artifacts")
            .select("linked_record_id, meeting_id")
            .eq("tenant_id", self._tid)
            .eq("linked_record_type", linked_type)
            .in_("linked_record_id", linked_ids)
            .execute()
        )
        selected = set(selected_meeting_ids)
        safe_ids = set(linked_ids)
        for row in response.data or []:
            linked_id = str(row.get("linked_record_id") or "")
            if linked_id and row.get("meeting_id") not in selected:
                safe_ids.discard(linked_id)
        return [linked_id for linked_id in linked_ids if linked_id in safe_ids]

    def _session_ids_for_meetings(self, meeting_ids: list[str]) -> list[str]:
        if not meeting_ids:
            return []
        response = (
            self._c.table("meeting_sessions")
            .select("id")
            .eq("tenant_id", self._tid)
            .in_("meeting_id", meeting_ids)
            .execute()
        )
        return [row["id"] for row in response.data or []]

    def _count_rows_for_meetings(self, table: str, meeting_ids: list[str]) -> int:
        if not meeting_ids:
            return 0
        response = (
            self._c.table(table)
            .select("id", count="exact")
            .eq("tenant_id", self._tid)
            .in_("meeting_id" if table != "meetings" else "id", meeting_ids)
            .execute()
        )
        return response.count or 0

    def _count_rows_for_sessions(self, table: str, session_ids: list[str]) -> int:
        if not session_ids:
            return 0
        response = (
            self._c.table(table)
            .select("id", count="exact")
            .eq("tenant_id", self._tid)
            .in_("session_id", session_ids)
            .execute()
        )
        return response.count or 0

    def _delete_by_ids(self, table: str, ids: list[str]) -> None:
        if not ids:
            return
        self._c.table(table).delete().eq("tenant_id", self._tid).in_("id", ids).execute()
