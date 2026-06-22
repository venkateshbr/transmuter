ALTER TABLE gate_submissions
  ADD COLUMN IF NOT EXISTS submission_type TEXT NOT NULL DEFAULT 'stage_gate',
  ADD COLUMN IF NOT EXISTS requested_bankable_plan_version INTEGER,
  ADD COLUMN IF NOT EXISTS requested_snapshot JSONB;

ALTER TABLE gate_submissions
  DROP CONSTRAINT IF EXISTS gate_submissions_submission_type_check;

ALTER TABLE gate_submissions
  ADD CONSTRAINT gate_submissions_submission_type_check
  CHECK (submission_type IN ('stage_gate', 'bankable_plan_rebaseline'));

CREATE INDEX IF NOT EXISTS gs_tenant_submission_type_idx
  ON gate_submissions(tenant_id, submission_type, decision);
