-- Add tenant-configurable recurring cost inflation metadata.

ALTER TABLE financial_cost_lines
  ADD COLUMN IF NOT EXISTS inflation_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS annual_inflation_rate_pct NUMERIC(7,4) NOT NULL DEFAULT 0;

UPDATE organizations
SET settings = COALESCE(settings, '{}'::jsonb)
  || jsonb_build_object(
    'financial_engine',
    COALESCE(settings -> 'financial_engine', '{}'::jsonb)
      || jsonb_build_object(
        'recurring_cost_inflation_mode',
        COALESCE(settings #> '{financial_engine,recurring_cost_inflation_mode}', '"manual_entry"'::jsonb),
        'default_annual_inflation_rate_pct',
        COALESCE(settings #> '{financial_engine,default_annual_inflation_rate_pct}', '"0.0000"'::jsonb),
        'allow_cost_line_inflation_override',
        COALESCE(settings #> '{financial_engine,allow_cost_line_inflation_override}', 'true'::jsonb)
      )
  )
WHERE settings IS NULL
   OR settings #> '{financial_engine,recurring_cost_inflation_mode}' IS NULL
   OR settings #> '{financial_engine,default_annual_inflation_rate_pct}' IS NULL
   OR settings #> '{financial_engine,allow_cost_line_inflation_override}' IS NULL;
