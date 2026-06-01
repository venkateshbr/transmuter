-- Support admin-created users with temporary passwords and forced first-login changes.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_status_check;

ALTER TABLE users
  ADD CONSTRAINT users_status_check
  CHECK (status IN ('pending','active','ghost','deactivated'));

CREATE INDEX IF NOT EXISTS users_tenant_status_idx ON users(tenant_id, status);
