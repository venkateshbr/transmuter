-- Bankable plan versions and immutable baseline snapshots.

CREATE TABLE bankable_plans (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL REFERENCES organizations(id),
  initiative_id         UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  version               INTEGER NOT NULL CHECK (version >= 1),
  trigger_type          TEXT NOT NULL CHECK (trigger_type IN ('approval', 'rebaseline')),
  trigger_submission_id UUID REFERENCES gate_submissions(id),
  locked_by_id          UUID REFERENCES users(id),
  locked_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  locked_reason         TEXT,
  snapshot              JSONB NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, initiative_id, version)
);

CREATE INDEX bankable_plans_initiative_idx ON bankable_plans(initiative_id, version DESC);
ALTER TABLE bankable_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "bp_select" ON bankable_plans FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "bp_insert" ON bankable_plans FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
