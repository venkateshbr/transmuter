from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from app.core.config import settings

bearer = HTTPBearer()


@lru_cache
def get_supabase_admin() -> Client:
    """Service-role client for admin operations (migrations, background jobs).
    Never expose to user-facing requests — use get_supabase_user() for those.
    """
    return create_client(settings.supabase_url, settings.supabase_service_key)


def get_supabase_user(user_jwt: str) -> Client:
    """User-scoped client. RLS is enforced automatically via the user's JWT."""
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(user_jwt)
    return client


def get_supabase_request_client(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> Client:
    return get_supabase_user(credentials.credentials)
