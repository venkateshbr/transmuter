-- Dependency-aware financial metric deletion.

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS financial_bridge_rows_tenant_id_id_uidx
  ON financial_bridge_rows(tenant_id, id);

CREATE TABLE IF NOT EXISTS financial_metric_formula_dependencies (
  tenant_id                    UUID NOT NULL,
  formula_metric_definition_id UUID NOT NULL,
  input_metric_definition_id   UUID NOT NULL,
  reference_kind               TEXT NOT NULL CHECK (reference_kind IN ('metric', 'baseline')),
  created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (
    tenant_id,
    formula_metric_definition_id,
    input_metric_definition_id,
    reference_kind
  ),
  CONSTRAINT financial_metric_formula_dependencies_owner_fk
    FOREIGN KEY (tenant_id, formula_metric_definition_id)
    REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT financial_metric_formula_dependencies_input_fk
    FOREIGN KEY (tenant_id, input_metric_definition_id)
    REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS financial_metric_formula_dependencies_input_idx
  ON financial_metric_formula_dependencies(tenant_id, input_metric_definition_id);

ALTER TABLE financial_metric_formula_dependencies ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "fmfd_select" ON financial_metric_formula_dependencies;
DROP POLICY IF EXISTS "fmfd_insert" ON financial_metric_formula_dependencies;
DROP POLICY IF EXISTS "fmfd_delete" ON financial_metric_formula_dependencies;
CREATE POLICY "fmfd_select" ON financial_metric_formula_dependencies
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fmfd_insert" ON financial_metric_formula_dependencies
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND app_can_manage_financial_configuration()
  );
CREATE POLICY "fmfd_delete" ON financial_metric_formula_dependencies
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND app_can_manage_financial_configuration()
  );

CREATE TABLE IF NOT EXISTS financial_bridge_metric_memberships (
  tenant_id            UUID NOT NULL,
  bridge_row_id        UUID NOT NULL,
  metric_definition_id UUID NOT NULL,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tenant_id, bridge_row_id, metric_definition_id),
  CONSTRAINT financial_bridge_metric_memberships_bridge_fk
    FOREIGN KEY (tenant_id, bridge_row_id)
    REFERENCES financial_bridge_rows(tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT financial_bridge_metric_memberships_metric_fk
    FOREIGN KEY (tenant_id, metric_definition_id)
    REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS financial_bridge_metric_memberships_metric_idx
  ON financial_bridge_metric_memberships(tenant_id, metric_definition_id);

ALTER TABLE financial_bridge_metric_memberships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "fbmm_select" ON financial_bridge_metric_memberships;
DROP POLICY IF EXISTS "fbmm_insert" ON financial_bridge_metric_memberships;
DROP POLICY IF EXISTS "fbmm_delete" ON financial_bridge_metric_memberships;
CREATE POLICY "fbmm_select" ON financial_bridge_metric_memberships
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fbmm_insert" ON financial_bridge_metric_memberships
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND app_can_manage_financial_configuration()
  );
CREATE POLICY "fbmm_delete" ON financial_bridge_metric_memberships
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND app_can_manage_financial_configuration()
  );

CREATE OR REPLACE FUNCTION refresh_financial_metric_formula_dependencies()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  DELETE FROM financial_metric_formula_dependencies
  WHERE tenant_id = NEW.tenant_id
    AND formula_metric_definition_id = NEW.id;

  IF NEW.aggregation = 'formula' THEN
    INSERT INTO financial_metric_formula_dependencies (
      tenant_id,
      formula_metric_definition_id,
      input_metric_definition_id,
      reference_kind
    )
    SELECT DISTINCT
      NEW.tenant_id,
      NEW.id,
      definition.id,
      CASE WHEN token.value = 'baseline_' || definition.key THEN 'baseline' ELSE 'metric' END
    FROM (
      SELECT unnest(COALESCE(NEW.formula_inputs, '{}'::TEXT[])) AS value
      UNION
      SELECT extracted.parts[1]
      FROM regexp_matches(
        COALESCE(NEW.formula, ''),
        '([A-Za-z_][A-Za-z0-9_]*)',
        'g'
      ) AS extracted(parts)
    ) AS token
    JOIN financial_metric_definitions definition
      ON definition.tenant_id = NEW.tenant_id
     AND token.value IN (definition.key, 'baseline_' || definition.key)
    WHERE definition.id <> NEW.id
    ON CONFLICT DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS financial_metric_formula_dependencies_refresh
  ON financial_metric_definitions;
