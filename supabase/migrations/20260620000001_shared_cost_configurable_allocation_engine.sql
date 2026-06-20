-- Shared Costs configurable allocation engine.
-- The existing shared_cost_* tables remain the canonical ledger. This migration
-- promotes them from legacy JSON rules into engine-backed pools, policy
-- versions, structured targets/weights, preview/lock status, and report
-- settings.

CREATE UNIQUE INDEX IF NOT EXISTS financial_scenarios_tenant_id_id_uidx
  ON financial_scenarios(tenant_id, id);

ALTER TABLE shared_cost_pools
  ADD COLUMN IF NOT EXISTS cost_category_id UUID,
  ADD COLUMN IF NOT EXISTS scenario_id UUID,
  ADD COLUMN IF NOT EXISTS period_grain TEXT NOT NULL DEFAULT 'annual',
  ADD COLUMN IF NOT EXISTS reporting_treatment TEXT NOT NULL DEFAULT 'report_only',
  ADD COLUMN IF NOT EXISTS currency_code TEXT NOT NULL DEFAULT 'USD',
  ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS locked_by UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE shared_cost_pools
  DROP CONSTRAINT IF EXISTS shared_cost_pools_period_grain_check,
  DROP CONSTRAINT IF EXISTS shared_cost_pools_reporting_treatment_check,
  DROP CONSTRAINT IF EXISTS shared_cost_pools_cost_category_tenant_fk,
  DROP CONSTRAINT IF EXISTS shared_cost_pools_scenario_tenant_fk;

ALTER TABLE shared_cost_pools
  ADD CONSTRAINT shared_cost_pools_period_grain_check
    CHECK (period_grain IN ('annual','quarterly','monthly')),
  ADD CONSTRAINT shared_cost_pools_reporting_treatment_check
    CHECK (reporting_treatment IN ('report_only','post_cost_lines','report_and_post'));

UPDATE shared_cost_pools pool
SET cost_category_id = cat.id
FROM financial_cost_categories cat
WHERE cat.tenant_id = pool.tenant_id
  AND cat.key = COALESCE(NULLIF(pool.category_key, ''), 'other')
  AND pool.cost_category_id IS NULL;

UPDATE shared_cost_pools pool
SET scenario_id = scenario.id
FROM financial_scenarios scenario
WHERE scenario.tenant_id = pool.tenant_id
  AND scenario.kind = 'plan'
  AND scenario.is_primary
  AND scenario.is_active
  AND pool.scenario_id IS NULL;

UPDATE shared_cost_pools pool
SET scenario_id = scenario.id
FROM financial_scenarios scenario
WHERE scenario.tenant_id = pool.tenant_id
  AND scenario.kind = 'plan'
  AND scenario.is_active
  AND pool.scenario_id IS NULL;

ALTER TABLE shared_cost_pools
  ADD CONSTRAINT shared_cost_pools_cost_category_tenant_fk
    FOREIGN KEY (tenant_id, cost_category_id)
    REFERENCES financial_cost_categories(tenant_id, id)
    ON DELETE SET NULL (cost_category_id),
  ADD CONSTRAINT shared_cost_pools_scenario_tenant_fk
    FOREIGN KEY (tenant_id, scenario_id)
    REFERENCES financial_scenarios(tenant_id, id)
    ON DELETE SET NULL (scenario_id);

CREATE INDEX IF NOT EXISTS shared_cost_pools_category_idx
  ON shared_cost_pools(tenant_id, cost_category_id, scenario_id, status);

ALTER TABLE shared_cost_allocation_rules
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS policy_status TEXT NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS driver_metric_definition_id UUID,
  ADD COLUMN IF NOT EXISTS driver_cost_category_id UUID,
  ADD COLUMN IF NOT EXISTS driver_scenario_id UUID,
  ADD COLUMN IF NOT EXISTS driver_period_mode TEXT NOT NULL DEFAULT 'pool_period',
  ADD COLUMN IF NOT EXISTS missing_basis_behavior TEXT NOT NULL DEFAULT 'fail',
  ADD COLUMN IF NOT EXISTS cap_floor_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS legacy_filters JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS legacy_weights JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE shared_cost_allocation_rules
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_rules_allocation_method_check,
  DROP CONSTRAINT IF EXISTS shared_cost_rules_policy_status_check,
  DROP CONSTRAINT IF EXISTS shared_cost_rules_driver_period_mode_check,
  DROP CONSTRAINT IF EXISTS shared_cost_rules_missing_basis_behavior_check,
  DROP CONSTRAINT IF EXISTS shared_cost_rules_metric_tenant_fk,
  DROP CONSTRAINT IF EXISTS shared_cost_rules_cost_category_tenant_fk,
  DROP CONSTRAINT IF EXISTS shared_cost_rules_scenario_tenant_fk;

