-- Meeting notes HITL workflow runs.

CREATE TABLE IF NOT EXISTS meeting_notes_workflow_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES organizations(id),
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
  submitter_user_id UUID NOT NULL REFERENCES users(id),
  transcript_text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'chunking'
    CHECK (status IN ('chunking','extracting','awaiting_review','approved','rejected','expired','failed')),
  chunks JSONB NOT NULL DEFAULT '[]'::jsonb,
  action_items JSONB NOT NULL DEFAULT '[]'::jsonb,
  decisions JSONB NOT NULL DEFAULT '[]'::jsonb,
  initiative_updates JSONB NOT NULL DEFAULT '[]'::jsonb,
  error TEXT,
  expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
  approved_at TIMESTAMPTZ,
  rejected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS mnwf_tenant_status_idx
  ON meeting_notes_workflow_runs(tenant_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS mnwf_session_idx
  ON meeting_notes_workflow_runs(tenant_id, session_id, created_at DESC);

ALTER TABLE meeting_notes_workflow_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "mnwf_select" ON meeting_notes_workflow_runs;
DROP POLICY IF EXISTS "mnwf_insert" ON meeting_notes_workflow_runs;
DROP POLICY IF EXISTS "mnwf_update" ON meeting_notes_workflow_runs;

CREATE POLICY "mnwf_select" ON meeting_notes_workflow_runs
  FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY "mnwf_insert" ON meeting_notes_workflow_runs
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY "mnwf_update" ON meeting_notes_workflow_runs
  FOR UPDATE USING (tenant_id = current_tenant_id())
  WITH CHECK (tenant_id = current_tenant_id());