CREATE TRIGGER financial_metric_formula_dependencies_refresh
  AFTER INSERT OR UPDATE OF aggregation, formula, formula_inputs
  ON financial_metric_definitions
  FOR EACH ROW
  EXECUTE FUNCTION refresh_financial_metric_formula_dependencies();

CREATE OR REPLACE FUNCTION refresh_financial_bridge_metric_memberships()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  DELETE FROM financial_bridge_metric_memberships
  WHERE tenant_id = NEW.tenant_id
    AND bridge_row_id = NEW.id;

  INSERT INTO financial_bridge_metric_memberships (
    tenant_id,
    bridge_row_id,
    metric_definition_id
  )
  SELECT NEW.tenant_id, NEW.id, metric_definition_id
  FROM unnest(COALESCE(NEW.metric_definition_ids, '{}'::UUID[])) AS metric(metric_definition_id)
  ON CONFLICT DO NOTHING;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS financial_bridge_metric_memberships_refresh
  ON financial_bridge_rows;
CREATE TRIGGER financial_bridge_metric_memberships_refresh
  AFTER INSERT OR UPDATE OF metric_definition_ids
  ON financial_bridge_rows
  FOR EACH ROW
  EXECUTE FUNCTION refresh_financial_bridge_metric_memberships();

INSERT INTO financial_metric_formula_dependencies (
  tenant_id,
  formula_metric_definition_id,
  input_metric_definition_id,
  reference_kind
)
SELECT DISTINCT
  formula_metric.tenant_id,
  formula_metric.id,
  input_metric.id,
  CASE WHEN token.value = 'baseline_' || input_metric.key THEN 'baseline' ELSE 'metric' END
FROM financial_metric_definitions formula_metric
CROSS JOIN LATERAL (
  SELECT unnest(COALESCE(formula_metric.formula_inputs, '{}'::TEXT[])) AS value
  UNION
  SELECT extracted.parts[1]
  FROM regexp_matches(
    COALESCE(formula_metric.formula, ''),
    '([A-Za-z_][A-Za-z0-9_]*)',
    'g'
  ) AS extracted(parts)
) AS token
JOIN financial_metric_definitions input_metric
  ON input_metric.tenant_id = formula_metric.tenant_id
 AND token.value IN (input_metric.key, 'baseline_' || input_metric.key)
WHERE formula_metric.aggregation = 'formula'
  AND formula_metric.id <> input_metric.id
ON CONFLICT DO NOTHING;

INSERT INTO financial_bridge_metric_memberships (
  tenant_id,
  bridge_row_id,
  metric_definition_id
)
SELECT bridge.tenant_id, bridge.id, metric_definition_id
FROM financial_bridge_rows bridge
CROSS JOIN LATERAL unnest(
  COALESCE(bridge.metric_definition_ids, '{}'::UUID[])
) AS metric(metric_definition_id)
ON CONFLICT DO NOTHING;

ALTER TABLE initiative_financial_selections
  ADD COLUMN IF NOT EXISTS metric_definition_id UUID;

UPDATE initiative_financial_selections selection
SET metric_definition_id = definition.id
FROM financial_metric_definitions definition
WHERE selection.item_type = 'metric'
  AND selection.metric_definition_id IS NULL
  AND definition.tenant_id = selection.tenant_id
  AND definition.key = REGEXP_REPLACE(selection.item_key, '_(base|high|actual)$', '');

CREATE OR REPLACE FUNCTION resolve_legacy_financial_selection_metric()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.item_type = 'metric' THEN
    SELECT definition.id INTO NEW.metric_definition_id
    FROM financial_metric_definitions definition
    WHERE definition.tenant_id = NEW.tenant_id
      AND definition.key = REGEXP_REPLACE(NEW.item_key, '_(base|high|actual)$', '')
    LIMIT 1;
  ELSE
    NEW.metric_definition_id := NULL;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS initiative_financial_selections_resolve_metric
  ON initiative_financial_selections;
