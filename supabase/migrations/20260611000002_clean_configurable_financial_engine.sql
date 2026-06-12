-- Clean configurable financial metric engine.
-- Destructive refactor baseline: current portfolio/financial data is reloadable
-- from Initiative_Portfolio_Anonymised.xlsx after this model is adopted.

BEGIN;

SET LOCAL search_path = transmuter, public, extensions;

-- Existing financial rows are not preserved; the workbook reload is canonical.
TRUNCATE TABLE
  financial_cell_assumptions,
  financial_forecasts,
  benefit_realization_ledger,
  bankable_plans,
  workstream_target_locks,
  initiative_financial_selections,
  financial_metric_values,
  financial_cost_lines,
  financial_entries
RESTART IDENTITY CASCADE;

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS fiscal_year_start_month SMALLINT NOT NULL DEFAULT 1
    CHECK (fiscal_year_start_month BETWEEN 1 AND 12),
  ADD COLUMN IF NOT EXISTS reporting_currency TEXT NOT NULL DEFAULT 'USD';

ALTER TABLE bankable_plans
  ADD COLUMN IF NOT EXISTS snapshot_schema_version SMALLINT NOT NULL DEFAULT 1;

ALTER TABLE initiatives
  ADD COLUMN IF NOT EXISTS context_problem TEXT;

ALTER TABLE initiatives
  DROP CONSTRAINT IF EXISTS initiatives_stage_check;

ALTER TABLE stage_gates
  DROP CONSTRAINT IF EXISTS stage_gates_gate_number_check,
  ADD CONSTRAINT stage_gates_gate_number_check CHECK (gate_number BETWEEN 1 AND 10);

ALTER TABLE gate_criteria
  DROP CONSTRAINT IF EXISTS gate_criteria_gate_number_check,
  ADD CONSTRAINT gate_criteria_gate_number_check CHECK (gate_number BETWEEN 1 AND 10);

ALTER TABLE workstreams
  ADD COLUMN IF NOT EXISTS lead_user_id UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS sponsor_user_id UUID REFERENCES users(id);

CREATE TABLE IF NOT EXISTS initiative_business_units (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  initiative_id    UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  business_unit_id UUID NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (initiative_id, business_unit_id)
);

CREATE INDEX IF NOT EXISTS initiative_business_units_tenant_idx
  ON initiative_business_units(tenant_id, initiative_id);

ALTER TABLE initiative_business_units ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "ibu_select" ON initiative_business_units;
DROP POLICY IF EXISTS "ibu_insert" ON initiative_business_units;
DROP POLICY IF EXISTS "ibu_update" ON initiative_business_units;
DROP POLICY IF EXISTS "ibu_delete" ON initiative_business_units;
CREATE POLICY "ibu_select" ON initiative_business_units FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ibu_insert" ON initiative_business_units FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "ibu_update" ON initiative_business_units FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "ibu_delete" ON initiative_business_units FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS stage_gate_definitions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  gate_number  INTEGER NOT NULL CHECK (gate_number BETWEEN 1 AND 10),
  key          TEXT NOT NULL,
  label        TEXT NOT NULL,
  from_stage   TEXT NOT NULL,
  to_stage     TEXT NOT NULL,
  description  TEXT,
  approval_required  BOOLEAN NOT NULL DEFAULT TRUE,
  approver_roles     TEXT[] NOT NULL DEFAULT ARRAY['transformation_office']::TEXT[],
  require_all_criteria BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order   INTEGER NOT NULL DEFAULT 0,
  is_system    BOOLEAN NOT NULL DEFAULT FALSE,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, gate_number),
  UNIQUE (tenant_id, key)
);

CREATE INDEX IF NOT EXISTS stage_gate_definitions_tenant_idx
  ON stage_gate_definitions(tenant_id, gate_number);

