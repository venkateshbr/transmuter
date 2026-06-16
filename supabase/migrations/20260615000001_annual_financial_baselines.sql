-- Annual tenant and initiative baseline metrics for transformation proof.

BEGIN;

CREATE TABLE IF NOT EXISTS financial_tenant_annual_baselines (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  metric_definition_id UUID NOT NULL REFERENCES financial_metric_definitions(id) ON DELETE CASCADE,
  baseline_year        INTEGER NOT NULL CHECK (baseline_year BETWEEN 2020 AND 2060),
  value                NUMERIC(15,4) NOT NULL DEFAULT 0,
  note                 TEXT,
  created_by           UUID REFERENCES users(id),
  updated_by           UUID REFERENCES users(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, metric_definition_id, baseline_year)
);

CREATE INDEX IF NOT EXISTS financial_tenant_annual_baselines_lookup_idx
  ON financial_tenant_annual_baselines(tenant_id, baseline_year, metric_definition_id);

ALTER TABLE financial_tenant_annual_baselines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ftab_select" ON financial_tenant_annual_baselines
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ftab_insert" ON financial_tenant_annual_baselines
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "ftab_update" ON financial_tenant_annual_baselines
  FOR UPDATE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  ) WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "ftab_delete" ON financial_tenant_annual_baselines
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

CREATE TABLE IF NOT EXISTS financial_initiative_annual_baselines (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  initiative_id        UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  metric_definition_id UUID NOT NULL REFERENCES financial_metric_definitions(id) ON DELETE CASCADE,
  baseline_year        INTEGER NOT NULL CHECK (baseline_year BETWEEN 2020 AND 2060),
  value                NUMERIC(15,4) NOT NULL DEFAULT 0,
  source               TEXT NOT NULL DEFAULT 'initiative'
                         CHECK (source IN ('tenant_default','initiative')),
  lock_gate_number     INTEGER CHECK (lock_gate_number BETWEEN 1 AND 10),
  locked_at            TIMESTAMPTZ,
  locked_by            UUID REFERENCES users(id),
  note                 TEXT,
  created_by           UUID REFERENCES users(id),
  updated_by           UUID REFERENCES users(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, initiative_id, metric_definition_id, baseline_year)
);

CREATE INDEX IF NOT EXISTS financial_initiative_annual_baselines_lookup_idx
  ON financial_initiative_annual_baselines(tenant_id, initiative_id, baseline_year, metric_definition_id);

ALTER TABLE financial_initiative_annual_baselines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "fiab_select" ON financial_initiative_annual_baselines
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fiab_insert" ON financial_initiative_annual_baselines
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "fiab_update" ON financial_initiative_annual_baselines
  FOR UPDATE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  ) WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );
CREATE POLICY "fiab_delete" ON financial_initiative_annual_baselines
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

UPDATE organizations
SET settings = jsonb_set(
  jsonb_set(
    COALESCE(settings, '{}'::jsonb),
    '{bankable_plan_governance,baseline_lock_gate_number}',
    COALESCE(settings #> '{bankable_plan_governance,baseline_lock_gate_number}', '2'::jsonb),
    TRUE
  ),
  '{bankable_plan_governance,baseline_lock_on_approval}',
  COALESCE(settings #> '{bankable_plan_governance,baseline_lock_on_approval}', 'true'::jsonb),
  TRUE
)
WHERE settings IS NULL
   OR settings #> '{bankable_plan_governance,baseline_lock_gate_number}' IS NULL
   OR settings #> '{bankable_plan_governance,baseline_lock_on_approval}' IS NULL;

COMMIT;
