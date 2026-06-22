-- Tenant-configurable dashboard registry.

BEGIN;

CREATE TABLE IF NOT EXISTS tenant_dashboard_config (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  dashboard_key TEXT NOT NULL,
  label         TEXT NOT NULL,
  route_path    TEXT NOT NULL,
  menu_group    TEXT NOT NULL DEFAULT 'dashboard',
  icon          TEXT NOT NULL DEFAULT 'grid',
  display_order INTEGER NOT NULL DEFAULT 0,
  is_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
  allowed_roles TEXT[] NOT NULL DEFAULT ARRAY['transformation_office','initiative_owner','viewer']::TEXT[],
  is_system     BOOLEAN NOT NULL DEFAULT TRUE,
  metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, dashboard_key),
  CHECK (dashboard_key ~ '^[a-z0-9_]+$'),
  CHECK (route_path LIKE '/%')
);

CREATE INDEX IF NOT EXISTS tenant_dashboard_config_tenant_idx
  ON tenant_dashboard_config(tenant_id, is_enabled, menu_group, display_order);

ALTER TABLE tenant_dashboard_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tdc_select" ON tenant_dashboard_config;
DROP POLICY IF EXISTS "tdc_insert" ON tenant_dashboard_config;
DROP POLICY IF EXISTS "tdc_update" ON tenant_dashboard_config;
DROP POLICY IF EXISTS "tdc_delete" ON tenant_dashboard_config;

CREATE POLICY "tdc_select" ON tenant_dashboard_config
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "tdc_insert" ON tenant_dashboard_config
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "tdc_update" ON tenant_dashboard_config
  FOR UPDATE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  ) WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "tdc_delete" ON tenant_dashboard_config
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

WITH defaults(dashboard_key, label, route_path, menu_group, icon, display_order) AS (
  VALUES
    ('executive_dashboard', 'Executive Dashboard', '/dashboard', 'dashboard', 'grid', 10),
    ('financial_overview', 'Financial Overview', '/financials', 'dashboard', 'payments', 20),
    ('initiative_portfolio', 'Initiative Portfolio', '/financials/initiative-portfolio', 'dashboard', 'table_chart', 30),
    ('investments_payback', 'Investments & Payback', '/financials/investments-payback', 'dashboard', 'request_quote', 40),
    ('bankable_plan', 'Bankable Plan', '/financials/bankable-plan', 'dashboard', 'account_balance', 50),
    ('benefits_register', 'Benefits Register', '/financials/benefits-register', 'dashboard', 'fact_check', 60),
    ('benefit_tracking', 'Benefit Tracking', '/financials/benefit-tracking', 'dashboard', 'trending_up', 70),
    ('waterline', 'Waterline', '/financials/waterline', 'dashboard', 'water_drop', 80),
    ('control_tower', 'Control Tower', '/reports/control-tower', 'dashboard', 'summarize', 90),
    ('shared_costs', 'Shared Costs', '/shared-costs', 'primary', 'account_balance', 100)
)
INSERT INTO tenant_dashboard_config (
  tenant_id,
  dashboard_key,
  label,
  route_path,
  menu_group,
  icon,
  display_order,
  is_enabled,
  is_system
)
SELECT
  org.id,
  defaults.dashboard_key,
  defaults.label,
  defaults.route_path,
  defaults.menu_group,
  defaults.icon,
  defaults.display_order,
  TRUE,
  TRUE
FROM organizations org
CROSS JOIN defaults
ON CONFLICT (tenant_id, dashboard_key) DO NOTHING;

COMMIT;
