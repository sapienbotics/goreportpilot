-- ============================================================
-- Migration 018 — Goals & Alerts (Phase 6)
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS).
--
-- Design notes:
--  * Per-client metric targets. Each goal names a canonical metric
--    (e.g. 'ga4.sessions', 'meta_ads.roas'), a comparison operator,
--    a target value, and a period (weekly | monthly).
--  * user_id is denormalised onto goals (copied from clients.user_id
--    at insert time) so plan-enforcement can count goals per user
--    without a join and RLS stays simple.
--  * alerts_sent JSONB tracks idempotency: keys like '2026-04:missed'
--    point to ISO timestamps so the scheduler won't double-send for
--    the same (period, alert_type) tuple. Mirrors the pattern used
--    by connections.alerts_sent in migration 013.
--  * alert_emails is a jsonb array of optional override recipients.
--    When empty, the alerter falls back to profiles.agency_email.
-- ============================================================

CREATE TABLE IF NOT EXISTS goals (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id      UUID        NOT NULL REFERENCES clients(id)  ON DELETE CASCADE,
  user_id        UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  metric         TEXT        NOT NULL,
  comparison     TEXT        NOT NULL DEFAULT 'gte',
  target_value   NUMERIC     NOT NULL,
  tolerance_pct  NUMERIC     NOT NULL DEFAULT 5,
  period         TEXT        NOT NULL DEFAULT 'monthly',
  is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
  alert_emails   JSONB       NOT NULL DEFAULT '[]'::jsonb,
  alerts_sent    JSONB       NOT NULL DEFAULT '{}'::jsonb,
  last_evaluated_at TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enum-style CHECK constraints — added guarded so re-runs are safe.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'goals_comparison_check') THEN
    ALTER TABLE goals
      ADD CONSTRAINT goals_comparison_check
      CHECK (comparison IN ('gte', 'lte', 'eq'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'goals_period_check') THEN
    ALTER TABLE goals
      ADD CONSTRAINT goals_period_check
      CHECK (period IN ('weekly', 'monthly'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_goals_client_id ON goals(client_id);
CREATE INDEX IF NOT EXISTS idx_goals_user_id   ON goals(user_id);
CREATE INDEX IF NOT EXISTS idx_goals_active    ON goals(is_active) WHERE is_active = TRUE;

-- updated_at trigger (reuses the function defined in migration 001).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'update_goals_updated_at'
  ) THEN
    CREATE TRIGGER update_goals_updated_at
      BEFORE UPDATE ON goals
      FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
END $$;

-- ============================================================
-- Row-Level Security
-- ============================================================
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'goals' AND policyname = 'Users can view own goals'
  ) THEN
    CREATE POLICY "Users can view own goals"
      ON goals FOR SELECT
      USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'goals' AND policyname = 'Users can create own goals'
  ) THEN
    CREATE POLICY "Users can create own goals"
      ON goals FOR INSERT
      WITH CHECK (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'goals' AND policyname = 'Users can update own goals'
  ) THEN
    CREATE POLICY "Users can update own goals"
      ON goals FOR UPDATE
      USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'goals' AND policyname = 'Users can delete own goals'
  ) THEN
    CREATE POLICY "Users can delete own goals"
      ON goals FOR DELETE
      USING (auth.uid() = user_id);
  END IF;
END $$;
