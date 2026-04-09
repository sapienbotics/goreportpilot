"""
Dashboard stats endpoint.
Returns aggregated metrics for the dashboard home page.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from middleware.auth import get_current_user_id
from middleware.plan_enforcement import get_user_subscription
from services.plans import get_client_limit
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


def _time_ago(iso: str) -> str:
    """Return a human-readable relative time string."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m}m ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h}h ago"
        d = seconds // 86400
        return f"{d}d ago"
    except Exception:
        return ""


@router.get("/stats")
async def get_dashboard_stats(user_id: str = Depends(get_current_user_id)) -> dict:
    """Return aggregated metrics for the authenticated user's dashboard."""
    try:
        return await _build_dashboard_stats(user_id)
    except Exception as exc:
        logger.error("Dashboard stats error for user %s: %s", user_id, exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to load dashboard stats. Please try again."},
        )


async def _build_dashboard_stats(user_id: str) -> dict:
    """Internal helper — builds the full stats dict."""
    supabase = get_supabase_admin()
    now = datetime.now(timezone.utc)

    # ── Subscription / plan ──────────────────────────────────────────────────
    sub = get_user_subscription(user_id)
    plan = sub.get("plan", "trial")
    client_limit = get_client_limit(plan)

    # ── Clients ──────────────────────────────────────────────────────────────
    clients_result = (
        supabase.table("clients")
        .select("id, name, created_at")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )
    clients = clients_result.data or []
    total_clients = len(clients)
    client_ids = [c["id"] for c in clients]
    client_map = {c["id"]: c["name"] for c in clients}

    # ── Reports ──────────────────────────────────────────────────────────────
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    reports_result = (
        supabase.table("reports")
        .select("id, client_id, title, status, created_at, period_start, period_end")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    all_reports = reports_result.data or []
    reports_all_time = len(all_reports)
    reports_this_month = sum(
        1 for r in all_reports
        if r.get("created_at", "") >= month_start.isoformat()
    )

    # ── Scheduled reports due this week ──────────────────────────────────────
    week_end = now + timedelta(days=7)
    scheduled_result = (
        supabase.table("scheduled_reports")
        .select("id, client_id, frequency, next_run_at, template")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    scheduled = scheduled_result.data or []
    due_this_week = []
    for s in scheduled:
        next_run = s.get("next_run_at")
        if next_run and now.isoformat() <= next_run <= week_end.isoformat():
            due_this_week.append({
                "client_name": client_map.get(s["client_id"], "Unknown Client"),
                "frequency": s.get("frequency", ""),
                "next_run_at": next_run,
                "template": s.get("template", "full"),
            })

    # ── Connection health ─────────────────────────────────────────────────────
    connections: list[dict] = []
    if client_ids:
        connections_result = (
            supabase.table("connections")
            .select("id, client_id, platform, status, account_name")
            .in_("client_id", client_ids)
            .execute()
        )
        connections = connections_result.data or []

    health: dict[str, dict] = {}
    for conn in connections:
        platform = conn.get("platform", "unknown")
        if platform not in health:
            health[platform] = {"connected": 0, "healthy": 0, "issues": 0}
        health[platform]["connected"] += 1
        if conn.get("status") == "active":
            health[platform]["healthy"] += 1
        else:
            health[platform]["issues"] += 1

    # ── Recent activity ───────────────────────────────────────────────────────
    activity = []

    # Recent reports (up to 3)
    for r in all_reports[:3]:
        client_name = client_map.get(r["client_id"], "Unknown Client")
        activity.append({
            "type": "report_generated",
            "description": f"Report generated for {client_name}",
            "time": _time_ago(r["created_at"]),
            "created_at": r["created_at"],
        })

    # Recent clients (up to 2)
    for c in clients[:2]:
        activity.append({
            "type": "client_added",
            "description": f'Client "{c["name"]}" added',
            "time": _time_ago(c["created_at"]),
            "created_at": c["created_at"],
        })

    # Recent connections (up to 2)
    if connections:
        for conn in connections[:2]:
            platform_label = {"ga4": "Google Analytics", "meta_ads": "Meta Ads"}.get(
                conn.get("platform", ""), conn.get("platform", "")
            )
            activity.append({
                "type": "connection_added",
                "description": f"{platform_label} connected",
                "time": "",
                "created_at": "0",
            })

    # Sort by created_at descending, keep top 5
    activity.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    activity = activity[:5]

    # ── Onboarding status ──────────────────────────────────────────────────
    total_connections = len(connections)
    onboarding = {
        "has_client": total_clients >= 1,
        "has_connection": total_connections >= 1,
        "has_report": reports_all_time >= 1,
        "complete": total_clients >= 1 and total_connections >= 1 and reports_all_time >= 1,
    }

    return {
        "total_clients": total_clients,
        "client_limit": client_limit,
        "reports_this_month": reports_this_month,
        "reports_all_time": reports_all_time,
        "reports_due_this_week": due_this_week,
        "connection_health": health,
        "recent_activity": activity,
        "onboarding": onboarding,
    }
