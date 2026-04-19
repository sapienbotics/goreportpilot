-- ============================================================
-- Migration 013 — Connection Health Monitor
-- Phase 2 of the Phase 1 & 2 build plan.
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS).
--
-- Design notes:
--  * Adds three new columns to the existing `connections` table so we can
--    monitor OAuth / API health independently of the existing `status`
--    column (which reflects token state from OAuth callbacks).
--  * `health_status` may overlap with `status` on the shared value
--    'expiring_soon'; they coexist because they have different semantics:
--      - `status`         = OAuth token state as known from the callback
--      - `health_status`  = live probe/freshness state from background checks
--  * `alerts_sent` jsonb tracks idempotency for alert emails. Keys are
--    alert names ('broken', 'expiring', 'zero_data') and values are ISO
--    timestamps of the most recent send. Zero-data alerts reset when the
--    connection returns to non-zero data.
--  * last_error_message ALREADY EXISTS in migration 001 — not re-added.
-- ============================================================

ALTER TABLE connections
  ADD COLUMN IF NOT EXISTS last_health_check_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS health_status        VARCHAR(20) DEFAULT 'healthy',
  ADD COLUMN IF NOT EXISTS alerts_sent          JSONB       DEFAULT '{}'::jsonb;

-- Optional CHECK constraint — only add when not already present.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'connections_health_status_check'
  ) THEN
    ALTER TABLE connections
      ADD CONSTRAINT connections_health_status_check
      CHECK (health_status IN ('healthy', 'warning', 'broken', 'expiring_soon'));
  END IF;
END $$;

-- Index for the dashboard health widget + pre-generation gate lookups.
CREATE INDEX IF NOT EXISTS idx_connections_health_status
  ON connections(health_status);

-- Back-fill: any existing row with a null health_status gets 'healthy' so
-- the gate doesn't accidentally block first-time users after deploy.
UPDATE connections
   SET health_status = 'healthy'
 WHERE health_status IS NULL;
