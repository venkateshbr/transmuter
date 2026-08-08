-- Rollback-only real PostgreSQL acceptance for dependency-aware metric deletion.

BEGIN;

DO $$
DECLARE
  actor users%ROWTYPE;
  other_tenant_id UUID;
  custom_metric_id UUID := gen_random_uuid();
  default_metric_id UUID := gen_random_uuid();
  custom_key TEXT := 'db_delete_acceptance_' || SUBSTRING(custom_metric_id::TEXT, 1, 8);
  default_key TEXT := 'db_default_acceptance_' || SUBSTRING(default_metric_id::TEXT, 1, 8);
  claims JSONB;
  impact JSONB;
  deletion_result JSONB;
  direct_delete_blocked BOOLEAN := FALSE;
BEGIN
  SELECT * INTO actor
  FROM users
  WHERE status = 'active'
    AND role IN ('transformation_office', 'tenant_admin', 'finance_lead')
  ORDER BY CASE role WHEN 'transformation_office' THEN 1 WHEN 'tenant_admin' THEN 2 ELSE 3 END
  LIMIT 1;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Metric deletion acceptance requires an active financial configuration manager';
  END IF;

  SELECT id INTO other_tenant_id
  FROM organizations
  WHERE id <> actor.tenant_id
  ORDER BY created_at
  LIMIT 1;

  INSERT INTO financial_metric_definitions (
    id, tenant_id, key, label, value_type, aggregation, origin, catalog_version, is_system, is_active
  ) VALUES
    (custom_metric_id, actor.tenant_id, custom_key, 'DB deletion acceptance custom', 'currency', 'sum', 'tenant', NULL, FALSE, TRUE),
    (default_metric_id, actor.tenant_id, default_key, 'DB deletion acceptance default', 'currency', 'sum', 'default_catalog', 'acceptance', FALSE, TRUE);

  INSERT INTO financial_tenant_annual_baselines (
    tenant_id, metric_definition_id, baseline_year, value
  ) VALUES (actor.tenant_id, custom_metric_id, 2060, 123.4500);

  claims := jsonb_build_object(
    'sub', actor.id,
    'tenant_id', actor.tenant_id,
    'app_role', actor.role
  );
  PERFORM set_config('request.jwt.claims', claims::TEXT, TRUE);

  BEGIN
    DELETE FROM financial_metric_definitions
    WHERE tenant_id = actor.tenant_id AND id = custom_metric_id;
  EXCEPTION WHEN insufficient_privilege THEN
    direct_delete_blocked := TRUE;
  END;
  IF NOT direct_delete_blocked THEN
    RAISE EXCEPTION 'Direct authenticated metric deletion was not blocked';
  END IF;

  impact := financial_metric_deletion_impact(actor.tenant_id, custom_metric_id);
  IF impact IS NULL
     OR NOT (impact ->> 'can_delete')::BOOLEAN
     OR (impact #>> '{cleanup,tenant_annual_baselines,count}')::INTEGER <> 1 THEN
    RAISE EXCEPTION 'Custom metric impact did not disclose safe baseline cleanup: %', impact;
  END IF;

  impact := financial_metric_deletion_impact(actor.tenant_id, default_metric_id);
  IF impact IS NULL
     OR NOT (impact ->> 'can_delete')::BOOLEAN
     OR (impact ->> 'blocked_by_system')::BOOLEAN
     OR impact #>> '{metric,origin}' <> 'default_catalog' THEN
    RAISE EXCEPTION 'Unused default metric was not deletable: %', impact;
  END IF;

  deletion_result := delete_financial_metric_definition(
    actor.tenant_id,
    default_metric_id,
    default_key
  );
  IF deletion_result ->> 'status' <> 'deleted' THEN
    RAISE EXCEPTION 'Default metric confirmed deletion failed: %', deletion_result;
  END IF;

  IF other_tenant_id IS NOT NULL
     AND financial_metric_deletion_impact(other_tenant_id, custom_metric_id) IS NOT NULL THEN
    RAISE EXCEPTION 'Cross-tenant deletion impact disclosed a metric';
  END IF;

  deletion_result := delete_financial_metric_definition(
    actor.tenant_id,
    custom_metric_id,
    custom_key
  );
  IF deletion_result ->> 'status' <> 'deleted'
     OR EXISTS (
       SELECT 1 FROM financial_tenant_annual_baselines
       WHERE tenant_id = actor.tenant_id AND metric_definition_id = custom_metric_id
     ) THEN
    RAISE EXCEPTION 'Confirmed custom metric deletion or baseline cleanup failed: %', deletion_result;
  END IF;

  PERFORM set_config('request.jwt.claims', '{}'::TEXT, TRUE);
END;
$$;

ROLLBACK;