CREATE TRIGGER initiative_financial_selections_resolve_metric
  BEFORE INSERT OR UPDATE OF tenant_id, item_key, item_type
  ON initiative_financial_selections
  FOR EACH ROW
  EXECUTE FUNCTION resolve_legacy_financial_selection_metric();

ALTER TABLE initiative_financial_selections
  DROP CONSTRAINT IF EXISTS initiative_financial_selections_metric_tenant_fk;
ALTER TABLE initiative_financial_selections
  ADD CONSTRAINT initiative_financial_selections_metric_tenant_fk
  FOREIGN KEY (tenant_id, metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE financial_config_items
  ADD COLUMN IF NOT EXISTS metric_definition_id UUID;

UPDATE financial_config_items item
SET metric_definition_id = definition.id
FROM financial_metric_definitions definition
WHERE item.item_type = 'metric'
  AND item.metric_definition_id IS NULL
  AND definition.tenant_id = item.tenant_id
  AND definition.key = REGEXP_REPLACE(item.system_metric_key, '_(base|high|actual)$', '');

CREATE OR REPLACE FUNCTION resolve_financial_config_item_metric()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.item_type = 'metric' AND NEW.system_metric_key IS NOT NULL THEN
    SELECT definition.id INTO NEW.metric_definition_id
    FROM financial_metric_definitions definition
    WHERE definition.tenant_id = NEW.tenant_id
      AND definition.key = REGEXP_REPLACE(NEW.system_metric_key, '_(base|high|actual)$', '')
    LIMIT 1;
  ELSE
    NEW.metric_definition_id := NULL;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS financial_config_items_resolve_metric ON financial_config_items;
CREATE TRIGGER financial_config_items_resolve_metric
  BEFORE INSERT OR UPDATE OF tenant_id, item_type, system_metric_key
  ON financial_config_items
  FOR EACH ROW
  EXECUTE FUNCTION resolve_financial_config_item_metric();

ALTER TABLE financial_config_items
  DROP CONSTRAINT IF EXISTS financial_config_items_metric_tenant_fk;
ALTER TABLE financial_config_items
  ADD CONSTRAINT financial_config_items_metric_tenant_fk
  FOREIGN KEY (tenant_id, metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE financial_benefit_lines
  DROP CONSTRAINT IF EXISTS financial_benefit_lines_metric_definition_id_fkey,
  DROP CONSTRAINT IF EXISTS financial_benefit_lines_metric_tenant_fk;
ALTER TABLE financial_benefit_lines
  ADD CONSTRAINT financial_benefit_lines_metric_tenant_fk
  FOREIGN KEY (tenant_id, metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE financial_metric_values
  DROP CONSTRAINT IF EXISTS financial_metric_values_metric_definition_id_fkey,
  DROP CONSTRAINT IF EXISTS financial_metric_values_metric_tenant_fk;
ALTER TABLE financial_metric_values
  ADD CONSTRAINT financial_metric_values_metric_tenant_fk
  FOREIGN KEY (tenant_id, metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE initiative_financial_scope
  DROP CONSTRAINT IF EXISTS initiative_financial_scope_metric_tenant_fk;
ALTER TABLE initiative_financial_scope
  ADD CONSTRAINT initiative_financial_scope_metric_tenant_fk
  FOREIGN KEY (tenant_id, metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE financial_initiative_annual_baselines
  DROP CONSTRAINT IF EXISTS financial_initiative_annual_baselines_metric_definition_id_fkey,
  DROP CONSTRAINT IF EXISTS financial_initiative_annual_baselines_metric_tenant_fk;
ALTER TABLE financial_initiative_annual_baselines
  ADD CONSTRAINT financial_initiative_annual_baselines_metric_tenant_fk
  FOREIGN KEY (tenant_id, metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE financial_tenant_annual_baselines
  DROP CONSTRAINT IF EXISTS financial_tenant_annual_baselines_metric_definition_id_fkey,
  DROP CONSTRAINT IF EXISTS financial_tenant_annual_baselines_metric_tenant_fk;
ALTER TABLE financial_tenant_annual_baselines
  ADD CONSTRAINT financial_tenant_annual_baselines_metric_tenant_fk
  FOREIGN KEY (tenant_id, metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE CASCADE;

ALTER TABLE shared_cost_allocation_rules
  DROP CONSTRAINT IF EXISTS shared_cost_rules_metric_tenant_fk;
ALTER TABLE shared_cost_allocation_rules
  ADD CONSTRAINT shared_cost_rules_metric_tenant_fk
  FOREIGN KEY (tenant_id, driver_metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

ALTER TABLE shared_cost_allocations
  DROP CONSTRAINT IF EXISTS shared_cost_allocations_metric_tenant_fk;
ALTER TABLE shared_cost_allocations
  ADD CONSTRAINT shared_cost_allocations_metric_tenant_fk
  FOREIGN KEY (tenant_id, basis_metric_definition_id)
  REFERENCES financial_metric_definitions(tenant_id, id) ON DELETE RESTRICT;

DO $$
DECLARE
  expected RECORD;
  actual_action "char";
BEGIN
  FOR expected IN
    SELECT * FROM (VALUES
      ('financial_metric_formula_dependencies_owner_fk', 'c'::"char"),
      ('financial_metric_formula_dependencies_input_fk', 'r'::"char"),
      ('financial_bridge_metric_memberships_bridge_fk', 'c'::"char"),
      ('financial_bridge_metric_memberships_metric_fk', 'r'::"char"),
      ('initiative_financial_selections_metric_tenant_fk', 'r'::"char"),
      ('financial_config_items_metric_tenant_fk', 'r'::"char"),
      ('financial_benefit_lines_metric_tenant_fk', 'r'::"char"),
      ('financial_metric_values_metric_tenant_fk', 'r'::"char"),
      ('initiative_financial_scope_metric_tenant_fk', 'r'::"char"),
      ('financial_initiative_annual_baselines_metric_tenant_fk', 'r'::"char"),
      ('financial_tenant_annual_baselines_metric_tenant_fk', 'c'::"char"),
      ('shared_cost_rules_metric_tenant_fk', 'r'::"char"),
      ('shared_cost_allocations_metric_tenant_fk', 'r'::"char")
    ) AS checks(constraint_name, delete_action)
  LOOP
    SELECT constraint_row.confdeltype
    INTO actual_action
    FROM pg_constraint constraint_row
    WHERE constraint_row.conname = expected.constraint_name
      AND constraint_row.connamespace = current_schema()::regnamespace;

    IF actual_action IS DISTINCT FROM expected.delete_action THEN
      RAISE EXCEPTION 'Metric FK % has delete action %, expected %',
        expected.constraint_name, actual_action, expected.delete_action;
    END IF;
  END LOOP;
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
  metric financial_metric_definitions%ROWTYPE;
  blockers JSONB;
  cleanup JSONB;
  blocker_total INTEGER;
BEGIN
  IF current_tenant_id() IS DISTINCT FROM p_tenant_id THEN
    RETURN NULL;
  END IF;
  IF NOT app_can_manage_financial_configuration() THEN
    RAISE EXCEPTION 'Insufficient role' USING ERRCODE = '42501';
  END IF;

  SELECT * INTO metric
  FROM financial_metric_definitions
  WHERE tenant_id = p_tenant_id
    AND id = p_metric_definition_id;
  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  blockers := jsonb_build_object(
    'benefit_lines', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM financial_benefit_lines WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT line.id, line.initiative_id, initiative.name AS initiative_name, line.name AS label
        FROM financial_benefit_lines line
        JOIN initiatives initiative ON initiative.tenant_id = line.tenant_id AND initiative.id = line.initiative_id
        WHERE line.tenant_id = p_tenant_id AND line.metric_definition_id = metric.id
        ORDER BY initiative.name, line.name LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'metric_values', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM financial_metric_values WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT value.id, value.initiative_id, initiative.name AS initiative_name,
               CONCAT(value.year, '-', LPAD(value.month::TEXT, 2, '0')) AS label
        FROM financial_metric_values value
        JOIN initiatives initiative ON initiative.tenant_id = value.tenant_id AND initiative.id = value.initiative_id
        WHERE value.tenant_id = p_tenant_id AND value.metric_definition_id = metric.id
        ORDER BY value.year DESC, value.month DESC LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'initiative_scope', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM initiative_financial_scope WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT scope.id, scope.initiative_id, initiative.name AS initiative_name,
               CASE WHEN scope.is_active THEN 'Active scope' ELSE 'Inactive scope' END AS label
        FROM initiative_financial_scope scope
        JOIN initiatives initiative ON initiative.tenant_id = scope.tenant_id AND initiative.id = scope.initiative_id
        WHERE scope.tenant_id = p_tenant_id AND scope.metric_definition_id = metric.id
        ORDER BY initiative.name LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'initiative_baselines', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM financial_initiative_annual_baselines WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT baseline.id, baseline.initiative_id, initiative.name AS initiative_name,
               baseline.baseline_year::TEXT AS label
        FROM financial_initiative_annual_baselines baseline
        JOIN initiatives initiative ON initiative.tenant_id = baseline.tenant_id AND initiative.id = baseline.initiative_id
        WHERE baseline.tenant_id = p_tenant_id AND baseline.metric_definition_id = metric.id
        ORDER BY baseline.baseline_year DESC, initiative.name LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'legacy_selections', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM initiative_financial_selections WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT selection.id, selection.initiative_id, initiative.name AS initiative_name, selection.item_key AS label
        FROM initiative_financial_selections selection
        JOIN initiatives initiative ON initiative.tenant_id = selection.tenant_id AND initiative.id = selection.initiative_id
        WHERE selection.tenant_id = p_tenant_id AND selection.metric_definition_id = metric.id
        ORDER BY initiative.name LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'legacy_configuration', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM financial_config_items WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT item.id, NULL::UUID AS initiative_id, NULL::TEXT AS initiative_name, item.label
        FROM financial_config_items item
        WHERE item.tenant_id = p_tenant_id AND item.metric_definition_id = metric.id
        ORDER BY item.label LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'formula_dependencies', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM financial_metric_formula_dependencies WHERE tenant_id = p_tenant_id AND input_metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT dependency.formula_metric_definition_id AS id, NULL::UUID AS initiative_id,
               NULL::TEXT AS initiative_name,
               formula_metric.label || ' · ' || dependency.reference_kind AS label
        FROM financial_metric_formula_dependencies dependency
        JOIN financial_metric_definitions formula_metric
          ON formula_metric.tenant_id = dependency.tenant_id
         AND formula_metric.id = dependency.formula_metric_definition_id
        WHERE dependency.tenant_id = p_tenant_id AND dependency.input_metric_definition_id = metric.id
        ORDER BY formula_metric.label LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'bridge_rows', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM financial_bridge_metric_memberships WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT bridge.id, NULL::UUID AS initiative_id, NULL::TEXT AS initiative_name, bridge.label
        FROM financial_bridge_metric_memberships membership
        JOIN financial_bridge_rows bridge
          ON bridge.tenant_id = membership.tenant_id AND bridge.id = membership.bridge_row_id
        WHERE membership.tenant_id = p_tenant_id AND membership.metric_definition_id = metric.id
        ORDER BY bridge.label LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'shared_cost_rules', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM shared_cost_allocation_rules WHERE tenant_id = p_tenant_id AND driver_metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT rule.id, NULL::UUID AS initiative_id, NULL::TEXT AS initiative_name,
               COALESCE(pool.name, 'Shared cost rule') AS label
        FROM shared_cost_allocation_rules rule
        LEFT JOIN shared_cost_pools pool ON pool.tenant_id = rule.tenant_id AND pool.id = rule.pool_id
        WHERE rule.tenant_id = p_tenant_id AND rule.driver_metric_definition_id = metric.id
        ORDER BY pool.name NULLS LAST LIMIT 10
      ) ref), '[]'::jsonb)
    ),
    'shared_cost_allocations', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM shared_cost_allocations WHERE tenant_id = p_tenant_id AND basis_metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT allocation.id, allocation.initiative_id, initiative.name AS initiative_name,
               COALESCE(allocation.basis_label, 'Historical allocation') AS label
        FROM shared_cost_allocations allocation
        LEFT JOIN initiatives initiative ON initiative.tenant_id = allocation.tenant_id AND initiative.id = allocation.initiative_id
        WHERE allocation.tenant_id = p_tenant_id AND allocation.basis_metric_definition_id = metric.id
        ORDER BY allocation.created_at DESC LIMIT 10
      ) ref), '[]'::jsonb)
    )
  );

  SELECT COALESCE(SUM((value ->> 'count')::INTEGER), 0)
  INTO blocker_total
  FROM jsonb_each(blockers);

  cleanup := jsonb_build_object(
    'tenant_annual_baselines', jsonb_build_object(
      'count', (SELECT COUNT(*) FROM financial_tenant_annual_baselines WHERE tenant_id = p_tenant_id AND metric_definition_id = metric.id),
      'references', COALESCE((SELECT jsonb_agg(to_jsonb(ref)) FROM (
        SELECT baseline.id, NULL::UUID AS initiative_id, NULL::TEXT AS initiative_name,
               baseline.baseline_year::TEXT AS label
        FROM financial_tenant_annual_baselines baseline
        WHERE baseline.tenant_id = p_tenant_id AND baseline.metric_definition_id = metric.id
        ORDER BY baseline.baseline_year DESC LIMIT 10
      ) ref), '[]'::jsonb)
    )
  );

  RETURN jsonb_build_object(
    'metric', jsonb_build_object(
      'id', metric.id,
      'key', metric.key,
      'label', metric.label,
      'is_system', metric.is_system,
      'is_active', metric.is_active
    ),
    'can_delete', NOT metric.is_system AND blocker_total = 0,
    'blocked_by_system', metric.is_system,
    'blocker_total', blocker_total,
    'blockers', blockers,
    'cleanup', cleanup,
    'confirmation_key', metric.key
  );
