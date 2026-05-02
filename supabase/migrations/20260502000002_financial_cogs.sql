-- Migration: Add COGS fields to financial_entries
-- Date: 2026-05-02

ALTER TABLE financial_entries
  ADD COLUMN IF NOT EXISTS cogs_base   NUMERIC(15,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_high   NUMERIC(15,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_actual NUMERIC(15,4),
  ADD COLUMN IF NOT EXISTS cogs_pct_base   NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_pct_high   NUMERIC(8,4) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cogs_pct_actual NUMERIC(8,4);
