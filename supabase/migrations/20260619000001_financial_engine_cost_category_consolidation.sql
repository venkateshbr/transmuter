BEGIN;

CREATE TABLE IF NOT EXISTS financial_cost_categories (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  key           TEXT NOT NULL,
  label         TEXT NOT NULL,
  group_key     TEXT,
  rollup_type   TEXT CHECK (rollup_type IN ('recurring_cost','one_off_cost','total_cost','net_value')),
  display_order INTEGER NOT NULL DEFAULT 0,
  attributes    JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_system     BOOLEAN NOT NULL DEFAULT FALSE,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, key)
);

CREATE INDEX IF NOT EXISTS financial_cost_categories_tenant_idx
  ON financial_cost_categories(tenant_id, is_active, display_order);

CREATE UNIQUE INDEX IF NOT EXISTS financial_cost_categories_tenant_id_id_uidx
  ON financial_cost_categories(tenant_id, id);

ALTER TABLE financial_cost_categories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fcc_select" ON financial_cost_categories;
DROP POLICY IF EXISTS "fcc_insert" ON financial_cost_categories;
DROP POLICY IF EXISTS "fcc_update" ON financial_cost_categories;
DROP POLICY IF EXISTS "fcc_delete" ON financial_cost_categories;

CREATE POLICY "fcc_select" ON financial_cost_categories
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fcc_insert" ON financial_cost_categories
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "fcc_update" ON financial_cost_categories
  FOR UPDATE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  ) WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "fcc_delete" ON financial_cost_categories
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

INSERT INTO financial_cost_categories (
  tenant_id,
  key,
  label,
  group_key,
  rollup_type,
  display_order,
  is_system,
  is_active
)
SELECT
  item.tenant_id,
  item.key,
  item.label,
  grp.key AS group_key,
  CASE
    WHEN item.rollup_type IN ('recurring_cost','one_off_cost','total_cost','net_value')
      THEN item.rollup_type
    ELSE NULL
  END,
  item.display_order,
  item.is_system,
  item.is_active
FROM financial_config_items item
LEFT JOIN financial_config_groups grp
  ON grp.tenant_id = item.tenant_id
 AND grp.id = item.group_id
WHERE item.item_type = 'cost_category'
ON CONFLICT (tenant_id, key) DO UPDATE SET
  label = EXCLUDED.label,
  group_key = EXCLUDED.group_key,
  rollup_type = EXCLUDED.rollup_type,
  display_order = EXCLUDED.display_order,
  is_system = financial_cost_categories.is_system OR EXCLUDED.is_system,
  is_active = EXCLUDED.is_active,
  updated_at = NOW();

INSERT INTO financial_cost_categories (
  tenant_id,
  key,
  label,
  group_key,
  rollup_type,
  display_order,
  is_system,
  is_active
)
SELECT
  org.id,
  'other',
  'Other',
  'uncategorized',
  NULL,
  9999,
  TRUE,
  TRUE
FROM organizations org
ON CONFLICT (tenant_id, key) DO NOTHING;

INSERT INTO financial_cost_categories (
  tenant_id,
  key,
  label,
  group_key,
  rollup_type,
  display_order,
  is_system,
  is_active
)
SELECT DISTINCT
  line.tenant_id,
  COALESCE(NULLIF(line.category_key, ''), 'other') AS key,
  INITCAP(REPLACE(COALESCE(NULLIF(line.category_key, ''), 'other'), '_', ' ')) AS label,
  'imported',
  CASE WHEN line.is_recurring THEN 'recurring_cost' ELSE 'one_off_cost' END,
  10000,
  FALSE,
  TRUE
FROM financial_cost_lines line
WHERE NOT EXISTS (
  SELECT 1
  FROM financial_cost_categories cat
  WHERE cat.tenant_id = line.tenant_id
    AND cat.key = COALESCE(NULLIF(line.category_key, ''), 'other')
);

ALTER TABLE financial_cost_lines
  ADD COLUMN IF NOT EXISTS category_id UUID;

