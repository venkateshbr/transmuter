-- Make Microsoft 365 organizer authorization tenant-admin owned and enforce one
-- Microsoft Graph credential set per tenant.

BEGIN;

DO $migration$
DECLARE
  app_schema NAME := current_schema();
  duplicate_tenant UUID;
BEGIN
  SELECT tenant_id
  INTO duplicate_tenant
  FROM integration_connections
  WHERE provider = 'microsoft_graph'
  GROUP BY tenant_id
  HAVING COUNT(*) > 1
  LIMIT 1;

  IF duplicate_tenant IS NOT NULL THEN
    RAISE EXCEPTION
      'Tenant % has multiple Microsoft Graph connections; reconcile them before applying this migration',
      duplicate_tenant;
  END IF;

  EXECUTE format(
    'CREATE UNIQUE INDEX IF NOT EXISTS integration_connections_one_microsoft_graph_per_tenant '
    'ON %I.integration_connections (tenant_id) WHERE provider = ''microsoft_graph''',
    app_schema
  );
END
$migration$;

DO $migration$
DECLARE
  app_schema NAME := current_schema();
  target_function RECORD;
  function_definition TEXT;
  rewritten_definition TEXT;
  old_role_clause CONSTANT TEXT :=
    'platform_user.role IN (''transformation_office'', ''pmo_lead'')';
  new_role_clause CONSTANT TEXT :=
    'platform_user.role IN (''transformation_office'', ''tenant_admin'')';
BEGIN
  FOR target_function IN
    SELECT procedure.oid, procedure.proname
    FROM pg_catalog.pg_proc AS procedure
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = procedure.pronamespace
    WHERE namespace.nspname = app_schema
      AND procedure.proname IN (
        'create_microsoft_graph_oauth_state',
        'complete_microsoft_graph_oauth',
        'disconnect_microsoft_graph_connection'
      )
  LOOP
    function_definition := pg_catalog.pg_get_functiondef(target_function.oid);
    rewritten_definition := pg_catalog.replace(
      function_definition,
      old_role_clause,
      new_role_clause
    );
    IF rewritten_definition = function_definition THEN
      RAISE EXCEPTION
        'Expected Microsoft Graph authorization clause was not found in %.%',
        app_schema,
        target_function.proname;
    END IF;
    EXECUTE rewritten_definition;
  END LOOP;

  IF (
    SELECT COUNT(*)
    FROM pg_catalog.pg_proc AS procedure
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = procedure.pronamespace
    WHERE namespace.nspname = app_schema
      AND procedure.proname IN (
        'create_microsoft_graph_oauth_state',
        'complete_microsoft_graph_oauth',
        'disconnect_microsoft_graph_connection'
      )
      AND pg_catalog.strpos(
        pg_catalog.pg_get_functiondef(procedure.oid),
        new_role_clause
      ) > 0
  ) <> 3 THEN
    RAISE EXCEPTION 'Microsoft Graph tenant-admin authorization was not applied exactly three times';
  END IF;
END
$migration$;

COMMIT;
