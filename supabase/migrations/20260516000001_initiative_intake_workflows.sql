-- Initiative intake HITL workflow runs.

CREATE TABLE IF NOT EXISTS initiative_intake_workflow_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES organizations(id),
  submitter_user_id UUID NOT NULL REFERENCES users(id),
  raw_text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'extracting'
    CHECK (status IN ('extracting','suggesting','awaiting_review','approved','rejected','expired','failed')),
  extracted_draft JSONB NOT NULL DEFAULT '{}'::jsonb,
  kpi_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb,
  risk_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_initiative_id UUID REFERENCES initiatives(id) ON DELETE SET NULL,
  error TEXT,
  expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '48 hours',
  approved_at TIMESTAMPTZ,
  rejected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS iiwf_tenant_status_idx
  ON initiative_intake_workflow_runs(tenant_id, status, created_at DESC);

ALTER TABLE initiative_intake_workflow_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "iiwf_select" ON initiative_intake_workflow_runs;
DROP POLICY IF EXISTS "iiwf_insert" ON initiative_intake_workflow_runs;
DROP POLICY IF EXISTS "iiwf_update" ON initiative_intake_workflow_runs;

CREATE POLICY "iiwf_select" ON initiative_intake_workflow_runs
  FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY "iiwf_insert" ON initiative_intake_workflow_runs
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY "iiwf_update" ON initiative_intake_workflow_runs
  FOR UPDATE USING (tenant_id = current_tenant_id())
  WITH CHECK (tenant_id = current_tenant_id());