ALTER TABLE shared_cost_allocation_rules
  ADD CONSTRAINT shared_cost_allocation_rules_allocation_method_check
    CHECK (allocation_method IN (
      'fixed_percentage',
      'equal_split',
      'manual_amount',
      'benefit_weighted',
      'revenue_weighted',
      'savings_weighted',
      'direct_cost_weighted',
      'headcount_weighted',
      'metric_weighted'
    )),
  ADD CONSTRAINT shared_cost_rules_policy_status_check
    CHECK (policy_status IN ('draft','active','locked','archived')),
  ADD CONSTRAINT shared_cost_rules_driver_period_mode_check
    CHECK (driver_period_mode IN ('pool_period','fiscal_year','trailing_12','custom')),
  ADD CONSTRAINT shared_cost_rules_missing_basis_behavior_check
    CHECK (missing_basis_behavior IN ('fail','zero','equal_split'));

UPDATE shared_cost_allocation_rules
SET legacy_filters = filters,
    legacy_weights = weights
WHERE legacy_filters = '{}'::jsonb
  AND legacy_weights = '{}'::jsonb;

ALTER TABLE shared_cost_allocation_rules
  ADD CONSTRAINT shared_cost_rules_metric_tenant_fk
    FOREIGN KEY (tenant_id, driver_metric_definition_id)
    REFERENCES financial_metric_definitions(tenant_id, id)
    ON DELETE SET NULL (driver_metric_definition_id),
  ADD CONSTRAINT shared_cost_rules_cost_category_tenant_fk
    FOREIGN KEY (tenant_id, driver_cost_category_id)
    REFERENCES financial_cost_categories(tenant_id, id)
    ON DELETE SET NULL (driver_cost_category_id),
  ADD CONSTRAINT shared_cost_rules_scenario_tenant_fk
    FOREIGN KEY (tenant_id, driver_scenario_id)
    REFERENCES financial_scenarios(tenant_id, id)
    ON DELETE SET NULL (driver_scenario_id);

CREATE INDEX IF NOT EXISTS shared_cost_rules_driver_idx
  ON shared_cost_allocation_rules(tenant_id, allocation_method, driver_metric_definition_id, driver_cost_category_id);

ALTER TABLE shared_cost_allocation_runs
  ADD COLUMN IF NOT EXISTS run_type TEXT NOT NULL DEFAULT 'posting',
  ADD COLUMN IF NOT EXISTS scenario_id UUID,
  ADD COLUMN IF NOT EXISTS period_start DATE,
  ADD COLUMN IF NOT EXISTS period_end DATE,
  ADD COLUMN IF NOT EXISTS rule_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS input_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS exception_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS locked_by UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS void_reason TEXT,
  ADD COLUMN IF NOT EXISTS reporting_treatment TEXT NOT NULL DEFAULT 'report_only';

ALTER TABLE shared_cost_allocation_runs
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_runs_status_check,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_runs_scenario_check,
  DROP CONSTRAINT IF EXISTS shared_cost_runs_run_type_check,
  DROP CONSTRAINT IF EXISTS shared_cost_runs_reporting_treatment_check,
  DROP CONSTRAINT IF EXISTS shared_cost_runs_scenario_tenant_fk;

ALTER TABLE shared_cost_allocation_runs
  ADD CONSTRAINT shared_cost_allocation_runs_status_check
    CHECK (status IN ('preview','approved','locked','posted','completed','voided')),
  ADD CONSTRAINT shared_cost_allocation_runs_scenario_check
    CHECK (scenario IN ('plan','actual','forecast','baseline')),
  ADD CONSTRAINT shared_cost_runs_run_type_check
    CHECK (run_type IN ('preview','posting')),
  ADD CONSTRAINT shared_cost_runs_reporting_treatment_check
    CHECK (reporting_treatment IN ('report_only','post_cost_lines','report_and_post'));

