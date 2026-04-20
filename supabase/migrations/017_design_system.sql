-- ============================================================
-- Migration 017 — Design System unification (Option F v1)
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS + DO-block CHECKs).
--
-- Purpose
-- -------
-- Replace the scattered "cover preset" concept with a single per-client
-- `theme` choice that selects one of the 6 existing visual templates.
-- The theme governs the whole deck (cover + content slides + chart
-- palette), eliminating the preset-vs-template mismatch that caused
-- repeated visual bugs in v3..v10.
--
-- Schema changes
-- --------------
--   clients
--     + theme VARCHAR(30) DEFAULT 'modern_clean'  CHECK in 6 values
--     (keeps existing cover_headline, cover_subtitle, brand colours,
--      logo placement fields — those are still used as overrides)
--
-- Deprecation (column kept, write path removed in the UI)
-- -------------------------------------------------------
--   clients.cover_design_preset — superseded by theme. Left as NULLable
--     so historical reads don't break. Dropped in a future migration.
--   clients.cover_hero_image_url — v1 drops the hero concept. Kept so
--     existing uploads aren't orphaned. Dropped in a future migration.
--   reports.visual_template, scheduled_reports.visual_template — kept
--     for historical read-back. New writes come from clients.theme
--     via the generator. No UI exposes these fields after this change.
--
-- Backfill
-- --------
-- Best-effort mapping from the old preset to a coherent theme:
--   default   → modern_clean   (safe fallback)
--   minimal   → minimal_elegant
--   bold      → bold_geometric
--   corporate → dark_executive
--   gradient  → gradient_modern
--   hero      → modern_clean   (hero dropped in v1; safe fallback)
-- Clients with no preset (new clients) default to modern_clean.
-- ============================================================

-- 1) Add the theme column with safe default.
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS theme VARCHAR(30) DEFAULT 'modern_clean';

-- 2) CHECK constraint — 6 themes (1:1 with existing visual templates).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'clients_theme_check'
  ) THEN
    ALTER TABLE clients
      ADD CONSTRAINT clients_theme_check
      CHECK (theme IN (
        'modern_clean',
        'dark_executive',
        'colorful_agency',
        'bold_geometric',
        'minimal_elegant',
        'gradient_modern'
      ));
  END IF;
END $$;

-- 3) Backfill from cover_design_preset where it holds a recognisable
--    value. Unknown / NULL values keep the default 'modern_clean'.
UPDATE clients
   SET theme = CASE cover_design_preset
     WHEN 'minimal'   THEN 'minimal_elegant'
     WHEN 'bold'      THEN 'bold_geometric'
     WHEN 'corporate' THEN 'dark_executive'
     WHEN 'gradient'  THEN 'gradient_modern'
     -- 'default' / 'hero' / anything else → keep modern_clean fallback
     ELSE 'modern_clean'
   END
 WHERE theme IS NULL OR theme = 'modern_clean';

-- 4) Index on theme (cheap; speeds up any future per-theme analytics).
CREATE INDEX IF NOT EXISTS idx_clients_theme ON clients(theme);
