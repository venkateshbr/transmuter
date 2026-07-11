-- Bind Microsoft Graph OAuth credentials to one deployment and make callback
-- state one-time, tenant-scoped, and service-role only.
-- Rollback category: forward-fix-only. Apply with the application stack stopped;
-- never restart pre-migration code after this transaction commits.

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS users_tenant_id_id_key
  ON users(tenant_id, id);

ALTER TABLE integration_connections
  ADD COLUMN IF NOT EXISTS deployment_environment TEXT,
  ADD COLUMN IF NOT EXISTS deployment_schema TEXT,
  ADD COLUMN IF NOT EXISTS entra_tenant_id UUID,
  ADD COLUMN IF NOT EXISTS oauth_client_id UUID,
  ADD COLUMN IF NOT EXISTS oauth_redirect_uri TEXT,
  ADD COLUMN IF NOT EXISTS encryption_key_fingerprint TEXT,
  ADD COLUMN IF NOT EXISTS context_fingerprint TEXT,
  ADD COLUMN IF NOT EXISTS oauth_generation BIGINT,
  ADD COLUMN IF NOT EXISTS token_generation BIGINT,
  ADD COLUMN IF NOT EXISTS connected_by_user_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS integration_connections_tenant_id_id_key
  ON integration_connections(tenant_id, id);

ALTER TABLE integration_connections
  DROP CONSTRAINT IF EXISTS integration_connections_connected_by_user_id_fkey;
ALTER TABLE integration_connections
  DROP CONSTRAINT IF EXISTS integration_connections_tenant_connected_by_user_fkey;
ALTER TABLE integration_connections
  ADD CONSTRAINT integration_connections_tenant_connected_by_user_fkey
  FOREIGN KEY (tenant_id, connected_by_user_id)
  REFERENCES users(tenant_id, id)
  ON DELETE SET NULL (connected_by_user_id);

ALTER TABLE integration_connections
  DROP CONSTRAINT IF EXISTS integration_connections_sync_status_check;
ALTER TABLE integration_connections
  ADD CONSTRAINT integration_connections_sync_status_check CHECK (
    sync_status IN (
      'not_configured',
      'pending',
      'connected',
      'failed',
      'disabled',
      'reconnect_required'
    )
  );

DO $migration$
DECLARE
  app_schema NAME := current_schema();
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_constraint
    WHERE conname = 'integration_connections_tenant_provider_external_account_key'
      AND conrelid = format('%I.integration_connections', app_schema)::regclass
  ) THEN
    EXECUTE format(
      'ALTER TABLE %I.integration_connections '
      'ADD CONSTRAINT integration_connections_tenant_provider_external_account_key '
      'UNIQUE (tenant_id, provider, external_account_id)',
      app_schema
    );
  END IF;
END
$migration$;

CREATE UNIQUE INDEX IF NOT EXISTS integration_connections_graph_organizer_email_key
  ON integration_connections(tenant_id, provider, lower(organizer_email))
  WHERE provider = 'microsoft_graph' AND organizer_email IS NOT NULL;

DO $migration$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM meeting_external_events AS external_event
    JOIN integration_connections AS connection
      ON connection.id = external_event.integration_connection_id
    WHERE external_event.integration_connection_id IS NOT NULL
      AND external_event.tenant_id <> connection.tenant_id
  ) THEN
    RAISE EXCEPTION 'Cross-tenant meeting integration references must be removed first';
  END IF;
END
$migration$;

ALTER TABLE meeting_external_events
  DROP CONSTRAINT IF EXISTS meeting_external_events_integration_connection_id_fkey;
ALTER TABLE meeting_external_events
  DROP CONSTRAINT IF EXISTS meeting_external_events_tenant_connection_fkey;
ALTER TABLE meeting_external_events
  ADD CONSTRAINT meeting_external_events_tenant_connection_fkey
  FOREIGN KEY (tenant_id, integration_connection_id)
  REFERENCES integration_connections(tenant_id, id)
  ON DELETE SET NULL (integration_connection_id);

UPDATE integration_connections
SET
  sync_status = 'reconnect_required',
  sync_error = 'oauth_context_missing',
  updated_at = NOW()
