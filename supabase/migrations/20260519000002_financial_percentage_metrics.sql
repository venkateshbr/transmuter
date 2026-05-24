-- Migration: add selectable percentage and gross-margin system metrics

WITH groups AS (
  SELECT tenant_id, id, key
  FROM financial_config_groups
  WHERE key IN ('revenue', 'cogs', 'gross_margin')
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
SELECT tenant_id, group_id, key, label, 'metric', system_metric_key, rollup_type, display_order, TRUE
FROM (
  SELECT g.tenant_id, g.id AS group_id, i.*
  FROM groups g
  JOIN (
    VALUES
      ('revenue','revenue_uplift_pct_base','Revenue Uplift % (Base)','revenue_uplift_pct_base',NULL,40),
      ('revenue','revenue_uplift_pct_high','Revenue Uplift % (High)','revenue_uplift_pct_high',NULL,50),
      ('revenue','revenue_uplift_pct_actual','Revenue Uplift % (Actual)','revenue_uplift_pct_actual',NULL,60),
      ('cogs','cogs_pct_base','COGS % (Base)','cogs_pct_base',NULL,40),
      ('cogs','cogs_pct_high','COGS % (High)','cogs_pct_high',NULL,50),
      ('cogs','cogs_pct_actual','COGS % (Actual)','cogs_pct_actual',NULL,60),
      ('gross_margin','gross_margin_base','Gross Margin (Base)','gross_margin_base','benefit',10),
      ('gross_margin','gross_margin_high','Gross Margin (High)','gross_margin_high','benefit',20),
      ('gross_margin','gross_margin_actual','Gross Margin (Actual)','gross_margin_actual','benefit',30),
      ('gross_margin','gm_pct_base','Gross Margin % (Base)','gm_pct_base',NULL,40),
      ('gross_margin','gm_pct_high','Gross Margin % (High)','gm_pct_high',NULL,50),
      ('gross_margin','gm_pct_actual','Gross Margin % (Actual)','gm_pct_actual',NULL,60),
      ('gross_margin','gm_uplift_pct_base','GM Uplift % (Base)','gm_uplift_pct_base',NULL,100),
      ('gross_margin','gm_uplift_pct_high','GM Uplift % (High)','gm_uplift_pct_high',NULL,110),
      ('gross_margin','gm_uplift_pct_actual','GM Uplift % (Actual)','gm_uplift_pct_actual',NULL,120)
  ) AS i(group_key, key, label, system_metric_key, rollup_type, display_order)
    ON i.group_key = g.key
) seeded
ON CONFLICT (tenant_id, key) DO UPDATE SET
  label = EXCLUDED.label,
  system_metric_key = EXCLUDED.system_metric_key,
  rollup_type = EXCLUDED.rollup_type,
  display_order = EXCLUDED.display_order,
  item_type = EXCLUDED.item_type,
  is_system = TRUE,
  is_active = TRUE,
  updated_at = NOW();

WITH system_metric_labels AS (
  SELECT tenant_id, label
  FROM financial_config_items
  WHERE item_type = 'metric'
    AND is_system = TRUE
    AND is_active = TRUE
    AND system_metric_key IS NOT NULL
)
UPDATE financial_config_items item
SET is_active = FALSE,
    updated_at = NOW()
FROM system_metric_labels system_item
WHERE item.tenant_id = system_item.tenant_id
  AND item.item_type = 'metric'
  AND item.is_system = FALSE
  AND item.system_metric_key IS NULL
  AND item.label = system_item.label;
