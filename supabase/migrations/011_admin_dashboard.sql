-- ============================================================================
-- Migration 011: Admin Dashboard — profiles flags, activity log, GDPR requests
-- ============================================================================
-- Run this in the Supabase SQL Editor manually.
-- ============================================================================

-- Add admin and disabled flags to profiles
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_disabled BOOLEAN DEFAULT false;

-- Set admin for operator account
UPDATE profiles SET is_admin = true WHERE email = 'sapienbotics@gmail.com';

-- Admin activity log (no RLS policies = service role only)
CREATE TABLE IF NOT EXISTS admin_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID REFERENCES auth.users(id),
    action TEXT NOT NULL,
    target_user_id UUID,
    target_user_email TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE admin_activity_log ENABLE ROW LEVEL SECURITY;

-- GDPR request tracker (no RLS policies = service role only)
CREATE TABLE IF NOT EXISTS gdpr_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email TEXT NOT NULL,
    request_type TEXT NOT NULL CHECK (request_type IN ('access', 'portability', 'erasure', 'rectification', 'restriction')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'rejected')),
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
ALTER TABLE gdpr_requests ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_admin_activity_created ON admin_activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gdpr_requests_status ON gdpr_requests(status);
CREATE INDEX IF NOT EXISTS idx_profiles_is_admin ON profiles(is_admin) WHERE is_admin = true;
CREATE INDEX IF NOT EXISTS idx_profiles_is_disabled ON profiles(is_disabled) WHERE is_disabled = true;
