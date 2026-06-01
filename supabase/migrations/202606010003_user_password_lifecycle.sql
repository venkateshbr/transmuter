-- Support admin-created users with temporary passwords and forced first-login changes.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_status_check;

ALTER TABLE users
  ADD CONSTRAINT users_status_check
  CHECK (status IN ('pending','active','ghost','deactivated'));

CREATE INDEX IF NOT EXISTS users_tenant_status_idx ON users(tenant_id, status);

-- User lifecycle fields are service-role controlled. Direct Supabase clients may
-- read tenant users, but cannot mutate role, status, or forced-password state.
DROP POLICY IF EXISTS "users_insert" ON users;
DROP POLICY IF EXISTS "users_update" ON users;
DROP POLICY IF EXISTS "users_delete" ON users;

REVOKE INSERT, UPDATE, DELETE ON TABLE users FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON TABLE user_workstreams FROM anon, authenticated;
