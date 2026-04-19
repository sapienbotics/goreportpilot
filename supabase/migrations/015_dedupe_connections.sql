-- ============================================================
-- Migration 015 — Deduplicate connections + enforce (client_id, platform)
-- uniqueness for OAuth platforms (Phase 2 bug-fix).
--
-- Context:
--   create_connection() previously deduped on (client_id, platform,
--   account_id). When a reconnect produced a slightly different
--   account_id (user picked a different GA4 property, for example),
--   dedup missed and an extra row was inserted. The dashboard widget
--   then displayed the same client/platform twice.
--
-- This migration:
--   1. Removes duplicate rows, keeping the most recent per
--      (client_id, platform) for non-CSV platforms. CSV uploads
--      legitimately create many csv_* rows per client, so they are
--      excluded.
--   2. Adds a partial UNIQUE index as a DB-level safety net so no
--      future code path can re-introduce duplicates.
--
-- Run manually via Supabase Dashboard → SQL Editor.
-- Safe to re-run: uses IF NOT EXISTS for the index.
-- ============================================================

-- ── 1. Clean up existing duplicates ────────────────────────────────────────
-- Keep the newest row per (client_id, platform) for non-CSV platforms.
-- If there's a tie on created_at (practically unreachable), Postgres picks
-- arbitrarily — the SELECT below is just the "row to keep" per group.
WITH duplicates AS (
  SELECT id
  FROM (
    SELECT id,
           ROW_NUMBER() OVER (
             PARTITION BY client_id, platform
             ORDER BY created_at DESC, id DESC
           ) AS rn
    FROM connections
    WHERE platform NOT LIKE 'csv\_%' ESCAPE '\'
  ) ranked
  WHERE rn > 1
)
DELETE FROM connections
WHERE id IN (SELECT id FROM duplicates);

-- ── 2. DB-level guard ───────────────────────────────────────────────────────
-- Partial unique index: one row per (client_id, platform) for OAuth
-- platforms; CSV uploads (which use csv_<slug> platform values) can
-- legitimately co-exist and are excluded from the constraint.
CREATE UNIQUE INDEX IF NOT EXISTS idx_connections_unique_oauth_per_client
  ON connections (client_id, platform)
  WHERE platform NOT LIKE 'csv\_%' ESCAPE '\';
