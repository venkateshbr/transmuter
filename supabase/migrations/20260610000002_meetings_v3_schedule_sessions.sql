-- Meetings V3: scheduled series metadata and session-level snapshots.

ALTER TABLE meetings
  ADD COLUMN IF NOT EXISTS day_of_week INTEGER CHECK (day_of_week BETWEEN 0 AND 6),
  ADD COLUMN IF NOT EXISTS start_time TIME NOT NULL DEFAULT '09:00',
  ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC',
  ADD COLUMN IF NOT EXISTS duration_minutes INTEGER NOT NULL DEFAULT 60
    CHECK (duration_minutes > 0 AND duration_minutes <= 1440),
  ADD COLUMN IF NOT EXISTS one_off_date DATE;

ALTER TABLE meeting_sessions
  ADD COLUMN IF NOT EXISTS scheduled_start_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS scheduled_end_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS meeting_session_agenda_items (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL REFERENCES organizations(id),
  meeting_id            UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  session_id            UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
  source_agenda_item_id UUID REFERENCES agenda_items(id) ON DELETE SET NULL,
  initiative_id         UUID REFERENCES initiatives(id) ON DELETE SET NULL,
  text                  TEXT NOT NULL,
  sort_order            INTEGER DEFAULT 0,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, session_id, source_agenda_item_id)
);

CREATE INDEX IF NOT EXISTS meeting_session_agenda_tenant_idx
  ON meeting_session_agenda_items(tenant_id);
CREATE INDEX IF NOT EXISTS meeting_session_agenda_session_idx
  ON meeting_session_agenda_items(tenant_id, session_id);

ALTER TABLE meeting_session_agenda_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "msag_select" ON meeting_session_agenda_items;
DROP POLICY IF EXISTS "msag_insert" ON meeting_session_agenda_items;
DROP POLICY IF EXISTS "msag_update" ON meeting_session_agenda_items;
DROP POLICY IF EXISTS "msag_delete" ON meeting_session_agenda_items;
CREATE POLICY "msag_select" ON meeting_session_agenda_items FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "msag_insert" ON meeting_session_agenda_items FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "msag_update" ON meeting_session_agenda_items FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "msag_delete" ON meeting_session_agenda_items FOR DELETE USING (tenant_id = current_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON meeting_session_agenda_items TO authenticated;
GRANT ALL ON meeting_session_agenda_items TO service_role;

CREATE TABLE IF NOT EXISTS meeting_session_attendees (
  id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                  UUID NOT NULL REFERENCES organizations(id),
  meeting_id                 UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  session_id                 UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
  source_meeting_attendee_id UUID REFERENCES meeting_attendees(id) ON DELETE SET NULL,
  user_id                    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, session_id, user_id)
);

CREATE INDEX IF NOT EXISTS meeting_session_attendees_tenant_idx
  ON meeting_session_attendees(tenant_id);
CREATE INDEX IF NOT EXISTS meeting_session_attendees_session_idx
  ON meeting_session_attendees(tenant_id, session_id);

ALTER TABLE meeting_session_attendees ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "msatt_select" ON meeting_session_attendees;
DROP POLICY IF EXISTS "msatt_insert" ON meeting_session_attendees;
DROP POLICY IF EXISTS "msatt_delete" ON meeting_session_attendees;
CREATE POLICY "msatt_select" ON meeting_session_attendees FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "msatt_insert" ON meeting_session_attendees FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "msatt_delete" ON meeting_session_attendees FOR DELETE USING (tenant_id = current_tenant_id());

GRANT SELECT, INSERT, UPDATE, DELETE ON meeting_session_attendees TO authenticated;
GRANT ALL ON meeting_session_attendees TO service_role;

ALTER TABLE meeting_external_events
  ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES meeting_sessions(id) ON DELETE CASCADE;

ALTER TABLE meeting_external_events
  DROP CONSTRAINT IF EXISTS meeting_external_events_meeting_id_provider_key;

CREATE INDEX IF NOT EXISTS meeting_external_events_session_idx
  ON meeting_external_events(tenant_id, session_id);
CREATE UNIQUE INDEX IF NOT EXISTS meeting_external_events_series_provider_idx
  ON meeting_external_events(tenant_id, meeting_id, provider)
  WHERE session_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS meeting_external_events_session_provider_idx
  ON meeting_external_events(tenant_id, session_id, provider)
  WHERE session_id IS NOT NULL;
