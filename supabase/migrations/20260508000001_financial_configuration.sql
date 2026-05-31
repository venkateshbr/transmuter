-- Migration: Tenant-scoped financial configuration and cost line categories

CREATE TABLE IF NOT EXISTS financial_config_groups (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  key           TEXT NOT NULL,
  label         TEXT NOT NULL,
  kind          TEXT NOT NULL CHECK (kind IN ('calculation','metric','cost_category')),
  rollup_type   TEXT CHECK (rollup_type IN ('benefit','recurring_cost','one_off_cost','total_cost','net_value')),
  display_order INTEGER NOT NULL DEFAULT 0,
  is_system     BOOLEAN NOT NULL DEFAULT FALSE,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, key)
);

CREATE TABLE IF NOT EXISTS financial_config_items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES organizations(id),
  group_id          UUID NOT NULL REFERENCES financial_config_groups(id) ON DELETE CASCADE,
  key               TEXT NOT NULL,
  label             TEXT NOT NULL,
  item_type         TEXT NOT NULL CHECK (item_type IN ('metric','cost_category')),
  system_metric_key TEXT,
  rollup_type       TEXT CHECK (rollup_type IN ('benefit','recurring_cost','one_off_cost','total_cost','net_value')),
  display_order     INTEGER NOT NULL DEFAULT 0,
  is_system         BOOLEAN NOT NULL DEFAULT FALSE,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, key)
);

CREATE INDEX IF NOT EXISTS financial_config_groups_tenant_idx
  ON financial_config_groups(tenant_id, kind, display_order);
CREATE INDEX IF NOT EXISTS financial_config_items_tenant_idx
  ON financial_config_items(tenant_id, item_type, display_order);
CREATE INDEX IF NOT EXISTS financial_config_items_group_idx
  ON financial_config_items(group_id, display_order);

ALTER TABLE financial_config_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_config_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fcg_select" ON financial_config_groups;
DROP POLICY IF EXISTS "fcg_insert" ON financial_config_groups;
DROP POLICY IF EXISTS "fcg_update" ON financial_config_groups;
DROP POLICY IF EXISTS "fcg_delete" ON financial_config_groups;
DROP POLICY IF EXISTS "fci_select" ON financial_config_items;
DROP POLICY IF EXISTS "fci_insert" ON financial_config_items;
DROP POLICY IF EXISTS "fci_update" ON financial_config_items;
DROP POLICY IF EXISTS "fci_delete" ON financial_config_items;

CREATE POLICY "fcg_select" ON financial_config_groups FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fcg_insert" ON financial_config_groups FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fcg_update" ON financial_config_groups FOR UPDATE
  USING (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  )
  WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "fcg_delete" ON financial_config_groups FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fci_select" ON financial_config_items FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fci_insert" ON financial_config_items FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fci_update" ON financial_config_items FOR UPDATE
  USING (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  )
  WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "fci_delete" ON financial_config_items FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);

ALTER TABLE financial_cost_lines
  ADD COLUMN IF NOT EXISTS category_key TEXT NOT NULL DEFAULT 'other';

CREATE INDEX IF NOT EXISTS cost_lines_category_idx
  ON financial_cost_lines(tenant_id, category_key);