UPDATE shared_cost_allocation_runs run
SET scenario_id = pool.scenario_id,
    period_start = make_date(pool.year, COALESCE(pool.month, ((COALESCE(pool.quarter, 1) - 1) * 3) + 1), 1),
    period_end = (
      make_date(
        pool.year,
        CASE
          WHEN pool.month IS NOT NULL THEN pool.month
          WHEN pool.quarter IS NOT NULL THEN pool.quarter * 3
          ELSE 12
        END,
        1
      ) + interval '1 month - 1 day'
    )::date,
    reporting_treatment = pool.reporting_treatment,
    locked_at = COALESCE(run.locked_at, run.created_at),
    approved_at = COALESCE(run.approved_at, run.created_at),
    rule_version = COALESCE(rule.version, 1)
FROM shared_cost_pools pool
JOIN shared_cost_allocation_rules rule
  ON rule.pool_id = pool.id
WHERE pool.id = run.pool_id
  AND rule.id = run.rule_id;

ALTER TABLE shared_cost_allocation_runs
  ADD CONSTRAINT shared_cost_runs_scenario_tenant_fk
    FOREIGN KEY (tenant_id, scenario_id)
    REFERENCES financial_scenarios(tenant_id, id)
    ON DELETE SET NULL (scenario_id);

CREATE INDEX IF NOT EXISTS shared_cost_runs_status_period_idx
  ON shared_cost_allocation_runs(tenant_id, status, scenario_id, period_start, period_end);

ALTER TABLE shared_cost_allocations
  ADD COLUMN IF NOT EXISTS period_start DATE,
  ADD COLUMN IF NOT EXISTS period_end DATE,
  ADD COLUMN IF NOT EXISTS scenario_id UUID,
  ADD COLUMN IF NOT EXISTS basis_metric_definition_id UUID,
  ADD COLUMN IF NOT EXISTS basis_label TEXT,
  ADD COLUMN IF NOT EXISTS allocation_share NUMERIC(15,8) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rounding_adjustment NUMERIC(15,4) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS explanation TEXT,
  ADD COLUMN IF NOT EXISTS posted_cost_line_id UUID REFERENCES financial_cost_lines(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS exception_flags JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE shared_cost_allocations
  DROP CONSTRAINT IF EXISTS shared_cost_allocations_scenario_tenant_fk,
  DROP CONSTRAINT IF EXISTS shared_cost_allocations_metric_tenant_fk;

UPDATE shared_cost_allocations allocation
SET scenario_id = run.scenario_id,
    period_start = run.period_start,
    period_end = run.period_end,
    allocation_share = CASE
      WHEN COALESCE(run.total_amount_plan, 0) = 0 THEN 0
      ELSE ROUND((allocation.allocated_plan / run.total_amount_plan)::numeric, 8)
    END,
    basis_label = COALESCE(allocation.basis_label, allocation.allocation_basis)
FROM shared_cost_allocation_runs run
WHERE run.id = allocation.run_id;

ALTER TABLE shared_cost_allocations
  ADD CONSTRAINT shared_cost_allocations_scenario_tenant_fk
    FOREIGN KEY (tenant_id, scenario_id)
    REFERENCES financial_scenarios(tenant_id, id)
    ON DELETE SET NULL (scenario_id),
  ADD CONSTRAINT shared_cost_allocations_metric_tenant_fk
    FOREIGN KEY (tenant_id, basis_metric_definition_id)
    REFERENCES financial_metric_definitions(tenant_id, id)
    ON DELETE SET NULL (basis_metric_definition_id);

CREATE INDEX IF NOT EXISTS shared_cost_allocations_period_idx
  ON shared_cost_allocations(tenant_id, scenario_id, period_start, period_end);

CREATE TABLE IF NOT EXISTS shared_cost_pool_periods (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  pool_id             UUID NOT NULL REFERENCES shared_cost_pools(id) ON DELETE CASCADE,
  scenario_id         UUID REFERENCES financial_scenarios(id) ON DELETE SET NULL,
  year                INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2060),
  quarter             INTEGER CHECK (quarter BETWEEN 1 AND 4),
  month               INTEGER CHECK (month BETWEEN 1 AND 12),
  period_start        DATE NOT NULL,
  period_end          DATE NOT NULL,
  amount_plan         NUMERIC(15,4) NOT NULL DEFAULT 0,
  amount_actual       NUMERIC(15,4),
  status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','locked','archived')),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE NULLS NOT DISTINCT (tenant_id, pool_id, scenario_id, year, quarter, month)
);

