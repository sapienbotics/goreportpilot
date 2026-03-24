-- Migration 007: Add report language preference to clients
-- Run this in Supabase Dashboard → SQL Editor

ALTER TABLE clients ADD COLUMN IF NOT EXISTS report_language TEXT DEFAULT 'en';

COMMENT ON COLUMN clients.report_language IS 'ISO 639-1 language code for AI narrative generation (en, es, fr, de, hi, ar, ja, it, ko, zh, nl, tr, pt)';
