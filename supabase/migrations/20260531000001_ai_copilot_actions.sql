-- Migration: Durable AI copilot action drafts and confirmations

CREATE TABLE IF NOT EXISTS ai_copilot_actions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  user_id       UUID NOT NULL REFERENCES users(id),
  action_type   TEXT NOT NULL,
  title         TEXT NOT NULL,
  description   TEXT NOT NULL,
  payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
  payload_hash  TEXT NOT NULL,
  plan          JSONB NOT NULL DEFAULT '{}'::jsonb,
  guardrails    JSONB NOT NULL DEFAULT '[]'::jsonb,
  status        TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'confirmed', 'expired', 'cancelled', 'failed')),
  result        JSONB,
  expires_at    TIMESTAMPTZ NOT NULL,
  confirmed_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ai_copilot_actions_tenant_user_idx
  ON ai_copilot_actions(tenant_id, user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS ai_copilot_actions_expiry_idx
  ON ai_copilot_actions(tenant_id, status, expires_at);

ALTER TABLE ai_copilot_actions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "copilot_actions_select" ON ai_copilot_actions;
DROP POLICY IF EXISTS "copilot_actions_insert" ON ai_copilot_actions;
DROP POLICY IF EXISTS "copilot_actions_update" ON ai_copilot_actions;

CREATE POLICY "copilot_actions_select" ON ai_copilot_actions
  FOR SELECT USING (
    tenant_id = current_tenant_id()
    AND user_id = auth.uid()
  );

-- Drafts and confirmations are written only by the backend service-role client.
-- Do not add authenticated INSERT/UPDATE policies here: browser-visible Supabase
-- credentials must not be able to forge or mutate action payloads.
