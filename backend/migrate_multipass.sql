-- Migration: Add multi-pass consensus columns to aeo_runs
-- This allows us to track multiple passes of the same engine+prompt combination 
-- to reduce signal noise and compute fractional mention rates.

ALTER TABLE aeo_runs ADD COLUMN IF NOT EXISTS pass_number INT DEFAULT 1;
ALTER TABLE aeo_runs ADD COLUMN IF NOT EXISTS scan_group_id UUID;

-- Optional: Index on scan_group_id for faster grouping during scoring
CREATE INDEX IF NOT EXISTS idx_aeo_runs_scan_group ON aeo_runs(scan_group_id);
