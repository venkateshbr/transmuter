ALTER TABLE financial_benefit_lines
  ADD COLUMN IF NOT EXISTS validation_status TEXT NOT NULL DEFAULT 'draft'
    CHECK (validation_status IN ('draft','submitted','finance_validated','rejected')),
  ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS submitted_by UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS validated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS validated_by UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS validation_comment TEXT,
  ADD COLUMN IF NOT EXISTS evidence_url TEXT,
  ADD COLUMN IF NOT EXISTS evidence_label TEXT,
  ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
  ADD COLUMN IF NOT EXISTS realization_owner_id UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS handoff_status TEXT NOT NULL DEFAULT 'not_started'
    CHECK (handoff_status IN ('not_started','owner_assigned','handoff_ready','handoff_complete')),
  ADD COLUMN IF NOT EXISTS handoff_due_date DATE,
  ADD COLUMN IF NOT EXISTS risk_rating TEXT NOT NULL DEFAULT 'medium'
    CHECK (risk_rating IN ('low','medium','high')),
  ADD COLUMN IF NOT EXISTS risk_adjustment_pct NUMERIC(5,2) NOT NULL DEFAULT 100
    CHECK (risk_adjustment_pct >= 0 AND risk_adjustment_pct <= 100);

CREATE INDEX IF NOT EXISTS financial_benefit_lines_validation_idx
  ON financial_benefit_lines(tenant_id, validation_status, initiative_id);

CREATE INDEX IF NOT EXISTS financial_benefit_lines_handoff_idx
  ON financial_benefit_lines(tenant_id, handoff_status, handoff_due_date);

CREATE TABLE IF NOT EXISTS financial_benefit_line_validation_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  initiative_id   UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  benefit_line_id UUID NOT NULL REFERENCES financial_benefit_lines(id) ON DELETE CASCADE,
  event_type      TEXT NOT NULL CHECK (event_type IN ('submit','validate','reject','handoff_update')),
  actor_user_id   UUID REFERENCES users(id),
  comment         TEXT,
  evidence_url    TEXT,
  evidence_label  TEXT,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS financial_benefit_line_validation_events_line_idx
  ON financial_benefit_line_validation_events(tenant_id, benefit_line_id, created_at);

ALTER TABLE financial_benefit_line_validation_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = current_schema()
      AND tablename = 'financial_benefit_line_validation_events'
      AND policyname = 'fblve_select'
  ) THEN
    CREATE POLICY "fblve_select"
      ON financial_benefit_line_validation_events
      FOR SELECT
      USING (tenant_id = current_tenant_id());
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = current_schema()
      AND tablename = 'financial_benefit_line_validation_events'
      AND policyname = 'fblve_insert'
  ) THEN
    CREATE POLICY "fblve_insert"
      ON financial_benefit_line_validation_events
      FOR INSERT
      WITH CHECK (
        tenant_id = current_tenant_id()
        AND current_user_role() = 'transformation_office'
      );
  END IF;
END $$;
