-- Migration: Add initiative_team table for collaboration
CREATE TABLE IF NOT EXISTS initiative_team (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role          TEXT NOT NULL DEFAULT 'member', -- member, reviewer, agent, qa
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (initiative_id, user_id)
);

CREATE INDEX IF NOT EXISTS it_tenant_idx ON initiative_team(tenant_id);
CREATE INDEX IF NOT EXISTS it_init_idx ON initiative_team(initiative_id);

ALTER TABLE initiative_team ENABLE ROW LEVEL SECURITY;

CREATE POLICY "it_select" ON initiative_team FOR SELECT USING (tenant_id = (select tenant_id from users where id = auth.uid()));
CREATE POLICY "it_insert" ON initiative_team FOR INSERT WITH CHECK (tenant_id = (select tenant_id from users where id = auth.uid()));
CREATE POLICY "it_update" ON initiative_team FOR UPDATE USING (tenant_id = (select tenant_id from users where id = auth.uid()));
CREATE POLICY "it_delete" ON initiative_team FOR DELETE USING (tenant_id = (select tenant_id from users where id = auth.uid()));