CREATE INDEX IF NOT EXISTS shared_cost_pool_periods_tenant_idx
  ON shared_cost_pool_periods(tenant_id, pool_id, scenario_id, year, month);

ALTER TABLE shared_cost_pool_periods ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scpp_select" ON shared_cost_pool_periods;
DROP POLICY IF EXISTS "scpp_insert" ON shared_cost_pool_periods;
DROP POLICY IF EXISTS "scpp_update" ON shared_cost_pool_periods;
DROP POLICY IF EXISTS "scpp_delete" ON shared_cost_pool_periods;
CREATE POLICY "scpp_select" ON shared_cost_pool_periods FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scpp_insert" ON shared_cost_pool_periods FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scpp_update" ON shared_cost_pool_periods FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scpp_delete" ON shared_cost_pool_periods FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

INSERT INTO shared_cost_pool_periods (
  tenant_id,
  pool_id,
  scenario_id,
  year,
  quarter,
  month,
  period_start,
  period_end,
  amount_plan,
  amount_actual,
  status
)
SELECT
  pool.tenant_id,
  pool.id,
  pool.scenario_id,
  pool.year,
  pool.quarter,
  pool.month,
  make_date(pool.year, COALESCE(pool.month, ((COALESCE(pool.quarter, 1) - 1) * 3) + 1), 1),
  (
    make_date(
      pool.year,
      CASE
        WHEN pool.month IS NOT NULL THEN pool.month
        WHEN pool.quarter IS NOT NULL THEN pool.quarter * 3
        ELSE 12
      END,
      1
    ) + interval '1 month - 1 day'
  )::date,
  pool.amount_plan,
  pool.amount_actual,
  CASE WHEN pool.status = 'archived' THEN 'archived' ELSE 'active' END
FROM shared_cost_pools pool
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS shared_cost_allocation_targets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  rule_id         UUID NOT NULL REFERENCES shared_cost_allocation_rules(id) ON DELETE CASCADE,
  target_mode     TEXT NOT NULL DEFAULT 'include' CHECK (target_mode IN ('include','exclude')),
  dimension_type  TEXT NOT NULL CHECK (dimension_type IN (
    'all','initiative','workstream','business_unit','tag','country','stage','owner','rag_status'
  )),
  dimension_value TEXT,
  label           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS shared_cost_targets_rule_idx
  ON shared_cost_allocation_targets(tenant_id, rule_id, target_mode, dimension_type);

ALTER TABLE shared_cost_allocation_targets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scat_select" ON shared_cost_allocation_targets;
DROP POLICY IF EXISTS "scat_insert" ON shared_cost_allocation_targets;
DROP POLICY IF EXISTS "scat_update" ON shared_cost_allocation_targets;
DROP POLICY IF EXISTS "scat_delete" ON shared_cost_allocation_targets;
CREATE POLICY "scat_select" ON shared_cost_allocation_targets FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scat_insert" ON shared_cost_allocation_targets FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scat_update" ON shared_cost_allocation_targets FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scat_delete" ON shared_cost_allocation_targets FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

