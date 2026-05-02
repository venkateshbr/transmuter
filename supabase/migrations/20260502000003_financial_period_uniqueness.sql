-- Migration: Enforce deterministic financial periods
-- Date: 2026-05-02
--
-- PostgreSQL UNIQUE constraints treat NULL values as distinct unless
-- NULLS NOT DISTINCT is specified. Financial periods use NULL quarter/month
-- to represent monthly, quarterly, or annual rows, so enforce the period key
-- explicitly and clean up older duplicate sample rows first.

ALTER TABLE financial_entries
  ADD COLUMN IF NOT EXISTS cogs_base   NUMERIC(15,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_high   NUMERIC(15,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_actual NUMERIC(15,4),
  ADD COLUMN IF NOT EXISTS cogs_pct_base   NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_pct_high   NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_pct_actual NUMERIC(8,4);

WITH ranked AS (
  SELECT
    id,
    row_number() OVER (
      PARTITION BY tenant_id, initiative_id, year, quarter, month
      ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
    ) AS rn
  FROM financial_entries
)
DELETE FROM financial_entries f
USING ranked r
WHERE f.id = r.id
  AND r.rn > 1;

ALTER TABLE financial_entries
  DROP CONSTRAINT IF EXISTS financial_entries_initiative_id_year_quarter_key,
  DROP CONSTRAINT IF EXISTS financial_entries_initiative_year_period_key,
  DROP CONSTRAINT IF EXISTS financial_entries_tenant_initiative_year_period_key;

ALTER TABLE financial_entries
  ADD CONSTRAINT financial_entries_tenant_initiative_year_period_key
  UNIQUE NULLS NOT DISTINCT (tenant_id, initiative_id, year, quarter, month);

CREATE INDEX IF NOT EXISTS fin_tenant_initiative_year_month_idx
  ON financial_entries(tenant_id, initiative_id, year, month);
