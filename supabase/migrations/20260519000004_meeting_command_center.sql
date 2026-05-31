-- Meeting Command Center v1

ALTER TABLE meeting_sessions
  ADD COLUMN IF NOT EXISTS minutes_markdown TEXT,
  ADD COLUMN IF NOT EXISTS minutes_status TEXT NOT NULL DEFAULT 'not_generated'
    CHECK (minutes_status IN ('not_generated', 'draft', 'sent')),
  ADD COLUMN IF NOT EXISTS minutes_generated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS minutes_sent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS transcript_source TEXT;

CREATE TABLE IF NOT EXISTS meeting_artifacts (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id          UUID NOT NULL REFERENCES organizations(id),
  meeting_id         UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  session_id         UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
  agenda_item_id     UUID REFERENCES agenda_items(id) ON DELETE SET NULL,
  initiative_id      UUID REFERENCES initiatives(id) ON DELETE SET NULL,
  artifact_type      TEXT NOT NULL CHECK (artifact_type IN ('action', 'decision', 'risk', 'assumption', 'issue')),
  title              TEXT NOT NULL,
  description        TEXT,
  status             TEXT NOT NULL DEFAULT 'open',
  priority           TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
  owner_id           UUID REFERENCES users(id) ON DELETE SET NULL,
  assignee_id        UUID REFERENCES users(id) ON DELETE SET NULL,
  due_date           DATE,
  linked_record_type TEXT,
  linked_record_id   UUID,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS meeting_artifacts_tenant_idx ON meeting_artifacts(tenant_id);
CREATE INDEX IF NOT EXISTS meeting_artifacts_session_idx ON meeting_artifacts(session_id);
CREATE INDEX IF NOT EXISTS meeting_artifacts_meeting_idx ON meeting_artifacts(meeting_id);
CREATE INDEX IF NOT EXISTS meeting_artifacts_linked_record_idx
  ON meeting_artifacts(linked_record_type, linked_record_id);

ALTER TABLE meeting_artifacts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "meeting_artifacts_select" ON meeting_artifacts;
DROP POLICY IF EXISTS "meeting_artifacts_insert" ON meeting_artifacts;
DROP POLICY IF EXISTS "meeting_artifacts_update" ON meeting_artifacts;
DROP POLICY IF EXISTS "meeting_artifacts_delete" ON meeting_artifacts;
CREATE POLICY "meeting_artifacts_select" ON meeting_artifacts FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "meeting_artifacts_insert" ON meeting_artifacts FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "meeting_artifacts_update" ON meeting_artifacts FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "meeting_artifacts_delete" ON meeting_artifacts FOR DELETE USING (tenant_id = current_tenant_id());

CREATE TABLE IF NOT EXISTS meeting_external_events (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           UUID NOT NULL REFERENCES organizations(id),
  meeting_id          UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  provider            TEXT NOT NULL CHECK (provider IN ('microsoft')),
  external_event_id   TEXT,
  online_meeting_id   TEXT,
  join_url            TEXT,
  organizer_email     TEXT,
  sync_status         TEXT NOT NULL DEFAULT 'not_configured'
    CHECK (sync_status IN ('not_configured', 'pending', 'synced', 'failed')),
  sync_error          TEXT,
  last_synced_at      TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (meeting_id, provider)
);

CREATE INDEX IF NOT EXISTS meeting_external_events_tenant_idx ON meeting_external_events(tenant_id);
CREATE INDEX IF NOT EXISTS meeting_external_events_meeting_idx ON meeting_external_events(meeting_id);

ALTER TABLE meeting_external_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "meeting_external_events_select" ON meeting_external_events;
DROP POLICY IF EXISTS "meeting_external_events_insert" ON meeting_external_events;
DROP POLICY IF EXISTS "meeting_external_events_update" ON meeting_external_events;
DROP POLICY IF EXISTS "meeting_external_events_delete" ON meeting_external_events;
CREATE POLICY "meeting_external_events_select" ON meeting_external_events FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "meeting_external_events_insert" ON meeting_external_events FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "meeting_external_events_update" ON meeting_external_events FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "meeting_external_events_delete" ON meeting_external_events FOR DELETE USING (tenant_id = current_tenant_id());
