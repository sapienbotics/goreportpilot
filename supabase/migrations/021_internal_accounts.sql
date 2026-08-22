-- ============================================================
-- Migration 021 — Internal (owner) account flag
-- Run manually via Supabase Dashboard → SQL Editor.
-- All additions are idempotent (IF NOT EXISTS / guarded DO blocks).
--
-- Adds profiles.is_internal: grants full Agency-tier access regardless of
-- subscription/trial state, for the product owner's own accounts. Read by
-- middleware/plan_enforcement.py:get_user_subscription() — that is the
-- single seam every access check in the app already goes through, so no
-- other gating code needs to know this column exists.
--
-- "DB-only, not settable by users" is enforced at the database layer, not
-- just by omitting the field from the API's Pydantic models. Checked first:
-- profiles' RLS policies ("Users can update own profile", USING
-- auth.uid() = id) have no column restriction, and both `anon` and
-- `authenticated` hold table-level UPDATE/INSERT grants covering every
-- column. A user could otherwise set this on their own row with a direct
-- PostgREST call using their own JWT, entirely bypassing the FastAPI
-- backend. Column-level REVOKE does not fix this: a role's privilege comes
-- from its TABLE-level grant unless that grant is replaced with an explicit
-- per-column allowlist (invasive — every legitimate column would need
-- re-enumerating). A trigger that pins the column for any non-privileged
-- role is the correct, minimal mechanism: it holds regardless of which path
-- the write comes through.
-- ============================================================

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_internal BOOLEAN NOT NULL DEFAULT FALSE;

CREATE OR REPLACE FUNCTION protect_is_internal()
RETURNS TRIGGER AS $$
BEGIN
  -- service_role = the backend's Supabase service-role key (PostgREST maps
  -- it to this Postgres role). postgres = direct admin connections (the
  -- Dashboard SQL Editor, the session-pooler connection used for manual
  -- migrations). Every other role — anon, authenticated — is an end user,
  -- however they reached the database.
  IF current_user NOT IN ('service_role', 'postgres') THEN
    IF TG_OP = 'INSERT' THEN
      NEW.is_internal := FALSE;
    ELSIF TG_OP = 'UPDATE' AND NEW.is_internal IS DISTINCT FROM OLD.is_internal THEN
      NEW.is_internal := OLD.is_internal;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = 'trg_protect_is_internal'
      AND tgrelid = 'profiles'::regclass
  ) THEN
    CREATE TRIGGER trg_protect_is_internal
      BEFORE INSERT OR UPDATE ON profiles
      FOR EACH ROW EXECUTE FUNCTION protect_is_internal();
  END IF;
END $$;


-- ── Verification ────────────────────────────────────────────────────────
-- Expect one row: column present, trigger attached.
SELECT
  (SELECT count(*) FROM information_schema.columns
    WHERE table_schema='public' AND table_name='profiles' AND column_name='is_internal') AS column_present,
  (SELECT count(*) FROM pg_trigger
    WHERE tgname='trg_protect_is_internal' AND tgrelid='profiles'::regclass) AS trigger_present;
