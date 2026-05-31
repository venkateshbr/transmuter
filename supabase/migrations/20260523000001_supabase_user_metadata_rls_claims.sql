-- Allow RLS helpers to work with first-party Supabase Auth access tokens.
-- Supabase places custom tenant/application role data under user_metadata,
-- while older app-minted tokens used top-level tenant_id and role claims.

CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid
  LANGUAGE sql STABLE
  AS $$
    SELECT COALESCE(
      auth.jwt() ->> 'tenant_id',
      auth.jwt() -> 'user_metadata' ->> 'tenant_id'
    )::uuid
  $$;

CREATE OR REPLACE FUNCTION current_user_role() RETURNS text
  LANGUAGE sql STABLE
  AS $$
    SELECT COALESCE(
      auth.jwt() ->> 'app_role',
      auth.jwt() -> 'user_metadata' ->> 'role',
      NULLIF(auth.jwt() ->> 'role', 'authenticated'),
      auth.jwt() ->> 'role'
    )
  $$;
