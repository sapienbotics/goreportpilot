-- Migration 009: Widen connections.platform CHECK constraint
--
-- The original constraint limited platform to a fixed enum list.
-- Phase 2 adds CSV uploads (csv_linkedin_ads, csv_tiktok_ads, csv_mailchimp,
-- csv_shopify, csv_generic, plus any user-defined csv_* slug) and therefore
-- needs a flexible check that:
--   • still rejects obviously invalid values
--   • allows all known oauth platforms
--   • allows any csv_* slug (prefix-based regex check)
--
-- Run in Supabase Dashboard › SQL Editor.

ALTER TABLE connections
  DROP CONSTRAINT IF EXISTS connections_platform_check;

ALTER TABLE connections
  ADD CONSTRAINT connections_platform_check
    CHECK (
      platform IN ('ga4', 'meta_ads', 'google_ads', 'search_console')
      OR platform ~ '^csv_[a-z][a-z0-9_]{0,63}$'
    );
