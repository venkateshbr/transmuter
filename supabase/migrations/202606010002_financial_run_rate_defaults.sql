-- Align tenant financial defaults to run-rate EBITDA semantics.
-- Net Run-rate Impact = Total Benefits - Recurring Costs. One-off costs remain separate.

UPDATE financial_config_groups
SET label = CASE key
    WHEN 'benefits' THEN 'Total Benefits'
    WHEN 'one_off_costs' THEN 'One-off Costs'
    WHEN 'net_value' THEN 'Net Run-rate Impact'
    WHEN 'implementation' THEN 'One-off Costs'
    WHEN 'operating' THEN 'Recurring Costs'
    ELSE label
  END,
  updated_at = NOW()
WHERE key IN ('benefits', 'one_off_costs', 'net_value', 'implementation', 'operating');

INSERT INTO financial_config_groups (tenant_id, key, label, kind, rollup_type, display_order, is_system)
SELECT org.id, defaults.key, defaults.label, defaults.kind, defaults.rollup_type, defaults.display_order, TRUE
FROM organizations org
CROSS JOIN (
  VALUES
    ('savings', 'Savings', 'metric', NULL, 40),
    ('payback_period', 'Payback Period', 'calculation', NULL, 70)
) AS defaults(key, label, kind, rollup_type, display_order)
ON CONFLICT (tenant_id, key) DO UPDATE SET
  label = EXCLUDED.label,
  kind = EXCLUDED.kind,
  rollup_type = EXCLUDED.rollup_type,
  display_order = EXCLUDED.display_order,
  is_system = TRUE,
  is_active = TRUE,
  updated_at = NOW();

WITH groups AS (
  SELECT tenant_id, id, key
  FROM financial_config_groups
  WHERE key IN ('revenue', 'gross_margin', 'savings', 'implementation', 'operating', 'uncategorized')
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
  FROM groups g
  JOIN (
    VALUES
      ('revenue','revenue_uplift_base','Revenue Uplift ($) (Base)','metric','revenue_uplift_base','benefit',10),
      ('revenue','revenue_uplift_high','Revenue Uplift ($) (High)','metric','revenue_uplift_high','benefit',20),
      ('revenue','revenue_uplift_actual','Revenue Uplift ($) (Actual)','metric','revenue_uplift_actual','benefit',30),
      ('gross_margin','gm_uplift_base','Gross Margin Uplift ($) (Base)','metric','gm_uplift_base','benefit',70),
      ('gross_margin','gm_uplift_high','Gross Margin Uplift ($) (High)','metric','gm_uplift_high','benefit',80),
      ('gross_margin','gm_uplift_actual','Gross Margin Uplift ($) (Actual)','metric','gm_uplift_actual','benefit',90),
      ('savings','cost_savings','Cost Savings ($)','metric',NULL,'benefit',10),
      ('implementation','implementation','Implementation / Project Cost','cost_category',NULL,'one_off_cost',10),
      ('implementation','technology_tooling','Technology / Tooling','cost_category',NULL,'one_off_cost',20),
      ('implementation','external_consultants','External Consultants','cost_category',NULL,'one_off_cost',30),
      ('implementation','training_change','Training / Change Management','cost_category',NULL,'one_off_cost',40),
      ('implementation','other_one_off','Other One-off Cost','cost_category',NULL,'one_off_cost',90),
      ('operating','software_subscriptions','Software Subscriptions','cost_category',NULL,'recurring_cost',10),
      ('operating','support_maintenance','Support / Maintenance','cost_category',NULL,'recurring_cost',20),
      ('operating','additional_headcount','Additional Headcount','cost_category',NULL,'recurring_cost',30),
      ('operating','run_rate_operating','Run-rate Operating Cost','cost_category',NULL,'recurring_cost',40),
      ('operating','maintenance','Maintenance','cost_category',NULL,'recurring_cost',50),
      ('operating','software','Software / Licenses','cost_category',NULL,'recurring_cost',60),
      ('operating','labor','Labor / Operations','cost_category',NULL,'recurring_cost',70),
      ('uncategorized','other','Other','cost_category',NULL,NULL,99)
  ) AS i(group_key, key, label, item_type, system_metric_key, rollup_type, display_order)
    ON i.group_key = g.key
) seeded
ON CONFLICT (tenant_id, key) DO UPDATE SET
  group_id = EXCLUDED.group_id,
  label = EXCLUDED.label,
  item_type = EXCLUDED.item_type,
  system_metric_key = EXCLUDED.system_metric_key,
  rollup_type = EXCLUDED.rollup_type,
  display_order = EXCLUDED.display_order,
  is_system = TRUE,
  is_active = TRUE,
  updated_at = NOW();
