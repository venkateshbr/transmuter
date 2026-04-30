from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

bearer = HTTPBearer()


class TokenPayload(BaseModel):
    sub: str          # user id
    tenant_id: str
    role: str         # transformation_office | initiative_owner | workstream_lead
    email: str
    exp: int


class CurrentUser(BaseModel):
    id: UUID
    tenant_id: UUID
    role: str
    email: str


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except (JWTError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> CurrentUser:
    payload = decode_token(credentials.credentials)

    if datetime.fromtimestamp(payload.exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return CurrentUser(
        id=UUID(payload.sub),
        tenant_id=UUID(payload.tenant_id),
        role=payload.role,
        email=payload.email,
    )


def require_role(*roles: str):
    """Factory: returns a dependency that enforces one of the given roles."""
    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return _check


# Convenience role dependencies
RequireAdmin = Depends(require_role("transformation_office"))
RequireOwnerOrAdmin = Depends(require_role("transformation_office", "initiative_owner"))
AnyRole = Depends(get_current_user)
