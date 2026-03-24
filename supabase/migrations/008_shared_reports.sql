-- Migration 008: Shared reports and view tracking
-- Run this in Supabase Dashboard → SQL Editor

CREATE TABLE IF NOT EXISTS shared_reports (
    id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       UUID          NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_id         UUID          NOT NULL REFERENCES auth.users(id),
    share_hash      VARCHAR(32)   NOT NULL UNIQUE,
    password_hash   VARCHAR(255),
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN       DEFAULT true,
    created_at      TIMESTAMPTZ   DEFAULT now(),
    updated_at      TIMESTAMPTZ   DEFAULT now()
);

ALTER TABLE shared_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users manage own shared reports" ON shared_reports;
CREATE POLICY "Users manage own shared reports" ON shared_reports
    FOR ALL USING (auth.uid() = user_id);

-- ── View tracking ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS report_views (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    shared_report_id  UUID        NOT NULL REFERENCES shared_reports(id) ON DELETE CASCADE,
    viewer_ip         VARCHAR(45),
    user_agent        TEXT,
    device_type       VARCHAR(20),     -- 'mobile' | 'desktop' | 'tablet'
    viewed_at         TIMESTAMPTZ DEFAULT now(),
    duration_seconds  INTEGER
);

ALTER TABLE report_views ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users view own report analytics" ON report_views;
CREATE POLICY "Users view own report analytics" ON report_views
    FOR SELECT USING (
        shared_report_id IN (
            SELECT id FROM shared_reports WHERE user_id = auth.uid()
        )
    );

-- Anyone can insert a view (public report viewing)
DROP POLICY IF EXISTS "Public can log views" ON report_views;
CREATE POLICY "Public can log views" ON report_views
    FOR INSERT WITH CHECK (true);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_shared_reports_hash   ON shared_reports(share_hash);
CREATE INDEX IF NOT EXISTS idx_shared_reports_user   ON shared_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_shared_reports_report ON shared_reports(report_id);
CREATE INDEX IF NOT EXISTS idx_report_views_shared   ON report_views(shared_report_id);
CREATE INDEX IF NOT EXISTS idx_report_views_date     ON report_views(viewed_at DESC);

-- ── Updated_at trigger ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_shared_reports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_shared_reports_updated_at ON shared_reports;
CREATE TRIGGER trg_shared_reports_updated_at
    BEFORE UPDATE ON shared_reports
    FOR EACH ROW EXECUTE FUNCTION update_shared_reports_updated_at();