WITH default_groups AS (
  INSERT INTO financial_config_groups (tenant_id, key, label, kind, rollup_type, display_order, is_system)
  SELECT id, key, label, kind, rollup_type, display_order, TRUE
  FROM organizations
  CROSS JOIN (
    VALUES
      ('benefits','Benefits','calculation','benefit',10),
      ('recurring_costs','Recurring Costs','calculation','recurring_cost',20),
      ('one_off_costs','One-time Costs','calculation','one_off_cost',30),
      ('total_costs','Total Costs','calculation','total_cost',40),
      ('net_value','Net Value','calculation','net_value',50),
      ('revenue','Revenue','metric',NULL,10),
      ('cogs','COGS','metric',NULL,20),
      ('gross_margin','Gross Margin','metric',NULL,30),
      ('implementation','Implementation Costs','cost_category',NULL,10),
      ('operating','Operating Costs','cost_category',NULL,20),
      ('uncategorized','Uncategorized','cost_category',NULL,99)
  ) AS defaults(key, label, kind, rollup_type, display_order)
  ON CONFLICT (tenant_id, key) DO NOTHING
  RETURNING tenant_id, id, key
),
all_groups AS (
  SELECT tenant_id, id, key FROM default_groups
  UNION
  SELECT tenant_id, id, key FROM financial_config_groups
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
SELECT tenant_id, group_id, key, label, item_type, system_metric_key, rollup_type, display_order, TRUE
FROM (
  SELECT g.tenant_id, g.id AS group_id, i.*
  FROM all_groups g
  JOIN (
    VALUES
      ('revenue','revenue_uplift_base','Revenue Uplift (Base)','metric','revenue_uplift_base','benefit',10),
      ('revenue','revenue_uplift_high','Revenue Uplift (High)','metric','revenue_uplift_high','benefit',20),
      ('revenue','revenue_uplift_actual','Revenue Uplift (Actual)','metric','revenue_uplift_actual','benefit',30),
      ('revenue','revenue_uplift_pct_base','Revenue Uplift % (Base)','metric','revenue_uplift_pct_base',NULL,40),
      ('revenue','revenue_uplift_pct_high','Revenue Uplift % (High)','metric','revenue_uplift_pct_high',NULL,50),
      ('revenue','revenue_uplift_pct_actual','Revenue Uplift % (Actual)','metric','revenue_uplift_pct_actual',NULL,60),
      ('cogs','cogs_base','COGS (Base)','metric','cogs_base',NULL,10),
      ('cogs','cogs_high','COGS (High)','metric','cogs_high',NULL,20),
      ('cogs','cogs_actual','COGS (Actual)','metric','cogs_actual',NULL,30),
      ('cogs','cogs_pct_base','COGS % (Base)','metric','cogs_pct_base',NULL,40),
      ('cogs','cogs_pct_high','COGS % (High)','metric','cogs_pct_high',NULL,50),
      ('cogs','cogs_pct_actual','COGS % (Actual)','metric','cogs_pct_actual',NULL,60),
      ('gross_margin','gross_margin_base','Gross Margin (Base)','metric','gross_margin_base','benefit',10),
      ('gross_margin','gross_margin_high','Gross Margin (High)','metric','gross_margin_high','benefit',20),
      ('gross_margin','gross_margin_actual','Gross Margin (Actual)','metric','gross_margin_actual','benefit',30),
      ('gross_margin','gm_pct_base','Gross Margin % (Base)','metric','gm_pct_base',NULL,40),
      ('gross_margin','gm_pct_high','Gross Margin % (High)','metric','gm_pct_high',NULL,50),
      ('gross_margin','gm_pct_actual','Gross Margin % (Actual)','metric','gm_pct_actual',NULL,60),
      ('gross_margin','gm_uplift_base','GM Uplift (Base)','metric','gm_uplift_base','benefit',70),
      ('gross_margin','gm_uplift_high','GM Uplift (High)','metric','gm_uplift_high','benefit',80),
      ('gross_margin','gm_uplift_actual','GM Uplift (Actual)','metric','gm_uplift_actual','benefit',90),
      ('gross_margin','gm_uplift_pct_base','GM Uplift % (Base)','metric','gm_uplift_pct_base',NULL,100),
      ('gross_margin','gm_uplift_pct_high','GM Uplift % (High)','metric','gm_uplift_pct_high',NULL,110),
      ('gross_margin','gm_uplift_pct_actual','GM Uplift % (Actual)','metric','gm_uplift_pct_actual',NULL,120),
      ('implementation','implementation','Implementation','cost_category',NULL,'one_off_cost',10),
      ('implementation','vendor','Vendor / Consulting','cost_category',NULL,'one_off_cost',20),
      ('operating','maintenance','Maintenance','cost_category',NULL,'recurring_cost',10),
      ('operating','software','Software / Licenses','cost_category',NULL,'recurring_cost',20),
      ('operating','labor','Labor / Operations','cost_category',NULL,'recurring_cost',30),
      ('uncategorized','other','Other','cost_category',NULL,NULL,99)
  ) AS i(group_key, key, label, item_type, system_metric_key, rollup_type, display_order)
    ON i.group_key = g.key
) seeded
ON CONFLICT (tenant_id, key) DO NOTHING;

UPDATE financial_cost_lines SET category_key = 'other' WHERE category_key IS NULL OR category_key = '';
