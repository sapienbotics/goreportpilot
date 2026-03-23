-- ============================================================
-- Migration 003: Report customization, inline editing, email delivery
-- Run via Supabase Dashboard SQL Editor
-- ============================================================

-- 1. Add report_config JSONB to clients table
--    Stores per-client section toggles, KPI selection, and template choice.
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS report_config JSONB NOT NULL DEFAULT '{
    "sections": {
      "cover_page": true,
      "executive_summary": true,
      "kpi_scorecard": true,
      "website_traffic": true,
      "meta_ads": true,
      "key_wins": true,
      "concerns": true,
      "next_steps": true,
      "custom_section": false
    },
    "kpis": {
      "website": ["sessions", "users", "conversions", "bounce_rate"],
      "ads": ["spend", "roas", "cpc", "conversions"]
    },
    "template": "monthly",
    "custom_section_title": "",
    "custom_section_text": ""
  }'::jsonb;

-- 2. Add user_edits JSONB to reports table
--    Stores manual text overrides per narrative section.
--    user_edits keys match ai_narrative keys (executive_summary, etc.).
ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS user_edits JSONB DEFAULT '{}'::jsonb;

-- 3. Add agency / email settings to profiles table
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS agency_name    TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS agency_email   TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS sender_name    TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS reply_to_email TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS email_footer   TEXT DEFAULT '';

-- 4. Extend report_deliveries for multi-recipient email tracking
--    Adds columns needed by the email delivery endpoint.
ALTER TABLE report_deliveries
  ADD COLUMN IF NOT EXISTS user_id         UUID REFERENCES auth.users(id),
  ADD COLUMN IF NOT EXISTS recipient_emails JSONB,         -- list of email addresses sent to
  ADD COLUMN IF NOT EXISTS resend_id       TEXT,           -- Resend API email ID
  ADD COLUMN IF NOT EXISTS error_message   TEXT;           -- failure details
