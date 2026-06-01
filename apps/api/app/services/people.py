"""People service — directory, workload, invites, and pressure."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from secrets import token_urlsafe
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client
from supabase_auth.errors import AuthApiError

from app.core.database import get_supabase_admin
from app.core.rbac import assert_valid_role
from app.domain.people import InviteCreate, UserCreate, UserUpdate, WorkstreamAssignment
from app.repositories.people import PeopleRepository


class PeopleService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = PeopleRepository(client, tenant_id)
        self._tenant_id = str(tenant_id)

    def list_users(
        self,
        *,
        role: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        users = [
            self._with_directory_metrics(row)
            for row in self._repo.list_users(role=role, status=status_filter, search=search)
        ]
        return {"items": users, "data": users, "total": len(users)}

    def get_profile(self, user_id: str) -> dict[str, Any]:
        user = self._assert_user(user_id)
        pressure = self.get_pressure(user_id)
        return {
            **self._with_directory_metrics(user),
            "workstreams": self._repo.list_user_workstreams(user_id),
            "on_their_plate": {
                "initiatives": self._repo.list_owned_initiatives(user_id),
                "milestones": self._repo.list_owned_milestones(user_id),
                "action_items": self._repo.list_assigned_actions(user_id),
            },
            "pressure": pressure,
        }

    def update_profile(self, user_id: str, data: UserUpdate) -> dict[str, Any]:
        user = self._assert_user(user_id)
        patch = data.model_dump(exclude_none=True)
        if not patch:
            return self.get_profile(user_id)
        if "role" in patch:
            assert_valid_role(str(patch["role"]))
        patch["updated_at"] = datetime.now(UTC).isoformat()
        self._repo.update_user(user_id, patch)
        self._sync_auth_metadata(
            user_id,
            {
                "tenant_id": self._tenant_id,
                "role": patch.get("role", user.get("role")),
                "display_name": patch.get("display_name", user.get("display_name")),
            },
        )
        return self.get_profile(user_id)

    def ghost_user(self, user_id: str) -> dict[str, Any]:
        self._assert_user(user_id)
        self._repo.update_user(
            user_id,
            {"status": "ghost", "updated_at": datetime.now(UTC).isoformat()},
        )
        return self.get_profile(user_id)

    def deactivate_user(self, user_id: str) -> dict[str, Any]:
        self._assert_user(user_id)
        self._repo.update_user(
            user_id,
            {"status": "deactivated", "updated_at": datetime.now(UTC).isoformat()},
        )
        return self.get_profile(user_id)

    def invite_user(self, data: InviteCreate) -> dict[str, Any]:
        assert_valid_role(data.role)
        existing = self._repo.get_user_by_email(str(data.email))
        if existing:
            return self.get_profile(existing["id"])

        auth_user_id = self._ensure_auth_invite_user(data)
        row = self._repo.upsert_user(
            {
                "id": auth_user_id,
                "tenant_id": self._tenant_id,
                "email": str(data.email),
                "display_name": data.display_name,
                "role": data.role,
                "title": data.title,
                "department": data.department,
                "market": data.market,
                "status": "ghost",
                "onboarding_completed": False,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        if data.workstream_ids:
            self._repo.replace_user_workstreams(row["id"], data.workstream_ids)
        return self.get_profile(row["id"])

    def create_user(self, data: UserCreate) -> dict[str, Any]:
        assert_valid_role(data.role)
        self._validate_temporary_password(data.temporary_password)
        existing = self._repo.get_user_by_email(str(data.email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists in this tenant",
            )

        auth_user_id = self._ensure_auth_password_user(data)
        row = self._repo.upsert_user(
            {
                "id": auth_user_id,
                "tenant_id": self._tenant_id,
                "email": str(data.email),
                "display_name": data.display_name,
                "role": data.role,
                "title": data.title,
                "department": data.department,
                "market": data.market,
                "status": "pending",
                "must_change_password": True,
                "onboarding_completed": False,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        if data.workstream_ids:
            self._repo.replace_user_workstreams(row["id"], data.workstream_ids)
        return self.get_profile(row["id"])

    def list_invites(self) -> dict[str, Any]:
        invites = [
            row
            for status_value in ("ghost", "pending")
            for row in self._repo.list_users(status=status_value)
            if row.get("onboarding_completed") is not True
        ]
        return {"items": invites, "total": len(invites)}

    def assign_workstreams(self, user_id: str, data: WorkstreamAssignment) -> dict[str, Any]:
        self._assert_user(user_id)
        workstreams = self._repo.replace_user_workstreams(user_id, data.workstream_ids)
        return {"user_id": user_id, "workstreams": workstreams}

    def get_pressure(self, user_id: str) -> dict[str, Any]:
        self._assert_user(user_id)
        initiatives = self._repo.list_owned_initiatives(user_id)
        milestones = self._repo.list_owned_milestones(user_id)
        actions = self._repo.list_assigned_actions(user_id)

        overdue_milestones = [row for row in milestones if self._is_overdue(row)]
        high_pressure_milestones = [
            row for row in milestones if self._decimal(row.get("pressure_score")) > Decimal("6.0")
        ]
        overdue_actions = [row for row in actions if self._is_action_overdue(row)]

        score = min(
            Decimal("10.0"),
            Decimal(len(initiatives)) * Decimal("1.4")
            + Decimal(len(high_pressure_milestones)) * Decimal("1.6")
            + Decimal(len(overdue_milestones)) * Decimal("2.0")
            + Decimal(len(overdue_actions)) * Decimal("1.2"),
        )
        return {
            "user_id": user_id,
            "pressure_score": f"{score:.1f}",
            "breakdown": {
                "active_initiatives": len(initiatives),
                "active_milestones": len(milestones),
                "high_pressure_milestones": len(high_pressure_milestones),
                "overdue_milestones": len(overdue_milestones),
                "open_action_items": len(actions),
                "overdue_action_items": len(overdue_actions),
            },
        }

    def _with_directory_metrics(self, row: dict[str, Any]) -> dict[str, Any]:
        pressure = self.get_pressure(row["id"])
        initiatives = self._repo.list_owned_initiatives(row["id"])
        return {
            **row,
            "initiative_count": len(initiatives),
            "pressure_score": pressure["pressure_score"],
            "workstreams": self._repo.list_user_workstreams(row["id"]),
        }

    def _assert_user(self, user_id: str) -> dict[str, Any]:
        user = self._repo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def _ensure_auth_invite_user(self, data: InviteCreate) -> str:
        existing_id = self._find_auth_user_id(str(data.email))
        if existing_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An auth account already exists for this email",
            )

        try:
            response = get_supabase_admin().auth.admin.invite_user_by_email(
                str(data.email),
                {
                    "data": {
                        "tenant_id": self._tenant_id,
                        "role": data.role,
                        "display_name": data.display_name,
                    },
                },
            )
        except AuthApiError as exc:
            if "rate limit" in exc.message.lower():
                return self._create_rate_limited_auth_invite(data)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supabase invite failed: {exc.message}",
            ) from exc
        return str(response.user.id)

    def _create_rate_limited_auth_invite(self, data: InviteCreate) -> str:
        response = get_supabase_admin().auth.admin.create_user(
            {
                "email": str(data.email),
                "password": f"TransmuterInvite{token_urlsafe(24)}!",
                "email_confirm": False,
                "user_metadata": {
                    "tenant_id": self._tenant_id,
                    "role": data.role,
                    "display_name": data.display_name,
                    "invite_delivery_status": "deferred_rate_limited",
                },
            }
        )
        return str(response.user.id)

    def _ensure_auth_password_user(self, data: UserCreate) -> str:
        existing_id = self._find_auth_user_id(str(data.email))
        metadata = {
            "tenant_id": self._tenant_id,
            "role": data.role,
            "display_name": data.display_name,
            "must_change_password": True,
        }
        if existing_id:
            owner = (
                get_supabase_admin()
                .table("users")
                .select("id,tenant_id")
                .eq("id", existing_id)
                .maybe_single()
                .execute()
            )
            if owner and owner.data and owner.data.get("tenant_id") != self._tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already belongs to another tenant",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An auth account already exists for this email",
            )

        response = get_supabase_admin().auth.admin.create_user(
            {
                "email": str(data.email),
                "password": data.temporary_password,
                "email_confirm": True,
                "user_metadata": metadata,
            }
        )
        return str(response.user.id)

    def _sync_auth_metadata(self, user_id: str, metadata: dict[str, Any]) -> None:
        try:
            get_supabase_admin().auth.admin.update_user_by_id(
                user_id,
                {"user_metadata": metadata},
            )
        except Exception:
            return

    def _find_auth_user_id(self, email: str) -> str | None:
        page = 1
        per_page = 100
        while True:
            users = get_supabase_admin().auth.admin.list_users(page=page, per_page=per_page)
            for user in users:
                if getattr(user, "email", None) == email:
                    return str(user.id)
            if len(users) < per_page:
                return None
            page += 1

    @staticmethod
    def _validate_temporary_password(password: str) -> None:
        if len(password) < 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temporary password must be at least 12 characters",
            )
        if not any(ch.islower() for ch in password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temporary password must include a lowercase letter",
            )
        if not any(ch.isupper() for ch in password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temporary password must include an uppercase letter",
            )
        if not any(ch.isdigit() for ch in password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temporary password must include a number",
            )

    @staticmethod
    def _decimal(value: object) -> Decimal:
        try:
            return Decimal(str(value or "0"))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @staticmethod
    def _date(value: str | None) -> date | None:
        if not value:
            return None
        return datetime.fromisoformat(value).date()

    def _is_overdue(self, row: dict[str, Any]) -> bool:
        if row.get("status") == "complete":
            return False
        due = self._date(row.get("planned_end"))
        return row.get("status") == "overdue" or bool(due and due < date.today())

    def _is_action_overdue(self, row: dict[str, Any]) -> bool:
        if row.get("status") == "completed":
            return False
        due = self._date(row.get("due_date"))
        return bool(due and due < date.today())