ALTER TABLE financial_cost_lines
  DROP CONSTRAINT IF EXISTS financial_cost_lines_category_id_fkey;

UPDATE financial_cost_lines line
SET
  category_key = COALESCE(NULLIF(line.category_key, ''), 'other'),
  category_id = cat.id
FROM financial_cost_categories cat
WHERE cat.tenant_id = line.tenant_id
  AND cat.key = COALESCE(NULLIF(line.category_key, ''), 'other')
  AND (line.category_id IS DISTINCT FROM cat.id OR line.category_key IS NULL OR line.category_key = '');

CREATE INDEX IF NOT EXISTS financial_cost_lines_category_id_idx
  ON financial_cost_lines(tenant_id, category_id);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'financial_cost_lines_category_tenant_fk'
      AND conrelid = 'financial_cost_lines'::regclass
  ) THEN
    ALTER TABLE financial_cost_lines
      ADD CONSTRAINT financial_cost_lines_category_tenant_fk
      FOREIGN KEY (tenant_id, category_id)
      REFERENCES financial_cost_categories(tenant_id, id)
      ON DELETE SET NULL (category_id);
  END IF;
END $$;

ALTER TABLE financial_bridge_rows
  ADD COLUMN IF NOT EXISTS cost_category_ids UUID[] NOT NULL DEFAULT '{}';

UPDATE financial_bridge_rows row
SET cost_category_ids = COALESCE((
  SELECT ARRAY_AGG(cat.id ORDER BY cat.display_order, cat.label)
  FROM financial_cost_categories cat
  WHERE cat.tenant_id = row.tenant_id
    AND cat.key = ANY(row.cost_category_keys)
), '{}')
WHERE row.cost_category_ids = '{}'
  AND COALESCE(array_length(row.cost_category_keys, 1), 0) > 0;

CREATE OR REPLACE FUNCTION financial_bridge_rows_validate_tenant_refs()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM unnest(COALESCE(NEW.metric_definition_ids, '{}'::uuid[])) metric_id
    LEFT JOIN financial_metric_definitions def
      ON def.id = metric_id
     AND def.tenant_id = NEW.tenant_id
    WHERE def.id IS NULL
  ) THEN
    RAISE EXCEPTION 'financial_bridge_rows metric_definition_ids must belong to the same tenant';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM unnest(COALESCE(NEW.cost_category_ids, '{}'::uuid[])) category_id
    LEFT JOIN financial_cost_categories cat
      ON cat.id = category_id
     AND cat.tenant_id = NEW.tenant_id
    WHERE cat.id IS NULL
  ) THEN
    RAISE EXCEPTION 'financial_bridge_rows cost_category_ids must belong to the same tenant';
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS financial_bridge_rows_validate_tenant_refs
  ON financial_bridge_rows;

CREATE TRIGGER financial_bridge_rows_validate_tenant_refs
  BEFORE INSERT OR UPDATE OF tenant_id, metric_definition_ids, cost_category_ids
  ON financial_bridge_rows
  FOR EACH ROW
  EXECUTE FUNCTION financial_bridge_rows_validate_tenant_refs();

CREATE UNIQUE INDEX IF NOT EXISTS initiatives_tenant_id_id_uidx
  ON initiatives(tenant_id, id);

CREATE UNIQUE INDEX IF NOT EXISTS financial_metric_definitions_tenant_id_id_uidx
  ON financial_metric_definitions(tenant_id, id);

CREATE TABLE IF NOT EXISTS initiative_financial_scope (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  initiative_id        UUID NOT NULL,
  scope_type           TEXT NOT NULL CHECK (scope_type IN ('metric_definition','cost_category')),
  metric_definition_id UUID,
  cost_category_id     UUID,
  is_active            BOOLEAN NOT NULL DEFAULT TRUE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (
    (scope_type = 'metric_definition' AND metric_definition_id IS NOT NULL AND cost_category_id IS NULL)
    OR
    (scope_type = 'cost_category' AND cost_category_id IS NOT NULL AND metric_definition_id IS NULL)
  )
);

