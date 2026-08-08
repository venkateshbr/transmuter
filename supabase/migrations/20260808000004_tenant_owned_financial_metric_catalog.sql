BEGIN;

ALTER TABLE financial_metric_definitions
  ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'tenant'
    CHECK (origin IN ('default_catalog', 'tenant', 'legacy_default')),
  ADD COLUMN IF NOT EXISTS catalog_version TEXT,
  ADD COLUMN IF NOT EXISTS semantic_role TEXT,
  ADD COLUMN IF NOT EXISTS evaluation_grain TEXT NOT NULL DEFAULT 'period'
    CHECK (evaluation_grain IN ('period', 'annual'));

-- The previous immutable-system trigger must be replaced before legacy starter
-- rows can be reclassified inside this migration transaction.
DROP TRIGGER IF EXISTS financial_metric_definitions_protect_write
  ON financial_metric_definitions;

-- Preserve existing tenant data and identity. These rows become deletable starter
-- definitions, not silently reinterpreted v2 metrics.
UPDATE financial_metric_definitions
SET origin = 'legacy_default',
    catalog_version = 'legacy-v1',
    is_system = FALSE
WHERE is_system;

WITH candidates AS (
  SELECT id,
         CASE key
           WHEN 'baseline_revenue' THEN 'revenue_baseline'
           WHEN 'annual_revenue_baseline' THEN 'revenue_baseline'
           WHEN 'annual_gross_margin_baseline' THEN 'gross_profit_baseline'
           WHEN 'revenue_uplift' THEN 'revenue_uplift'
           WHEN 'gm_uplift' THEN 'gross_profit_uplift'
           WHEN 'cost_savings' THEN 'cost_savings'
           WHEN 'target_revenue' THEN 'target_revenue'
           WHEN 'target_gross_margin' THEN 'target_gross_profit'
           WHEN 'cogs' THEN 'target_cogs'
         END AS role,
         ROW_NUMBER() OVER (
           PARTITION BY tenant_id,
             CASE key
               WHEN 'baseline_revenue' THEN 'revenue_baseline'
               WHEN 'annual_revenue_baseline' THEN 'revenue_baseline'
               WHEN 'annual_gross_margin_baseline' THEN 'gross_profit_baseline'
               WHEN 'revenue_uplift' THEN 'revenue_uplift'
               WHEN 'gm_uplift' THEN 'gross_profit_uplift'
               WHEN 'cost_savings' THEN 'cost_savings'
               WHEN 'target_revenue' THEN 'target_revenue'
               WHEN 'target_gross_margin' THEN 'target_gross_profit'
               WHEN 'cogs' THEN 'target_cogs'
             END
           ORDER BY is_active DESC, display_order, id
         ) AS preference
  FROM financial_metric_definitions
  WHERE semantic_role IS NULL
    AND key IN (
      'baseline_revenue', 'annual_revenue_baseline',
      'annual_gross_margin_baseline', 'revenue_uplift', 'gm_uplift',
      'cost_savings', 'target_revenue', 'target_gross_margin', 'cogs'
    )
)
UPDATE financial_metric_definitions definition
SET semantic_role = candidates.role
FROM candidates
WHERE definition.id = candidates.id AND candidates.preference = 1;

CREATE UNIQUE INDEX IF NOT EXISTS financial_metric_definitions_semantic_role_uq
  ON financial_metric_definitions(tenant_id, semantic_role)
  WHERE semantic_role IS NOT NULL AND is_active;

