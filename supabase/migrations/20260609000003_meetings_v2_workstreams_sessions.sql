-- Meetings v2 completion: multi-workstream series and dated sessions.

CREATE TABLE IF NOT EXISTS meeting_workstreams (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  meeting_id    UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  workstream_id UUID NOT NULL REFERENCES workstreams(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, meeting_id, workstream_id)
);

CREATE INDEX IF NOT EXISTS meeting_workstreams_tenant_idx
  ON meeting_workstreams(tenant_id);
CREATE INDEX IF NOT EXISTS meeting_workstreams_meeting_idx
  ON meeting_workstreams(tenant_id, meeting_id);
CREATE INDEX IF NOT EXISTS meeting_workstreams_workstream_idx
  ON meeting_workstreams(tenant_id, workstream_id);

INSERT INTO meeting_workstreams (tenant_id, meeting_id, workstream_id)
SELECT tenant_id, id, workstream_id
FROM meetings
WHERE workstream_id IS NOT NULL
ON CONFLICT (tenant_id, meeting_id, workstream_id) DO NOTHING;

ALTER TABLE meeting_workstreams ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "mw_select" ON meeting_workstreams;
DROP POLICY IF EXISTS "mw_insert" ON meeting_workstreams;
DROP POLICY IF EXISTS "mw_delete" ON meeting_workstreams;
CREATE POLICY "mw_select" ON meeting_workstreams FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "mw_insert" ON meeting_workstreams FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "mw_delete" ON meeting_workstreams FOR DELETE USING (tenant_id = current_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON meeting_workstreams TO authenticated;
GRANT SELECT ON meeting_workstreams TO anon;
GRANT ALL ON meeting_workstreams TO service_role;

CREATE UNIQUE INDEX IF NOT EXISTS meeting_sessions_tenant_meeting_date_idx
  ON meeting_sessions(tenant_id, meeting_id, session_date);
