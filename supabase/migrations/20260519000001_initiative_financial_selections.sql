-- Migration: Initiative-specific financial metric selection and custom metric values

WITH operating_groups AS (
  SELECT tenant_id, id
  FROM financial_config_groups
  WHERE key = 'operating'
)
INSERT INTO financial_config_items (
  tenant_id,
  group_id,
  key,
  label,
  item_type,
  system_metric_key,
  rollup_type,
  display_order,
  is_system
)
SELECT tenant_id, id, 'maintenance', 'Maintenance', 'cost_category', NULL, 'recurring_cost', 10, TRUE
FROM operating_groups
ON CONFLICT (tenant_id, key) DO NOTHING;

CREATE TABLE IF NOT EXISTS initiative_financial_selections (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  item_key      TEXT NOT NULL,
  item_type     TEXT NOT NULL CHECK (item_type IN ('metric','cost_category')),
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, initiative_id, item_key, item_type)
);

CREATE INDEX IF NOT EXISTS initiative_financial_selections_idx
  ON initiative_financial_selections(tenant_id, initiative_id, item_type, is_active);

ALTER TABLE initiative_financial_selections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ifs_select" ON initiative_financial_selections;
DROP POLICY IF EXISTS "ifs_insert" ON initiative_financial_selections;
DROP POLICY IF EXISTS "ifs_update" ON initiative_financial_selections;
DROP POLICY IF EXISTS "ifs_delete" ON initiative_financial_selections;

CREATE POLICY "ifs_select" ON initiative_financial_selections
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ifs_insert" ON initiative_financial_selections
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "ifs_update" ON initiative_financial_selections
  FOR UPDATE
  USING (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  )
  WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "ifs_delete" ON initiative_financial_selections
  FOR DELETE USING (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  );

CREATE TABLE IF NOT EXISTS financial_metric_values (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id),
  initiative_id   UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  metric_key      TEXT NOT NULL,
  year            INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2040),
  quarter         INTEGER CHECK (quarter BETWEEN 1 AND 4),
  month           INTEGER CHECK (month BETWEEN 1 AND 12),
  value_base      NUMERIC(15,4) DEFAULT 0,
  value_high      NUMERIC(15,4) DEFAULT 0,
  value_actual    NUMERIC(15,4),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE NULLS NOT DISTINCT (tenant_id, initiative_id, metric_key, year, quarter, month)
);

CREATE INDEX IF NOT EXISTS financial_metric_values_idx
  ON financial_metric_values(tenant_id, initiative_id, metric_key, year, month);

ALTER TABLE financial_metric_values ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fmv_select" ON financial_metric_values;
DROP POLICY IF EXISTS "fmv_insert" ON financial_metric_values;
DROP POLICY IF EXISTS "fmv_update" ON financial_metric_values;
DROP POLICY IF EXISTS "fmv_delete" ON financial_metric_values;

CREATE POLICY "fmv_select" ON financial_metric_values
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fmv_insert" ON financial_metric_values
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "fmv_update" ON financial_metric_values
  FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "fmv_delete" ON financial_metric_values
  FOR DELETE USING (tenant_id = current_tenant_id());

WITH retired_groups AS (
  SELECT tenant_id, key
  FROM financial_config_groups
  WHERE label IN ('Uncategorized', 'Cost Group 4', 'Metric Category 4', 'Metric Category 5')
)
UPDATE financial_config_items item
SET is_active = FALSE, updated_at = NOW()
FROM retired_groups grp
WHERE item.tenant_id = grp.tenant_id
  AND item.group_id IN (
    SELECT id
    FROM financial_config_groups
    WHERE tenant_id = grp.tenant_id
      AND key = grp.key
  );

UPDATE financial_config_groups
SET is_active = FALSE, updated_at = NOW()
WHERE label IN ('Uncategorized', 'Cost Group 4', 'Metric Category 4', 'Metric Category 5');
