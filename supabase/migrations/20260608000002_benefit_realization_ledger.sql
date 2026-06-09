-- Benefit realization ledger with server-side variance rollups.

CREATE TABLE benefit_realization_ledger (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL REFERENCES organizations(id),
  initiative_id         UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  period_granularity    TEXT NOT NULL CHECK (period_granularity IN ('weekly', 'monthly', 'yearly')),
  period_start          DATE NOT NULL,
  period_end            DATE NOT NULL,
  bankable_plan_amount  NUMERIC(15,4) NOT NULL DEFAULT 0,
  actual_amount         NUMERIC(15,4) NOT NULL DEFAULT 0,
  description           TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (period_end >= period_start),
  UNIQUE (tenant_id, initiative_id, period_granularity, period_start)
);

CREATE INDEX benefit_ledger_initiative_idx
  ON benefit_realization_ledger(tenant_id, initiative_id, period_granularity, period_start);

ALTER TABLE benefit_realization_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY "brl_select" ON benefit_realization_ledger FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "brl_insert" ON benefit_realization_ledger FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "brl_update" ON benefit_realization_ledger FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "brl_delete" ON benefit_realization_ledger FOR DELETE USING (tenant_id = current_tenant_id());
