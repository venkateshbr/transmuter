-- Meeting series cancellation support.

ALTER TABLE meetings
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'cancelled'));

CREATE INDEX IF NOT EXISTS meetings_tenant_status_idx
  ON meetings(tenant_id, status);

ALTER TABLE meeting_sessions
  DROP CONSTRAINT IF EXISTS meeting_sessions_status_check;

ALTER TABLE meeting_sessions
  ADD CONSTRAINT meeting_sessions_status_check
  CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled'));

ALTER TABLE meeting_external_events
  DROP CONSTRAINT IF EXISTS meeting_external_events_sync_status_check;

ALTER TABLE meeting_external_events
  ADD CONSTRAINT meeting_external_events_sync_status_check
  CHECK (sync_status IN ('not_configured', 'pending', 'synced', 'failed', 'cancelled'));
