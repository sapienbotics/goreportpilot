"""
Plan enforcement helpers.
Check subscription status and plan limits before allowing actions.
"""
import logging
from datetime import datetime, timezone

from services.plans import get_client_limit, check_feature, get_plan
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


def get_user_subscription(user_id: str) -> dict:
    """
    Return the user's active subscription row, auto-creating a trial if none exists.
    Also checks whether a trial has expired and updates the status accordingly.
    """
    supabase = get_supabase_admin()
    result = (
        supabase.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        # Auto-create a 14-day trial subscription
        trial_sub = {
            "user_id": user_id,
            "plan": "trial",
            "status": "trialing",
            "trial_ends_at": (
                datetime.now(timezone.utc).replace(tzinfo=None)
                # Use raw ISO string — Supabase handles timezones
            ).isoformat() + "Z",
        }
        # Recalculate with timedelta
        from datetime import timedelta
        trial_end = datetime.now(timezone.utc) + timedelta(days=14)
        trial_sub["trial_ends_at"] = trial_end.isoformat()

        ins = supabase.table("subscriptions").insert(trial_sub).execute()
        return ins.data[0] if ins.data else trial_sub

    sub = result.data

    # Check if trial has expired
    if sub.get("status") == "trialing" and sub.get("trial_ends_at"):
        try:
            trial_end = datetime.fromisoformat(sub["trial_ends_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > trial_end:
                supabase.table("subscriptions").update(
                    {"status": "expired"}
                ).eq("id", sub["id"]).execute()
                sub["status"] = "expired"
        except Exception as exc:
            logger.warning("Could not parse trial_ends_at: %s", exc)

    return sub


def can_create_client(user_id: str) -> tuple[bool, str]:
    """
    Return (True, "") if the user can create another client,
    or (False, reason) if they've hit their plan limit.
    """
    supabase = get_supabase_admin()
    sub = get_user_subscription(user_id)

    if sub.get("status") in ("expired", "cancelled"):
        return False, "Your subscription has expired. Please upgrade to continue."

    plan = sub.get("plan", "trial")
    limit = get_client_limit(plan)

    count_result = (
        supabase.table("clients")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    current_count = count_result.count or 0

    if current_count >= limit:
        return (
            False,
            f"You've reached your plan limit ({current_count}/{limit} clients). "
            "Upgrade to add more.",
        )

    return True, ""


def can_use_feature(user_id: str, feature: str) -> tuple[bool, str]:
    """
    Return (True, "") if the user's plan includes the given feature,
    or (False, reason) if not.
    """
    sub = get_user_subscription(user_id)

    if sub.get("status") in ("expired", "cancelled"):
        return False, "Your subscription has expired."

    plan = sub.get("plan", "trial")
    if check_feature(plan, feature):
        return True, ""

    plan_cfg = get_plan(plan)
    display = plan_cfg.get("display_name", plan.capitalize())
    return False, f"This feature requires an upgrade. You're on the {display} plan."