END;
$$;

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
  WHERE tenant_id = p_tenant_id
    AND id = p_metric_definition_id
  FOR UPDATE;
  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  impact := financial_metric_deletion_impact(p_tenant_id, p_metric_definition_id);
  IF metric.key IS DISTINCT FROM p_confirmation_key THEN
    RETURN impact || jsonb_build_object('deleted', FALSE, 'status', 'confirmation_mismatch');
  END IF;
  IF NOT COALESCE((impact ->> 'can_delete')::BOOLEAN, FALSE) THEN
    RETURN impact || jsonb_build_object('deleted', FALSE, 'status', 'blocked');
  END IF;

  PERFORM set_config('app.metric_delete_confirmed', metric.id::TEXT, TRUE);
  DELETE FROM financial_metric_definitions
  WHERE tenant_id = p_tenant_id AND id = metric.id;

  RETURN impact || jsonb_build_object('deleted', TRUE, 'status', 'deleted');
END;
$$;

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
    RETURN NEW;
  END IF;

  IF TG_OP = 'UPDATE' THEN
    IF NEW.is_system IS DISTINCT FROM OLD.is_system THEN
      RAISE EXCEPTION 'The system-metric classification is immutable'
        USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
  END IF;

  IF OLD.is_system AND current_tenant_id() IS NOT NULL THEN
    RAISE EXCEPTION 'System financial metrics cannot be deleted'
      USING ERRCODE = '23503';
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
  BEFORE INSERT OR UPDATE OF is_system
  ON financial_metric_definitions
  FOR EACH ROW
  EXECUTE FUNCTION protect_financial_metric_definition();

DROP TRIGGER IF EXISTS financial_metric_definitions_protect_delete
  ON financial_metric_definitions;
CREATE TRIGGER financial_metric_definitions_protect_delete
  BEFORE DELETE
  ON financial_metric_definitions
  FOR EACH ROW
  EXECUTE FUNCTION protect_financial_metric_definition();

REVOKE ALL ON FUNCTION financial_metric_deletion_impact(UUID, UUID) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION delete_financial_metric_definition(UUID, UUID, TEXT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION financial_metric_deletion_impact(UUID, UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION delete_financial_metric_definition(UUID, UUID, TEXT) TO authenticated, service_role;

COMMIT;