ALTER TABLE stage_gate_definitions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "sgd_select" ON stage_gate_definitions;
DROP POLICY IF EXISTS "sgd_insert" ON stage_gate_definitions;
DROP POLICY IF EXISTS "sgd_update" ON stage_gate_definitions;
DROP POLICY IF EXISTS "sgd_delete" ON stage_gate_definitions;
CREATE POLICY "sgd_select" ON stage_gate_definitions FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "sgd_insert" ON stage_gate_definitions FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "sgd_update" ON stage_gate_definitions FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "sgd_delete" ON stage_gate_definitions FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

-- Existing custom metric table shape is replaced by the new primary value store.
DROP TABLE IF EXISTS financial_metric_values CASCADE;
DROP TABLE IF EXISTS financial_entries CASCADE;

CREATE TABLE financial_metric_definitions (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  key            TEXT NOT NULL,
  label          TEXT NOT NULL,
  description    TEXT,
  group_key      TEXT,
  value_type     TEXT NOT NULL CHECK (value_type IN ('currency','percent','number')),
  unit           TEXT,
  direction      TEXT NOT NULL DEFAULT 'increase_good'
                   CHECK (direction IN ('increase_good','decrease_good','neutral')),
  aggregation    TEXT NOT NULL DEFAULT 'sum'
                   CHECK (aggregation IN ('sum','avg','last','formula')),
  rollup_type    TEXT CHECK (rollup_type IN ('benefit','recurring_cost','one_off_cost','total_cost','net_value')),
  is_benefit     BOOLEAN NOT NULL DEFAULT FALSE,
  benefit_class  TEXT CHECK (benefit_class IN ('savings','avoidance','revenue','margin','other')),
  cost_behavior  TEXT CHECK (cost_behavior IN ('recurring','one_time')),
  formula        TEXT,
  formula_inputs TEXT[] NOT NULL DEFAULT '{}',
  precision      SMALLINT NOT NULL DEFAULT 4 CHECK (precision BETWEEN 0 AND 8),
  display_order  INTEGER NOT NULL DEFAULT 0,
  applies_to     TEXT NOT NULL DEFAULT 'opt_in' CHECK (applies_to IN ('all','opt_in')),
  validation     JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_system      BOOLEAN NOT NULL DEFAULT FALSE,
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_by     UUID REFERENCES users(id),
  updated_by     UUID REFERENCES users(id),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, key)
);

CREATE INDEX financial_metric_definitions_tenant_idx
  ON financial_metric_definitions(tenant_id, is_active, display_order);

ALTER TABLE financial_metric_definitions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "fmd_select" ON financial_metric_definitions FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fmd_insert" ON financial_metric_definitions FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fmd_update" ON financial_metric_definitions FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fmd_delete" ON financial_metric_definitions FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

CREATE TABLE financial_scenarios (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  key           TEXT NOT NULL,
  label         TEXT NOT NULL,
  kind          TEXT NOT NULL CHECK (kind IN ('baseline','plan','forecast','actual')),
  is_primary    BOOLEAN NOT NULL DEFAULT FALSE,
  is_system     BOOLEAN NOT NULL DEFAULT FALSE,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, key)
);

CREATE UNIQUE INDEX financial_scenarios_one_actual
  ON financial_scenarios(tenant_id)
  WHERE kind = 'actual' AND is_active;
CREATE UNIQUE INDEX financial_scenarios_one_primary_plan
  ON financial_scenarios(tenant_id)
  WHERE kind = 'plan' AND is_primary AND is_active;

ALTER TABLE financial_scenarios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "fs_select" ON financial_scenarios FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fs_insert" ON financial_scenarios FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fs_update" ON financial_scenarios FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fs_delete" ON financial_scenarios FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

