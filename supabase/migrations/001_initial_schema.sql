-- ============================================================
-- ReportPilot Initial Database Schema
-- Run via Supabase Dashboard SQL Editor (copy-paste entire file)
-- Reference: docs/reportpilot-feature-design-blueprint.md § Section 9
-- ============================================================
-- Order of execution:
--   1. Tables (dependency order)
--   2. Foreign key additions
--   3. Indexes
--   4. Row-Level Security (enable + policies)
--   5. Triggers (handle_new_user, update_updated_at)
--   6. Seed data (default report template)
-- ============================================================


-- ============================================================
-- SECTION 1: TABLES
-- ============================================================

-- TABLE 1: profiles
-- Extends Supabase auth.users (1-to-1). Created automatically via trigger.
CREATE TABLE profiles (
  id                      UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email                   TEXT        NOT NULL,
  name                    TEXT,
  avatar_url              TEXT,
  plan                    TEXT        NOT NULL DEFAULT 'starter' CHECK (plan IN ('starter', 'pro', 'agency')),
  stripe_customer_id      TEXT,
  stripe_subscription_id  TEXT,
  preferences             JSONB       DEFAULT '{}',
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TABLE 2: clients
-- Each client belongs to one agency user (user_id → profiles.id).
CREATE TABLE clients (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  name                  TEXT        NOT NULL,
  industry              TEXT,
  logo_url              TEXT,
  website_url           TEXT,
  goals_context         TEXT,
  primary_contact_email TEXT,
  contact_emails        JSONB       DEFAULT '[]',
  report_schedule       JSONB       DEFAULT '{}',
  report_template_id    UUID,                        -- FK added after report_templates is created
  ai_tone               TEXT        NOT NULL DEFAULT 'professional'
                          CHECK (ai_tone IN ('professional', 'conversational', 'executive', 'data_heavy')),
  branding              JSONB       DEFAULT '{}',
  notes                 TEXT,
  is_active             BOOLEAN     NOT NULL DEFAULT true,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TABLE 3: connections
-- OAuth connections between a client and an ad/analytics platform.
CREATE TABLE connections (
  id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id               UUID        NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  platform                TEXT        NOT NULL
                            CHECK (platform IN ('ga4', 'meta_ads', 'google_ads', 'search_console', 'linkedin_ads')),
  account_id              TEXT        NOT NULL,
  account_name            TEXT,
  access_token_encrypted  TEXT        NOT NULL,
  refresh_token_encrypted TEXT,
  token_expires_at        TIMESTAMPTZ,
  token_type              TEXT        DEFAULT 'user'
                            CHECK (token_type IN ('user', 'long_lived', 'system_user')),
  status                  TEXT        NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'expiring_soon', 'expired', 'error', 'revoked')),
  last_successful_pull    TIMESTAMPTZ,
  last_error_message      TEXT,
  consecutive_failures    INTEGER     NOT NULL DEFAULT 0,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TABLE 4: data_snapshots
-- Cached metric data pulled from platforms for a given time period.
CREATE TABLE data_snapshots (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id  UUID        NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
  client_id      UUID        NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  platform       TEXT        NOT NULL,
  period_start   DATE        NOT NULL,
  period_end     DATE        NOT NULL,
  metrics        JSONB       NOT NULL DEFAULT '{}',
  raw_response   JSONB       DEFAULT '{}',
  pulled_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_valid       BOOLEAN     NOT NULL DEFAULT true
);

-- TABLE 5: report_templates
-- Reusable slide/section configurations. System defaults have user_id = NULL.
CREATE TABLE report_templates (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID        REFERENCES profiles(id) ON DELETE CASCADE,
  name              TEXT        NOT NULL,
  description       TEXT,
  sections          JSONB       NOT NULL DEFAULT '[]',
  is_system_default BOOLEAN     NOT NULL DEFAULT false,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TABLE 6: reports
-- Generated reports tied to a client and a time period.
CREATE TABLE reports (
  id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id               UUID        NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  user_id                 UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  template_id             UUID        REFERENCES report_templates(id) ON DELETE SET NULL,
  title                   TEXT        NOT NULL,
  period_start            DATE        NOT NULL,
  period_end              DATE        NOT NULL,
  comparison_period_start DATE,
  comparison_period_end   DATE,
  status                  TEXT        NOT NULL DEFAULT 'generating'
                            CHECK (status IN ('generating', 'draft', 'approved', 'sent', 'failed')),
  ai_narrative            JSONB       DEFAULT '{}',
  user_edits              JSONB       DEFAULT '{}',
  sections                JSONB       DEFAULT '[]',
  pptx_file_url           TEXT,
  pdf_file_url            TEXT,
  share_link_hash         TEXT        UNIQUE,
  share_link_password     TEXT,
  share_link_expires_at   TIMESTAMPTZ,
  sent_at                 TIMESTAMPTZ,
  opened_at               TIMESTAMPTZ,
  delivery_emails         JSONB       DEFAULT '[]',
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TABLE 7: report_deliveries
-- Individual delivery events (email sends, link accesses) for a report.
CREATE TABLE report_deliveries (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id        UUID        NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  delivery_method  TEXT        NOT NULL CHECK (delivery_method IN ('email', 'link')),
  recipient_email  TEXT,
  sent_at          TIMESTAMPTZ,
  opened_at        TIMESTAMPTZ,
  attachment_type  TEXT        CHECK (attachment_type IN ('pdf', 'pptx', 'both')),
  email_subject    TEXT,
  email_body       TEXT,
  status           TEXT        NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'sent', 'delivered', 'opened', 'bounced', 'failed'))
);

-- TABLE 8: scheduled_reports
-- Cron-style schedule for automatic report generation and optional delivery.
CREATE TABLE scheduled_reports (
  id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id            UUID        NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  user_id              UUID        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  frequency            TEXT        NOT NULL CHECK (frequency IN ('weekly', 'biweekly', 'monthly')),
  day_of_week          INTEGER     CHECK (day_of_week >= 0 AND day_of_week <= 6),
  day_of_month         INTEGER     CHECK (day_of_month >= 1 AND day_of_month <= 28),
  time_utc             TIME        NOT NULL DEFAULT '09:00:00',
  auto_send            BOOLEAN     NOT NULL DEFAULT false,
  is_active            BOOLEAN     NOT NULL DEFAULT true,
  last_generated_at    TIMESTAMPTZ,
  next_generation_at   TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- SECTION 2: FOREIGN KEY ADDITIONS
-- (Added after report_templates exists)
-- ============================================================

ALTER TABLE clients
  ADD CONSTRAINT fk_clients_report_template
  FOREIGN KEY (report_template_id)
  REFERENCES report_templates(id)
  ON DELETE SET NULL;


-- ============================================================
-- SECTION 3: INDEXES
-- ============================================================

-- clients
CREATE INDEX idx_clients_user_id      ON clients(user_id);
CREATE INDEX idx_clients_is_active    ON clients(user_id, is_active);

-- connections
CREATE INDEX idx_connections_client_id    ON connections(client_id);
CREATE INDEX idx_connections_status       ON connections(status);
CREATE INDEX idx_connections_token_expiry ON connections(token_expires_at)
  WHERE status = 'active';

-- data_snapshots
CREATE INDEX idx_data_snapshots_client_id     ON data_snapshots(client_id);
CREATE INDEX idx_data_snapshots_connection_id ON data_snapshots(connection_id);
CREATE INDEX idx_data_snapshots_period        ON data_snapshots(client_id, period_start, period_end);

-- reports
CREATE INDEX idx_reports_client_id  ON reports(client_id);
CREATE INDEX idx_reports_user_id    ON reports(user_id);
CREATE INDEX idx_reports_status     ON reports(user_id, status);
CREATE INDEX idx_reports_share_link ON reports(share_link_hash)
  WHERE share_link_hash IS NOT NULL;

-- report_deliveries
CREATE INDEX idx_report_deliveries_report_id ON report_deliveries(report_id);

-- scheduled_reports
CREATE INDEX idx_scheduled_reports_next   ON scheduled_reports(next_generation_at)
  WHERE is_active = true;
CREATE INDEX idx_scheduled_reports_client ON scheduled_reports(client_id);


-- ============================================================
-- SECTION 4: ROW-LEVEL SECURITY
-- Enable RLS on every table, then define per-table policies.
-- This ensures User A can NEVER read or modify User B's data.
-- ============================================================

ALTER TABLE profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients           ENABLE ROW LEVEL SECURITY;
ALTER TABLE connections       ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_snapshots    ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_templates  ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports           ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_reports ENABLE ROW LEVEL SECURITY;

-- PROFILES: users can only read/write their own profile row
CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

-- CLIENTS: users can only CRUD clients they own
CREATE POLICY "Users can view own clients"
  ON clients FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own clients"
  ON clients FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own clients"
  ON clients FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own clients"
  ON clients FOR DELETE
  USING (auth.uid() = user_id);

-- CONNECTIONS: users can only access connections for their own clients
CREATE POLICY "Users can view own connections"
  ON connections FOR SELECT
  USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

CREATE POLICY "Users can create connections for own clients"
  ON connections FOR INSERT
  WITH CHECK (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

CREATE POLICY "Users can update own connections"
  ON connections FOR UPDATE
  USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

CREATE POLICY "Users can delete own connections"
  ON connections FOR DELETE
  USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

-- DATA_SNAPSHOTS: users can only access snapshots for their own clients
CREATE POLICY "Users can view own data snapshots"
  ON data_snapshots FOR SELECT
  USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

CREATE POLICY "Users can create data snapshots for own clients"
  ON data_snapshots FOR INSERT
  WITH CHECK (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

-- REPORT_TEMPLATES: users can see system defaults + their own templates
CREATE POLICY "Users can view own and system templates"
  ON report_templates FOR SELECT
  USING (is_system_default = true OR user_id = auth.uid());

CREATE POLICY "Users can create own templates"
  ON report_templates FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own templates"
  ON report_templates FOR UPDATE
  USING (auth.uid() = user_id AND is_system_default = false);

CREATE POLICY "Users can delete own templates"
  ON report_templates FOR DELETE
  USING (auth.uid() = user_id AND is_system_default = false);

-- REPORTS: users can only access their own reports
CREATE POLICY "Users can view own reports"
  ON reports FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own reports"
  ON reports FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own reports"
  ON reports FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own reports"
  ON reports FOR DELETE
  USING (auth.uid() = user_id);

-- REPORT_DELIVERIES: users can access deliveries for their own reports
CREATE POLICY "Users can view own report deliveries"
  ON report_deliveries FOR SELECT
  USING (report_id IN (SELECT id FROM reports WHERE user_id = auth.uid()));

CREATE POLICY "Users can create deliveries for own reports"
  ON report_deliveries FOR INSERT
  WITH CHECK (report_id IN (SELECT id FROM reports WHERE user_id = auth.uid()));

CREATE POLICY "Users can update own report deliveries"
  ON report_deliveries FOR UPDATE
  USING (report_id IN (SELECT id FROM reports WHERE user_id = auth.uid()));

-- SCHEDULED_REPORTS: users can only manage their own schedules
CREATE POLICY "Users can view own scheduled reports"
  ON scheduled_reports FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own scheduled reports"
  ON scheduled_reports FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own scheduled reports"
  ON scheduled_reports FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own scheduled reports"
  ON scheduled_reports FOR DELETE
  USING (auth.uid() = user_id);


-- ============================================================
-- SECTION 5: TRIGGERS
-- ============================================================

-- TRIGGER: Auto-create profile row when a new auth user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- TRIGGER: Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_clients_updated_at
  BEFORE UPDATE ON clients
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_connections_updated_at
  BEFORE UPDATE ON connections
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_reports_updated_at
  BEFORE UPDATE ON reports
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


-- ============================================================
-- SECTION 6: SEED DATA
-- ============================================================

-- Default system report template (10 slides, Monthly Performance Review)
INSERT INTO report_templates (id, user_id, name, description, sections, is_system_default)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  NULL,
  'Monthly Performance Review',
  'Default 10-slide monthly report with executive summary, KPIs, channel breakdowns, AI insights, and recommendations.',
  '[
    {"type": "cover",               "title": "Cover Page",                    "enabled": true, "order": 1},
    {"type": "executive_summary",   "title": "Executive Summary",             "enabled": true, "order": 2},
    {"type": "kpi_scorecard",       "title": "KPI Scorecard",                 "enabled": true, "order": 3},
    {"type": "website_traffic",     "title": "Website Traffic & Engagement",  "enabled": true, "order": 4},
    {"type": "meta_ads",            "title": "Meta Ads Performance",          "enabled": true, "order": 5},
    {"type": "google_ads",          "title": "Google Ads Performance",        "enabled": true, "order": 6},
    {"type": "conversion_analysis", "title": "Conversion Analysis",           "enabled": true, "order": 7},
    {"type": "key_wins",            "title": "Key Wins & Highlights",         "enabled": true, "order": 8},
    {"type": "concerns",            "title": "Areas of Attention",            "enabled": true, "order": 9},
    {"type": "next_steps",          "title": "Next Steps & Action Items",     "enabled": true, "order": 10}
  ]'::jsonb,
  true
);