ALTER TABLE initiative_financial_scope
  DROP CONSTRAINT IF EXISTS initiative_financial_scope_initiative_id_fkey,
  DROP CONSTRAINT IF EXISTS initiative_financial_scope_metric_definition_id_fkey,
  DROP CONSTRAINT IF EXISTS initiative_financial_scope_cost_category_id_fkey;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'initiative_financial_scope_initiative_tenant_fk'
      AND conrelid = 'initiative_financial_scope'::regclass
  ) THEN
    ALTER TABLE initiative_financial_scope
      ADD CONSTRAINT initiative_financial_scope_initiative_tenant_fk
      FOREIGN KEY (tenant_id, initiative_id)
      REFERENCES initiatives(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'initiative_financial_scope_metric_tenant_fk'
      AND conrelid = 'initiative_financial_scope'::regclass
  ) THEN
    ALTER TABLE initiative_financial_scope
      ADD CONSTRAINT initiative_financial_scope_metric_tenant_fk
      FOREIGN KEY (tenant_id, metric_definition_id)
      REFERENCES financial_metric_definitions(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'initiative_financial_scope_category_tenant_fk'
      AND conrelid = 'initiative_financial_scope'::regclass
  ) THEN
    ALTER TABLE initiative_financial_scope
      ADD CONSTRAINT initiative_financial_scope_category_tenant_fk
      FOREIGN KEY (tenant_id, cost_category_id)
      REFERENCES financial_cost_categories(tenant_id, id)
      ON DELETE CASCADE;
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS initiative_financial_scope_metric_unique
  ON initiative_financial_scope(tenant_id, initiative_id, metric_definition_id)
  WHERE scope_type = 'metric_definition';

CREATE UNIQUE INDEX IF NOT EXISTS initiative_financial_scope_category_unique
  ON initiative_financial_scope(tenant_id, initiative_id, cost_category_id)
  WHERE scope_type = 'cost_category';

CREATE INDEX IF NOT EXISTS initiative_financial_scope_lookup_idx
  ON initiative_financial_scope(tenant_id, initiative_id, scope_type, is_active);

ALTER TABLE initiative_financial_scope ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ifs2_select" ON initiative_financial_scope;
DROP POLICY IF EXISTS "ifs2_insert" ON initiative_financial_scope;
DROP POLICY IF EXISTS "ifs2_update" ON initiative_financial_scope;
DROP POLICY IF EXISTS "ifs2_delete" ON initiative_financial_scope;

CREATE POLICY "ifs2_select" ON initiative_financial_scope
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ifs2_insert" ON initiative_financial_scope
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "ifs2_update" ON initiative_financial_scope
  FOR UPDATE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  ) WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "ifs2_delete" ON initiative_financial_scope
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

INSERT INTO initiative_financial_scope (
  tenant_id,
  initiative_id,
  scope_type,
  metric_definition_id,
  is_active
)
SELECT DISTINCT
  legacy.tenant_id,
  legacy.initiative_id,
  'metric_definition',
  def.id,
  legacy.is_active
FROM initiative_financial_selections legacy
JOIN financial_metric_definitions def
  ON def.tenant_id = legacy.tenant_id
 AND def.key = REGEXP_REPLACE(legacy.item_key, '_(base|high|actual)$', '')
WHERE legacy.item_type = 'metric'
ON CONFLICT DO NOTHING;

INSERT INTO initiative_financial_scope (
  tenant_id,
  initiative_id,
  scope_type,
  cost_category_id,
  is_active
)
SELECT DISTINCT
  legacy.tenant_id,
  legacy.initiative_id,
  'cost_category',
  cat.id,
  legacy.is_active
FROM initiative_financial_selections legacy
JOIN financial_cost_categories cat
  ON cat.tenant_id = legacy.tenant_id
 AND cat.key = legacy.item_key
WHERE legacy.item_type = 'cost_category'
ON CONFLICT DO NOTHING;

COMMIT;