WHERE provider = 'microsoft_graph'
  AND (
    deployment_environment IS NULL
    OR deployment_schema IS NULL
    OR entra_tenant_id IS NULL
    OR oauth_client_id IS NULL
    OR oauth_redirect_uri IS NULL
    OR encryption_key_fingerprint IS NULL
    OR context_fingerprint IS NULL
    OR oauth_generation IS NULL
    OR token_generation IS NULL
    OR connected_by_user_id IS NULL
    OR NULLIF(access_token_encrypted, '') IS NULL
    OR NULLIF(refresh_token_encrypted, '') IS NULL
    OR token_expires_at IS NULL
    OR NOT pg_catalog.isfinite(token_expires_at)
    OR NULLIF(external_account_id, '') IS NULL
    OR cardinality(scopes) = 0
  );

ALTER TABLE integration_connections
  DROP CONSTRAINT IF EXISTS integration_connections_microsoft_context_check;
ALTER TABLE integration_connections
  ADD CONSTRAINT integration_connections_microsoft_context_check CHECK (
    provider <> 'microsoft_graph'
    OR sync_status <> 'connected'
    OR (
      NULLIF(deployment_environment, '') IS NOT NULL
      AND NULLIF(deployment_schema, '') IS NOT NULL
      AND entra_tenant_id IS NOT NULL
      AND oauth_client_id IS NOT NULL
      AND NULLIF(oauth_redirect_uri, '') IS NOT NULL
      AND NULLIF(encryption_key_fingerprint, '') IS NOT NULL
      AND NULLIF(context_fingerprint, '') IS NOT NULL
      AND oauth_generation IS NOT NULL
      AND oauth_generation > 0
      AND token_generation IS NOT NULL
      AND token_generation >= 0
      AND NULLIF(access_token_encrypted, '') IS NOT NULL
      AND NULLIF(refresh_token_encrypted, '') IS NOT NULL
      AND token_expires_at IS NOT NULL
      AND pg_catalog.isfinite(token_expires_at)
      AND token_expires_at <= updated_at + INTERVAL '24 hours'
      AND NULLIF(external_account_id, '') IS NOT NULL
      AND cardinality(scopes) > 0
    )
  );

CREATE TABLE IF NOT EXISTS integration_oauth_states (
  id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  oauth_generation           BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
  tenant_id                  UUID NOT NULL REFERENCES organizations(id),
  provider                   TEXT NOT NULL CHECK (provider = 'microsoft_graph'),
  state_digest               TEXT NOT NULL UNIQUE CHECK (state_digest ~ '^[0-9a-f]{64}$'),
  browser_binding_digest     TEXT NOT NULL CHECK (browser_binding_digest ~ '^[0-9a-f]{64}$'),
  initiated_by_user_id       UUID NOT NULL,
  pkce_verifier_encrypted    TEXT,
  nonce_digest               TEXT NOT NULL CHECK (nonce_digest ~ '^[0-9a-f]{64}$'),
  deployment_environment     TEXT NOT NULL CHECK (deployment_environment <> ''),
  deployment_schema          TEXT NOT NULL CHECK (deployment_schema <> ''),
  entra_tenant_id            UUID NOT NULL,
  oauth_client_id            UUID NOT NULL,
  oauth_redirect_uri         TEXT NOT NULL CHECK (oauth_redirect_uri <> ''),
  encryption_key_fingerprint TEXT NOT NULL CHECK (encryption_key_fingerprint <> ''),
  context_fingerprint        TEXT NOT NULL CHECK (context_fingerprint <> ''),
  authorization_scopes       TEXT[] NOT NULL CHECK (cardinality(authorization_scopes) > 0),
  required_api_scopes        TEXT[] NOT NULL CHECK (cardinality(required_api_scopes) > 0),
  expires_at                 TIMESTAMPTZ NOT NULL,
  consumed_at                TIMESTAMPTZ,
  cancelled_at               TIMESTAMPTZ,
  failed_at                  TIMESTAMPTZ,
  completed_at               TIMESTAMPTZ,
  failure_code               TEXT,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT integration_oauth_states_lifetime_check
    CHECK (expires_at > created_at AND expires_at <= created_at + INTERVAL '10 minutes'),
  CONSTRAINT integration_oauth_states_terminal_check CHECK (
    num_nonnulls(cancelled_at, failed_at, completed_at) <= 1
    AND (
      num_nonnulls(cancelled_at, failed_at, completed_at) = 0
      OR consumed_at IS NOT NULL
    )
    AND (
      (num_nonnulls(cancelled_at, failed_at, completed_at) = 0
        AND pkce_verifier_encrypted IS NOT NULL)
      OR
      (num_nonnulls(cancelled_at, failed_at, completed_at) = 1
        AND pkce_verifier_encrypted IS NULL)
    )
  )
);