CREATE TABLE financial_benefit_lines (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  initiative_id        UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  metric_definition_id UUID NOT NULL REFERENCES financial_metric_definitions(id),
  name                 TEXT NOT NULL,
  description          TEXT,
  impact_type          TEXT CHECK (impact_type IN ('recurring','one_time')),
  timing               TEXT,
  confidence           NUMERIC(5,2) CHECK (confidence >= 0 AND confidence <= 100),
  phasing              JSONB NOT NULL DEFAULT '{}'::jsonb,
  attributes           JSONB NOT NULL DEFAULT '{}'::jsonb,
  show_in_summary      BOOLEAN NOT NULL DEFAULT TRUE,
  display_order        INTEGER NOT NULL DEFAULT 0,
  created_by           UUID REFERENCES users(id),
  updated_by           UUID REFERENCES users(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX financial_benefit_lines_initiative_idx
  ON financial_benefit_lines(tenant_id, initiative_id, display_order);

ALTER TABLE financial_benefit_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "fbl_select" ON financial_benefit_lines FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fbl_insert" ON financial_benefit_lines FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fbl_update" ON financial_benefit_lines FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fbl_delete" ON financial_benefit_lines FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

ALTER TABLE financial_cost_lines
  ADD COLUMN IF NOT EXISTS phasing JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id);

CREATE TABLE financial_metric_values (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  initiative_id        UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  metric_definition_id UUID NOT NULL REFERENCES financial_metric_definitions(id),
  benefit_line_id      UUID REFERENCES financial_benefit_lines(id) ON DELETE CASCADE,
  scenario_id          UUID NOT NULL REFERENCES financial_scenarios(id),
  year                 INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2060),
  month                SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
  value                NUMERIC(15,4) NOT NULL DEFAULT 0,
  status               TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','approved')),
  note                 TEXT,
  created_by           UUID REFERENCES users(id),
  updated_by           UUID REFERENCES users(id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE NULLS NOT DISTINCT (
    initiative_id,
    metric_definition_id,
    benefit_line_id,
    scenario_id,
    year,
    month
  )
);

CREATE INDEX financial_metric_values_lookup_idx
  ON financial_metric_values(tenant_id, initiative_id, metric_definition_id, scenario_id, year, month);
CREATE INDEX financial_metric_values_benefit_line_idx
  ON financial_metric_values(tenant_id, benefit_line_id);

ALTER TABLE financial_metric_values ENABLE ROW LEVEL SECURITY;
CREATE POLICY "fmv_select" ON financial_metric_values FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fmv_insert" ON financial_metric_values FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fmv_update" ON financial_metric_values FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fmv_delete" ON financial_metric_values FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

CREATE TABLE financial_bridge_rows (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  key                   TEXT NOT NULL,
  label                 TEXT NOT NULL,
  row_kind              TEXT NOT NULL CHECK (row_kind IN ('metric_set','cost_set','subtotal','net')),
  metric_definition_ids UUID[] NOT NULL DEFAULT '{}',
  cost_category_keys    TEXT[] NOT NULL DEFAULT '{}',
  sign                  SMALLINT NOT NULL DEFAULT 1 CHECK (sign IN (-1, 1)),
  display_order         INTEGER NOT NULL DEFAULT 0,
  is_active             BOOLEAN NOT NULL DEFAULT TRUE,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, key)
);

CREATE INDEX financial_bridge_rows_tenant_idx
  ON financial_bridge_rows(tenant_id, display_order);

ALTER TABLE financial_bridge_rows ENABLE ROW LEVEL SECURITY;
CREATE POLICY "fbr_select" ON financial_bridge_rows FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fbr_insert" ON financial_bridge_rows FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fbr_update" ON financial_bridge_rows FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);
CREATE POLICY "fbr_delete" ON financial_bridge_rows FOR DELETE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);

-- Seed default scenarios and five-gate model for all existing tenants.
INSERT INTO financial_scenarios (tenant_id, key, label, kind, is_primary, is_system, display_order)
SELECT org.id, item.key, item.label, item.kind, item.is_primary, TRUE, item.display_order
FROM organizations org
CROSS JOIN (
  VALUES
    ('baseline', 'Baseline', 'baseline', FALSE, 0),
    ('plan_base', 'Plan Base', 'plan', TRUE, 10),
    ('plan_high', 'Plan High', 'plan', FALSE, 20),
    ('actual', 'Actual', 'actual', FALSE, 30)
) AS item(key, label, kind, is_primary, display_order)
ON CONFLICT (tenant_id, key) DO NOTHING;

