-- Migration: Add tenant-scoped financial cell assumptions
-- Date: 2026-05-03

CREATE TABLE IF NOT EXISTS financial_cell_assumptions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  row_key       TEXT NOT NULL,
  column_key    TEXT NOT NULL,
  comment       TEXT NOT NULL CHECK (length(trim(comment)) > 0),
  created_by    UUID REFERENCES users(id),
  updated_by    UUID REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, initiative_id, row_key, column_key)
);

CREATE INDEX IF NOT EXISTS fca_tenant_initiative_idx
  ON financial_cell_assumptions(tenant_id, initiative_id);

ALTER TABLE financial_cell_assumptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fca_select" ON financial_cell_assumptions;
DROP POLICY IF EXISTS "fca_insert" ON financial_cell_assumptions;
DROP POLICY IF EXISTS "fca_update" ON financial_cell_assumptions;
DROP POLICY IF EXISTS "fca_delete" ON financial_cell_assumptions;

CREATE POLICY "fca_select" ON financial_cell_assumptions
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fca_insert" ON financial_cell_assumptions
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "fca_update" ON financial_cell_assumptions
  FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "fca_delete" ON financial_cell_assumptions
  FOR DELETE USING (tenant_id = current_tenant_id());
