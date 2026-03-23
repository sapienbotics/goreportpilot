-- ============================================================
-- Migration 004 — White-label branding + Scheduled Reports
-- Run in Supabase Dashboard → SQL Editor
-- ============================================================

-- ── Agency branding + identity fields on profiles ────────────
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS agency_name     TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS agency_email    TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS agency_logo_url TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS brand_color     TEXT DEFAULT '#4338CA';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS agency_website  TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS timezone        TEXT DEFAULT 'UTC';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS default_ai_tone TEXT DEFAULT 'professional';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS notification_report_generated  BOOLEAN DEFAULT true;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS notification_connection_expired BOOLEAN DEFAULT true;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS notification_payment_failed     BOOLEAN DEFAULT true;

-- ── Email delivery settings on profiles ──────────────────────
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS sender_name    TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS reply_to_email TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS email_footer   TEXT DEFAULT '';

-- ── Client logo ──────────────────────────────────────────────
ALTER TABLE clients ADD COLUMN IF NOT EXISTS logo_url TEXT DEFAULT '';

-- ── Scheduled reports table ──────────────────────────────────
-- Creates the table only if it doesn't already exist (migration 001 may have
-- created a partial version; this ensures the full schema is present).
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID REFERENCES clients(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    frequency       TEXT NOT NULL CHECK (frequency IN ('weekly', 'biweekly', 'monthly')),
    day_of_week     INTEGER CHECK (day_of_week >= 0 AND day_of_week <= 6),
    day_of_month    INTEGER CHECK (day_of_month >= 1 AND day_of_month <= 28),
    time_utc        TEXT DEFAULT '09:00',
    template        TEXT DEFAULT 'full' CHECK (template IN ('full', 'summary', 'brief')),
    auto_send       BOOLEAN DEFAULT false,
    send_to_emails  JSONB DEFAULT '[]'::jsonb,
    is_active       BOOLEAN DEFAULT true,
    last_generated_at TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── RLS for scheduled_reports ────────────────────────────────
ALTER TABLE scheduled_reports ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'scheduled_reports'
          AND policyname = 'Users manage own scheduled reports'
    ) THEN
        CREATE POLICY "Users manage own scheduled reports"
            ON scheduled_reports
            FOR ALL
            USING (user_id = auth.uid());
    END IF;
END
$$;

-- ── Indexes ──────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_scheduled_reports_next_run
    ON scheduled_reports(next_run_at) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_scheduled_reports_user
    ON scheduled_reports(user_id);

CREATE INDEX IF NOT EXISTS idx_scheduled_reports_client
    ON scheduled_reports(client_id);
