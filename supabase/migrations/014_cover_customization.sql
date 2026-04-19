-- ============================================================
-- Migration 014 — Custom Cover Page Editor (Phase 3)
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS).
--
-- Adds four columns to `clients` that let agency users customise the
-- first (cover) slide of every report generated for that client:
--   * cover_design_preset   — one of: default, minimal, bold, corporate,
--                             hero, gradient
--   * cover_headline        — overrides the default "Performance Report"
--                             title on the cover
--   * cover_subtitle        — second-line override
--   * cover_hero_image_url  — optional hero image URL (Supabase Storage
--                             public URL), used only by the `hero` preset
-- ============================================================

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS cover_design_preset   VARCHAR(50) DEFAULT 'default',
  ADD COLUMN IF NOT EXISTS cover_headline        TEXT,
  ADD COLUMN IF NOT EXISTS cover_subtitle        TEXT,
  ADD COLUMN IF NOT EXISTS cover_hero_image_url  TEXT;

-- Optional CHECK constraint — only add when not already present.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'clients_cover_design_preset_check'
  ) THEN
    ALTER TABLE clients
      ADD CONSTRAINT clients_cover_design_preset_check
      CHECK (cover_design_preset IN (
        'default', 'minimal', 'bold', 'corporate', 'hero', 'gradient'
      ));
  END IF;
END $$;
