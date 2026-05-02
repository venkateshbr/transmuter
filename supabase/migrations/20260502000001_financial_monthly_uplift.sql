-- ─────────────────────────────────────────────────────────────────────────────
-- Migration: Add monthly granularity + uplift fields to financial_entries
-- Issue: #101 (Karya) — Parent: #87
-- Date: 2026-05-02
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Add month column for monthly granularity (1-12, NULL = quarterly/annual)
ALTER TABLE financial_entries
  ADD COLUMN IF NOT EXISTS month INTEGER CHECK (month BETWEEN 1 AND 12);

-- 2. Revenue Uplift percentage (base/high/actual)
ALTER TABLE financial_entries
  ADD COLUMN IF NOT EXISTS revenue_uplift_pct_base  NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS revenue_uplift_pct_high  NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS revenue_uplift_pct_actual NUMERIC(8,4);

-- 3. Gross Margin Uplift value (base/high/actual)
ALTER TABLE financial_entries
  ADD COLUMN IF NOT EXISTS gm_uplift_base   NUMERIC(15,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS gm_uplift_high   NUMERIC(15,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS gm_uplift_actual NUMERIC(15,4);

-- 4. Gross Margin Uplift percentage (base/high/actual)
ALTER TABLE financial_entries
  ADD COLUMN IF NOT EXISTS gm_uplift_pct_base   NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS gm_uplift_pct_high   NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS gm_uplift_pct_actual NUMERIC(8,4);

-- 5. Update unique constraint to support monthly entries
-- Drop old constraint and create new one that includes month
ALTER TABLE financial_entries DROP CONSTRAINT IF EXISTS financial_entries_initiative_id_year_quarter_key;
ALTER TABLE financial_entries
  ADD CONSTRAINT financial_entries_initiative_year_period_key
  UNIQUE (initiative_id, year, quarter, month);

-- 6. Index for monthly lookups
CREATE INDEX IF NOT EXISTS fin_initiative_year_month_idx
  ON financial_entries(initiative_id, year, month);
