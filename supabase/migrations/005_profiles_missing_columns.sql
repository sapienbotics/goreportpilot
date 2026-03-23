-- ============================================================
-- Migration 005 — Add missing agency/email fields to profiles
-- These were omitted from migration 004.
-- Run in Supabase Dashboard → SQL Editor
-- ============================================================

-- Agency identity
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS agency_name     TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS agency_email    TEXT DEFAULT '';

-- Email delivery settings (sender display name, reply-to, footer text)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS sender_name     TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS reply_to_email  TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS email_footer    TEXT DEFAULT '';