CREATE TABLE IF NOT EXISTS financial_metric_catalog_installations (
  tenant_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  catalog_version TEXT NOT NULL,
  installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE financial_metric_catalog_installations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "fmci_select" ON financial_metric_catalog_installations;
CREATE POLICY "fmci_select" ON financial_metric_catalog_installations
  FOR SELECT USING (tenant_id = current_tenant_id());

INSERT INTO financial_metric_catalog_installations (tenant_id, catalog_version)
SELECT DISTINCT tenant_id, 'legacy-v1'
FROM financial_metric_definitions
ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION install_financial_metric_catalog(
  p_tenant_id UUID,
  p_catalog_version TEXT,
  p_catalog JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  item JSONB;
  inserted_marker UUID;
  affected_rows INTEGER := 0;
  inserted_scenarios INTEGER := 0;
  inserted_metrics INTEGER := 0;
  inserted_categories INTEGER := 0;
  inserted_bridges INTEGER := 0;
BEGIN
  IF auth.role() IS DISTINCT FROM 'service_role' THEN
    RAISE EXCEPTION 'Catalogue installation requires the service role'
      USING ERRCODE = '42501';
  END IF;
  IF p_catalog_version IS NULL OR BTRIM(p_catalog_version) = '' THEN
    RAISE EXCEPTION 'Catalogue version is required' USING ERRCODE = '22023';
  END IF;

  -- One marker guards the whole transaction. A concurrent caller blocks on the
  -- primary key and then returns without recreating deleted definitions.
  INSERT INTO financial_metric_catalog_installations (tenant_id, catalog_version)
  VALUES (p_tenant_id, p_catalog_version)
  ON CONFLICT DO NOTHING
  RETURNING tenant_id INTO inserted_marker;
  IF inserted_marker IS NULL THEN
    RETURN jsonb_build_object(
      'financial_scenarios', 0,
      'financial_metric_definitions', 0,
      'financial_cost_categories', 0,
      'financial_bridge_rows', 0
    );
  END IF;

  FOR item IN SELECT value FROM jsonb_array_elements(COALESCE(p_catalog->'scenarios', '[]'))
  LOOP
    INSERT INTO financial_scenarios (
      tenant_id, key, label, kind, is_primary, is_system, is_active, display_order
    ) VALUES (
      p_tenant_id, item->>'key', item->>'label', item->>'kind',
      COALESCE((item->>'is_primary')::BOOLEAN, FALSE), FALSE, TRUE,
      COALESCE((item->>'display_order')::INTEGER, 0)
    ) ON CONFLICT (tenant_id, key) DO NOTHING;
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    inserted_scenarios := inserted_scenarios + affected_rows;
  END LOOP;

  FOR item IN SELECT value FROM jsonb_array_elements(COALESCE(p_catalog->'metrics', '[]'))
  LOOP
    INSERT INTO financial_metric_definitions (
      tenant_id, key, label, semantic_role, group_key, value_type, unit, direction,
      aggregation, rollup_type, is_benefit, benefit_class, formula, formula_inputs,
      evaluation_grain, precision, display_order, applies_to, validation,
      origin, catalog_version, is_system, is_active
    ) VALUES (
      p_tenant_id, item->>'key', item->>'label', item->>'semantic_role',
      item->>'group_key', item->>'value_type', NULLIF(item->>'unit', ''),
      COALESCE(item->>'direction', 'increase_good'),
      item->>'aggregation', NULLIF(item->>'rollup_type', ''),
      COALESCE((item->>'is_benefit')::BOOLEAN, FALSE), NULLIF(item->>'benefit_class', ''),
      NULLIF(item->>'formula', ''),
      ARRAY(SELECT jsonb_array_elements_text(COALESCE(item->'formula_inputs', '[]'))),
      COALESCE(item->>'evaluation_grain', 'period'),
      COALESCE((item->>'precision')::SMALLINT, 4),
      COALESCE((item->>'display_order')::INTEGER, 0),
      COALESCE(item->>'applies_to', 'all'), COALESCE(item->'validation', '{}'::jsonb),
      'default_catalog', p_catalog_version, FALSE, TRUE
    ) ON CONFLICT (tenant_id, key) DO NOTHING;
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    inserted_metrics := inserted_metrics + affected_rows;
  END LOOP;

  FOR item IN SELECT value FROM jsonb_array_elements(COALESCE(p_catalog->'cost_categories', '[]'))
  LOOP
    INSERT INTO financial_cost_categories (
      tenant_id, key, label, group_key, rollup_type, display_order, attributes,
      is_system, is_active
    ) VALUES (
      p_tenant_id, item->>'key', item->>'label', item->>'group_key',
      NULLIF(item->>'rollup_type', ''), COALESCE((item->>'display_order')::INTEGER, 0),
      '{}'::jsonb, FALSE, TRUE
    ) ON CONFLICT (tenant_id, key) DO NOTHING;
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    inserted_categories := inserted_categories + affected_rows;
  END LOOP;

  FOR item IN SELECT value FROM jsonb_array_elements(COALESCE(p_catalog->'bridge_rows', '[]'))
  LOOP
    INSERT INTO financial_bridge_rows (
      tenant_id, key, label, row_kind, metric_definition_ids,
      cost_category_ids, cost_category_keys, sign, display_order, is_active
    ) VALUES (
      p_tenant_id, item->>'key', item->>'label', item->>'row_kind',
      ARRAY(
        SELECT definition.id FROM financial_metric_definitions definition
        WHERE definition.tenant_id = p_tenant_id
          AND definition.key IN (SELECT jsonb_array_elements_text(COALESCE(item->'metric_keys', '[]')))
      ),
      ARRAY(
        SELECT category.id FROM financial_cost_categories category
        WHERE category.tenant_id = p_tenant_id
          AND category.key IN (SELECT jsonb_array_elements_text(COALESCE(item->'cost_category_keys', '[]')))
      ),
      ARRAY(SELECT jsonb_array_elements_text(COALESCE(item->'cost_category_keys', '[]'))),
      COALESCE((item->>'sign')::SMALLINT, 1),
      COALESCE((item->>'display_order')::INTEGER, 0), TRUE
    ) ON CONFLICT (tenant_id, key) DO NOTHING;
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    inserted_bridges := inserted_bridges + affected_rows;
  END LOOP;

  RETURN jsonb_build_object(
    'financial_scenarios', inserted_scenarios,
    'financial_metric_definitions', inserted_metrics,
    'financial_cost_categories', inserted_categories,
    'financial_bridge_rows', inserted_bridges
  );
END;
$$;

REVOKE ALL ON FUNCTION install_financial_metric_catalog(UUID, TEXT, JSONB)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION install_financial_metric_catalog(UUID, TEXT, JSONB)
  TO service_role;

-- Default and legacy-default metrics are tenant-owned. The confirmed workflow
-- and all dependency FKs remain the deletion boundary.
CREATE OR REPLACE FUNCTION protect_financial_metric_definition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.is_system AND current_tenant_id() IS NOT NULL THEN
      RAISE EXCEPTION 'Tenant-created financial metrics cannot be system metrics'
        USING ERRCODE = '42501';
    END IF;
    IF current_tenant_id() IS NOT NULL THEN
      NEW.origin := 'tenant';
      NEW.catalog_version := NULL;
    END IF;
    RETURN NEW;
  END IF;
  IF TG_OP = 'UPDATE' THEN
    IF NEW.is_system IS DISTINCT FROM OLD.is_system
       OR NEW.origin IS DISTINCT FROM OLD.origin
       OR NEW.catalog_version IS DISTINCT FROM OLD.catalog_version THEN
      RAISE EXCEPTION 'Financial metric provenance is immutable'
        USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
  END IF;
  IF current_tenant_id() IS NOT NULL
     AND current_setting('app.metric_delete_confirmed', TRUE) IS DISTINCT FROM OLD.id::TEXT THEN
    RAISE EXCEPTION 'Use the confirmed financial metric deletion workflow'
      USING ERRCODE = '42501';
  END IF;
  RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS financial_metric_definitions_protect_write
  ON financial_metric_definitions;
CREATE TRIGGER financial_metric_definitions_protect_write
  BEFORE INSERT OR UPDATE OF is_system, origin, catalog_version
  ON financial_metric_definitions
  FOR EACH ROW EXECUTE FUNCTION protect_financial_metric_definition();

DO $$
BEGIN
  IF to_regprocedure('financial_metric_deletion_impact_v1(uuid,uuid)') IS NULL THEN
    ALTER FUNCTION financial_metric_deletion_impact(UUID, UUID)
      RENAME TO financial_metric_deletion_impact_v1;
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION financial_metric_deletion_impact(
  p_tenant_id UUID,
  p_metric_definition_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  impact JSONB;
  metric_origin TEXT;
  metric_catalog_version TEXT;
BEGIN
  impact := financial_metric_deletion_impact_v1(p_tenant_id, p_metric_definition_id);
  IF impact IS NULL THEN
    RETURN NULL;
  END IF;
  SELECT origin, catalog_version INTO metric_origin, metric_catalog_version
  FROM financial_metric_definitions
  WHERE tenant_id = p_tenant_id AND id = p_metric_definition_id;
  impact := jsonb_set(impact, '{metric,origin}', to_jsonb(metric_origin), TRUE);
  impact := jsonb_set(
    impact, '{metric,catalog_version}', COALESCE(to_jsonb(metric_catalog_version), 'null'::jsonb), TRUE
  );
  RETURN impact || jsonb_build_object(
    'can_delete', COALESCE((impact->>'blocker_total')::INTEGER, 0) = 0,
    'blocked_by_system', FALSE
  );
END;
$$;

REVOKE ALL ON FUNCTION financial_metric_deletion_impact(UUID, UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION financial_metric_deletion_impact(UUID, UUID)
  TO authenticated, service_role;

CREATE OR REPLACE FUNCTION delete_financial_metric_definition(
  p_tenant_id UUID,
  p_metric_definition_id UUID,
  p_confirmation_key TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  metric financial_metric_definitions%ROWTYPE;
  impact JSONB;
BEGIN
  IF current_tenant_id() IS DISTINCT FROM p_tenant_id THEN
    RETURN NULL;
  END IF;
  IF NOT app_can_manage_financial_configuration() THEN
    RAISE EXCEPTION 'Insufficient role' USING ERRCODE = '42501';
  END IF;
  SELECT * INTO metric
  FROM financial_metric_definitions
  WHERE tenant_id = p_tenant_id AND id = p_metric_definition_id
  FOR UPDATE;
  IF NOT FOUND THEN
    RETURN NULL;
  END IF;
  impact := financial_metric_deletion_impact(p_tenant_id, p_metric_definition_id);
  IF metric.key IS DISTINCT FROM p_confirmation_key THEN
    RETURN impact || jsonb_build_object('deleted', FALSE, 'status', 'confirmation_mismatch');
  END IF;
  IF NOT COALESCE((impact->>'can_delete')::BOOLEAN, FALSE) THEN
    RETURN impact || jsonb_build_object('deleted', FALSE, 'status', 'blocked');
  END IF;
  PERFORM set_config('app.metric_delete_confirmed', metric.id::TEXT, TRUE);
  DELETE FROM financial_metric_definitions
  WHERE tenant_id = p_tenant_id AND id = metric.id;
  RETURN impact || jsonb_build_object('deleted', TRUE, 'status', 'deleted');
END;
$$;

REVOKE ALL ON FUNCTION delete_financial_metric_definition(UUID, UUID, TEXT)
  FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION delete_financial_metric_definition(UUID, UUID, TEXT)
  TO authenticated, service_role;

COMMIT;