INSERT INTO stage_gate_definitions (
  tenant_id, gate_number, key, label, from_stage, to_stage, description, sort_order, is_system
)
SELECT org.id, item.gate_number, item.key, item.label, item.from_stage, item.to_stage,
       item.description, item.sort_order, TRUE
FROM organizations org
CROSS JOIN (
  VALUES
    (1, 'g1_identify_validate', 'Gate 1: Identify to Validate', 'identified', 'validated', 'Initial opportunity is qualified.', 10),
    (2, 'g2_validate_plan', 'Gate 2: Validate to Plan', 'validated', 'planned', 'Business case is validated.', 20),
    (3, 'g3_plan_commit', 'Gate 3: Plan to Commit', 'planned', 'committed', 'Execution plan and bankable value are committed.', 30),
    (4, 'g4_commit_execute', 'Gate 4: Commit to Execute', 'committed', 'executing', 'Delivery is materially complete.', 40),
    (5, 'g5_execute_realize', 'Gate 5: Execute to Realized', 'executing', 'realized', 'Finance-recognized value is realized.', 50)
) AS item(gate_number, key, label, from_stage, to_stage, description, sort_order)
ON CONFLICT (tenant_id, gate_number) DO NOTHING;

ALTER TABLE stage_gate_definitions
  ADD COLUMN IF NOT EXISTS approval_required BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS approver_roles TEXT[] NOT NULL DEFAULT ARRAY['transformation_office']::TEXT[],
  ADD COLUMN IF NOT EXISTS require_all_criteria BOOLEAN NOT NULL DEFAULT TRUE;

-- Seed system metrics. Formula strings are validated by application code.
INSERT INTO financial_metric_definitions (
  tenant_id, key, label, group_key, value_type, unit, direction, aggregation,
  rollup_type, is_benefit, benefit_class, formula, formula_inputs,
  display_order, applies_to, validation, is_system
)
SELECT org.id, item.key, item.label, item.group_key, item.value_type, item.unit,
       item.direction, item.aggregation, item.rollup_type, item.is_benefit,
       item.benefit_class, item.formula, item.formula_inputs, item.display_order,
       item.applies_to, item.validation::jsonb, TRUE
