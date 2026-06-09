-- Distinguish new-user invites from existing-user password setup links.

ALTER TABLE user_invites
  ADD COLUMN IF NOT EXISTS purpose TEXT NOT NULL DEFAULT 'invite';

ALTER TABLE user_invites
  DROP CONSTRAINT IF EXISTS user_invites_purpose_check;

ALTER TABLE user_invites
  ADD CONSTRAINT user_invites_purpose_check
  CHECK (purpose IN ('invite', 'password_setup'));

CREATE INDEX IF NOT EXISTS user_invites_tenant_purpose_status_idx
  ON user_invites(tenant_id, purpose, status);
