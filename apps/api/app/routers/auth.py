from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from supabase import create_client

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_supabase_admin
from jose import jwt

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response Models ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    tenant_id: str
    role: str


class UserProfile(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str
    display_name: str | None
    title: str | None
    status: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mint_token(user_id: str, tenant_id: str, role: str, email: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expiry_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authenticate with email + password. Returns a signed JWT."""
    # Use a FRESH anon client for sign-in — never mutate the cached admin client's session.
    anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        resp = anon_client.auth.sign_in_with_password({"email": body.email, "password": body.password})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc

    supabase_user = resp.user
    if not supabase_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Use admin client (service role) to fetch platform user — bypasses RLS.
    admin = get_supabase_admin()
    user_row = (
        admin.table("users")
        .select("id, tenant_id, role, status")
        .eq("id", str(supabase_user.id))
        .single()
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

    token = _mint_token(
        user_id=u["id"],
        tenant_id=u["tenant_id"],
        role=u["role"],
        email=body.email,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiry_minutes * 60,
        user_id=u["id"],
        tenant_id=u["tenant_id"],
        role=u["role"],
    )


@router.get("/me", response_model=UserProfile)
async def me(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> UserProfile:
    """Return the logged-in user's profile."""
    client = get_supabase_admin()
    row = (
        client.table("users")
        .select("id, tenant_id, email, role, display_name, title, status")
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
    )
