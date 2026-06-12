BEGIN;

SET LOCAL search_path = transmuter, public, extensions;

CREATE TABLE IF NOT EXISTS financial_attribute_definitions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  key           TEXT NOT NULL,
  label         TEXT NOT NULL,
  entity_type   TEXT NOT NULL CHECK (entity_type IN ('benefit_line', 'cost_line')),
  value_type    TEXT NOT NULL DEFAULT 'text'
                CHECK (value_type IN ('text', 'number', 'currency', 'percent', 'date', 'select', 'boolean')),
  options       JSONB NOT NULL DEFAULT '[]'::jsonb,
  is_required   BOOLEAN NOT NULL DEFAULT FALSE,
  display_order INTEGER NOT NULL DEFAULT 0,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, entity_type, key)
);

CREATE INDEX IF NOT EXISTS financial_attribute_definitions_tenant_idx
  ON financial_attribute_definitions(tenant_id, entity_type, display_order);

ALTER TABLE financial_attribute_definitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fad_select" ON financial_attribute_definitions
  FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY "fad_insert" ON financial_attribute_definitions
  FOR INSERT WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

CREATE POLICY "fad_update" ON financial_attribute_definitions
  FOR UPDATE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  ) WITH CHECK (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

CREATE POLICY "fad_delete" ON financial_attribute_definitions
  FOR DELETE USING (
    tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
  );

COMMIT;
