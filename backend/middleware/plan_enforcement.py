"""
Plan enforcement helpers.
Check subscription status and plan limits before allowing actions.
"""
import logging
from datetime import datetime, timezone

from services.plans import get_client_limit, get_goal_limit, check_feature, get_plan
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


def get_internal_user_ids() -> set[str]:
    """
    All profile ids with is_internal=true, for excluding owner accounts from
    admin revenue analytics (MRR, conversion, churn) — never appear as a
    paying customer in numbers meant to describe real users. Not used for
    access gating; see _is_internal_account for that.
    """
    try:
        supabase = get_supabase_admin()
        result = supabase.table("profiles").select("id").eq("is_internal", True).execute()
        return {row["id"] for row in (result.data or [])}
    except Exception:
        logger.exception("get_internal_user_ids failed")
        return set()


def _is_internal_account(user_id: str) -> bool:
    """
    True for the product owner's own accounts (profiles.is_internal).

    DB-only flag — see migration 021. A trigger on profiles pins the column
    for any role other than service_role/postgres, so this can never be set
    by a user through any path (the FastAPI backend, a direct PostgREST
    call, or the Supabase JS client), regardless of what this function does.
    Fails closed: any error here means "not internal", never the reverse.
    """
    try:
        supabase = get_supabase_admin()
        result = (
            supabase.table("profiles")
            .select("is_internal")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return bool(result and result.data and result.data.get("is_internal"))
    except Exception:
        logger.exception("IS_INTERNAL_CHECK_FAILED user_id=%s", user_id)
        return False


def get_user_subscription(user_id: str) -> dict:
    """
    Return the user's active subscription row, auto-creating a trial if none exists.
    Also checks whether a trial has expired and updates the status accordingly.

    Internal (owner) accounts get plan/status overridden to a fully active
    Agency subscription before returning, regardless of what's underneath.
    This is the single seam every access check in the app reads through
    (can_use_feature, can_create_client, the report-generation gate, the
    billing/dashboard/goals routers) — none of them need their own
    is_internal check as a result. Every other field (trial_ends_at, id,
    created_at, ...) is left as whatever the real underlying row says, so
    anything that displays subscription details shows an honest picture;
    only the two fields that actually gate access are overridden.
    """
    from datetime import timedelta

    supabase = get_supabase_admin()

    # maybe_single() returns None (not a result object) when no row is found
    # in some supabase-py versions — guard against that explicitly.
    existing: dict | None = None
    try:
        result = (
            supabase.table("subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        existing = result.data if result else None
    except Exception as exc:
        logger.error("Subscription query failed: %s", exc)
        existing = None

    if not existing:
        # Auto-create a 14-day trial subscription
        trial_sub = {
            "user_id": user_id,
            "plan": "trial",
            "status": "trialing",
            "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        }
        try:
            ins = supabase.table("subscriptions").insert(trial_sub).execute()
            sub = ins.data[0] if (ins and ins.data) else trial_sub
        except Exception as exc:
            logger.error("Trial subscription creation failed: %s", exc)
            sub = trial_sub
    else:
        sub = existing

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

    if _is_internal_account(user_id):
        return {**sub, "plan": "agency", "status": "active"}

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


def effective_goal_limit(sub: dict) -> int:
    """
    Phase 6 — resolve the goal limit for a subscription, accounting for trial.
    Trial users (status == 'trialing') get the Pro-equivalent limit (3) during
    their 14 days so they can evaluate Goals & Alerts properly; this drops to
    the plan's configured limit the moment they convert or the trial expires.
    """
    if sub.get("status") == "trialing":
        return get_goal_limit("pro")
    return get_goal_limit(sub.get("plan", "trial"))


def can_create_goal(user_id: str, client_id: str) -> tuple[bool, str]:
    """
    Phase 6 — enforce per-client goal limits.
    Starter = 1, Pro = 3, Agency = unlimited (999). Trial users get Pro's
    limit of 3 during the 14-day trial (see effective_goal_limit).
    Count is scoped per client (not per user), so one client's goals don't
    eat into another client's quota.
    """
    supabase = get_supabase_admin()
    sub = get_user_subscription(user_id)

    if sub.get("status") in ("expired", "cancelled"):
        return False, "Your subscription has expired. Please upgrade to continue."

    limit = effective_goal_limit(sub)
    plan  = sub.get("plan", "trial")

    count_result = (
        supabase.table("goals")
        .select("id", count="exact")
        .eq("client_id", client_id)
        .eq("user_id", user_id)
        .execute()
    )
    current_count = count_result.count or 0

    if current_count >= limit:
        is_trial = sub.get("status") == "trialing"
        plan_cfg = get_plan(plan)
        display  = "Trial" if is_trial else plan_cfg.get("display_name", plan.capitalize())
        return (
            False,
            f"You've reached the {display} plan's goal limit "
            f"({current_count}/{limit} goals on this client). Upgrade to add more.",
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
