-- Rollback-only real PostgreSQL acceptance for once-only catalogue installation.

BEGIN;

DO $$
DECLARE
  acceptance_tenant_id UUID := gen_random_uuid();
  acceptance_slug TEXT := 'catalog-install-' || SUBSTRING(acceptance_tenant_id::TEXT, 1, 8);
  acceptance_catalog JSONB;
  first_result JSONB;
  second_result JSONB;
BEGIN
  INSERT INTO organizations (id, name, slug)
  VALUES (acceptance_tenant_id, 'Catalogue Installation Acceptance', acceptance_slug);

  acceptance_catalog := jsonb_build_object(
    'scenarios', jsonb_build_array(
      jsonb_build_object(
        'key', 'plan_base', 'label', 'Plan Base', 'kind', 'plan',
        'is_primary', TRUE, 'display_order', 10
      )
    ),
    'metrics', jsonb_build_array(
      jsonb_build_object(
        'key', 'acceptance_revenue',
        'label', 'Acceptance Revenue',
        'semantic_role', 'acceptance_revenue',
        'group_key', 'revenue',
        'value_type', 'currency',
        'direction', 'increase_good',
        'aggregation', 'sum',
        'formula_inputs', jsonb_build_array(),
        'evaluation_grain', 'period',
        'precision', 4,
        'display_order', 10,
        'applies_to', 'all',
        'validation', '{}'::jsonb
      )
    ),
    'cost_categories', '[]'::jsonb,
    'bridge_rows', '[]'::jsonb
  );

  PERFORM set_config('request.jwt.claims', '{"role":"service_role"}', TRUE);
  first_result := install_financial_metric_catalog(
    acceptance_tenant_id,
    'acceptance-v1',
    acceptance_catalog
  );

  IF (first_result ->> 'financial_scenarios')::INTEGER <> 1
     OR (first_result ->> 'financial_metric_definitions')::INTEGER <> 1 THEN
    RAISE EXCEPTION 'First catalogue installation returned unexpected counts: %', first_result;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM financial_metric_definitions
    WHERE tenant_id = acceptance_tenant_id
      AND key = 'acceptance_revenue'
      AND origin = 'default_catalog'
      AND catalog_version = 'acceptance-v1'
      AND semantic_role = 'acceptance_revenue'
      AND NOT is_system
  ) THEN
    RAISE EXCEPTION 'First catalogue installation did not persist tenant-owned provenance';
  END IF;

  DELETE FROM financial_metric_definitions
  WHERE tenant_id = acceptance_tenant_id AND key = 'acceptance_revenue';

  second_result := install_financial_metric_catalog(
    acceptance_tenant_id,
    'acceptance-v1',
    acceptance_catalog
  );
  IF (second_result ->> 'financial_scenarios')::INTEGER <> 0
     OR (second_result ->> 'financial_metric_definitions')::INTEGER <> 0 THEN
    RAISE EXCEPTION 'Repeated catalogue installation was not a no-op: %', second_result;
  END IF;
  IF EXISTS (
    SELECT 1 FROM financial_metric_definitions
    WHERE tenant_id = acceptance_tenant_id AND key = 'acceptance_revenue'
  ) THEN
    RAISE EXCEPTION 'Deleted default metric was resurrected by repeated installation';
  END IF;
END;
$$;

ROLLBACK;
