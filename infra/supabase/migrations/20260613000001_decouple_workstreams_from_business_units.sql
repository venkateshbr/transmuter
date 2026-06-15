-- Decouple workstreams from business units.
-- Business-unit impact is now modeled at initiative level through
-- initiative_business_units. Backfill from the former workstream one-to-one
-- assignment before removing the obsolete workstream columns.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'workstreams'
      AND column_name = 'business_unit_id'
  ) THEN
    INSERT INTO initiative_business_units (id, tenant_id, initiative_id, business_unit_id)
    SELECT
      gen_random_uuid(),
      i.tenant_id,
      i.id,
      ws.business_unit_id
    FROM initiatives i
    JOIN workstreams ws
      ON ws.id = i.workstream_id
     AND ws.tenant_id = i.tenant_id
    WHERE ws.business_unit_id IS NOT NULL
    ON CONFLICT (initiative_id, business_unit_id) DO NOTHING;
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS initiative_business_units_business_unit_idx
  ON initiative_business_units(tenant_id, business_unit_id, initiative_id);

ALTER TABLE workstreams
  DROP COLUMN IF EXISTS business_unit_id,
  DROP COLUMN IF EXISTS lead_user_id,
  DROP COLUMN IF EXISTS sponsor_user_id;
