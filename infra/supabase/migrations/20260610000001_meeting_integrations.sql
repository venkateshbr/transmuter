-- Tenant-scoped meeting integration connections and richer external event sync state.

CREATE TABLE IF NOT EXISTS integration_connections (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                UUID NOT NULL REFERENCES organizations(id),
  provider                 TEXT NOT NULL CHECK (provider IN ('microsoft_graph', 'recall_ai', 'fireflies')),
  organizer_email          TEXT,
  external_account_id      TEXT,
  access_token_encrypted   TEXT,
  refresh_token_encrypted  TEXT,
  token_expires_at         TIMESTAMPTZ,
  scopes                   TEXT[] NOT NULL DEFAULT '{}',
  sync_status              TEXT NOT NULL DEFAULT 'not_configured'
    CHECK (sync_status IN ('not_configured', 'pending', 'connected', 'failed', 'disabled')),
  sync_error               TEXT,
  last_synced_at           TIMESTAMPTZ,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, provider, organizer_email)
);

CREATE INDEX IF NOT EXISTS integration_connections_tenant_idx
  ON integration_connections(tenant_id);
CREATE INDEX IF NOT EXISTS integration_connections_provider_idx
  ON integration_connections(tenant_id, provider);

ALTER TABLE integration_connections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "integration_connections_select" ON integration_connections;
DROP POLICY IF EXISTS "integration_connections_insert" ON integration_connections;
DROP POLICY IF EXISTS "integration_connections_update" ON integration_connections;
DROP POLICY IF EXISTS "integration_connections_delete" ON integration_connections;
CREATE POLICY "integration_connections_select" ON integration_connections FOR SELECT USING (tenant_id = current_tenant_id());

REVOKE ALL ON integration_connections FROM authenticated;
GRANT SELECT (
  id,
  tenant_id,
  provider,
  organizer_email,
  external_account_id,
  token_expires_at,
  scopes,
  sync_status,
  sync_error,
  last_synced_at,
  created_at,
  updated_at
) ON integration_connections TO authenticated;
GRANT ALL ON integration_connections TO service_role;

ALTER TABLE meeting_external_events
  ADD COLUMN IF NOT EXISTS integration_connection_id UUID REFERENCES integration_connections(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS scheduled_start_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS scheduled_end_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS time_zone TEXT NOT NULL DEFAULT 'UTC';

CREATE INDEX IF NOT EXISTS meeting_external_events_connection_idx
  ON meeting_external_events(tenant_id, integration_connection_id);
