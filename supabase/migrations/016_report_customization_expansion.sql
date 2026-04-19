-- ============================================================
-- Migration 016 — Report Customization expansion (Phase 3 fix Part B)
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS).
--
-- Extends migration 014's cover customisation with per-client brand
-- colour overrides + per-client logo placement controls. Supports the
-- unified "Report Customization" tab that replaces the narrower "Cover
-- Page" tab shipped in Phase 3.
--
-- Fields added to `clients`:
--   cover_brand_primary_color   — per-client override of the agency's
--                                 profile brand_color; falls back when NULL.
--                                 Applies to cover header + chart palette.
--   cover_brand_accent_color    — new per-client accent colour; renders
--                                 as a thin accent bar on the cover when
--                                 set. Not propagated to other slides
--                                 (future follow-up).
--   cover_agency_logo_position  — named placement target for the agency
--                                 logo on the cover slide:
--                                 default | top-left | top-right |
--                                 top-center | footer-left | footer-right |
--                                 footer-center | center.
--                                 NULL / 'default' = template placeholder
--                                 position (current behaviour).
--   cover_agency_logo_size      — small | medium | large | default.
--   cover_client_logo_position  — same set as agency.
--   cover_client_logo_size      — same set as agency.
-- ============================================================

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS cover_brand_primary_color   VARCHAR(7),
  ADD COLUMN IF NOT EXISTS cover_brand_accent_color    VARCHAR(7),
  ADD COLUMN IF NOT EXISTS cover_agency_logo_position  VARCHAR(20) DEFAULT 'default',
  ADD COLUMN IF NOT EXISTS cover_agency_logo_size      VARCHAR(20) DEFAULT 'default',
  ADD COLUMN IF NOT EXISTS cover_client_logo_position  VARCHAR(20) DEFAULT 'default',
  ADD COLUMN IF NOT EXISTS cover_client_logo_size      VARCHAR(20) DEFAULT 'default';

-- Optional CHECK constraints. Each guarded with DO-block so the migration
-- is safe to re-run.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'clients_cover_agency_logo_position_check'
  ) THEN
    ALTER TABLE clients
      ADD CONSTRAINT clients_cover_agency_logo_position_check
      CHECK (cover_agency_logo_position IN (
        'default','top-left','top-right','top-center',
        'footer-left','footer-right','footer-center','center'
      ));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'clients_cover_client_logo_position_check'
  ) THEN
    ALTER TABLE clients
      ADD CONSTRAINT clients_cover_client_logo_position_check
      CHECK (cover_client_logo_position IN (
        'default','top-left','top-right','top-center',
        'footer-left','footer-right','footer-center','center'
      ));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'clients_cover_agency_logo_size_check'
  ) THEN
    ALTER TABLE clients
      ADD CONSTRAINT clients_cover_agency_logo_size_check
      CHECK (cover_agency_logo_size IN ('default','small','medium','large'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'clients_cover_client_logo_size_check'
  ) THEN
    ALTER TABLE clients
      ADD CONSTRAINT clients_cover_client_logo_size_check
      CHECK (cover_client_logo_size IN ('default','small','medium','large'));
  END IF;
END $$;
