-- ============================================================
-- Migration 002: Add currency column to connections table
-- Stores the ad account's billing currency (e.g. "INR", "USD")
-- so reports can display the correct currency symbol.
-- ============================================================

ALTER TABLE connections
  ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'USD';
