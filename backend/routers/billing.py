"""
Billing & subscription endpoints.
Handles Razorpay subscription management, payment verification, and webhooks.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from services.plans import PLANS, get_plan
from middleware.auth import get_current_user_id
from middleware.plan_enforcement import get_user_subscription
from services.supabase_client import get_supabase_admin
import services.razorpay_service as rzp_svc

limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)
router = APIRouter()


def get_plan_from_razorpay_plan_id(razorpay_plan_id: str) -> tuple[str, str]:
    """Returns (plan_name, billing_cycle) from Razorpay plan ID.

    Covers all 12 plan IDs: 6 INR + 6 USD.
    """
    plan_map: dict[str, tuple[str, str]] = {}
    # INR plans
    for pid, val in [
        (settings.RAZORPAY_PLAN_STARTER_MONTHLY, ("starter", "monthly")),
        (settings.RAZORPAY_PLAN_STARTER_ANNUAL, ("starter", "annual")),
        (settings.RAZORPAY_PLAN_PRO_MONTHLY, ("pro", "monthly")),
        (settings.RAZORPAY_PLAN_PRO_ANNUAL, ("pro", "annual")),
        (settings.RAZORPAY_PLAN_AGENCY_MONTHLY, ("agency", "monthly")),
        (settings.RAZORPAY_PLAN_AGENCY_ANNUAL, ("agency", "annual")),
        # USD plans
        (settings.RAZORPAY_PLAN_STARTER_MONTHLY_USD, ("starter", "monthly")),
        (settings.RAZORPAY_PLAN_STARTER_ANNUAL_USD, ("starter", "annual")),
        (settings.RAZORPAY_PLAN_PRO_MONTHLY_USD, ("pro", "monthly")),
        (settings.RAZORPAY_PLAN_PRO_ANNUAL_USD, ("pro", "annual")),
        (settings.RAZORPAY_PLAN_AGENCY_MONTHLY_USD, ("agency", "monthly")),
        (settings.RAZORPAY_PLAN_AGENCY_ANNUAL_USD, ("agency", "annual")),
    ]:
        if pid:  # skip empty env vars
            plan_map[pid] = val
    return plan_map.get(razorpay_plan_id, ("trial", "monthly"))


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CreateSubscriptionPayload(BaseModel):
    plan: str
    billing_cycle: str = "monthly"
    currency: str = "INR"  # "INR" or "USD"


class VerifyPaymentPayload(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


class ChangePlanPayload(BaseModel):
    plan: str
    billing_cycle: str = "monthly"
    currency: str = "INR"


# ---------------------------------------------------------------------------
# GET /api/billing/subscription
# ---------------------------------------------------------------------------

@router.get("/subscription")
async def get_subscription(user_id: str = Depends(get_current_user_id)) -> dict:
    """Return the user's current subscription status, plan details, and usage stats."""
    supabase = get_supabase_admin()
    sub = get_user_subscription(user_id)
    plan_name = sub.get("plan", "trial")
    plan_cfg = get_plan(plan_name)

    # Count active clients
    count_result = (
        supabase.table("clients")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    client_count = count_result.count or 0
    client_limit = plan_cfg.get("client_limit", 3)

    trial_ends_at = sub.get("trial_ends_at")
    trial_days_remaining = None
    if trial_ends_at and sub.get("status") == "trialing":
        try:
            trial_end_dt = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = trial_end_dt - now
            trial_days_remaining = max(0, delta.days)
        except Exception:
            pass

    return {
        "plan": plan_name,
        "display_name": plan_cfg.get("display_name", plan_name.capitalize()),
        "status": sub.get("status", "trialing"),
        "billing_cycle": sub.get("billing_cycle", "monthly"),
        "client_count": client_count,
        "client_limit": client_limit,
        "current_period_start": sub.get("current_period_start"),
        "current_period_end": sub.get("current_period_end"),
        "trial_ends_at": trial_ends_at,
        "trial_days_remaining": trial_days_remaining,
        "cancelled_at": sub.get("cancelled_at"),
        "cancel_at_period_end": sub.get("cancel_at_period_end", False),
        "features": plan_cfg.get("features", {}),
        "can_create_client": client_count < client_limit and sub.get("status") not in ("expired", "cancelled"),
        "razorpay_subscription_id": sub.get("razorpay_subscription_id"),
        "pricing": {
            "monthly_inr": plan_cfg.get("monthly_price_inr"),
            "annual_inr": plan_cfg.get("annual_price_inr"),
            "monthly_usd": plan_cfg.get("monthly_price_usd"),
            "annual_usd": plan_cfg.get("annual_price_usd"),
        },
    }


# ---------------------------------------------------------------------------
# POST /api/billing/create-subscription
# ---------------------------------------------------------------------------

@router.post("/create-subscription")
@limiter.limit("5/minute")
async def create_subscription(
    request: Request,
    payload: CreateSubscriptionPayload,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Create a Razorpay subscription for the user.
    Returns subscription_id and razorpay_key_id for frontend checkout.
    """
    if payload.plan not in ("starter", "pro", "agency"):
        raise HTTPException(status_code=400, detail="Invalid plan")
    if payload.billing_cycle not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="Invalid billing cycle")
    if payload.currency not in ("INR", "USD"):
        raise HTTPException(status_code=400, detail="Invalid currency. Use INR or USD.")

    # Determine Razorpay plan ID from env — use USD suffixed keys when currency is USD
    usd_suffix = "_USD" if payload.currency == "USD" else ""
    plan_key = f"RAZORPAY_PLAN_{payload.plan.upper()}_{payload.billing_cycle.upper()}{usd_suffix}"
    razorpay_plan_id = getattr(settings, plan_key, "") or ""
    if not razorpay_plan_id:
        raise HTTPException(
            status_code=503,
            detail=f"Razorpay plan ID not configured for {payload.plan}/{payload.billing_cycle}. "
                   "Add the plan ID to backend .env once you create plans in Razorpay dashboard.",
        )

    supabase = get_supabase_admin()

    # Get or create Razorpay customer
    sub = get_user_subscription(user_id)
    razorpay_customer_id = sub.get("razorpay_customer_id")
    if not razorpay_customer_id:
        # Fetch user email from Supabase auth
        user_result = supabase.auth.admin.get_user_by_id(user_id)
        email = user_result.user.email if user_result.user else ""
        name = email.split("@")[0] if email else "User"
        customer = rzp_svc.create_customer(email=email, name=name)
        if customer:
            razorpay_customer_id = customer.get("id")
            supabase.table("subscriptions").update(
                {"razorpay_customer_id": razorpay_customer_id}
            ).eq("user_id", user_id).execute()

    if not razorpay_customer_id:
        raise HTTPException(status_code=503, detail="Failed to create Razorpay customer. Check API keys.")

    subscription = rzp_svc.create_subscription(
        plan_id=razorpay_plan_id,
        customer_id=razorpay_customer_id,
    )
    if not subscription:
        raise HTTPException(status_code=503, detail="Failed to create Razorpay subscription. Check API keys.")

    razorpay_subscription_id = subscription.get("id")

    # Store ONLY Razorpay IDs. Do NOT write plan or billing_cycle here.
    # The plan is set ONLY after payment is confirmed (verify-payment or
    # webhook). This prevents users from getting plan access just by
    # initiating checkout and then cancelling the payment modal.
    supabase.table("subscriptions").update(
        {
            "razorpay_subscription_id": razorpay_subscription_id,
            "razorpay_plan_id": razorpay_plan_id,
            "updated_at": datetime.utcnow().isoformat(),
        }
    ).eq("user_id", user_id).execute()

    return {
        "subscription_id": razorpay_subscription_id,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    }


# ---------------------------------------------------------------------------
# POST /api/billing/verify-payment
# ---------------------------------------------------------------------------

@router.post("/verify-payment")
async def verify_payment(
    payload: VerifyPaymentPayload,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Verify Razorpay payment signature and activate subscription."""
    # Verify signature using order_id = subscription_id for recurring payments
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or ""
    if key_secret:
        import hmac as hmac_lib, hashlib
        body = f"{payload.razorpay_payment_id}|{payload.razorpay_subscription_id}"
        expected = hmac_lib.new(
            key_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac_lib.compare_digest(expected, payload.razorpay_signature):
            raise HTTPException(status_code=400, detail="Invalid payment signature")

    supabase = get_supabase_admin()
    now = datetime.utcnow()

    # Fetch current subscription to get the razorpay_plan_id for reverse lookup
    sub_result = (
        supabase.table("subscriptions")
        .select("id,razorpay_plan_id")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    sub_data = sub_result.data if sub_result else None
    sub_id = sub_data.get("id") if sub_data else None
    razorpay_plan_id = sub_data.get("razorpay_plan_id", "") if sub_data else ""

    # Derive plan and billing_cycle from the Razorpay plan ID — this is the
    # ONLY place (along with webhooks) where plan/billing_cycle get written.
    plan_name, billing_cycle = get_plan_from_razorpay_plan_id(razorpay_plan_id)

    supabase.table("subscriptions").update(
        {
            "plan": plan_name,
            "billing_cycle": billing_cycle,
            "status": "active",
            "razorpay_subscription_id": payload.razorpay_subscription_id,
            "last_payment_at": now.isoformat(),
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "payment_failed_count": 0,
            "updated_at": now.isoformat(),
        }
    ).eq("user_id", user_id).execute()

    # Log the initial payment
    try:
        supabase.table("payment_history").insert({
            "user_id": user_id,
            "subscription_id": sub_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "amount": 0,  # Will be updated by webhook with actual amount
            "currency": "INR",
            "status": "captured",
            "plan": plan_name,
            "description": f"Subscription activated — {plan_name} plan",
        }).execute()
    except Exception as exc:
        logger.warning("Failed to log initial payment: %s", exc)

    logger.info("Subscription activated for user %s (plan=%s, cycle=%s)", user_id, plan_name, billing_cycle)
    return {"success": True, "status": "active"}


# ---------------------------------------------------------------------------
# POST /api/billing/change-plan
# ---------------------------------------------------------------------------

@router.post("/change-plan")
async def change_plan(
    request: Request,
    payload: ChangePlanPayload,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Cancel current subscription and create a new one for the target plan."""
    sub = get_user_subscription(user_id)
    current_rzp_sub_id = sub.get("razorpay_subscription_id")

    # Cancel current subscription at end of period if active
    if current_rzp_sub_id and sub.get("status") == "active":
        rzp_svc.cancel_subscription(current_rzp_sub_id, cancel_at_end=False)

    # Create new subscription (pass request through for rate limiter)
    return await create_subscription(request, payload, user_id)


# ---------------------------------------------------------------------------
# POST /api/billing/cancel
# ---------------------------------------------------------------------------

@router.post("/cancel")
async def cancel_subscription_endpoint(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Cancel subscription at the end of the current billing period."""
    sub = get_user_subscription(user_id)
    razorpay_sub_id = sub.get("razorpay_subscription_id")

    if razorpay_sub_id:
        rzp_svc.cancel_subscription(razorpay_sub_id, cancel_at_end=True)

    supabase = get_supabase_admin()
    now = datetime.utcnow()
    supabase.table("subscriptions").update(
        {
            "cancel_at_period_end": True,
            "cancelled_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    ).eq("user_id", user_id).execute()

    return {"success": True, "cancel_at_period_end": True}


# ---------------------------------------------------------------------------
# GET /api/billing/payment-history
# ---------------------------------------------------------------------------

@router.get("/payment-history")
async def get_payment_history(user_id: str = Depends(get_current_user_id)) -> dict:
    """Return the user's payment history."""
    supabase = get_supabase_admin()
    result = (
        supabase.table("payment_history")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"payments": result.data or []}


# ---------------------------------------------------------------------------
# POST /api/webhooks/razorpay  (PUBLIC — no auth)
# ---------------------------------------------------------------------------

@router.post("/webhooks/razorpay", include_in_schema=False)
async def razorpay_webhook(request: Request) -> dict:
    """
    Public webhook endpoint for Razorpay events.
    Verifies signature, then handles subscription lifecycle events.
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not rzp_svc.verify_webhook_signature(body, signature):
        logger.warning("Invalid Razorpay webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    import json
    try:
        event = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = event.get("event")
    payload = event.get("payload", {})
    supabase = get_supabase_admin()
    now = datetime.utcnow()

    logger.info("Razorpay webhook: %s", event_type)

    try:
        if event_type == "subscription.activated":
            sub_entity = payload.get("subscription", {}).get("entity", {})
            rzp_sub_id = sub_entity.get("id")
            rzp_plan_id = sub_entity.get("plan_id", "")
            if rzp_sub_id:
                plan_name, billing_cycle = get_plan_from_razorpay_plan_id(rzp_plan_id)
                supabase.table("subscriptions").update(
                    {
                        "plan": plan_name,
                        "billing_cycle": billing_cycle,
                        "status": "active",
                        "current_period_start": now.isoformat(),
                        "current_period_end": (now + timedelta(days=30)).isoformat(),
                        "updated_at": now.isoformat(),
                    }
                ).eq("razorpay_subscription_id", rzp_sub_id).execute()

        elif event_type == "subscription.charged":
            sub_entity = payload.get("subscription", {}).get("entity", {})
            payment_entity = payload.get("payment", {}).get("entity", {})
            rzp_sub_id = sub_entity.get("id")
            rzp_plan_id = sub_entity.get("plan_id", "")
            if rzp_sub_id:
                plan_name, billing_cycle = get_plan_from_razorpay_plan_id(rzp_plan_id)
                # Update subscription period and plan (belt-and-suspenders)
                supabase.table("subscriptions").update(
                    {
                        "plan": plan_name,
                        "billing_cycle": billing_cycle,
                        "status": "active",
                        "last_payment_at": now.isoformat(),
                        "current_period_start": now.isoformat(),
                        "current_period_end": (now + timedelta(days=30)).isoformat(),
                        "payment_failed_count": 0,
                        "updated_at": now.isoformat(),
                    }
                ).eq("razorpay_subscription_id", rzp_sub_id).execute()

                # Find user and log payment
                sub_result = (
                    supabase.table("subscriptions")
                    .select("id, user_id, razorpay_plan_id")
                    .eq("razorpay_subscription_id", rzp_sub_id)
                    .maybe_single()
                    .execute()
                )
                if sub_result.data:
                    supabase.table("payment_history").insert(
                        {
                            "user_id": sub_result.data["user_id"],
                            "subscription_id": sub_result.data["id"],
                            "razorpay_payment_id": payment_entity.get("id"),
                            "amount": payment_entity.get("amount", 0),
                            "currency": payment_entity.get("currency", "INR"),
                            "status": "captured",
                            "plan": plan_name,
                            "description": f"Subscription payment — {plan_name} plan",
                        }
                    ).execute()

        elif event_type == "subscription.cancelled":
            rzp_sub_id = payload.get("subscription", {}).get("entity", {}).get("id")
            if rzp_sub_id:
                supabase.table("subscriptions").update(
                    {
                        "status": "cancelled",
                        "cancelled_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    }
                ).eq("razorpay_subscription_id", rzp_sub_id).execute()

        elif event_type == "subscription.paused":
            rzp_sub_id = payload.get("subscription", {}).get("entity", {}).get("id")
            if rzp_sub_id:
                supabase.table("subscriptions").update(
                    {"status": "paused", "updated_at": now.isoformat()}
                ).eq("razorpay_subscription_id", rzp_sub_id).execute()

        elif event_type == "payment.failed":
            payment_entity = payload.get("payment", {}).get("entity", {})
            rzp_sub_id = payment_entity.get("subscription_id")
            if rzp_sub_id:
                # Increment failure count
                sub_result = (
                    supabase.table("subscriptions")
                    .select("id, user_id, plan, payment_failed_count")
                    .eq("razorpay_subscription_id", rzp_sub_id)
                    .maybe_single()
                    .execute()
                )
                if sub_result.data:
                    failed_count = (sub_result.data.get("payment_failed_count") or 0) + 1
                    new_status = "past_due" if failed_count < 3 else "past_due"
                    supabase.table("subscriptions").update(
                        {
                            "status": new_status,
                            "payment_failed_count": failed_count,
                            "updated_at": now.isoformat(),
                        }
                    ).eq("id", sub_result.data["id"]).execute()

                    # Log failed payment
                    supabase.table("payment_history").insert(
                        {
                            "user_id": sub_result.data["user_id"],
                            "subscription_id": sub_result.data["id"],
                            "razorpay_payment_id": payment_entity.get("id"),
                            "amount": payment_entity.get("amount", 0),
                            "currency": payment_entity.get("currency", "INR"),
                            "status": "failed",
                            "plan": sub_result.data.get("plan"),
                            "description": "Payment failed",
                        }
                    ).execute()

    except Exception as exc:
        logger.error("Error processing Razorpay webhook %s: %s", event_type, exc)

    return {"status": "ok"}
