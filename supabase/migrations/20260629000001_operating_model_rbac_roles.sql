-- Expand launch RBAC into the Transformation Office operating model roles.

BEGIN;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users
  ADD CONSTRAINT users_role_check CHECK (
    role IN (
      'transformation_office',
      'tenant_admin',
      'pmo_lead',
      'finance_lead',
      'workstream_lead',
      'initiative_owner',
      'business_benefit_owner',
      'executive_sponsor',
      'viewer'
    )
  );

ALTER TABLE user_invites DROP CONSTRAINT IF EXISTS user_invites_role_check;
ALTER TABLE user_invites
  ADD CONSTRAINT user_invites_role_check CHECK (
    role IN (
      'transformation_office',
      'tenant_admin',
      'pmo_lead',
      'finance_lead',
      'workstream_lead',
      'initiative_owner',
      'business_benefit_owner',
      'executive_sponsor',
      'viewer'
    )
  );

CREATE OR REPLACE FUNCTION app_can_manage_tenant_setup()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN ('transformation_office', 'tenant_admin')
$$;

CREATE OR REPLACE FUNCTION app_can_manage_governance()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN ('transformation_office', 'tenant_admin', 'pmo_lead')
$$;

CREATE OR REPLACE FUNCTION app_can_manage_financial_configuration()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN ('transformation_office', 'tenant_admin', 'finance_lead')
$$;

CREATE OR REPLACE FUNCTION app_can_manage_financials()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN ('transformation_office', 'finance_lead')
$$;

CREATE OR REPLACE FUNCTION app_can_validate_benefits()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN ('transformation_office', 'finance_lead')
$$;

CREATE OR REPLACE FUNCTION app_can_manage_benefit_realization()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN (
    'transformation_office',
    'finance_lead',
    'business_benefit_owner'
  )
$$;

CREATE OR REPLACE FUNCTION app_can_manage_shared_costs()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN ('transformation_office', 'finance_lead')
$$;

CREATE OR REPLACE FUNCTION app_can_manage_bankable_plans()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT current_user_role() IN ('transformation_office', 'finance_lead', 'pmo_lead')
$$;

CREATE OR REPLACE FUNCTION app_can_manage_initiative_financials(target_initiative_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT app_can_manage_financials()
    OR (
      current_user_role() = 'initiative_owner'
      AND EXISTS (
        SELECT 1
        FROM initiatives i
        WHERE i.tenant_id = current_tenant_id()
          AND i.id = target_initiative_id
          AND (i.owner_id = auth.uid() OR i.group_owner_id = auth.uid())
      )
    )
$$;

ALTER TABLE tenant_dashboard_config
  ALTER COLUMN allowed_roles SET DEFAULT ARRAY[
    'transformation_office',
    'tenant_admin',
    'pmo_lead',
    'finance_lead',
    'workstream_lead',
    'initiative_owner',
    'business_benefit_owner',
    'executive_sponsor',
    'viewer'
  ]::TEXT[];

UPDATE tenant_dashboard_config
SET allowed_roles = ARRAY(
  SELECT DISTINCT role_name
  FROM unnest(
    allowed_roles || ARRAY[
      'tenant_admin',
      'pmo_lead',
      'finance_lead',
      'workstream_lead',
      'business_benefit_owner',
      'executive_sponsor'
    ]::TEXT[]
  ) AS role_name(role_name)
  ORDER BY role_name
);

UPDATE organizations
SET settings = jsonb_set(
  COALESCE(settings, '{}'::jsonb),
  '{bankable_plan_governance,rebaseline_roles}',
  '["transformation_office","finance_lead","pmo_lead"]'::jsonb,
  true
)
WHERE settings #> '{bankable_plan_governance,rebaseline_roles}' IS NULL
   OR settings #> '{bankable_plan_governance,rebaseline_roles}' = '["transformation_office"]'::jsonb;

DROP POLICY IF EXISTS "tdc_insert" ON tenant_dashboard_config;
DROP POLICY IF EXISTS "tdc_update" ON tenant_dashboard_config;
DROP POLICY IF EXISTS "tdc_delete" ON tenant_dashboard_config;
CREATE POLICY "tdc_insert" ON tenant_dashboard_config
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_tenant_setup());
CREATE POLICY "tdc_update" ON tenant_dashboard_config
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_tenant_setup())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_tenant_setup());
CREATE POLICY "tdc_delete" ON tenant_dashboard_config
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_tenant_setup());

