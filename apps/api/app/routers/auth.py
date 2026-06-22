from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_supabase_admin
from app.domain.people import InviteAccept
from app.services.demo_portfolio_bootstrap import bootstrap_demo_portfolio
from app.services.people import PeopleInviteAcceptanceService
from app.services.tenant_bootstrap import TenantBootstrapService

router = APIRouter(prefix="/auth", tags=["auth"])
PLATFORM_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


# ── Request / Response Models ─────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    tenant_id: str
    role: str
    status: str = "active"
    must_change_password: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str
    display_name: str | None
    title: str | None
    status: str
    onboarding_completed: bool
    must_change_password: bool = False


class RegisterRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=200)
    organization_slug: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    admin_display_name: str = Field(..., min_length=1, max_length=200)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=12, max_length=256)
    invite_token: str | None = Field(None, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


class ChangePasswordResponse(BaseModel):
    status: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mint_token(user_id: str, tenant_id: str, role: str) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expiry_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _platform_admin_emails() -> set[str]:
    return {
        item.strip().lower() for item in settings.platform_admin_emails.split(",") if item.strip()
    }


def _platform_admin_profile_email() -> str:
    configured = sorted(_platform_admin_emails())
    return configured[0] if configured else "platform-admin@transmuter.local"


def _auth_metadata(user: Any, key: str) -> dict[str, Any]:
    value = getattr(user, key, None) or {}
    return value if isinstance(value, dict) else {}


def _is_platform_admin_auth_user(user: Any, email: str | None) -> bool:
    if (email or "").lower() not in _platform_admin_emails():
        return False
    app_metadata = _auth_metadata(user, "app_metadata")
    return (
        app_metadata.get("role") == "platform_admin" or app_metadata.get("platform_admin") is True
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authenticate with email + password. Returns a signed JWT."""
    # Use a FRESH anon client for sign-in — never mutate the cached admin client's session.
    anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        resp = anon_client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from exc

    supabase_user = resp.user
    if not supabase_user or not resp.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return _token_response_for_session(supabase_user, resp.session, str(body.email))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_blank_tenant(body: RegisterRequest) -> TokenResponse:
    """Create a blank tenant and first transformation-office admin."""
    if not settings.public_registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration is not enabled",
        )
    if (
        settings.registration_invite_token
        and body.invite_token != settings.registration_invite_token
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration invite token is invalid",
        )
    if str(body.admin_email).lower() in _platform_admin_emails():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email cannot be used for tenant registration",
        )
    _validate_new_password(body.admin_password)
    admin = get_supabase_admin()
    existing_org = (
        admin.table("organizations")
        .select("id")
        .eq("slug", body.organization_slug)
        .maybe_single()
        .execute()
    )
    if existing_org and existing_org.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug is already in use",
        )

    existing_user = (
        admin.table("users")
        .select("id,tenant_id")
        .eq("email", str(body.admin_email))
        .maybe_single()
        .execute()
    )
    if existing_user and existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin email is already registered",
        )
    if _find_auth_user_by_email(str(body.admin_email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin email is already registered",
        )

    tenant_id = str(uuid4())
    auth_user_id: str | None = None
    admin.table("organizations").insert(
        {
            "id": tenant_id,
            "name": body.organization_name,
            "slug": body.organization_slug,
            "settings": {},
        }
    ).execute()
    try:
        auth_user = admin.auth.admin.create_user(
            {
                "email": str(body.admin_email),
                "password": body.admin_password,
                "email_confirm": True,
                "user_metadata": {
                    "tenant_id": tenant_id,
                    "role": "transformation_office",
                    "display_name": body.admin_display_name,
                },
            }
        )
        auth_user_id = str(auth_user.user.id)
        admin.table("users").insert(
            {
                "id": auth_user_id,
                "tenant_id": tenant_id,
                "email": str(body.admin_email),
                "display_name": body.admin_display_name,
                "title": "Organization Admin",
                "role": "transformation_office",
                "status": "active",
                "must_change_password": False,
                "onboarding_completed": False,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
        TenantBootstrapService(admin).bootstrap_tenant(tenant_id)
        if settings.bootstrap_demo_data_on_registration:
            bootstrap_demo_portfolio(admin, tenant_id, auth_user_id)
    except Exception as exc:
        if auth_user_id:
            with suppress(Exception):
                admin.auth.admin.delete_user(auth_user_id)
        _cleanup_failed_registration(admin, tenant_id, auth_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant registration could not be completed",
        ) from exc

    anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        resp = anon_client.auth.sign_in_with_password(
            {"email": str(body.admin_email), "password": body.admin_password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant created, but automatic sign-in failed. Please sign in manually.",
        ) from exc
    return _token_response_for_session(resp.user, resp.session, str(body.admin_email))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(body: RefreshRequest) -> TokenResponse:
    """Rotate a Supabase refresh token and return the refreshed session."""
    anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        resp = anon_client.auth.refresh_session(body.refresh_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    supabase_user = resp.user
    if not supabase_user or not resp.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    return _token_response_for_session(supabase_user, resp.session, supabase_user.email)


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(body: InviteAccept) -> TokenResponse:
    accepted = PeopleInviteAcceptanceService(get_supabase_admin()).accept_invite(body)
    anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        resp = anon_client.auth.sign_in_with_password(
            {"email": accepted["email"], "password": body.password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invite accepted, but automatic sign-in failed. Please sign in manually.",
        ) from exc
    return _token_response_for_session(resp.user, resp.session, accepted["email"])


def _token_response_for_session(
    supabase_user: Any, session: Any, email: str | None
) -> TokenResponse:
    if _is_platform_admin_auth_user(supabase_user, email):
        return TokenResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user_id=str(supabase_user.id),
            tenant_id=str(PLATFORM_TENANT_ID),
            role="platform_admin",
            status="active",
            must_change_password=False,
        )

    # Use admin client (service role) to fetch platform user — bypasses RLS.
    admin = get_supabase_admin()
    user_row = (
        admin.table("users")
        .select("id, tenant_id, role, status, must_change_password")
        .eq("id", str(supabase_user.id))
        .maybe_single()
        .execute()
    )
    if not user_row.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account not found in platform",
        )

    u = user_row.data
    if u["status"] == "deactivated":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    if u["status"] == "ghost":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user_id=u["id"],
        tenant_id=u["tenant_id"],
        role=u["role"],
        status=u["status"],
        must_change_password=bool(u.get("must_change_password")),
    )


def _find_auth_user_by_email(email: str) -> str | None:
    page = 1
    per_page = 100
    admin = get_supabase_admin()
    while True:
        users = admin.auth.admin.list_users(page=page, per_page=per_page)
        for user in users:
            if (getattr(user, "email", "") or "").lower() == email.lower():
                return str(user.id)
        if len(users) < per_page:
            return None
        page += 1


def _cleanup_failed_registration(admin: Any, tenant_id: str, auth_user_id: str | None) -> None:
    tenant_tables = [
        "user_workstreams",
        "users",
        "gate_criteria",
        "financial_initiative_annual_baselines",
        "financial_tenant_annual_baselines",
        "initiative_financial_scope",
        "financial_bridge_rows",
        "financial_cost_categories",
        "financial_metric_definitions",
        "financial_scenarios",
        "financial_config_items",
        "financial_config_groups",
        "tenant_dashboard_config",
    ]
    for table in tenant_tables:
        with suppress(Exception):
            query = admin.table(table).delete().eq("tenant_id", tenant_id)
            if table == "users" and auth_user_id:
                query = query.eq("id", auth_user_id)
            query.execute()
    with suppress(Exception):
        admin.table("organizations").delete().eq("id", tenant_id).execute()


@router.get("/me", response_model=UserProfile)
async def me(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> UserProfile:
    """Return the logged-in user's profile."""
    if current_user.role == "platform_admin":
        return UserProfile(
            id=current_user.id,
            tenant_id=current_user.tenant_id,
            email=_platform_admin_profile_email(),
            role="platform_admin",
            display_name="Platform Admin",
            title="SaaS Operator",
            status="active",
            onboarding_completed=True,
            must_change_password=False,
        )

    client = get_supabase_admin()
    row = (
        client.table("users")
        .select(
            "id, tenant_id, email, role, display_name, title, status, "
            "onboarding_completed, must_change_password"
        )
        .eq("id", str(current_user.id))
        .single()
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    d = row.data
    return UserProfile(
        id=d["id"],
        tenant_id=d["tenant_id"],
        email=d["email"],
        role=d["role"],
        display_name=d.get("display_name"),
        title=d.get("title"),
        status=d["status"],
        onboarding_completed=d.get("onboarding_completed", False),
        must_change_password=bool(d.get("must_change_password")),
    )


@router.patch("/me", response_model=UserProfile)
async def patch_me(
    body: dict, current_user: Annotated[CurrentUser, Depends(get_current_user)]
) -> UserProfile:
    """Update the logged-in user's profile."""
    client = get_supabase_admin()

    # Only allow updating certain fields
    allowed_fields = {"display_name", "title", "onboarding_completed"}
    patch = {k: v for k, v in body.items() if k in allowed_fields}

    if not patch:
        return await me(current_user)

    patch["updated_at"] = datetime.now(tz=UTC).isoformat()

    row = client.table("users").update(patch).eq("id", str(current_user.id)).execute()

    if not row.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return await me(current_user)


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> TokenResponse:
    """Change the logged-in user's Supabase Auth password after re-authentication."""
    _validate_password_change_body(body)
    email = _email_for_current_user(current_user)
    anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        anon_client.auth.sign_in_with_password({"email": email, "password": body.current_password})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        ) from exc

    try:
        admin = get_supabase_admin()
        admin.auth.admin.update_user_by_id(
            str(current_user.id),
            {"password": body.new_password},
        )
        admin.table("users").update(
            {
                "must_change_password": False,
                "status": "active",
                "updated_at": datetime.now(tz=UTC).isoformat(),
            }
        ).eq("id", str(current_user.id)).eq("tenant_id", str(current_user.tenant_id)).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password could not be updated",
        ) from exc

    try:
        resp = anon_client.auth.sign_in_with_password(
            {"email": email, "password": body.new_password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password changed, but automatic sign-in failed. Please sign in manually.",
        ) from exc

    return _token_response_for_session(resp.user, resp.session, email)


def _validate_new_password(password: str) -> None:
    if len(password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters",
        )
    if not any(ch.islower() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include a lowercase letter",
        )
    if not any(ch.isupper() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include an uppercase letter",
        )
    if not any(ch.isdigit() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include a number",
        )


def _validate_password_change_body(body: ChangePasswordRequest) -> None:
    if not body.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is required",
        )
    if len(body.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 12 characters",
        )
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )
    if not any(ch.islower() for ch in body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must include a lowercase letter",
        )
    if not any(ch.isupper() for ch in body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must include an uppercase letter",
        )
    if not any(ch.isdigit() for ch in body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must include a number",
        )


def _email_for_current_user(current_user: CurrentUser) -> str:
    if current_user.role == "platform_admin":
        return _platform_admin_profile_email()

    row = (
        get_supabase_admin()
        .table("users")
        .select("email")
        .eq("id", str(current_user.id))
        .eq("tenant_id", str(current_user.tenant_id))
        .single()
        .execute()
    )
    if not row.data or not row.data.get("email"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return row.data["email"]
