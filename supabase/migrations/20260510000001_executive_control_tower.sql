-- Migration: Executive Control Tower phase 2A

ALTER TABLE initiatives
  ADD COLUMN IF NOT EXISTS benefit_confidence NUMERIC(5,2) NOT NULL DEFAULT 50.00
    CHECK (benefit_confidence >= 0 AND benefit_confidence <= 100),
  ADD COLUMN IF NOT EXISTS realization_status TEXT NOT NULL DEFAULT 'not_started'
    CHECK (realization_status IN (
      'not_started',
      'forecasted',
      'committed',
      'partially_realized',
      'realized',
      'at_risk'
    )),
  ADD COLUMN IF NOT EXISTS variance_explanation TEXT;

CREATE TABLE IF NOT EXISTS initiative_dependencies (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                UUID NOT NULL REFERENCES organizations(id),
  upstream_initiative_id   UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  downstream_initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  dependency_type          TEXT NOT NULL CHECK (dependency_type IN (
    'blocks','enables','informs','duplicates','requires_decision'
  )),
  status                   TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN (
    'proposed','active','at_risk','blocking','resolved','cancelled'
  )),
  severity                 TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('high','medium','low')),
  owner_id                 UUID REFERENCES users(id),
  due_date                 DATE,
  resolution_notes         TEXT,
  linked_milestone_id      UUID REFERENCES milestones(id) ON DELETE SET NULL,
  linked_action_item_id    UUID REFERENCES action_items(id) ON DELETE SET NULL,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (upstream_initiative_id <> downstream_initiative_id),
  UNIQUE (tenant_id, upstream_initiative_id, downstream_initiative_id, dependency_type)
);

CREATE INDEX IF NOT EXISTS initiative_dependencies_tenant_idx
  ON initiative_dependencies(tenant_id, status, severity);
CREATE INDEX IF NOT EXISTS initiative_dependencies_upstream_idx
  ON initiative_dependencies(tenant_id, upstream_initiative_id);
CREATE INDEX IF NOT EXISTS initiative_dependencies_downstream_idx
  ON initiative_dependencies(tenant_id, downstream_initiative_id);

ALTER TABLE initiative_dependencies ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "ideps_select" ON initiative_dependencies;
DROP POLICY IF EXISTS "ideps_insert" ON initiative_dependencies;
DROP POLICY IF EXISTS "ideps_update" ON initiative_dependencies;
DROP POLICY IF EXISTS "ideps_delete" ON initiative_dependencies;
CREATE POLICY "ideps_select" ON initiative_dependencies FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ideps_insert" ON initiative_dependencies FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "ideps_update" ON initiative_dependencies FOR UPDATE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() IN ('transformation_office', 'initiative_owner')
) WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() IN ('transformation_office', 'initiative_owner')
);
CREATE POLICY "ideps_delete" ON initiative_dependencies FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS shared_cost_pools (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  name          TEXT NOT NULL,
  description   TEXT,
  category_key  TEXT NOT NULL DEFAULT 'other',
  year          INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2040),
  quarter       INTEGER CHECK (quarter BETWEEN 1 AND 4),
  month         INTEGER CHECK (month BETWEEN 1 AND 12),
  amount_plan   NUMERIC(15,4) NOT NULL DEFAULT 0,
  amount_actual NUMERIC(15,4),
  is_recurring  BOOLEAN NOT NULL DEFAULT FALSE,
  status        TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','archived')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS shared_cost_pools_tenant_idx
  ON shared_cost_pools(tenant_id, year, quarter, month, status);

ALTER TABLE shared_cost_pools ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scp_select" ON shared_cost_pools;
DROP POLICY IF EXISTS "scp_insert" ON shared_cost_pools;
DROP POLICY IF EXISTS "scp_update" ON shared_cost_pools;
DROP POLICY IF EXISTS "scp_delete" ON shared_cost_pools;
CREATE POLICY "scp_select" ON shared_cost_pools FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scp_insert" ON shared_cost_pools FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scp_update" ON shared_cost_pools FOR UPDATE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scp_delete" ON shared_cost_pools FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS shared_cost_allocation_rules (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id          UUID NOT NULL REFERENCES organizations(id),
  pool_id            UUID NOT NULL REFERENCES shared_cost_pools(id) ON DELETE CASCADE,
  name               TEXT NOT NULL,
  allocation_method  TEXT NOT NULL CHECK (allocation_method IN (
    'fixed_percentage',
    'equal_split',
    'manual_amount',
    'benefit_weighted',
    'revenue_weighted',
    'headcount_weighted'
  )),
  filters            JSONB NOT NULL DEFAULT '{}'::jsonb,
  weights            JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS shared_cost_rules_tenant_idx
  ON shared_cost_allocation_rules(tenant_id, pool_id, is_active);