DROP POLICY IF EXISTS "gc_update" ON gate_criteria;
DROP POLICY IF EXISTS "gs_update" ON gate_submissions;
DROP POLICY IF EXISTS "sgd_insert" ON stage_gate_definitions;
DROP POLICY IF EXISTS "sgd_update" ON stage_gate_definitions;
DROP POLICY IF EXISTS "sgd_delete" ON stage_gate_definitions;
CREATE POLICY "gc_update" ON gate_criteria
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_governance())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_governance());
CREATE POLICY "gs_update" ON gate_submissions
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_governance())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_governance());
CREATE POLICY "sgd_insert" ON stage_gate_definitions
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_governance());
CREATE POLICY "sgd_update" ON stage_gate_definitions
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_governance())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_governance());
CREATE POLICY "sgd_delete" ON stage_gate_definitions
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_governance());

DROP POLICY IF EXISTS "fcg_insert" ON financial_config_groups;
DROP POLICY IF EXISTS "fcg_update" ON financial_config_groups;
DROP POLICY IF EXISTS "fcg_delete" ON financial_config_groups;
DROP POLICY IF EXISTS "fci_insert" ON financial_config_items;
DROP POLICY IF EXISTS "fci_update" ON financial_config_items;
DROP POLICY IF EXISTS "fci_delete" ON financial_config_items;
DROP POLICY IF EXISTS "fmd_insert" ON financial_metric_definitions;
DROP POLICY IF EXISTS "fmd_update" ON financial_metric_definitions;
DROP POLICY IF EXISTS "fmd_delete" ON financial_metric_definitions;
DROP POLICY IF EXISTS "fs_insert" ON financial_scenarios;
DROP POLICY IF EXISTS "fs_update" ON financial_scenarios;
DROP POLICY IF EXISTS "fs_delete" ON financial_scenarios;
DROP POLICY IF EXISTS "fcc_insert" ON financial_cost_categories;
DROP POLICY IF EXISTS "fcc_update" ON financial_cost_categories;
DROP POLICY IF EXISTS "fcc_delete" ON financial_cost_categories;
DROP POLICY IF EXISTS "fbr_insert" ON financial_bridge_rows;
DROP POLICY IF EXISTS "fbr_update" ON financial_bridge_rows;
DROP POLICY IF EXISTS "fbr_delete" ON financial_bridge_rows;
DROP POLICY IF EXISTS "fad_insert" ON financial_attribute_definitions;
DROP POLICY IF EXISTS "fad_update" ON financial_attribute_definitions;
DROP POLICY IF EXISTS "fad_delete" ON financial_attribute_definitions;
DROP POLICY IF EXISTS "ftab_insert" ON financial_tenant_annual_baselines;
DROP POLICY IF EXISTS "ftab_update" ON financial_tenant_annual_baselines;
DROP POLICY IF EXISTS "ftab_delete" ON financial_tenant_annual_baselines;

CREATE POLICY "fcg_insert" ON financial_config_groups
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fcg_update" ON financial_config_groups
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fcg_delete" ON financial_config_groups
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fci_insert" ON financial_config_items
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fci_update" ON financial_config_items
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fci_delete" ON financial_config_items
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fmd_insert" ON financial_metric_definitions
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fmd_update" ON financial_metric_definitions
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fmd_delete" ON financial_metric_definitions
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fs_insert" ON financial_scenarios
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fs_update" ON financial_scenarios
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fs_delete" ON financial_scenarios
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fcc_insert" ON financial_cost_categories
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fcc_update" ON financial_cost_categories
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fcc_delete" ON financial_cost_categories
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fbr_insert" ON financial_bridge_rows
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fbr_update" ON financial_bridge_rows
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fbr_delete" ON financial_bridge_rows
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fad_insert" ON financial_attribute_definitions
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fad_update" ON financial_attribute_definitions
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "fad_delete" ON financial_attribute_definitions
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "ftab_insert" ON financial_tenant_annual_baselines
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "ftab_update" ON financial_tenant_annual_baselines
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());
CREATE POLICY "ftab_delete" ON financial_tenant_annual_baselines
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_financial_configuration());

