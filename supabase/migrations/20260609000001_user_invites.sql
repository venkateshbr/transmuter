-- App-owned tenant invite lifecycle.

CREATE TABLE IF NOT EXISTS user_invites (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  email          TEXT NOT NULL,
  display_name   TEXT NOT NULL,
  role           TEXT NOT NULL CHECK (role IN ('transformation_office','initiative_owner','viewer')),
  title          TEXT,
  department     TEXT,
  market         TEXT,
  workstream_ids UUID[] NOT NULL DEFAULT '{}',
  token_hash     TEXT NOT NULL UNIQUE,
  status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','expired','revoked')),
  expires_at     TIMESTAMPTZ NOT NULL,
  accepted_at    TIMESTAMPTZ,
  created_by_id  UUID REFERENCES users(id),
  auth_user_id   UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  delivery_status TEXT,
  delivery_detail TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS user_invites_tenant_idx ON user_invites(tenant_id);
CREATE INDEX IF NOT EXISTS user_invites_tenant_status_idx ON user_invites(tenant_id, status);
CREATE INDEX IF NOT EXISTS user_invites_expires_idx ON user_invites(expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS user_invites_one_pending_email_idx
  ON user_invites(tenant_id, lower(email))
  WHERE status = 'pending';

ALTER TABLE user_invites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_invites_select" ON user_invites
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "user_invites_insert" ON user_invites
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "user_invites_update" ON user_invites
  FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

REVOKE INSERT, UPDATE, DELETE ON TABLE user_invites FROM anon, authenticated;
