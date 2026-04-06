-- ============================================================================
-- Migration 012: Fix subscriptions with no confirmed payment
-- ============================================================================
-- Run this in Supabase SQL Editor to clean up subscriptions where the user
-- initiated checkout but never completed payment.
-- ============================================================================

-- Reset subscriptions that have a paid plan but no corresponding captured payment
-- These users initiated Razorpay checkout but cancelled/abandoned it.
-- Set them back to trial status.
UPDATE subscriptions s
SET
    plan = 'trial',
    status = 'trialing',
    billing_cycle = 'monthly',
    razorpay_subscription_id = NULL,
    razorpay_plan_id = NULL,
    trial_ends_at = COALESCE(s.trial_ends_at, s.created_at + INTERVAL '14 days'),
    updated_at = NOW()
WHERE s.plan IN ('starter', 'pro', 'agency')
  AND s.status IN ('trialing', 'created')
  AND NOT EXISTS (
    SELECT 1 FROM payment_history ph
    WHERE ph.user_id = s.user_id
      AND ph.status = 'captured'
  );

-- Verify: show all subscriptions with their payment status
-- SELECT s.user_id, p.email, s.plan, s.status,
--        (SELECT COUNT(*) FROM payment_history ph WHERE ph.user_id = s.user_id AND ph.status = 'captured') as paid_count
-- FROM subscriptions s
-- JOIN profiles p ON p.id = s.user_id;
