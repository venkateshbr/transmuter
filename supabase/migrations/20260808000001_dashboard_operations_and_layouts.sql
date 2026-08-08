-- Consolidate dashboard navigation and add tenant/user widget layouts.

BEGIN;

UPDATE tenant_dashboard_config
SET label = CASE dashboard_key
      WHEN 'executive_dashboard' THEN 'Operational Dashboard'
      WHEN 'financial_overview' THEN 'Financial Dashboard'
      WHEN 'benefit_tracking' THEN 'Benefit Ledger'
      WHEN 'bankable_plan' THEN 'Bankable Plans'
      WHEN 'waterline' THEN 'Waterline & Target Locks'
      ELSE label
    END,
    menu_group = CASE
      WHEN dashboard_key IN ('executive_dashboard', 'financial_overview', 'initiative_portfolio') THEN 'dashboard'
      WHEN dashboard_key IN ('benefit_tracking', 'benefits_register', 'bankable_plan', 'waterline', 'shared_costs') THEN 'operations'
      WHEN dashboard_key IN ('investments_payback', 'control_tower') THEN 'hidden'
      ELSE menu_group
    END,
    display_order = CASE dashboard_key
      WHEN 'benefit_tracking' THEN 130
      WHEN 'benefits_register' THEN 140
      WHEN 'bankable_plan' THEN 150
      WHEN 'waterline' THEN 160
      WHEN 'shared_costs' THEN 170
      ELSE display_order
    END,
    is_enabled = CASE
      WHEN dashboard_key IN (
        'executive_dashboard', 'financial_overview', 'initiative_portfolio',
        'benefit_tracking', 'benefits_register', 'bankable_plan', 'waterline', 'shared_costs'
      ) THEN TRUE
      ELSE is_enabled
    END,
    updated_at = NOW();

CREATE TABLE IF NOT EXISTS dashboard_layouts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  dashboard_key   TEXT NOT NULL CHECK (dashboard_key IN ('operational', 'financial')),
  owner_type      TEXT NOT NULL CHECK (owner_type IN ('tenant', 'user')),
  owner_user_id   UUID REFERENCES users(id) ON DELETE CASCADE,
  role_key        TEXT,
  breakpoint      TEXT NOT NULL DEFAULT 'desktop' CHECK (breakpoint IN ('desktop', 'tablet')),
  layout_version  INTEGER NOT NULL DEFAULT 1,
  widgets         JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(widgets) = 'array'),
  is_published    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (
    (owner_type = 'user' AND owner_user_id IS NOT NULL AND role_key IS NULL)
    OR (owner_type = 'tenant' AND owner_user_id IS NULL AND role_key IS NOT NULL)
  ),
  CHECK (
    role_key IS NULL OR role_key IN (
      'transformation_office', 'tenant_admin', 'pmo_lead', 'finance_lead',
      'workstream_lead', 'initiative_owner', 'business_benefit_owner',
      'executive_sponsor', 'viewer'
    )
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS dashboard_layouts_user_unique
  ON dashboard_layouts(tenant_id, dashboard_key, owner_user_id, breakpoint)
  WHERE owner_type = 'user';
CREATE UNIQUE INDEX IF NOT EXISTS dashboard_layouts_tenant_unique
  ON dashboard_layouts(tenant_id, dashboard_key, role_key, breakpoint)
  WHERE owner_type = 'tenant';
CREATE INDEX IF NOT EXISTS dashboard_layouts_lookup_idx
  ON dashboard_layouts(tenant_id, dashboard_key, breakpoint, owner_type);

ALTER TABLE dashboard_layouts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "dashboard_layouts_select" ON dashboard_layouts
  FOR SELECT USING (
    tenant_id = current_tenant_id()
    AND (
      (owner_type = 'tenant' AND is_published AND role_key = current_user_role())
      OR owner_user_id = auth.uid()
      OR current_user_role() IN ('transformation_office', 'tenant_admin')
    )
  );
CREATE POLICY "dashboard_layouts_insert" ON dashboard_layouts
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id()
    AND (
      (owner_type = 'user' AND owner_user_id = auth.uid())
      OR (owner_type = 'tenant' AND current_user_role() IN ('transformation_office', 'tenant_admin'))
    )
  );
CREATE POLICY "dashboard_layouts_update" ON dashboard_layouts
  FOR UPDATE USING (
    tenant_id = current_tenant_id()
    AND (
      (owner_type = 'user' AND owner_user_id = auth.uid())
      OR (owner_type = 'tenant' AND current_user_role() IN ('transformation_office', 'tenant_admin'))
    )
  ) WITH CHECK (
    tenant_id = current_tenant_id()
    AND (
      (owner_type = 'user' AND owner_user_id = auth.uid())
      OR (owner_type = 'tenant' AND current_user_role() IN ('transformation_office', 'tenant_admin'))
    )
  );
CREATE POLICY "dashboard_layouts_delete" ON dashboard_layouts
  FOR DELETE USING (
    tenant_id = current_tenant_id()
    AND (
      (owner_type = 'user' AND owner_user_id = auth.uid())
      OR (owner_type = 'tenant' AND current_user_role() IN ('transformation_office', 'tenant_admin'))
    )
  );

COMMIT;