DROP POLICY IF EXISTS "fbl_insert" ON financial_benefit_lines;
DROP POLICY IF EXISTS "fbl_update" ON financial_benefit_lines;
DROP POLICY IF EXISTS "fbl_delete" ON financial_benefit_lines;
DROP POLICY IF EXISTS "fmv_insert" ON financial_metric_values;
DROP POLICY IF EXISTS "fmv_update" ON financial_metric_values;
DROP POLICY IF EXISTS "fmv_delete" ON financial_metric_values;
DROP POLICY IF EXISTS "fiab_insert" ON financial_initiative_annual_baselines;
DROP POLICY IF EXISTS "fiab_update" ON financial_initiative_annual_baselines;
DROP POLICY IF EXISTS "fiab_delete" ON financial_initiative_annual_baselines;
DROP POLICY IF EXISTS "ifs_insert" ON initiative_financial_selections;
DROP POLICY IF EXISTS "ifs_update" ON initiative_financial_selections;
DROP POLICY IF EXISTS "ifs_delete" ON initiative_financial_selections;
DROP POLICY IF EXISTS "ifs2_insert" ON initiative_financial_scope;
DROP POLICY IF EXISTS "ifs2_update" ON initiative_financial_scope;
DROP POLICY IF EXISTS "ifs2_delete" ON initiative_financial_scope;
DROP POLICY IF EXISTS "ff_insert" ON financial_forecasts;
DROP POLICY IF EXISTS "ff_update" ON financial_forecasts;
DROP POLICY IF EXISTS "ff_delete" ON financial_forecasts;
DROP POLICY IF EXISTS "bp_insert" ON bankable_plans;
DROP POLICY IF EXISTS "wtl_insert" ON workstream_target_locks;
DROP POLICY IF EXISTS "fca_insert" ON financial_cell_assumptions;
DROP POLICY IF EXISTS "fca_update" ON financial_cell_assumptions;
DROP POLICY IF EXISTS "fca_delete" ON financial_cell_assumptions;
DROP POLICY IF EXISTS "brl_insert" ON benefit_realization_ledger;
DROP POLICY IF EXISTS "brl_update" ON benefit_realization_ledger;
DROP POLICY IF EXISTS "brl_delete" ON benefit_realization_ledger;
DROP POLICY IF EXISTS "fblve_insert" ON financial_benefit_line_validation_events;

CREATE POLICY "fbl_insert" ON financial_benefit_lines
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fbl_update" ON financial_benefit_lines
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id))
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fbl_delete" ON financial_benefit_lines
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fmv_insert" ON financial_metric_values
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fmv_update" ON financial_metric_values
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id))
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fmv_delete" ON financial_metric_values
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fiab_insert" ON financial_initiative_annual_baselines
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fiab_update" ON financial_initiative_annual_baselines
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id))
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fiab_delete" ON financial_initiative_annual_baselines
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ifs_insert" ON initiative_financial_selections
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ifs_update" ON initiative_financial_selections
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id))
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ifs_delete" ON initiative_financial_selections
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ifs2_insert" ON initiative_financial_scope
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ifs2_update" ON initiative_financial_scope
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id))
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ifs2_delete" ON initiative_financial_scope
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ff_delete" ON financial_forecasts
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ff_insert" ON financial_forecasts
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "ff_update" ON financial_forecasts
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id))
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "bp_insert" ON bankable_plans
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_bankable_plans());
CREATE POLICY "wtl_insert" ON workstream_target_locks
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_financials());
CREATE POLICY "fca_insert" ON financial_cell_assumptions
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fca_update" ON financial_cell_assumptions
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id))
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "fca_delete" ON financial_cell_assumptions
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_initiative_financials(initiative_id));
CREATE POLICY "brl_insert" ON benefit_realization_ledger
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_benefit_realization());
CREATE POLICY "brl_update" ON benefit_realization_ledger
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_benefit_realization())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_benefit_realization());
CREATE POLICY "brl_delete" ON benefit_realization_ledger
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_benefit_realization());
CREATE POLICY "fblve_insert" ON financial_benefit_line_validation_events
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id()
    AND (
      app_can_validate_benefits()
      OR (
        event_type IN ('submit', 'handoff_update')
        AND app_can_manage_initiative_financials(initiative_id)
      )
    )
    AND EXISTS (
      SELECT 1
      FROM financial_benefit_lines line
      WHERE line.id = benefit_line_id
        AND line.tenant_id = current_tenant_id()
        AND line.initiative_id = financial_benefit_line_validation_events.initiative_id
    )
  );

