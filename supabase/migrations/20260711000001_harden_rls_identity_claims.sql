-- Resolve RLS identity from the canonical platform user, accepting only signed
-- authorization claims that exactly match that row.

BEGIN;

DO $migration$
DECLARE
  app_schema NAME := current_schema();
  authorization_key TEXT := 'transmuter_authorization_' || current_schema();
BEGIN
  EXECUTE format(
    $definition$
      CREATE OR REPLACE FUNCTION %1$I.current_tenant_id()
      RETURNS UUID
      LANGUAGE sql
      STABLE
      SECURITY DEFINER
      SET search_path = pg_catalog, %1$I
      AS $body$
        SELECT platform_user.tenant_id
        FROM %1$I.users AS platform_user
        CROSS JOIN LATERAL (SELECT auth.jwt() AS claims) AS token
        WHERE platform_user.id = auth.uid()
          AND platform_user.status = 'active'
          AND (
            (
              token.claims -> 'app_metadata' -> %2$L ->> 'tenant_id' = platform_user.tenant_id::TEXT
              AND token.claims -> 'app_metadata' -> %2$L ->> 'role' = platform_user.role
            )
            OR (
              token.claims -> 'app_metadata' -> %2$L IS NULL
              AND token.claims ->> 'tenant_id' = platform_user.tenant_id::TEXT
              AND token.claims ->> 'app_role' = platform_user.role
            )
          )
        LIMIT 1
      $body$
    $definition$,
    app_schema,
    authorization_key
  );

  EXECUTE format(
    $definition$
      CREATE OR REPLACE FUNCTION %1$I.current_user_role()
      RETURNS TEXT
      LANGUAGE sql
      STABLE
      SECURITY DEFINER
      SET search_path = pg_catalog, %1$I
      AS $body$
        SELECT platform_user.role
        FROM %1$I.users AS platform_user
        CROSS JOIN LATERAL (SELECT auth.jwt() AS claims) AS token
        WHERE platform_user.id = auth.uid()
          AND platform_user.status = 'active'
          AND (
            (
              token.claims -> 'app_metadata' -> %2$L ->> 'tenant_id' = platform_user.tenant_id::TEXT
              AND token.claims -> 'app_metadata' -> %2$L ->> 'role' = platform_user.role
            )
            OR (
              token.claims -> 'app_metadata' -> %2$L IS NULL
              AND token.claims ->> 'tenant_id' = platform_user.tenant_id::TEXT
              AND token.claims ->> 'app_role' = platform_user.role
            )
          )
        LIMIT 1
      $body$
    $definition$,
    app_schema,
    authorization_key
  );

  EXECUTE format(
    'REVOKE ALL PRIVILEGES ON FUNCTION %I.current_tenant_id() FROM PUBLIC, anon, authenticated, service_role',
    app_schema
  );
  EXECUTE format(
    'REVOKE ALL PRIVILEGES ON FUNCTION %I.current_user_role() FROM PUBLIC, anon, authenticated, service_role',
    app_schema
  );
  EXECUTE format(
    'GRANT EXECUTE ON FUNCTION %I.current_tenant_id() TO authenticated, service_role',
    app_schema
  );
  EXECUTE format(
    'GRANT EXECUTE ON FUNCTION %I.current_user_role() TO authenticated, service_role',
    app_schema
  );
END
$migration$;

COMMIT;