ALTER TABLE integration_oauth_states
  DROP CONSTRAINT IF EXISTS integration_oauth_states_initiated_by_user_id_fkey;
ALTER TABLE integration_oauth_states
  DROP CONSTRAINT IF EXISTS integration_oauth_states_tenant_initiated_by_user_fkey;
ALTER TABLE integration_oauth_states
  ADD CONSTRAINT integration_oauth_states_tenant_initiated_by_user_fkey
  FOREIGN KEY (tenant_id, initiated_by_user_id)
  REFERENCES users(tenant_id, id)
  ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS integration_oauth_states_tenant_provider_idx
  ON integration_oauth_states(tenant_id, provider, created_at DESC);
CREATE INDEX IF NOT EXISTS integration_oauth_states_expiry_idx
  ON integration_oauth_states(expires_at);

ALTER TABLE integration_oauth_states ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "integration_oauth_states_service_role_all" ON integration_oauth_states;
CREATE POLICY "integration_oauth_states_service_role_all"
  ON integration_oauth_states
  FOR ALL
  TO service_role
  USING (TRUE)
  WITH CHECK (TRUE);
REVOKE ALL PRIVILEGES ON integration_oauth_states FROM PUBLIC, anon, authenticated;
REVOKE ALL PRIVILEGES ON integration_oauth_states FROM service_role;
GRANT SELECT, UPDATE, DELETE ON integration_oauth_states TO service_role;
REVOKE ALL PRIVILEGES ON SEQUENCE integration_oauth_states_oauth_generation_seq
  FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL PRIVILEGES ON integration_connections FROM PUBLIC, anon, authenticated;
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
  updated_at,
  deployment_environment,
  deployment_schema,
  entra_tenant_id,
  oauth_client_id,
  oauth_redirect_uri,
  context_fingerprint,
  oauth_generation,
  token_generation,
  connected_by_user_id
) ON integration_connections TO authenticated;
GRANT ALL PRIVILEGES ON integration_connections TO service_role;

DO $migration$
DECLARE
  app_schema NAME := current_schema();
  migration_owner OID;
BEGIN
  SELECT role.oid
  INTO migration_owner
  FROM pg_catalog.pg_roles AS role
  WHERE role.rolname = current_user
    AND (role.rolsuper OR role.rolbypassrls);

  IF migration_owner IS NULL THEN
    RAISE EXCEPTION 'Microsoft Graph OAuth migration owner must bypass RLS';
  END IF;
  IF EXISTS (
    SELECT 1
    FROM pg_catalog.pg_class AS relation
    WHERE relation.oid IN (
      format('%I.integration_connections', app_schema)::regclass,
      format('%I.integration_oauth_states', app_schema)::regclass
    )
      AND relation.relowner <> migration_owner
  ) THEN
    RAISE EXCEPTION 'Microsoft Graph OAuth tables must be owned by the migration owner';
  END IF;
END
$migration$;

DO $migration$
DECLARE
  app_schema NAME := current_schema();