DROP POLICY IF EXISTS "scp_insert" ON shared_cost_pools;
DROP POLICY IF EXISTS "scp_update" ON shared_cost_pools;
DROP POLICY IF EXISTS "scp_delete" ON shared_cost_pools;
DROP POLICY IF EXISTS "scpp_insert" ON shared_cost_pool_periods;
DROP POLICY IF EXISTS "scpp_update" ON shared_cost_pool_periods;
DROP POLICY IF EXISTS "scpp_delete" ON shared_cost_pool_periods;
DROP POLICY IF EXISTS "scar_insert" ON shared_cost_allocation_rules;
DROP POLICY IF EXISTS "scar_update" ON shared_cost_allocation_rules;
DROP POLICY IF EXISTS "scar_delete" ON shared_cost_allocation_rules;
DROP POLICY IF EXISTS "scat_insert" ON shared_cost_allocation_targets;
DROP POLICY IF EXISTS "scat_update" ON shared_cost_allocation_targets;
DROP POLICY IF EXISTS "scat_delete" ON shared_cost_allocation_targets;
DROP POLICY IF EXISTS "scaw_insert" ON shared_cost_allocation_weights;
DROP POLICY IF EXISTS "scaw_update" ON shared_cost_allocation_weights;
DROP POLICY IF EXISTS "scaw_delete" ON shared_cost_allocation_weights;
DROP POLICY IF EXISTS "scaruns_insert" ON shared_cost_allocation_runs;
DROP POLICY IF EXISTS "scaruns_update" ON shared_cost_allocation_runs;
DROP POLICY IF EXISTS "sca_insert" ON shared_cost_allocations;
DROP POLICY IF EXISTS "scrs_insert" ON shared_cost_reporting_settings;
DROP POLICY IF EXISTS "scrs_update" ON shared_cost_reporting_settings;
DROP POLICY IF EXISTS "scae_insert" ON shared_cost_allocation_exceptions;
DROP POLICY IF EXISTS "scae_delete" ON shared_cost_allocation_exceptions;
DROP POLICY IF EXISTS "scaa_insert" ON shared_cost_allocation_audit_events;

CREATE POLICY "scp_insert" ON shared_cost_pools
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scp_update" ON shared_cost_pools
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scp_delete" ON shared_cost_pools
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scpp_insert" ON shared_cost_pool_periods
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scpp_update" ON shared_cost_pool_periods
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scpp_delete" ON shared_cost_pool_periods
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scar_insert" ON shared_cost_allocation_rules
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scar_update" ON shared_cost_allocation_rules
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scar_delete" ON shared_cost_allocation_rules
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scat_insert" ON shared_cost_allocation_targets
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scat_update" ON shared_cost_allocation_targets
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scat_delete" ON shared_cost_allocation_targets
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scaw_insert" ON shared_cost_allocation_weights
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scaw_update" ON shared_cost_allocation_weights
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scaw_delete" ON shared_cost_allocation_weights
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scaruns_insert" ON shared_cost_allocation_runs
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scaruns_update" ON shared_cost_allocation_runs
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "sca_insert" ON shared_cost_allocations
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scrs_insert" ON shared_cost_reporting_settings
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scrs_update" ON shared_cost_reporting_settings
  FOR UPDATE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs())
  WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scae_insert" ON shared_cost_allocation_exceptions
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scae_delete" ON shared_cost_allocation_exceptions
  FOR DELETE USING (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());
CREATE POLICY "scaa_insert" ON shared_cost_allocation_audit_events
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id() AND app_can_manage_shared_costs());

DROP POLICY IF EXISTS "ivrn_insert" ON initiative_value_realization_notes;
DROP POLICY IF EXISTS "ivrn_update" ON initiative_value_realization_notes;
DROP POLICY IF EXISTS "ivrn_delete" ON initiative_value_realization_notes;
CREATE POLICY "ivrn_insert" ON initiative_value_realization_notes
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id()
    AND (
      current_user_role() IN ('transformation_office', 'finance_lead', 'business_benefit_owner')
      OR (current_user_role() = 'initiative_owner' AND author_id = auth.uid())
    )
  );
CREATE POLICY "ivrn_update" ON initiative_value_realization_notes
  FOR UPDATE USING (
    tenant_id = current_tenant_id()
    AND current_user_role() IN ('transformation_office', 'finance_lead', 'business_benefit_owner')
  ) WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() IN ('transformation_office', 'finance_lead', 'business_benefit_owner')
  );
CREATE POLICY "ivrn_delete" ON initiative_value_realization_notes
  FOR DELETE USING (
    tenant_id = current_tenant_id()
    AND current_user_role() IN ('transformation_office', 'finance_lead', 'business_benefit_owner')
  );

COMMIT;