FROM organizations org
CROSS JOIN (
  VALUES
    ('revenue_uplift', 'Revenue Uplift', 'revenue', 'currency', NULL, 'increase_good', 'sum', 'benefit', TRUE, 'revenue', NULL, ARRAY[]::TEXT[], 10, 'all', '{}'),
    ('gross_margin', 'Gross Margin', 'margin', 'currency', NULL, 'increase_good', 'sum', 'benefit', TRUE, 'margin', NULL, ARRAY[]::TEXT[], 20, 'all', '{}'),
    ('gm_uplift', 'Gross Margin Uplift', 'margin', 'currency', NULL, 'increase_good', 'sum', 'benefit', TRUE, 'margin', NULL, ARRAY[]::TEXT[], 30, 'all', '{}'),
    ('cogs', 'Cost of Goods Sold', 'cost', 'currency', NULL, 'decrease_good', 'sum', 'total_cost', FALSE, NULL, NULL, ARRAY[]::TEXT[], 40, 'opt_in', '{}'),
    ('cost_savings', 'Cost Savings', 'savings', 'currency', NULL, 'increase_good', 'sum', 'benefit', TRUE, 'savings', NULL, ARRAY[]::TEXT[], 50, 'opt_in', '{}'),
    ('baseline_revenue', 'Baseline Revenue', 'revenue', 'currency', NULL, 'neutral', 'last', NULL, FALSE, NULL, NULL, ARRAY[]::TEXT[], 55, 'opt_in', '{}'),
    ('revenue_uplift_pct', 'Revenue Uplift %', 'revenue', 'percent', '%', 'increase_good', 'formula', NULL, FALSE, NULL, 'revenue_uplift / baseline_revenue * 100', ARRAY['revenue_uplift','baseline_revenue']::TEXT[], 60, 'opt_in', '{"min":0}'),
    ('gm_pct', 'Gross Margin %', 'margin', 'percent', '%', 'increase_good', 'formula', NULL, FALSE, NULL, 'gross_margin / revenue_uplift * 100', ARRAY['gross_margin','revenue_uplift']::TEXT[], 70, 'opt_in', '{"min":0,"max":100}'),
    ('gm_uplift_pct', 'Gross Margin Uplift %', 'margin', 'percent', '%', 'increase_good', 'formula', NULL, FALSE, NULL, 'gm_uplift / revenue_uplift * 100', ARRAY['gm_uplift','revenue_uplift']::TEXT[], 80, 'opt_in', '{"min":0,"max":100}'),
    ('cogs_pct', 'COGS %', 'cost', 'percent', '%', 'decrease_good', 'formula', NULL, FALSE, NULL, 'cogs / revenue_uplift * 100', ARRAY['cogs','revenue_uplift']::TEXT[], 90, 'opt_in', '{"min":0,"max":100}'),
    ('roi_actual', 'ROI Actual %', 'returns', 'percent', '%', 'increase_good', 'formula', NULL, FALSE, NULL, NULL, ARRAY[]::TEXT[], 100, 'opt_in', '{}')
) AS item(
  key, label, group_key, value_type, unit, direction, aggregation, rollup_type,
  is_benefit, benefit_class, formula, formula_inputs, display_order, applies_to, validation
)
ON CONFLICT (tenant_id, key) DO NOTHING;

INSERT INTO financial_bridge_rows (
  tenant_id, key, label, row_kind, metric_definition_ids, cost_category_keys, sign, display_order
)
SELECT org.id, item.key, item.label, item.row_kind, ARRAY[]::UUID[], item.cost_category_keys, item.sign, item.display_order
FROM organizations org
CROSS JOIN (
  VALUES
    ('revenue', 'Revenue Uplift', 'metric_set', ARRAY[]::TEXT[], 1, 10),
    ('margin', 'Gross Margin Uplift', 'metric_set', ARRAY[]::TEXT[], 1, 20),
    ('other_benefits', 'Other Benefits', 'metric_set', ARRAY[]::TEXT[], 1, 30),
    ('recurring_costs', 'Recurring Costs', 'cost_set', ARRAY['maintenance','software','labor','run_rate_operating']::TEXT[], -1, 40),
    ('one_off_costs', 'One-off Costs', 'cost_set', ARRAY['implementation','external_consultants','training_change','other_one_off']::TEXT[], -1, 50),
    ('net_value', 'Net Value', 'net', ARRAY[]::TEXT[], 1, 60)
) AS item(key, label, row_kind, cost_category_keys, sign, display_order)
ON CONFLICT (tenant_id, key) DO NOTHING;

UPDATE financial_bridge_rows row
SET metric_definition_ids = ARRAY[
  (SELECT def.id FROM financial_metric_definitions def WHERE def.tenant_id = row.tenant_id AND def.key = 'revenue_uplift')
]
WHERE row.key = 'revenue';

UPDATE financial_bridge_rows row
SET metric_definition_ids = ARRAY[
  (SELECT def.id FROM financial_metric_definitions def WHERE def.tenant_id = row.tenant_id AND def.key = 'gm_uplift')
]
WHERE row.key = 'margin';

UPDATE financial_bridge_rows row
SET metric_definition_ids = ARRAY[
  (SELECT def.id FROM financial_metric_definitions def WHERE def.tenant_id = row.tenant_id AND def.key = 'cost_savings')
]
WHERE row.key = 'other_benefits';

COMMIT;
