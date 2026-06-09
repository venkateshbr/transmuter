-- Workstream target locks and explicit post-lock forecast outlooks.

CREATE TABLE financial_forecasts (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL REFERENCES organizations(id),
  initiative_id  UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  line_type      TEXT NOT NULL CHECK (line_type IN ('metric','cost')),
  line_key       TEXT NOT NULL,
  year           INTEGER NOT NULL CHECK (year >= 2020 AND year <= 2040),
  quarter        INTEGER CHECK (quarter IN (1,2,3,4)),
  month          INTEGER CHECK (month >= 1 AND month <= 12),
  amount_forecast NUMERIC(15,4) NOT NULL DEFAULT 0,
  notes          TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX financial_forecasts_initiative_idx
  ON financial_forecasts(tenant_id, initiative_id, year, quarter, month);
CREATE UNIQUE INDEX financial_forecasts_unique_period_idx
  ON financial_forecasts(tenant_id, initiative_id, line_type, line_key, year, COALESCE(quarter, 0), COALESCE(month, 0));

ALTER TABLE financial_forecasts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ff_select" ON financial_forecasts FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ff_insert" ON financial_forecasts FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "ff_update" ON financial_forecasts FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "ff_delete" ON financial_forecasts FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);

CREATE TABLE workstream_target_locks (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                UUID NOT NULL REFERENCES organizations(id),
  workstream_id            UUID NOT NULL REFERENCES workstreams(id) ON DELETE CASCADE,
  version                  INTEGER NOT NULL CHECK (version >= 1),
  lock_date                DATE NOT NULL,
  locked_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  locked_by_id             UUID REFERENCES users(id),
  lock_cadence             TEXT NOT NULL DEFAULT 'one_off' CHECK (lock_cadence IN ('one_off','annual','cycle_based')),
  cutoff_rule              TEXT NOT NULL DEFAULT 'approved_at_lte_lock_date',
  valuation_method         TEXT NOT NULL DEFAULT 'run_rate',
  locked_value_basis       TEXT NOT NULL DEFAULT 'net_run_rate',
  included_initiative_ids  UUID[] NOT NULL DEFAULT '{}',
  excluded_initiative_ids  UUID[] NOT NULL DEFAULT '{}',
  locked_run_rate_value    NUMERIC(15,4) NOT NULL DEFAULT 0,
  plan_total               NUMERIC(15,4) NOT NULL DEFAULT 0,
  actual_total             NUMERIC(15,4) NOT NULL DEFAULT 0,
  variance                 NUMERIC(15,4) NOT NULL DEFAULT 0,
  snapshot                 JSONB NOT NULL,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, workstream_id, version)
);

CREATE INDEX workstream_target_locks_workstream_idx
  ON workstream_target_locks(tenant_id, workstream_id, version DESC);
CREATE INDEX workstream_target_locks_lock_date_idx
  ON workstream_target_locks(tenant_id, lock_date DESC);

ALTER TABLE workstream_target_locks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "wtl_select" ON workstream_target_locks FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "wtl_insert" ON workstream_target_locks FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