BEGIN
  EXECUTE format(
    $definition$
      CREATE OR REPLACE FUNCTION %1$I.create_microsoft_graph_oauth_state(
        p_tenant_id UUID,
        p_provider TEXT,
        p_state_digest TEXT,
        p_browser_binding_digest TEXT,
        p_initiated_by_user_id UUID,
        p_pkce_verifier_encrypted TEXT,
        p_nonce_digest TEXT,
        p_deployment_environment TEXT,
        p_deployment_schema TEXT,
        p_entra_tenant_id UUID,
        p_oauth_client_id UUID,
        p_oauth_redirect_uri TEXT,
        p_encryption_key_fingerprint TEXT,
        p_context_fingerprint TEXT,
        p_authorization_scopes TEXT[],
        p_required_api_scopes TEXT[]
      )
      RETURNS UUID
      LANGUAGE plpgsql
      SECURITY DEFINER
      SET search_path = pg_catalog, %1$I
      AS $body$
      DECLARE
        created_state_id UUID;
        now_at TIMESTAMPTZ := pg_catalog.clock_timestamp();
      BEGIN
        IF p_provider <> 'microsoft_graph'
          OR NULLIF(p_state_digest, '') IS NULL
          OR NULLIF(p_browser_binding_digest, '') IS NULL
          OR NULLIF(p_pkce_verifier_encrypted, '') IS NULL
          OR NULLIF(p_nonce_digest, '') IS NULL
          OR NULLIF(p_deployment_environment, '') IS NULL
          OR NULLIF(p_deployment_schema, '') IS NULL
          OR p_entra_tenant_id IS NULL
          OR p_oauth_client_id IS NULL
          OR NULLIF(p_oauth_redirect_uri, '') IS NULL
          OR NULLIF(p_encryption_key_fingerprint, '') IS NULL
          OR NULLIF(p_context_fingerprint, '') IS NULL
          OR cardinality(p_authorization_scopes) = 0
          OR cardinality(p_required_api_scopes) = 0
        THEN
          RAISE EXCEPTION 'invalid_oauth_state';
        END IF;

        PERFORM pg_catalog.pg_advisory_xact_lock(
          pg_catalog.hashtextextended(
            %2$L || ':' || p_tenant_id::TEXT || ':' || p_provider,
            0
          )
        );

        PERFORM 1
        FROM %1$I.users AS platform_user
        WHERE platform_user.tenant_id = p_tenant_id
          AND platform_user.id = p_initiated_by_user_id
          AND platform_user.status = 'active'
          AND NOT platform_user.must_change_password
          AND platform_user.role IN ('transformation_office', 'pmo_lead')
        FOR UPDATE;

        IF NOT FOUND THEN
          RAISE EXCEPTION 'oauth_actor_not_authorized';
        END IF;

        INSERT INTO %1$I.integration_oauth_states (
          tenant_id,
          provider,
          state_digest,
          browser_binding_digest,
          initiated_by_user_id,
          pkce_verifier_encrypted,
          nonce_digest,
          deployment_environment,
          deployment_schema,
          entra_tenant_id,
          oauth_client_id,
          oauth_redirect_uri,
          encryption_key_fingerprint,
          context_fingerprint,
          authorization_scopes,
          required_api_scopes,
          expires_at,
          created_at
        ) VALUES (
          p_tenant_id,
          p_provider,
          p_state_digest,
          p_browser_binding_digest,
          p_initiated_by_user_id,
          p_pkce_verifier_encrypted,
          p_nonce_digest,
          p_deployment_environment,
          p_deployment_schema,
          p_entra_tenant_id,
          p_oauth_client_id,
          p_oauth_redirect_uri,
          p_encryption_key_fingerprint,
          p_context_fingerprint,
          p_authorization_scopes,
          p_required_api_scopes,
          now_at + INTERVAL '10 minutes',
          now_at
        )
        RETURNING id INTO created_state_id;

        RETURN created_state_id;
      END
      $body$
    $definition$,
    app_schema,
    app_schema::TEXT
  );

  EXECUTE format(
    $definition$
      CREATE OR REPLACE FUNCTION %1$I.complete_microsoft_graph_oauth(
        p_tenant_id UUID,
        p_provider TEXT,
        p_state_digest TEXT,
        p_context_fingerprint TEXT,
        p_external_account_id TEXT,
        p_organizer_email TEXT,
        p_access_token_encrypted TEXT,
        p_refresh_token_encrypted TEXT,
        p_token_expires_at TIMESTAMPTZ,
        p_scopes TEXT[]
      )
      RETURNS UUID
      LANGUAGE plpgsql
      SECURITY DEFINER
      SET search_path = pg_catalog, %1$I
      AS $body$
      DECLARE
        oauth_state RECORD;
        existing_connection RECORD;
        connection_existed BOOLEAN := FALSE;
        completed_connection_id UUID;
        canonical_external_account_id UUID;
        now_at TIMESTAMPTZ := pg_catalog.clock_timestamp();
      BEGIN
        IF p_provider <> 'microsoft_graph'
          OR NULLIF(p_state_digest, '') IS NULL
          OR NULLIF(p_context_fingerprint, '') IS NULL
          OR NULLIF(p_external_account_id, '') IS NULL
          OR NULLIF(p_organizer_email, '') IS NULL
          OR NULLIF(p_access_token_encrypted, '') IS NULL
          OR NULLIF(p_refresh_token_encrypted, '') IS NULL
          OR p_token_expires_at IS NULL
          OR NOT pg_catalog.isfinite(p_token_expires_at)
          OR p_token_expires_at <= now_at
          OR p_token_expires_at > now_at + INTERVAL '24 hours'
          OR cardinality(p_scopes) = 0
        THEN
          RAISE EXCEPTION 'invalid_oauth_completion';
        END IF;

        BEGIN
          canonical_external_account_id := p_external_account_id::UUID;
        EXCEPTION
          WHEN invalid_text_representation THEN
            RAISE EXCEPTION 'invalid_oauth_account';
        END;
        IF p_external_account_id <> canonical_external_account_id::TEXT THEN
          RAISE EXCEPTION 'invalid_oauth_account';
        END IF;

        PERFORM pg_catalog.pg_advisory_xact_lock(
          pg_catalog.hashtextextended(
            %2$L || ':' || p_tenant_id::TEXT || ':' || p_provider,
            0
          )
        );

        SELECT oauth.*
        INTO oauth_state
        FROM %1$I.integration_oauth_states AS oauth
        WHERE oauth.tenant_id = p_tenant_id
          AND oauth.provider = p_provider
          AND oauth.state_digest = p_state_digest
          AND oauth.context_fingerprint = p_context_fingerprint
        FOR UPDATE;

        IF NOT FOUND
          OR oauth_state.consumed_at IS NULL
          OR oauth_state.cancelled_at IS NOT NULL
          OR oauth_state.failed_at IS NOT NULL
          OR oauth_state.completed_at IS NOT NULL
          OR oauth_state.expires_at <= now_at
          OR oauth_state.pkce_verifier_encrypted IS NULL
        THEN
          RAISE EXCEPTION 'oauth_state_not_completable';
        END IF;

        PERFORM 1
        FROM %1$I.users AS platform_user
        WHERE platform_user.tenant_id = p_tenant_id
          AND platform_user.id = oauth_state.initiated_by_user_id
          AND platform_user.status = 'active'
          AND NOT platform_user.must_change_password
          AND platform_user.role IN ('transformation_office', 'pmo_lead')
        FOR UPDATE;

        IF NOT FOUND THEN
          RAISE EXCEPTION 'oauth_actor_not_authorized';
        END IF;

        IF EXISTS (
          SELECT 1
          FROM pg_catalog.unnest(oauth_state.required_api_scopes) AS required_scope
          WHERE NOT EXISTS (
            SELECT 1
            FROM pg_catalog.unnest(p_scopes) AS granted_scope
            WHERE pg_catalog.lower(granted_scope) = pg_catalog.lower(required_scope)
          )
        ) THEN
          RAISE EXCEPTION 'oauth_scope_incomplete';
        END IF;

        FOR existing_connection IN
          SELECT
            connection.id,
            connection.external_account_id,
            connection.organizer_email,
            connection.oauth_generation
          FROM %1$I.integration_connections AS connection
          WHERE connection.tenant_id = p_tenant_id
            AND connection.provider = p_provider
            AND (
              connection.external_account_id = p_external_account_id
              OR pg_catalog.lower(connection.organizer_email) = pg_catalog.lower(p_organizer_email)
            )
          FOR UPDATE
        LOOP
          IF existing_connection.external_account_id = p_external_account_id
            AND existing_connection.oauth_generation >= oauth_state.oauth_generation
          THEN
            RAISE EXCEPTION 'oauth_state_superseded';
          END IF;
          IF existing_connection.external_account_id IS DISTINCT FROM p_external_account_id
            AND pg_catalog.lower(existing_connection.organizer_email)
              = pg_catalog.lower(p_organizer_email)
          THEN
            RAISE EXCEPTION 'oauth_account_collision';
          END IF;
          connection_existed := TRUE;
        END LOOP;

        INSERT INTO %1$I.integration_connections (
          tenant_id,
          provider,
          organizer_email,
          external_account_id,
          access_token_encrypted,
          refresh_token_encrypted,
          token_expires_at,
          scopes,
          sync_status,
          sync_error,
          last_synced_at,
          deployment_environment,
          deployment_schema,
          entra_tenant_id,
          oauth_client_id,
          oauth_redirect_uri,
          encryption_key_fingerprint,
          context_fingerprint,
          oauth_generation,
          token_generation,
          connected_by_user_id,
          updated_at
        ) VALUES (
          p_tenant_id,
          p_provider,
          p_organizer_email,
          p_external_account_id,
          p_access_token_encrypted,
          p_refresh_token_encrypted,
          p_token_expires_at,
          p_scopes,
          'connected',
          NULL,
          now_at,
          oauth_state.deployment_environment,
          oauth_state.deployment_schema,
          oauth_state.entra_tenant_id,
          oauth_state.oauth_client_id,
          oauth_state.oauth_redirect_uri,
          oauth_state.encryption_key_fingerprint,
          oauth_state.context_fingerprint,
          oauth_state.oauth_generation,
          0,
          oauth_state.initiated_by_user_id,
          now_at
        )
        ON CONFLICT ON CONSTRAINT integration_connections_tenant_provider_external_account_key
        DO UPDATE SET
          organizer_email = EXCLUDED.organizer_email,
          access_token_encrypted = EXCLUDED.access_token_encrypted,
          refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
          token_expires_at = EXCLUDED.token_expires_at,
          scopes = EXCLUDED.scopes,
          sync_status = 'connected',
          sync_error = NULL,
          last_synced_at = now_at,
          deployment_environment = EXCLUDED.deployment_environment,
          deployment_schema = EXCLUDED.deployment_schema,
          entra_tenant_id = EXCLUDED.entra_tenant_id,
          oauth_client_id = EXCLUDED.oauth_client_id,
          oauth_redirect_uri = EXCLUDED.oauth_redirect_uri,
          encryption_key_fingerprint = EXCLUDED.encryption_key_fingerprint,
          context_fingerprint = EXCLUDED.context_fingerprint,
          oauth_generation = EXCLUDED.oauth_generation,
          token_generation = EXCLUDED.token_generation,
          connected_by_user_id = EXCLUDED.connected_by_user_id,
          updated_at = now_at
        WHERE integration_connections.tenant_id = EXCLUDED.tenant_id
          AND integration_connections.provider = EXCLUDED.provider
          AND integration_connections.external_account_id = EXCLUDED.external_account_id
        RETURNING id INTO completed_connection_id;

        IF completed_connection_id IS NULL THEN
          RAISE EXCEPTION 'oauth_connection_not_completed';
        END IF;

        INSERT INTO %1$I.audit_log (
          tenant_id,
          user_id,
          entity_type,
          entity_id,
          action,
          after_data
        ) VALUES (
          p_tenant_id,
          oauth_state.initiated_by_user_id,
          'integration_connection',
          completed_connection_id,
          CASE
            WHEN connection_existed THEN 'update'
            ELSE 'create'
          END,
          pg_catalog.jsonb_build_object(
            'provider', p_provider,
            'context_fingerprint', oauth_state.context_fingerprint
          )
        );

        UPDATE %1$I.integration_oauth_states AS oauth
        SET
          consumed_at = COALESCE(oauth.consumed_at, now_at),
          cancelled_at = now_at,
          pkce_verifier_encrypted = NULL,
          failure_code = 'oauth_state_superseded'
        WHERE oauth.tenant_id = p_tenant_id
          AND oauth.provider = p_provider
          AND oauth.id <> oauth_state.id
          AND oauth.oauth_generation < oauth_state.oauth_generation
          AND oauth.cancelled_at IS NULL
          AND oauth.failed_at IS NULL
          AND oauth.completed_at IS NULL;

        UPDATE %1$I.integration_oauth_states AS oauth
        SET
          completed_at = now_at,
          pkce_verifier_encrypted = NULL,
          failure_code = NULL
        WHERE oauth.id = oauth_state.id
          AND oauth.tenant_id = p_tenant_id
          AND oauth.provider = p_provider
          AND oauth.state_digest = p_state_digest
          AND oauth.context_fingerprint = p_context_fingerprint;

        RETURN completed_connection_id;
      END
      $body$
    $definition$,
    app_schema,
    app_schema::TEXT
  );

  EXECUTE format(
    $definition$
      CREATE OR REPLACE FUNCTION %1$I.disconnect_microsoft_graph_connection(
        p_tenant_id UUID,
        p_provider TEXT,
        p_connection_id UUID,
        p_actor_id UUID
      )
      RETURNS BOOLEAN
      LANGUAGE plpgsql
      SECURITY DEFINER
      SET search_path = pg_catalog, %1$I
      AS $body$
      DECLARE
        matched_connection_id UUID;
        matched_context_fingerprint TEXT;
        deleted_connection BOOLEAN;
        now_at TIMESTAMPTZ := pg_catalog.clock_timestamp();
      BEGIN
        IF p_provider <> 'microsoft_graph' THEN
          RETURN FALSE;
        END IF;

        PERFORM pg_catalog.pg_advisory_xact_lock(
          pg_catalog.hashtextextended(
            %2$L || ':' || p_tenant_id::TEXT || ':' || p_provider,
            0
          )
        );

        PERFORM 1
        FROM %1$I.users AS platform_user
        WHERE platform_user.tenant_id = p_tenant_id
          AND platform_user.id = p_actor_id
          AND platform_user.status = 'active'
          AND NOT platform_user.must_change_password
          AND platform_user.role IN ('transformation_office', 'pmo_lead')
        FOR UPDATE;

        IF NOT FOUND THEN
          RETURN FALSE;
        END IF;

        SELECT connection.id, connection.context_fingerprint
        INTO matched_connection_id, matched_context_fingerprint
        FROM %1$I.integration_connections AS connection
        WHERE connection.tenant_id = p_tenant_id
          AND connection.provider = p_provider
          AND connection.id = p_connection_id
        FOR UPDATE;

        IF NOT FOUND THEN
          RETURN FALSE;
        END IF;

        UPDATE %1$I.integration_oauth_states AS oauth
        SET
          consumed_at = COALESCE(oauth.consumed_at, now_at),
          cancelled_at = now_at,
          pkce_verifier_encrypted = NULL,
          failure_code = 'connection_disconnected'
        WHERE oauth.tenant_id = p_tenant_id
          AND oauth.provider = p_provider
          AND oauth.cancelled_at IS NULL
          AND oauth.failed_at IS NULL
          AND oauth.completed_at IS NULL;

        DELETE FROM %1$I.integration_connections AS connection
        WHERE connection.tenant_id = p_tenant_id
          AND connection.provider = p_provider
          AND connection.id = matched_connection_id;

        deleted_connection := FOUND;
        IF NOT deleted_connection THEN
          RETURN FALSE;
        END IF;

        INSERT INTO %1$I.audit_log (
          tenant_id,
          user_id,
          entity_type,
          entity_id,
          action,
          before_data
        ) VALUES (
          p_tenant_id,
          p_actor_id,
          'integration_connection',
          matched_connection_id,
          'delete',
          pg_catalog.jsonb_build_object(
            'provider', p_provider,
            'context_fingerprint', matched_context_fingerprint
          )
        );

        RETURN TRUE;
      END
      $body$
    $definition$,
    app_schema,
    app_schema::TEXT
  );

  EXECUTE format(
    'REVOKE ALL PRIVILEGES ON FUNCTION %I.create_microsoft_graph_oauth_state('
    'UUID, TEXT, TEXT, TEXT, UUID, TEXT, TEXT, TEXT, TEXT, UUID, UUID, TEXT, TEXT, '
    'TEXT, TEXT[], TEXT[]) FROM PUBLIC, anon, authenticated, service_role',
    app_schema
  );
  EXECUTE format(
    'GRANT EXECUTE ON FUNCTION %I.create_microsoft_graph_oauth_state('
    'UUID, TEXT, TEXT, TEXT, UUID, TEXT, TEXT, TEXT, TEXT, UUID, UUID, TEXT, TEXT, '
    'TEXT, TEXT[], TEXT[]) TO service_role',
    app_schema
  );
  EXECUTE format(
    'REVOKE ALL PRIVILEGES ON FUNCTION %I.complete_microsoft_graph_oauth('
    'UUID, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TIMESTAMPTZ, TEXT[]) '
    'FROM PUBLIC, anon, authenticated, service_role',
    app_schema
  );
  EXECUTE format(
    'GRANT EXECUTE ON FUNCTION %I.complete_microsoft_graph_oauth('
    'UUID, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, TIMESTAMPTZ, TEXT[]) '
    'TO service_role',
    app_schema
  );
  EXECUTE format(
    'REVOKE ALL PRIVILEGES ON FUNCTION %I.disconnect_microsoft_graph_connection('
    'UUID, TEXT, UUID, UUID) FROM PUBLIC, anon, authenticated, service_role',
    app_schema
  );
  EXECUTE format(
    'GRANT EXECUTE ON FUNCTION %I.disconnect_microsoft_graph_connection('
    'UUID, TEXT, UUID, UUID) TO service_role',
    app_schema
  );
END
$migration$;

COMMIT;
