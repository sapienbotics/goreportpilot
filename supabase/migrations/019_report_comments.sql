-- ============================================================
-- Migration 019 — Client Comments on Shared Reports (Phase 5)
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS).
--
-- Design notes:
--  * Clients viewing a shared report can leave per-slide, per-section,
--    or general comments without signing up. Identity is captured via
--    free-text name + email (not verified — cheap feedback channel).
--  * share_id references shared_reports.id (not share_hash) so a
--    revoked / regenerated share link naturally orphans comments.
--  * user_id is denormalised from shared_reports.user_id so RLS + the
--    unread-count query in comments.py stay simple (no extra join).
--  * slide_number (int, nullable) and section_key (text, nullable)
--    are the two targeting dimensions. Both null ⇒ general feedback.
--  * is_resolved + resolved_at + resolved_by_user_id form a simple
--    triage workflow. Agency marks a comment resolved once actioned.
--  * Adds profiles.comment_notifications_enabled so the agency can
--    mute per-comment emails without disabling the whole feature.
-- ============================================================

CREATE TABLE IF NOT EXISTS report_comments (
  id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  share_id             UUID        NOT NULL REFERENCES shared_reports(id) ON DELETE CASCADE,
  report_id            UUID        NOT NULL REFERENCES reports(id)        ON DELETE CASCADE,
  user_id              UUID        NOT NULL REFERENCES profiles(id)       ON DELETE CASCADE,
  client_name          TEXT        NOT NULL,
  client_email         TEXT        NOT NULL,
  slide_number         INTEGER,
  section_key          TEXT,
  comment_text         TEXT        NOT NULL,
  is_resolved          BOOLEAN     NOT NULL DEFAULT FALSE,
  resolved_at          TIMESTAMPTZ,
  resolved_by_user_id  UUID        REFERENCES profiles(id) ON DELETE SET NULL,
  commenter_ip         VARCHAR(45),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Length guards: keep comments sane, fail fast on abuse.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'report_comments_text_len_check') THEN
    ALTER TABLE report_comments
      ADD CONSTRAINT report_comments_text_len_check
      CHECK (char_length(comment_text) BETWEEN 1 AND 2000);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'report_comments_name_len_check') THEN
    ALTER TABLE report_comments
      ADD CONSTRAINT report_comments_name_len_check
      CHECK (char_length(client_name) BETWEEN 1 AND 120);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'report_comments_email_len_check') THEN
    ALTER TABLE report_comments
      ADD CONSTRAINT report_comments_email_len_check
      CHECK (char_length(client_email) BETWEEN 3 AND 254);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_report_comments_share     ON report_comments(share_id);
CREATE INDEX IF NOT EXISTS idx_report_comments_report    ON report_comments(report_id);
CREATE INDEX IF NOT EXISTS idx_report_comments_user      ON report_comments(user_id);
CREATE INDEX IF NOT EXISTS idx_report_comments_unresolved
  ON report_comments(user_id, is_resolved)
  WHERE is_resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_report_comments_created   ON report_comments(created_at DESC);

-- ============================================================
-- Row-Level Security
-- ============================================================
ALTER TABLE report_comments ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'report_comments' AND policyname = 'Agency can view own comments'
  ) THEN
    CREATE POLICY "Agency can view own comments"
      ON report_comments FOR SELECT
      USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'report_comments' AND policyname = 'Agency can update own comments'
  ) THEN
    CREATE POLICY "Agency can update own comments"
      ON report_comments FOR UPDATE
      USING (auth.uid() = user_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'report_comments' AND policyname = 'Agency can delete own comments'
  ) THEN
    CREATE POLICY "Agency can delete own comments"
      ON report_comments FOR DELETE
      USING (auth.uid() = user_id);
  END IF;

  -- Public insert — service_role bypasses RLS anyway, but keep the
  -- policy explicit for defence in depth if anon key is ever used.
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'report_comments' AND policyname = 'Public can post comments'
  ) THEN
    CREATE POLICY "Public can post comments"
      ON report_comments FOR INSERT
      WITH CHECK (true);
  END IF;
END $$;

-- ============================================================
-- Opt-out toggle for per-comment email notifications.
-- Default TRUE — agencies that want the feedback surface by default.
-- ============================================================
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS comment_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE;
