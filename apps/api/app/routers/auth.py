from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, EmailStr
from supabase import create_client

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_supabase_admin

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


def _token_response_for_session(
    supabase_user: Any, session: Any, email: str | None
) -> TokenResponse:
    if (email or "").lower() in _platform_admin_emails():
        return TokenResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user_id=str(supabase_user.id),
            tenant_id=str(PLATFORM_TENANT_ID),
            role="platform_admin",
        )

    # Use admin client (service role) to fetch platform user — bypasses RLS.
    admin = get_supabase_admin()
    user_row = (
        admin.table("users")
        .select("id, tenant_id, role, status")
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

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user_id=u["id"],
        tenant_id=u["tenant_id"],
        role=u["role"],
    )


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
        )

    client = get_supabase_admin()
    row = (
        client.table("users")
        .select("id, tenant_id, email, role, display_name, title, status, onboarding_completed")
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


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ChangePasswordResponse:
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
        get_supabase_admin().auth.admin.update_user_by_id(
            str(current_user.id),
            {"password": body.new_password},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password could not be updated",
        ) from exc

    return ChangePasswordResponse(status="password_changed")


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
