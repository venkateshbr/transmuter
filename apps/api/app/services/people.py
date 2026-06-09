"""People service — directory, workload, invites, and pressure."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from secrets import token_urlsafe
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.config import settings
from app.core.database import get_supabase_admin
from app.core.rbac import assert_valid_role
from app.domain.people import (
    InviteAccept,
    InviteCreate,
    UserCreate,
    UserTemporaryPassword,
    UserUpdate,
    WorkstreamAssignment,
)
from app.repositories.people import PeopleRepository
from app.services.email_delivery import EmailDeliveryService

INVITE_EXPIRY_DAYS = 7
INVITE_PURPOSE = "invite"
PASSWORD_SETUP_PURPOSE = "password_setup"


class PeopleService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = PeopleRepository(client, tenant_id)
        self._tenant_id = str(tenant_id)
        self._email = EmailDeliveryService()

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

    def invite_user(self, data: InviteCreate, created_by_id: str) -> dict[str, Any]:
        assert_valid_role(data.role)
        email = str(data.email).lower()
        existing = self._repo.get_user_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists in this tenant",
            )
        if self._find_auth_user_id(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An auth account already exists for this email",
            )
        if self._repo.get_pending_invite_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending invite already exists for this email",
            )

        token, token_hash = self._new_invite_token()
        now = datetime.now(UTC)
        invite = self._repo.insert_invite(
            {
                "tenant_id": self._tenant_id,
                "email": email,
                "display_name": data.display_name,
                "role": data.role,
                "title": data.title,
                "department": data.department,
                "market": data.market,
                "workstream_ids": data.workstream_ids,
                "token_hash": token_hash,
                "purpose": INVITE_PURPOSE,
                "status": "pending",
                "expires_at": self._invite_expiry(now),
                "created_by_id": created_by_id,
                "updated_at": now.isoformat(),
            }
        )
        return self._deliver_invite(invite, token)

    def create_user(self, data: UserCreate) -> dict[str, Any]:
        assert_valid_role(data.role)
        self._validate_temporary_password(data.temporary_password)
        email = str(data.email).lower()
        existing = self._repo.get_user_by_email(email)
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
                "email": email,
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

    def send_password_setup_link(self, user_id: str, created_by_id: str) -> dict[str, Any]:
        user = self._assert_user(user_id)
        if user.get("status") in {"ghost", "deactivated"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Password setup link cannot be sent for inactive users",
            )

        email = str(user["email"]).lower()
        self._revoke_pending_access_tokens_for_email(email)
        token, token_hash = self._new_invite_token()
        now = datetime.now(UTC)
        invite = self._repo.insert_invite(
            {
                "tenant_id": self._tenant_id,
                "email": email,
                "display_name": user.get("display_name") or email,
                "role": user["role"],
                "title": user.get("title"),
                "department": user.get("department"),
                "market": user.get("market"),
                "workstream_ids": [],
                "token_hash": token_hash,
                "purpose": PASSWORD_SETUP_PURPOSE,
                "status": "pending",
                "expires_at": self._invite_expiry(now),
                "created_by_id": created_by_id,
                "auth_user_id": user["id"],
                "updated_at": now.isoformat(),
            }
        )
        return self._deliver_invite(invite, token)

    def set_temporary_password(self, user_id: str, data: UserTemporaryPassword) -> dict[str, Any]:
        user = self._assert_user(user_id)
        if user.get("status") in {"ghost", "deactivated"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Password cannot be reset for inactive users",
            )
        self._validate_temporary_password(data.temporary_password)
        self._set_auth_password_for_user(user, data.temporary_password, must_change_password=True)
        self._revoke_pending_access_tokens_for_email(str(user["email"]).lower())
        self._repo.update_user(
            user_id,
            {
                "status": "active",
                "must_change_password": True,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        return self.get_profile(user_id)

    def list_invites(self) -> dict[str, Any]:
        invites = [self._public_invite(self._expire_if_needed(row)) for row in self._repo.list_invites()]
        return {"items": invites, "total": len(invites)}

    def resend_invite(self, invite_id: str) -> dict[str, Any]:
        invite = self._assert_invite(invite_id)
        if invite["status"] in {"accepted", "revoked"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invite cannot be resent",
            )
        token, token_hash = self._new_invite_token()
        now = datetime.now(UTC)
        invite = self._repo.update_invite(
            invite_id,
            {
                "token_hash": token_hash,
                "status": "pending",
                "expires_at": self._invite_expiry(now),
                "updated_at": now.isoformat(),
            },
        )
        return self._deliver_invite(invite, token)

    def revoke_invite(self, invite_id: str) -> dict[str, Any]:
        invite = self._assert_invite(invite_id)
        if invite["status"] == "accepted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Accepted invite cannot be revoked",
            )
        invite = self._repo.update_invite(
            invite_id,
            {
                "status": "revoked",
                "token_hash": f"revoked:{invite_id}:{invite['token_hash']}",
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        return self._public_invite(invite)

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

    def _ensure_auth_password_user(self, data: UserCreate) -> str:
        existing_id = self._find_auth_user_id(str(data.email).lower())
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
                "email": str(data.email).lower(),
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
                if (getattr(user, "email", "") or "").lower() == email.lower():
                    return str(user.id)
            if len(users) < per_page:
                return None
            page += 1

    def _set_auth_password_for_user(
        self,
        user: dict[str, Any],
        password: str,
        *,
        must_change_password: bool,
    ) -> None:
        metadata = {
            "tenant_id": self._tenant_id,
            "role": user["role"],
            "display_name": user.get("display_name"),
            "must_change_password": must_change_password,
        }
        try:
            get_supabase_admin().auth.admin.update_user_by_id(
                str(user["id"]),
                {
                    "password": password,
                    "user_metadata": metadata,
                },
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password could not be reset for this user",
            ) from exc

    def _revoke_pending_access_tokens_for_email(self, email: str) -> None:
        now = datetime.now(UTC).isoformat()
        for invite in self._repo.list_pending_invites_by_email(email):
            self._repo.update_invite(
                str(invite["id"]),
                {
                    "status": "revoked",
                    "token_hash": f"revoked:{invite['id']}:{invite['token_hash']}",
                    "updated_at": now,
                },
            )

    def _assert_invite(self, invite_id: str) -> dict[str, Any]:
        invite = self._repo.get_invite(invite_id)
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
        return self._expire_if_needed(invite)

    def _expire_if_needed(self, invite: dict[str, Any]) -> dict[str, Any]:
        if invite.get("status") != "pending":
            return invite
        expires_at = self._parse_datetime(invite.get("expires_at"))
        if expires_at and expires_at <= datetime.now(UTC):
            return self._repo.update_invite(
                invite["id"],
                {
                    "status": "expired",
                    "token_hash": f"expired:{invite['id']}:{invite['token_hash']}",
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
        return invite

    def _deliver_invite(self, invite: dict[str, Any], token: str) -> dict[str, Any]:
        invite_url = self._invite_url(token)
        is_setup = invite.get("purpose") == PASSWORD_SETUP_PURPOSE
        subject = (
            "Set up your Transmuter password"
            if is_setup
            else "You're invited to Transmuter"
        )
        action_text = (
            "Use this secure link to set your Transmuter password and access your workspace."
            if is_setup
            else "You have been invited to join Transmuter. Set your password and activate your account here:"
        )
        delivery = self._email.deliver(
            to=[invite["email"]],
            subject=subject,
            text=(
                f"{invite['display_name']},\n\n"
                f"{action_text}\n\n{invite_url}\n\n"
                "This link expires in 7 days."
            ),
        )
        updated = self._repo.update_invite(
            invite["id"],
            {
                "delivery_status": delivery.status,
                "delivery_detail": delivery.detail,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        if delivery.status != "sent":
            updated["invite_url"] = invite_url
        return self._public_invite(updated)

    @staticmethod
    def _public_invite(invite: dict[str, Any]) -> dict[str, Any]:
        public = {key: value for key, value in invite.items() if key != "token_hash"}
        return public

    @staticmethod
    def _new_invite_token() -> tuple[str, str]:
        token = token_urlsafe(48)
        return token, PeopleInviteAcceptanceService.hash_token(token)

    @staticmethod
    def _invite_expiry(now: datetime) -> str:
        return (now.replace(tzinfo=UTC) + timedelta(days=INVITE_EXPIRY_DAYS)).isoformat()

    @staticmethod
    def _invite_url(token: str) -> str:
        base = (settings.app_public_url or "http://localhost:4300").rstrip("/")
        return f"{base}/auth/accept-invite?{urlencode({'token': token})}"

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

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


class PeopleInviteAcceptanceService:
    def __init__(self, client: Client) -> None:
        self._client = client

    def accept_invite(self, data: InviteAccept) -> dict[str, Any]:
        PeopleService._validate_temporary_password(data.password)
        if data.password != data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password and confirmation do not match",
            )

        token_hash = self.hash_token(data.token)
        invite = self._get_pending_invite(token_hash)
        expires_at = PeopleService._parse_datetime(invite.get("expires_at"))
        if not expires_at or expires_at <= datetime.now(UTC):
            self._expire_invite(invite, token_hash)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invite has expired",
            )

        purpose = invite.get("purpose") or INVITE_PURPOSE
        if purpose == PASSWORD_SETUP_PURPOSE:
            return self._accept_password_setup(invite, token_hash, data.password)
        if purpose != INVITE_PURPOSE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite purpose is not supported",
            )
        return self._accept_new_invite(invite, token_hash, data.password)

    def _accept_new_invite(
        self,
        invite: dict[str, Any],
        token_hash: str,
        password: str,
    ) -> dict[str, Any]:
        email = str(invite["email"]).lower()
        tenant_id = str(invite["tenant_id"])
        if self._tenant_user_by_email(tenant_id, email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists in this tenant",
            )
        if self._find_auth_user_id(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An auth account already exists for this email",
            )

        auth_user_id = self._create_auth_user(invite, password)
        row = self._client.table("users").insert(
            {
                "id": auth_user_id,
                "tenant_id": tenant_id,
                "email": email,
                "display_name": invite["display_name"],
                "role": invite["role"],
                "title": invite.get("title"),
                "department": invite.get("department"),
                "market": invite.get("market"),
                "status": "active",
                "must_change_password": False,
                "onboarding_completed": False,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
        user = row.data[0] if row.data else {"id": auth_user_id, "tenant_id": tenant_id}
        workstream_ids = invite.get("workstream_ids") or []
        if workstream_ids:
            PeopleRepository(self._client, UUID(tenant_id)).replace_user_workstreams(
                auth_user_id,
                [str(workstream_id) for workstream_id in workstream_ids],
            )

        self._mark_invite_accepted(invite, token_hash, auth_user_id)
        return {"user": user, "email": email}

    def _accept_password_setup(
        self,
        invite: dict[str, Any],
        token_hash: str,
        password: str,
    ) -> dict[str, Any]:
        email = str(invite["email"]).lower()
        tenant_id = str(invite["tenant_id"])
        user = self._tenant_user_by_email(tenant_id, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account was not found for this setup link",
            )
        if user.get("status") in {"ghost", "deactivated"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User account is not active",
            )

        auth_user_id = str(user["id"])
        self._update_auth_password(user, password)
        updated = (
            self._client.table("users")
            .update(
                {
                    "status": "active",
                    "must_change_password": False,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("tenant_id", tenant_id)
            .eq("id", auth_user_id)
            .execute()
        )
        self._mark_invite_accepted(invite, token_hash, auth_user_id)
        row = updated.data[0] if updated.data else {**user, "status": "active"}
        return {"user": row, "email": email}

    def _mark_invite_accepted(
        self,
        invite: dict[str, Any],
        token_hash: str,
        auth_user_id: str,
    ) -> None:
        self._client.table("user_invites").update(
            {
                "status": "accepted",
                "accepted_at": datetime.now(UTC).isoformat(),
                "auth_user_id": auth_user_id,
                "token_hash": f"accepted:{invite['id']}:{token_hash}",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", invite["id"]).execute()

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _get_pending_invite(self, token_hash: str) -> dict[str, Any]:
        response = (
            self._client.table("user_invites")
            .select("*")
            .eq("token_hash", token_hash)
            .maybe_single()
            .execute()
        )
        invite = response.data if response else None
        if not invite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
        if invite.get("status") != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invite is no longer active",
            )
        return invite

    def _expire_invite(self, invite: dict[str, Any], token_hash: str) -> None:
        self._client.table("user_invites").update(
            {
                "status": "expired",
                "token_hash": f"expired:{invite['id']}:{token_hash}",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", invite["id"]).execute()

    def _tenant_user_by_email(self, tenant_id: str, email: str) -> dict[str, Any] | None:
        response = (
            self._client.table("users")
            .select("id, tenant_id, email, role, display_name, status")
            .eq("tenant_id", tenant_id)
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return response.data if response else None

    def _update_auth_password(self, user: dict[str, Any], password: str) -> None:
        try:
            self._client.auth.admin.update_user_by_id(
                str(user["id"]),
                {
                    "password": password,
                    "user_metadata": {
                        "tenant_id": str(user["tenant_id"]),
                        "role": user["role"],
                        "display_name": user.get("display_name"),
                        "must_change_password": False,
                    },
                },
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password could not be updated for this setup link",
            ) from exc

    def _create_auth_user(self, invite: dict[str, Any], password: str) -> str:
        response = self._client.auth.admin.create_user(
            {
                "email": str(invite["email"]).lower(),
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "tenant_id": str(invite["tenant_id"]),
                    "role": invite["role"],
                    "display_name": invite["display_name"],
                },
            }
        )
        return str(response.user.id)

    def _find_auth_user_id(self, email: str) -> str | None:
        page = 1
        per_page = 100
        while True:
            users = self._client.auth.admin.list_users(page=page, per_page=per_page)
            for user in users:
                if (getattr(user, "email", "") or "").lower() == email.lower():
                    return str(user.id)
            if len(users) < per_page:
                return None
            page += 1
