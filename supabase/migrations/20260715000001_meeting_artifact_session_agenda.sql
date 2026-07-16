-- Preserve agenda scope for artifacts captured against generated/session agenda rows.

ALTER TABLE meeting_artifacts
  ADD COLUMN IF NOT EXISTS session_agenda_item_id UUID
    REFERENCES meeting_session_agenda_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS meeting_artifacts_session_agenda_idx
  ON meeting_artifacts(tenant_id, session_agenda_item_id);
