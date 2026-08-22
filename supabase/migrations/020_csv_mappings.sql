-- ============================================================
-- Migration 020 — Universal CSV ingestion (Track A)
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS / guarded DO blocks).
--
-- Two tables:
--   csv_mappings       a confirmed column mapping, keyed by a fingerprint of
--                      the uploaded file's header row. When next month's export
--                      arrives with the same headers we replay this mapping and
--                      skip the LLM entirely — that is the "one click next
--                      month" promise, and it also caps OpenAI spend at roughly
--                      one call per new export format per client.
--   csv_mapping_usage  append-only meter for the per-user daily cap on AI
--                      mapping calls (25/day, see routers/csv_ingest.py).
--                      Replayed mappings are not recorded, because they cost
--                      nothing.
--
-- Note: no changes are needed to the reports table. Generation settings
-- (including csv_sources) ride on the existing reports.sections JSONB.
-- ============================================================

-- ── csv_mappings ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS csv_mappings (
  id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  client_id          UUID        NOT NULL REFERENCES clients(id)  ON DELETE CASCADE,
  name               TEXT        NOT NULL,
  -- SHA-256 prefix of the sorted, normalised header row. Order- and
  -- case-insensitive, so a re-export with reordered columns still matches.
  column_fingerprint TEXT        NOT NULL,
  -- The full MappingProposal (see services/csv_ingest/schema.py).
  mapping            JSONB       NOT NULL DEFAULT '{}'::jsonb,
  -- true for the five bundled KPI templates seeded below.
  is_system          BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One mapping per (client, file layout). The upsert in
-- services/csv_ingest/templates.py:save() targets this constraint, so remapping
-- the same export replaces the old mapping rather than accumulating duplicates.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'csv_mappings_client_fingerprint_key'
  ) THEN
    ALTER TABLE csv_mappings
      ADD CONSTRAINT csv_mappings_client_fingerprint_key
      UNIQUE (client_id, column_fingerprint);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_csv_mappings_user        ON csv_mappings(user_id);
CREATE INDEX IF NOT EXISTS idx_csv_mappings_client      ON csv_mappings(client_id);
CREATE INDEX IF NOT EXISTS idx_csv_mappings_fingerprint ON csv_mappings(user_id, column_fingerprint);

-- updated_at maintenance, matching the pattern used by earlier migrations.
CREATE OR REPLACE FUNCTION set_csv_mappings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Created only when absent. Deliberately NOT written as
-- "DROP TRIGGER IF EXISTS ... ; CREATE TRIGGER ...": this migration contains
-- no DROP of any kind, so it can be read and approved at a glance without
-- anyone having to reason about whether a given DROP is safe.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = 'trg_csv_mappings_updated_at'
      AND tgrelid = 'csv_mappings'::regclass
  ) THEN
    CREATE TRIGGER trg_csv_mappings_updated_at
      BEFORE UPDATE ON csv_mappings
      FOR EACH ROW EXECUTE FUNCTION set_csv_mappings_updated_at();
  END IF;
END $$;


-- ── csv_mapping_usage ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS csv_mapping_usage (
  id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  column_fingerprint TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The quota query is "count rows for this user in the last 24 hours".
CREATE INDEX IF NOT EXISTS idx_csv_mapping_usage_user_time
  ON csv_mapping_usage(user_id, created_at DESC);


-- ── Row-Level Security ──────────────────────────────────────────────────────
-- Consistent with every other table: a user sees only their own rows.

ALTER TABLE csv_mappings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE csv_mapping_usage ENABLE ROW LEVEL SECURITY;

-- Created only when absent, for the same reason as the trigger above.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'csv_mappings'
      AND policyname = 'csv_mappings_owner'
  ) THEN
    CREATE POLICY csv_mappings_owner ON csv_mappings
      FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'csv_mapping_usage'
      AND policyname = 'csv_mapping_usage_owner'
  ) THEN
    CREATE POLICY csv_mapping_usage_owner ON csv_mapping_usage
      FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;


-- ── Housekeeping ────────────────────────────────────────────────────────────
-- csv_mapping_usage is append-only metering data with no value past 24 hours.
-- Run this occasionally, or wire it to pg_cron if that extension is enabled:
--
--   DELETE FROM csv_mapping_usage WHERE created_at < NOW() - INTERVAL '7 days';


-- ── Verification ────────────────────────────────────────────────────────────
-- Expect two rows.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('csv_mappings', 'csv_mapping_usage')
ORDER BY table_name;