INSERT INTO shared_cost_allocation_targets (tenant_id, rule_id, target_mode, dimension_type, label)
SELECT tenant_id, id, 'include', 'all', 'All active initiatives'
FROM shared_cost_allocation_rules
WHERE filters = '{}'::jsonb
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS shared_cost_allocation_weights (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  rule_id         UUID NOT NULL REFERENCES shared_cost_allocation_rules(id) ON DELETE CASCADE,
  initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
  dimension_type  TEXT CHECK (dimension_type IN (
    'initiative','workstream','business_unit','tag','country','stage','owner','rag_status'
  )),
  dimension_value TEXT,
  weight_value    NUMERIC(15,4),
  percentage      NUMERIC(9,4),
  manual_amount   NUMERIC(15,4),
  label           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS shared_cost_weights_rule_idx
  ON shared_cost_allocation_weights(tenant_id, rule_id, initiative_id);

ALTER TABLE shared_cost_allocation_weights ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scaw_select" ON shared_cost_allocation_weights;
DROP POLICY IF EXISTS "scaw_insert" ON shared_cost_allocation_weights;
DROP POLICY IF EXISTS "scaw_update" ON shared_cost_allocation_weights;
DROP POLICY IF EXISTS "scaw_delete" ON shared_cost_allocation_weights;
CREATE POLICY "scaw_select" ON shared_cost_allocation_weights FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scaw_insert" ON shared_cost_allocation_weights FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scaw_update" ON shared_cost_allocation_weights FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scaw_delete" ON shared_cost_allocation_weights FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS shared_cost_reporting_settings (
  tenant_id                             UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  include_in_executive_control_tower    BOOLEAN NOT NULL DEFAULT TRUE,
  include_in_dashboard_executive_brief  BOOLEAN NOT NULL DEFAULT TRUE,
  include_in_portfolio_financials       BOOLEAN NOT NULL DEFAULT FALSE,
  include_in_initiative_financials      BOOLEAN NOT NULL DEFAULT TRUE,
  include_in_bankable_plan              BOOLEAN NOT NULL DEFAULT FALSE,
  posting_mode                          TEXT NOT NULL DEFAULT 'report_only'
                                         CHECK (posting_mode IN ('report_only','post_cost_lines','report_and_post')),
  created_at                            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE shared_cost_reporting_settings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scrs_select" ON shared_cost_reporting_settings;
DROP POLICY IF EXISTS "scrs_insert" ON shared_cost_reporting_settings;
DROP POLICY IF EXISTS "scrs_update" ON shared_cost_reporting_settings;
CREATE POLICY "scrs_select" ON shared_cost_reporting_settings FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scrs_insert" ON shared_cost_reporting_settings FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scrs_update" ON shared_cost_reporting_settings FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

INSERT INTO shared_cost_reporting_settings (tenant_id)
SELECT id FROM organizations
ON CONFLICT (tenant_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS shared_cost_allocation_exceptions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  run_id          UUID REFERENCES shared_cost_allocation_runs(id) ON DELETE CASCADE,
  rule_id         UUID REFERENCES shared_cost_allocation_rules(id) ON DELETE CASCADE,
  pool_id         UUID REFERENCES shared_cost_pools(id) ON DELETE CASCADE,
  initiative_id   UUID REFERENCES initiatives(id) ON DELETE CASCADE,
  exception_type  TEXT NOT NULL,
  severity        TEXT NOT NULL DEFAULT 'warning' CHECK (severity IN ('info','warning','blocking')),
  message         TEXT NOT NULL,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS shared_cost_exceptions_run_idx
  ON shared_cost_allocation_exceptions(tenant_id, run_id, severity);

ALTER TABLE shared_cost_allocation_exceptions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scae_select" ON shared_cost_allocation_exceptions;
DROP POLICY IF EXISTS "scae_insert" ON shared_cost_allocation_exceptions;
DROP POLICY IF EXISTS "scae_delete" ON shared_cost_allocation_exceptions;
CREATE POLICY "scae_select" ON shared_cost_allocation_exceptions FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scae_insert" ON shared_cost_allocation_exceptions FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scae_delete" ON shared_cost_allocation_exceptions FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS shared_cost_allocation_audit_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  pool_id         UUID REFERENCES shared_cost_pools(id) ON DELETE CASCADE,
  rule_id         UUID REFERENCES shared_cost_allocation_rules(id) ON DELETE CASCADE,
  run_id          UUID REFERENCES shared_cost_allocation_runs(id) ON DELETE CASCADE,
  actor_id        UUID REFERENCES users(id),
  event_type      TEXT NOT NULL,
  message         TEXT,
  before_state    JSONB,
  after_state     JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS shared_cost_audit_events_idx
  ON shared_cost_allocation_audit_events(tenant_id, pool_id, rule_id, run_id, created_at DESC);

ALTER TABLE shared_cost_allocation_audit_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scaa_select" ON shared_cost_allocation_audit_events;
DROP POLICY IF EXISTS "scaa_insert" ON shared_cost_allocation_audit_events;
CREATE POLICY "scaa_select" ON shared_cost_allocation_audit_events FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scaa_insert" ON shared_cost_allocation_audit_events FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
