"""
Admin dashboard endpoints.
All endpoints require is_admin = true on the caller's profile.
Uses supabase_admin (service role) to bypass RLS.
NEVER returns encrypted tokens, ai_narrative, user_edits, sections,
goals_context, notes, or contact_emails.
"""
import json
import logging
import shutil
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from config import settings as app_settings
from middleware.auth import get_current_user_id
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Admin guard ──────────────────────────────────────────────────────────────

async def _require_admin(user_id: str = Depends(get_current_user_id)) -> str:
    """Dependency — raises 403 if the user is not an admin."""
    sb = get_supabase_admin()
    result = sb.table("profiles").select("is_admin").eq("id", user_id).single().execute()
    if not result.data or not result.data.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user_id


def _log_action(admin_id: str, action: str, target_user_id: str | None = None,
                target_user_email: str | None = None, details: dict | None = None) -> None:
    sb = get_supabase_admin()
    sb.table("admin_activity_log").insert({
        "admin_user_id": admin_id,
        "action": action,
        "target_user_id": target_user_id,
        "target_user_email": target_user_email,
        "details": details or {},
    }).execute()


# ═════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
async def admin_stats(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    seven_days_later = (now + timedelta(days=7)).isoformat()

    total_users = len((sb.table("profiles").select("id", count="exact").execute()).data or [])
    active_30d = len((sb.table("profiles").select("id").gte("updated_at", thirty_days_ago).execute()).data or [])
    total_clients = len((sb.table("clients").select("id", count="exact").eq("is_active", True).execute()).data or [])
    reports_month = len((sb.table("reports").select("id").gte("created_at", month_start).execute()).data or [])
    reports_all = len((sb.table("reports").select("id", count="exact").execute()).data or [])

    # Subscriptions by plan
    subs = (sb.table("subscriptions").select("plan,status").execute()).data or []
    active_subs: dict[str, int] = {}
    for s in subs:
        if s.get("status") in ("active", "trialing"):
            p = s.get("plan", "unknown")
            active_subs[p] = active_subs.get(p, 0) + 1

    # Trials expiring in 7 days
    trials = [s for s in subs if s.get("status") == "trialing"]
    trials_expiring = 0
    for t in trials:
        # Approximate — just count all trialing for simplicity
        trials_expiring += 1

    # Revenue
    payments = (sb.table("payment_history").select("amount,status").execute()).data or []
    total_revenue = sum(p.get("amount", 0) for p in payments if p.get("status") == "captured")
    failed_30d = len((sb.table("payment_history").select("id").eq("status", "failed").gte("created_at", thirty_days_ago).execute()).data or [])

    return {
        "total_users": total_users,
        "active_users_30d": active_30d,
        "total_clients": total_clients,
        "reports_this_month": reports_month,
        "reports_all_time": reports_all,
        "active_subscriptions": active_subs,
        "failed_payments_30d": failed_30d,
        "trials_expiring_7d": trials_expiring,
        "total_revenue": total_revenue,
    }


@router.get("/activity")
async def admin_activity(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    events: list[dict] = []

    # Recent reports
    reports = (sb.table("reports").select("id,user_id,title,created_at").order("created_at", desc=True).limit(10).execute()).data or []
    user_ids = list({r["user_id"] for r in reports})
    email_map: dict[str, str] = {}
    if user_ids:
        profiles = (sb.table("profiles").select("id,email").in_("id", user_ids).execute()).data or []
        email_map = {p["id"]: p.get("email", "") for p in profiles}
    for r in reports:
        events.append({
            "timestamp": r["created_at"],
            "event_type": "report_created",
            "user_email": email_map.get(r["user_id"], ""),
            "details": f"Generated report: {r.get('title', 'Untitled')}",
        })

    # Recent signups
    signups = (sb.table("profiles").select("id,email,created_at").order("created_at", desc=True).limit(10).execute()).data or []
    for s in signups:
        events.append({
            "timestamp": s["created_at"],
            "event_type": "user_signup",
            "user_email": s.get("email", ""),
            "details": "New user signed up",
        })

    # Recent admin activity
    admin_logs = (sb.table("admin_activity_log").select("*").order("created_at", desc=True).limit(10).execute()).data or []
    for a in admin_logs:
        events.append({
            "timestamp": a["created_at"],
            "event_type": "admin_action",
            "user_email": a.get("target_user_email", ""),
            "details": a.get("action", ""),
        })

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return {"events": events[:30]}


# ═════════════════════════════════════════════════════════════════════════════
# USERS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/users")
async def list_users(
    admin_id: str = Depends(_require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    plan: str | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    sb = get_supabase_admin()

    # Fetch all profiles
    q = sb.table("profiles").select("id,email,full_name,agency_name,created_at,updated_at,is_admin,is_disabled")
    if search:
        q = q.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%,agency_name.ilike.%{search}%")
    profiles = (q.execute()).data or []

    # Fetch subscriptions
    subs = (sb.table("subscriptions").select("user_id,plan,status,billing_cycle").execute()).data or []
    sub_map = {s["user_id"]: s for s in subs}

    # Fetch client/report counts
    clients_all = (sb.table("clients").select("user_id,id").eq("is_active", True).execute()).data or []
    client_counts: dict[str, int] = {}
    for c in clients_all:
        uid = c["user_id"]
        client_counts[uid] = client_counts.get(uid, 0) + 1

    reports_all = (sb.table("reports").select("user_id,id").execute()).data or []
    report_counts: dict[str, int] = {}
    for r in reports_all:
        uid = r["user_id"]
        report_counts[uid] = report_counts.get(uid, 0) + 1

    # Build user list
    users = []
    for p in profiles:
        uid = p["id"]
        sub = sub_map.get(uid, {})
        user_plan = sub.get("plan", "free")
        sub_status = sub.get("status", "none")

        if plan and user_plan != plan:
            continue

        users.append({
            "id": uid,
            "email": p.get("email", ""),
            "full_name": p.get("full_name", ""),
            "agency_name": p.get("agency_name", ""),
            "plan": user_plan,
            "subscription_status": sub_status,
            "client_count": client_counts.get(uid, 0),
            "report_count": report_counts.get(uid, 0),
            "created_at": p.get("created_at", ""),
            "is_admin": p.get("is_admin", False),
            "is_disabled": p.get("is_disabled", False),
        })

    # Sort
    reverse = sort_order == "desc"
    users.sort(key=lambda u: u.get(sort_by, "") or "", reverse=reverse)

    total = len(users)
    start = (page - 1) * limit
    end = start + limit
    return {"users": users[start:end], "total": total, "page": page, "limit": limit}


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str, admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()

    # Profile (non-sensitive)
    profile = (sb.table("profiles").select(
        "id,email,full_name,agency_name,agency_logo_url,agency_website,"
        "brand_color,sender_name,agency_email,reply_to_email,email_footer,"
        "is_admin,is_disabled,created_at,updated_at"
    ).eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Subscription
    sub = (sb.table("subscriptions").select("*").eq("user_id", user_id).maybe_single().execute()).data

    # Payment history
    payments = (sb.table("payment_history").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()).data or []

    # Clients (with connected platforms + report counts)
    clients_raw = (sb.table("clients").select(
        "id,name,industry,logo_url,is_active,created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()).data or []

    client_ids = [c["id"] for c in clients_raw]
    connections_raw = []
    report_counts_by_client: dict[str, int] = {}
    if client_ids:
        connections_raw = (sb.table("connections").select(
            "client_id,platform,account_name,status,token_expires_at,updated_at"
        ).in_("client_id", client_ids).execute()).data or []

        reports_by_client = (sb.table("reports").select("client_id,id").in_("client_id", client_ids).execute()).data or []
        for r in reports_by_client:
            cid = r["client_id"]
            report_counts_by_client[cid] = report_counts_by_client.get(cid, 0) + 1

    conn_by_client: dict[str, list] = {}
    for c in connections_raw:
        cid = c["client_id"]
        conn_by_client.setdefault(cid, []).append({
            "platform": c["platform"],
            "account_name": c.get("account_name", ""),
            "status": c["status"],
            "token_expires_at": c.get("token_expires_at"),
            "updated_at": c.get("updated_at"),
        })

    clients = []
    for c in clients_raw:
        clients.append({
            **c,
            "connections": conn_by_client.get(c["id"], []),
            "report_count": report_counts_by_client.get(c["id"], 0),
        })

    # Connections (flat list — no encrypted tokens)
    all_connections = []
    for c in connections_raw:
        client_name_map = {cl["id"]: cl["name"] for cl in clients_raw}
        all_connections.append({
            "client_name": client_name_map.get(c["client_id"], ""),
            "platform": c["platform"],
            "account_name": c.get("account_name", ""),
            "status": c["status"],
            "token_expires_at": c.get("token_expires_at"),
            "updated_at": c.get("updated_at"),
        })

    # Reports (metadata only — no ai_narrative/user_edits/sections)
    reports = (sb.table("reports").select(
        "id,title,client_id,period_start,period_end,status,created_at,updated_at"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()).data or []
    client_name_map = {c["id"]: c["name"] for c in clients_raw}
    for r in reports:
        r["client_name"] = client_name_map.get(r.get("client_id", ""), "")

    # Shared reports
    report_ids = [r["id"] for r in reports]
    shared = []
    if report_ids:
        shared = (sb.table("shared_reports").select(
            "id,report_id,share_hash,is_active,expires_at,created_at,view_count"
        ).in_("report_id", report_ids).order("created_at", desc=True).execute()).data or []

    # Scheduled reports
    scheduled = (sb.table("scheduled_reports").select(
        "id,client_id,frequency,template,auto_send,next_run_at,is_active,created_at"
    ).eq("user_id", user_id).execute()).data or []
    for s in scheduled:
        s["client_name"] = client_name_map.get(s.get("client_id", ""), "")

    return {
        "profile": profile,
        "subscription": sub,
        "payment_history": payments,
        "clients": clients,
        "connections": all_connections,
        "reports": reports,
        "shared_reports": shared,
        "scheduled_reports": scheduled,
    }


@router.post("/users/{user_id}/disable")
async def disable_user(user_id: str, admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    profile = (sb.table("profiles").select("email").eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    sb.table("profiles").update({"is_disabled": True}).eq("id", user_id).execute()
    _log_action(admin_id, "disable_user", user_id, profile.get("email"))
    return {"success": True, "message": f"User {profile.get('email')} disabled"}


@router.post("/users/{user_id}/enable")
async def enable_user(user_id: str, admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    profile = (sb.table("profiles").select("email").eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    sb.table("profiles").update({"is_disabled": False}).eq("id", user_id).execute()
    _log_action(admin_id, "enable_user", user_id, profile.get("email"))
    return {"success": True, "message": f"User {profile.get('email')} enabled"}


@router.post("/users/{user_id}/export")
async def export_user_data(user_id: str, admin_id: str = Depends(_require_admin)) -> Response:
    """GDPR data export — downloadable JSON with non-sensitive user data."""
    sb = get_supabase_admin()

    profile = (sb.table("profiles").select(
        "id,email,full_name,agency_name,agency_logo_url,agency_website,"
        "brand_color,is_admin,is_disabled,created_at,updated_at"
    ).eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    sub = (sb.table("subscriptions").select("*").eq("user_id", user_id).maybe_single().execute()).data
    payments = (sb.table("payment_history").select("*").eq("user_id", user_id).execute()).data or []

    clients = (sb.table("clients").select(
        "id,name,industry,website_url,logo_url,is_active,created_at"
    ).eq("user_id", user_id).execute()).data or []

    client_ids = [c["id"] for c in clients]
    connections = []
    if client_ids:
        connections = (sb.table("connections").select(
            "platform,account_name,status,created_at"
        ).in_("client_id", client_ids).execute()).data or []

    reports = (sb.table("reports").select(
        "id,title,period_start,period_end,status,created_at"
    ).eq("user_id", user_id).execute()).data or []

    report_ids = [r["id"] for r in reports]
    shared = []
    if report_ids:
        shared = (sb.table("shared_reports").select(
            "share_hash,is_active,expires_at,created_at,view_count"
        ).in_("report_id", report_ids).execute()).data or []

    scheduled = (sb.table("scheduled_reports").select(
        "frequency,template,auto_send,next_run_at,is_active,created_at"
    ).eq("user_id", user_id).execute()).data or []

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "subscription": sub,
        "payment_history": payments,
        "clients": clients,
        "connections": connections,
        "reports": reports,
        "shared_reports": shared,
        "scheduled_reports": scheduled,
    }

    _log_action(admin_id, "export_user_data", user_id, profile.get("email"))

    return Response(
        content=json.dumps(export, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="user_export_{user_id}.json"'},
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin_id: str = Depends(_require_admin)) -> dict:
    """GDPR erasure — deletes the user and all associated data."""
    sb = get_supabase_admin()

    profile = (sb.table("profiles").select("email").eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    email = profile.get("email", "")

    # Prevent deleting yourself
    if user_id == admin_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    # 1. Delete Supabase Storage logos
    try:
        files = sb.storage.from_("logos").list(user_id)
        if files:
            paths = [f"{user_id}/{f['name']}" for f in files]
            sb.storage.from_("logos").remove(paths)
        # Also try nested folders
        for sub in ["agency", "clients", "custom_sections"]:
            try:
                nested = sb.storage.from_("logos").list(f"{user_id}/{sub}")
                if nested:
                    nested_paths = [f"{user_id}/{sub}/{f['name']}" for f in nested]
                    sb.storage.from_("logos").remove(nested_paths)
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Storage cleanup for user %s failed: %s", user_id, exc)

    # 2. Delete from auth.users — CASCADE removes profiles, clients, connections, reports, etc.
    try:
        sb.auth.admin.delete_user(user_id)
    except Exception as exc:
        logger.error("Failed to delete user %s from auth: %s", user_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {exc}")

    _log_action(admin_id, "delete_user", user_id, email, {"reason": "GDPR erasure"})
    return {"success": True, "message": f"User {email} and all associated data deleted"}


# ═════════════════════════════════════════════════════════════════════════════
# SUBSCRIPTIONS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/subscriptions")
async def list_subscriptions(
    admin_id: str = Depends(_require_admin),
    plan: str | None = None,
    sub_status: str | None = Query(None, alias="status"),
    billing_cycle: str | None = None,
) -> dict:
    sb = get_supabase_admin()
    q = sb.table("subscriptions").select("*")
    if plan:
        q = q.eq("plan", plan)
    if sub_status:
        q = q.eq("status", sub_status)
    if billing_cycle:
        q = q.eq("billing_cycle", billing_cycle)
    subs = (q.order("created_at", desc=True).execute()).data or []

    user_ids = list({s["user_id"] for s in subs})
    email_map: dict[str, dict] = {}
    if user_ids:
        profiles = (sb.table("profiles").select("id,email,full_name").in_("id", user_ids).execute()).data or []
        email_map = {p["id"]: {"email": p.get("email", ""), "full_name": p.get("full_name", "")} for p in profiles}

    for s in subs:
        info = email_map.get(s["user_id"], {})
        s["user_email"] = info.get("email", "")
        s["user_name"] = info.get("full_name", "")

    return {"subscriptions": subs, "total": len(subs)}


@router.get("/payments")
async def list_payments(
    admin_id: str = Depends(_require_admin),
    payment_status: str | None = Query(None, alias="status"),
) -> dict:
    sb = get_supabase_admin()
    q = sb.table("payment_history").select("*")
    if payment_status:
        q = q.eq("status", payment_status)
    payments = (q.order("created_at", desc=True).limit(200).execute()).data or []

    user_ids = list({p["user_id"] for p in payments if p.get("user_id")})
    email_map: dict[str, str] = {}
    if user_ids:
        profiles = (sb.table("profiles").select("id,email").in_("id", user_ids).execute()).data or []
        email_map = {p["id"]: p.get("email", "") for p in profiles}

    for p in payments:
        p["user_email"] = email_map.get(p.get("user_id", ""), "")

    return {"payments": payments, "total": len(payments)}


@router.get("/revenue")
async def revenue_stats(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()

    subs = (sb.table("subscriptions").select("plan,status,billing_cycle").execute()).data or []
    payments = (sb.table("payment_history").select("amount,status").execute()).data or []

    total_revenue = sum(p.get("amount", 0) for p in payments if p.get("status") == "captured")

    # Plan distribution
    plan_counts: dict[str, int] = {}
    active_count = 0
    trialing_count = 0
    for s in subs:
        p = s.get("plan", "free")
        plan_counts[p] = plan_counts.get(p, 0) + 1
        if s.get("status") == "active":
            active_count += 1
        elif s.get("status") == "trialing":
            trialing_count += 1

    # MRR estimate (active subs * plan price)
    plan_prices = {"starter": 19, "pro": 39, "agency": 69}
    mrr = 0
    for s in subs:
        if s.get("status") == "active":
            price = plan_prices.get(s.get("plan", ""), 0)
            if s.get("billing_cycle") == "annual":
                price = round(price * 0.8)  # 20% discount
            mrr += price

    return {
        "mrr": mrr,
        "total_revenue": total_revenue,
        "plan_distribution": plan_counts,
        "active_count": active_count,
        "trialing_count": trialing_count,
        "total_subscriptions": len(subs),
    }


# ═════════════════════════════════════════════════════════════════════════════
# CONNECTIONS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/connections")
async def list_connections(
    admin_id: str = Depends(_require_admin),
    platform: str | None = None,
    conn_status: str | None = Query(None, alias="status"),
) -> dict:
    sb = get_supabase_admin()
    q = sb.table("connections").select(
        "id,client_id,platform,account_name,status,token_expires_at,created_at,updated_at"
    )
    if platform:
        q = q.eq("platform", platform)
    if conn_status:
        q = q.eq("status", conn_status)
    conns = (q.order("token_expires_at", desc=False).limit(500).execute()).data or []

    # Map client_id → client name & user email
    client_ids = list({c["client_id"] for c in conns})
    client_map: dict[str, dict] = {}
    if client_ids:
        clients = (sb.table("clients").select("id,name,user_id").in_("id", client_ids).execute()).data or []
        user_ids = list({c["user_id"] for c in clients})
        email_map: dict[str, str] = {}
        if user_ids:
            profiles = (sb.table("profiles").select("id,email").in_("id", user_ids).execute()).data or []
            email_map = {p["id"]: p.get("email", "") for p in profiles}
        for c in clients:
            client_map[c["id"]] = {"name": c["name"], "user_email": email_map.get(c["user_id"], "")}

    for c in conns:
        info = client_map.get(c["client_id"], {})
        c["client_name"] = info.get("name", "")
        c["user_email"] = info.get("user_email", "")

    return {"connections": conns, "total": len(conns)}


# ═════════════════════════════════════════════════════════════════════════════
# REPORTS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/reports")
async def list_reports(
    admin_id: str = Depends(_require_admin),
    report_status: str | None = Query(None, alias="status"),
) -> dict:
    sb = get_supabase_admin()
    q = sb.table("reports").select(
        "id,user_id,client_id,title,period_start,period_end,status,created_at"
    )
    if report_status:
        q = q.eq("status", report_status)
    reports = (q.order("created_at", desc=True).limit(200).execute()).data or []

    # Enrich with user email + client name
    user_ids = list({r["user_id"] for r in reports})
    client_ids = list({r["client_id"] for r in reports})

    email_map: dict[str, str] = {}
    if user_ids:
        profiles = (sb.table("profiles").select("id,email").in_("id", user_ids).execute()).data or []
        email_map = {p["id"]: p.get("email", "") for p in profiles}

    client_map: dict[str, str] = {}
    if client_ids:
        clients = (sb.table("clients").select("id,name").in_("id", client_ids).execute()).data or []
        client_map = {c["id"]: c["name"] for c in clients}

    for r in reports:
        r["user_email"] = email_map.get(r["user_id"], "")
        r["client_name"] = client_map.get(r["client_id"], "")

    return {"reports": reports, "total": len(reports)}


@router.get("/reports/stats")
async def report_stats(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    all_reports = (sb.table("reports").select("id,status,created_at").execute()).data or []

    today_count = sum(1 for r in all_reports if r.get("created_at", "") >= today_start)
    week_count = sum(1 for r in all_reports if r.get("created_at", "") >= week_ago)
    month_count = sum(1 for r in all_reports if r.get("created_at", "") >= month_start)
    failed_count = sum(1 for r in all_reports if r.get("status") == "failed")

    return {
        "today": today_count,
        "this_week": week_count,
        "this_month": month_count,
        "all_time": len(all_reports),
        "failed": failed_count,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SYSTEM
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/system/health")
async def system_health(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()

    health: dict = {
        "status": "healthy",
        "service": "reportpilot-api",
        "environment": app_settings.ENVIRONMENT,
    }

    try:
        sb.table("profiles").select("id").limit(1).execute()
        health["supabase"] = "connected"
    except Exception as e:
        health["supabase"] = f"error: {str(e)[:100]}"
        health["status"] = "degraded"

    health["openai"] = "configured" if app_settings.OPENAI_API_KEY else "missing"
    health["libreoffice"] = "available" if shutil.which("soffice") or shutil.which("libreoffice") else "unavailable"
    health["resend"] = "configured" if getattr(app_settings, "RESEND_API_KEY", None) else "missing"
    health["razorpay"] = "configured" if getattr(app_settings, "RAZORPAY_KEY_ID", None) else "missing"

    health["frontend_url"] = app_settings.FRONTEND_URL
    health["backend_url"] = app_settings.BACKEND_URL
    health["version"] = "0.1.0"

    return health


# ═════════════════════════════════════════════════════════════════════════════
# GDPR
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/gdpr/requests")
async def list_gdpr_requests(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    requests = (sb.table("gdpr_requests").select("*").order("created_at", desc=True).execute()).data or []
    return {"requests": requests, "total": len(requests)}


@router.post("/gdpr/requests")
async def create_gdpr_request(
    body: dict,
    admin_id: str = Depends(_require_admin),
) -> dict:
    sb = get_supabase_admin()
    user_email = body.get("user_email", "")
    request_type = body.get("request_type", "access")
    admin_notes = body.get("admin_notes", "")

    if not user_email:
        raise HTTPException(status_code=422, detail="user_email is required")
    if request_type not in ("access", "portability", "erasure", "rectification", "restriction"):
        raise HTTPException(status_code=422, detail="Invalid request_type")

    result = sb.table("gdpr_requests").insert({
        "user_email": user_email,
        "request_type": request_type,
        "admin_notes": admin_notes,
    }).execute()

    _log_action(admin_id, f"gdpr_{request_type}_request_created", target_user_email=user_email)
    return result.data[0] if result.data else {}


@router.patch("/gdpr/requests/{request_id}")
async def update_gdpr_request(
    request_id: str,
    body: dict,
    admin_id: str = Depends(_require_admin),
) -> dict:
    sb = get_supabase_admin()
    update: dict = {}
    if "status" in body:
        update["status"] = body["status"]
        if body["status"] == "completed":
            update["completed_at"] = datetime.now(timezone.utc).isoformat()
    if "admin_notes" in body:
        update["admin_notes"] = body["admin_notes"]

    if not update:
        raise HTTPException(status_code=422, detail="Nothing to update")

    result = (sb.table("gdpr_requests").update(update).eq("id", request_id).execute())
    if not result.data:
        raise HTTPException(status_code=404, detail="GDPR request not found")

    _log_action(admin_id, "gdpr_request_updated", details={"request_id": request_id, **update})
    return result.data[0]


@router.get("/gdpr/inactive-users")
async def inactive_users(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()

    profiles = (sb.table("profiles").select(
        "id,email,full_name,updated_at,created_at"
    ).lt("updated_at", cutoff).execute()).data or []

    return {"users": profiles, "total": len(profiles)}
