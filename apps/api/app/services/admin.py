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
    "agenda_items",
    "meeting_sessions",
    "meeting_initiatives",
    "meeting_attendees",
    "meetings",
    "gate_submissions",
    "stage_gates",
    "nudge_log",
    "status_updates",
    "financial_cost_lines",
    "financial_entries",
    "financial_cell_assumptions",
    "risks",
    "kpi_entries",
    "kpis",
    "milestone_dependencies",
    "milestone_checklist",
    "milestones",
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
            "financial_entries",
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
        counts = {
            "business_units": self._count_tenant_rows("business_units"),
            "workstreams": self._count_tenant_rows("workstreams"),
            "users": self._count_users(),
            "financial_config_items": self._count_tenant_rows("financial_config_items"),
            "gate_criteria": self._count_tenant_rows("gate_criteria"),
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
                "complete": counts["financial_config_items"] > 0,
            },
            {
                "key": "gate_criteria",
                "label": "Gate criteria",
                "complete": counts["gate_criteria"] > 0,
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
        response = (
            self._c.table(table).select("id", count="exact").eq("tenant_id", self._tid).execute()
        )
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
        self._c.table(table).delete().eq("tenant_id", self._tid).execute()
        return count

    @staticmethod
    def _portfolio_cleanup_object_counts(table_counts: dict[str, int]) -> dict[str, int]:
        groups = {
            "initiatives": ["initiatives", "initiative_team"],
            "financials": [
                "financial_entries",
                "financial_cost_lines",
                "financial_cell_assumptions",
            ],
            "kpis": ["kpis", "kpi_entries"],
            "risks": ["risks"],
            "milestones": ["milestones", "milestone_checklist", "milestone_dependencies"],
            "meetings": [
                "meetings",
                "meeting_attendees",
                "meeting_initiatives",
                "meeting_external_events",
                "meeting_artifacts",
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