ALTER TABLE shared_cost_allocation_rules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scar_select" ON shared_cost_allocation_rules;
DROP POLICY IF EXISTS "scar_insert" ON shared_cost_allocation_rules;
DROP POLICY IF EXISTS "scar_update" ON shared_cost_allocation_rules;
DROP POLICY IF EXISTS "scar_delete" ON shared_cost_allocation_rules;
CREATE POLICY "scar_select" ON shared_cost_allocation_rules FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scar_insert" ON shared_cost_allocation_rules FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scar_update" ON shared_cost_allocation_rules FOR UPDATE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scar_delete" ON shared_cost_allocation_rules FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS shared_cost_allocation_runs (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           UUID NOT NULL REFERENCES organizations(id),
  pool_id             UUID NOT NULL REFERENCES shared_cost_pools(id) ON DELETE CASCADE,
  rule_id             UUID NOT NULL REFERENCES shared_cost_allocation_rules(id) ON DELETE CASCADE,
  scenario            TEXT NOT NULL DEFAULT 'plan' CHECK (scenario IN ('plan','actual')),
  status              TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed','voided')),
  total_amount_plan   NUMERIC(15,4) NOT NULL DEFAULT 0,
  total_amount_actual NUMERIC(15,4),
  created_by          UUID REFERENCES users(id),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS shared_cost_runs_tenant_idx
  ON shared_cost_allocation_runs(tenant_id, pool_id, rule_id, status);

ALTER TABLE shared_cost_allocation_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scaruns_select" ON shared_cost_allocation_runs;
DROP POLICY IF EXISTS "scaruns_insert" ON shared_cost_allocation_runs;
DROP POLICY IF EXISTS "scaruns_update" ON shared_cost_allocation_runs;
CREATE POLICY "scaruns_select" ON shared_cost_allocation_runs FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "scaruns_insert" ON shared_cost_allocation_runs FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "scaruns_update" ON shared_cost_allocation_runs FOR UPDATE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS shared_cost_allocations (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           UUID NOT NULL REFERENCES organizations(id),
  run_id              UUID NOT NULL REFERENCES shared_cost_allocation_runs(id) ON DELETE CASCADE,
  pool_id             UUID NOT NULL REFERENCES shared_cost_pools(id) ON DELETE CASCADE,
  rule_id             UUID NOT NULL REFERENCES shared_cost_allocation_rules(id) ON DELETE CASCADE,
  initiative_id       UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  allocation_basis    TEXT NOT NULL,
  basis_value         NUMERIC(15,4) NOT NULL DEFAULT 0,
  allocated_plan      NUMERIC(15,4) NOT NULL DEFAULT 0,
  allocated_actual    NUMERIC(15,4),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, run_id, initiative_id)
);

CREATE INDEX IF NOT EXISTS shared_cost_allocations_tenant_idx
  ON shared_cost_allocations(tenant_id, initiative_id, pool_id);

ALTER TABLE shared_cost_allocations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "sca_select" ON shared_cost_allocations;
DROP POLICY IF EXISTS "sca_insert" ON shared_cost_allocations;
CREATE POLICY "sca_select" ON shared_cost_allocations FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "sca_insert" ON shared_cost_allocations FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);

CREATE TABLE IF NOT EXISTS initiative_value_realization_notes (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id          UUID NOT NULL REFERENCES organizations(id),
  initiative_id      UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  author_id          UUID REFERENCES users(id),
  note_type          TEXT NOT NULL DEFAULT 'variance' CHECK (note_type IN (
    'variance','benefit_confidence','allocation','realization','board_note'
  )),
  period_label       TEXT,
  planned_value      NUMERIC(15,4),
  actual_value       NUMERIC(15,4),
  explanation        TEXT NOT NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS value_notes_tenant_idx
  ON initiative_value_realization_notes(tenant_id, initiative_id, note_type, created_at DESC);

ALTER TABLE initiative_value_realization_notes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "ivrn_select" ON initiative_value_realization_notes;
DROP POLICY IF EXISTS "ivrn_insert" ON initiative_value_realization_notes;
DROP POLICY IF EXISTS "ivrn_update" ON initiative_value_realization_notes;
DROP POLICY IF EXISTS "ivrn_delete" ON initiative_value_realization_notes;
CREATE POLICY "ivrn_select" ON initiative_value_realization_notes FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ivrn_insert" ON initiative_value_realization_notes FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND (
    current_user_role() = 'transformation_office'
    OR (current_user_role() = 'initiative_owner' AND author_id = auth.uid())
  )
);
CREATE POLICY "ivrn_update" ON initiative_value_realization_notes FOR UPDATE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
) WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "ivrn_delete" ON initiative_value_realization_notes FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
