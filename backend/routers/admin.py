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


def _safe_parse_dt(val: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime, or return None."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
async def admin_stats(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()

    profiles = (sb.table("profiles").select("id").execute()).data or []
    total_users = len(profiles)
    active_30d = len((sb.table("profiles").select("id").gte("updated_at", thirty_days_ago).execute()).data or [])
    total_clients = len((sb.table("clients").select("id").eq("is_active", True).execute()).data or [])
    reports_month = len((sb.table("reports").select("id").gte("created_at", month_start).execute()).data or [])
    reports_all = len((sb.table("reports").select("id").execute()).data or [])

    # Subscriptions by plan — count active + trialing
    subs = (sb.table("subscriptions").select("plan,status,billing_cycle").execute()).data or []
    active_subs: dict[str, int] = {}
    trialing_count = 0
    for s in subs:
        if s.get("status") in ("active", "trialing"):
            p = s.get("plan", "unknown")
            active_subs[p] = active_subs.get(p, 0) + 1
        if s.get("status") == "trialing":
            trialing_count += 1

    # Revenue + failed payments
    payments = (sb.table("payment_history").select("amount,status,created_at").execute()).data or []
    total_revenue = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "captured")
    failed_30d = sum(1 for p in payments if p.get("status") == "failed" and (p.get("created_at", "") >= thirty_days_ago))

    return {
        "total_users": total_users,
        "active_users_30d": active_30d,
        "total_clients": total_clients,
        "reports_this_month": reports_month,
        "reports_all_time": reports_all,
        "active_subscriptions": active_subs,
        "failed_payments_30d": failed_30d,
        "trials_expiring_7d": trialing_count,
        "total_revenue": total_revenue,
    }


@router.get("/activity")
async def admin_activity(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    events: list[dict] = []

    # Build a master email map from profiles
    all_profiles = (sb.table("profiles").select("id,email,full_name,created_at").execute()).data or []
    email_map: dict[str, str] = {p["id"]: p.get("email", "") for p in all_profiles}
    name_map: dict[str, str] = {p["id"]: p.get("full_name", "") for p in all_profiles}

    # Signups
    for p in sorted(all_profiles, key=lambda x: x.get("created_at", ""), reverse=True)[:10]:
        events.append({
            "timestamp": p["created_at"],
            "event_type": "user_signup",
            "user_email": p.get("email", ""),
            "details": f"New signup: {p.get('full_name') or p.get('email', '')}",
        })

    # Reports
    reports = (sb.table("reports").select("id,user_id,client_id,title,created_at").order("created_at", desc=True).limit(10).execute()).data or []
    client_ids = list({r["client_id"] for r in reports})
    client_map: dict[str, str] = {}
    if client_ids:
        cl = (sb.table("clients").select("id,name").in_("id", client_ids).execute()).data or []
        client_map = {c["id"]: c["name"] for c in cl}
    for r in reports:
        cname = client_map.get(r["client_id"], "")
        events.append({
            "timestamp": r["created_at"],
            "event_type": "report_created",
            "user_email": email_map.get(r["user_id"], ""),
            "details": f"Report: {r.get('title', '')} for {cname}",
        })

    # Subscriptions
    subs = (sb.table("subscriptions").select("user_id,plan,status,created_at").order("created_at", desc=True).limit(10).execute()).data or []
    for s in subs:
        events.append({
            "timestamp": s["created_at"],
            "event_type": "subscription_created",
            "user_email": email_map.get(s["user_id"], ""),
            "details": f"Subscription: {s.get('plan', '')} ({s.get('status', '')})",
        })

    # Connections
    conns = (sb.table("connections").select("client_id,platform,created_at").order("created_at", desc=True).limit(10).execute()).data or []
    # need client → user mapping
    conn_client_ids = list({c["client_id"] for c in conns})
    conn_client_map: dict[str, dict] = {}
    if conn_client_ids:
        cl = (sb.table("clients").select("id,name,user_id").in_("id", conn_client_ids).execute()).data or []
        conn_client_map = {c["id"]: {"name": c["name"], "user_id": c["user_id"]} for c in cl}
    for c in conns:
        info = conn_client_map.get(c["client_id"], {})
        events.append({
            "timestamp": c["created_at"],
            "event_type": "connection_created",
            "user_email": email_map.get(info.get("user_id", ""), ""),
            "details": f"Connected {c.get('platform', '')} for {info.get('name', '')}",
        })

    # Payments
    payments = (sb.table("payment_history").select("user_id,amount,status,created_at").order("created_at", desc=True).limit(10).execute()).data or []
    for p in payments:
        evt_type = "payment_captured" if p.get("status") == "captured" else "payment_failed"
        events.append({
            "timestamp": p["created_at"],
            "event_type": evt_type,
            "user_email": email_map.get(p.get("user_id", ""), ""),
            "details": f"Payment {'captured' if p.get('status') == 'captured' else 'failed'}: \u20b9{p.get('amount', 0)}",
        })

    # Admin log
    admin_logs = (sb.table("admin_activity_log").select("*").order("created_at", desc=True).limit(10).execute()).data or []
    for a in admin_logs:
        events.append({
            "timestamp": a["created_at"],
            "event_type": "admin_action",
            "user_email": a.get("target_user_email", ""),
            "details": a.get("action", ""),
        })

    events.sort(key=lambda e: e.get("timestamp", "") or "", reverse=True)
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
    sub_status: str | None = Query(None, alias="status"),
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    sb = get_supabase_admin()

    # Fetch ALL profiles — no filters that would exclude users
    q = sb.table("profiles").select("id,email,full_name,agency_name,created_at,updated_at,is_admin,is_disabled")
    if search:
        q = q.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%,agency_name.ilike.%{search}%")
    profiles = (q.execute()).data or []

    if not profiles:
        return {"users": [], "total": 0, "page": page, "limit": limit}

    # LEFT JOIN: fetch ALL subscriptions and map by user_id
    subs = (sb.table("subscriptions").select("user_id,plan,status,billing_cycle").execute()).data or []
    sub_map: dict[str, dict] = {}
    for s in subs:
        sub_map[s["user_id"]] = s

    # Counts
    clients_all = (sb.table("clients").select("user_id").eq("is_active", True).execute()).data or []
    client_counts: dict[str, int] = {}
    for c in clients_all:
        client_counts[c["user_id"]] = client_counts.get(c["user_id"], 0) + 1

    reports_all = (sb.table("reports").select("user_id").execute()).data or []
    report_counts: dict[str, int] = {}
    for r in reports_all:
        report_counts[r["user_id"]] = report_counts.get(r["user_id"], 0) + 1

    # Build user list — every profile appears regardless of subscription
    users = []
    for p in profiles:
        uid = p["id"]
        sub = sub_map.get(uid)
        user_plan = sub.get("plan", "free") if sub else "free"
        user_status = sub.get("status", "none") if sub else "none"

        # Apply filters
        if plan and user_plan != plan:
            continue
        if sub_status and user_status != sub_status:
            continue

        users.append({
            "id": uid,
            "email": p.get("email", ""),
            "full_name": p.get("full_name", ""),
            "agency_name": p.get("agency_name", ""),
            "plan": user_plan,
            "subscription_status": user_status,
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

    profile = (sb.table("profiles").select(
        "id,email,full_name,agency_name,agency_logo_url,agency_website,"
        "brand_color,sender_name,agency_email,reply_to_email,email_footer,"
        "is_admin,is_disabled,created_at,updated_at"
    ).eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    sub = (sb.table("subscriptions").select("*").eq("user_id", user_id).maybe_single().execute()).data
    payments = (sb.table("payment_history").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()).data or []

    clients_raw = (sb.table("clients").select(
        "id,name,industry,logo_url,is_active,created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()).data or []

    client_ids = [c["id"] for c in clients_raw]
    connections_raw: list[dict] = []
    report_counts_by_client: dict[str, int] = {}
    if client_ids:
        connections_raw = (sb.table("connections").select(
            "client_id,platform,account_name,status,token_expires_at,updated_at"
        ).in_("client_id", client_ids).execute()).data or []

        reports_by_client = (sb.table("reports").select("client_id").in_("client_id", client_ids).execute()).data or []
        for r in reports_by_client:
            cid = r["client_id"]
            report_counts_by_client[cid] = report_counts_by_client.get(cid, 0) + 1

    conn_by_client: dict[str, list] = {}
    for c in connections_raw:
        conn_by_client.setdefault(c["client_id"], []).append({
            "platform": c["platform"],
            "account_name": c.get("account_name", ""),
            "status": c["status"],
            "token_expires_at": c.get("token_expires_at"),
            "updated_at": c.get("updated_at"),
        })

    clients = [{**c, "connections": conn_by_client.get(c["id"], []),
                "report_count": report_counts_by_client.get(c["id"], 0)} for c in clients_raw]

    client_name_map = {c["id"]: c["name"] for c in clients_raw}
    all_connections = [{
        "client_name": client_name_map.get(c["client_id"], ""),
        "platform": c["platform"],
        "account_name": c.get("account_name", ""),
        "status": c["status"],
        "token_expires_at": c.get("token_expires_at"),
        "updated_at": c.get("updated_at"),
    } for c in connections_raw]

    reports = (sb.table("reports").select(
        "id,title,client_id,period_start,period_end,status,created_at,updated_at"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()).data or []
    for r in reports:
        r["client_name"] = client_name_map.get(r.get("client_id", ""), "")

    report_ids = [r["id"] for r in reports]
    shared: list[dict] = []
    if report_ids:
        shared = (sb.table("shared_reports").select(
            "id,report_id,share_hash,is_active,expires_at,created_at,view_count"
        ).in_("report_id", report_ids).order("created_at", desc=True).execute()).data or []

    scheduled = (sb.table("scheduled_reports").select(
        "id,client_id,frequency,template,auto_send,next_run_at,is_active,created_at"
    ).eq("user_id", user_id).execute()).data or []
    for s in scheduled:
        s["client_name"] = client_name_map.get(s.get("client_id", ""), "")

    return {
        "profile": profile, "subscription": sub, "payment_history": payments,
        "clients": clients, "connections": all_connections, "reports": reports,
        "shared_reports": shared, "scheduled_reports": scheduled,
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
    sb = get_supabase_admin()
    profile = (sb.table("profiles").select(
        "id,email,full_name,agency_name,agency_logo_url,agency_website,"
        "brand_color,is_admin,is_disabled,created_at,updated_at"
    ).eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    sub = (sb.table("subscriptions").select("*").eq("user_id", user_id).maybe_single().execute()).data
    payments = (sb.table("payment_history").select("*").eq("user_id", user_id).execute()).data or []
    clients = (sb.table("clients").select("id,name,industry,website_url,logo_url,is_active,created_at").eq("user_id", user_id).execute()).data or []
    client_ids = [c["id"] for c in clients]
    connections: list[dict] = []
    if client_ids:
        connections = (sb.table("connections").select("platform,account_name,status,created_at").in_("client_id", client_ids).execute()).data or []
    reports = (sb.table("reports").select("id,title,period_start,period_end,status,created_at").eq("user_id", user_id).execute()).data or []
    report_ids = [r["id"] for r in reports]
    shared: list[dict] = []
    if report_ids:
        shared = (sb.table("shared_reports").select("share_hash,is_active,expires_at,created_at,view_count").in_("report_id", report_ids).execute()).data or []
    scheduled = (sb.table("scheduled_reports").select("frequency,template,auto_send,next_run_at,is_active,created_at").eq("user_id", user_id).execute()).data or []

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile, "subscription": sub, "payment_history": payments,
        "clients": clients, "connections": connections, "reports": reports,
        "shared_reports": shared, "scheduled_reports": scheduled,
    }
    _log_action(admin_id, "export_user_data", user_id, profile.get("email"))
    return Response(
        content=json.dumps(export, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="user_export_{user_id}.json"'},
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    profile = (sb.table("profiles").select("email").eq("id", user_id).single().execute()).data
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    email = profile.get("email", "")
    if user_id == admin_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    try:
        for sub in ["agency", "clients", "custom_sections"]:
            try:
                nested = sb.storage.from_("logos").list(f"{user_id}/{sub}")
                if nested:
                    sb.storage.from_("logos").remove([f"{user_id}/{sub}/{f['name']}" for f in nested])
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Storage cleanup for user %s failed: %s", user_id, exc)

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

    # Enrich with user email/name
    user_ids = list({s["user_id"] for s in subs})
    profile_map: dict[str, dict] = {}
    if user_ids:
        profiles = (sb.table("profiles").select("id,email,full_name").in_("id", user_ids).execute()).data or []
        profile_map = {p["id"]: {"email": p.get("email", ""), "full_name": p.get("full_name", "")} for p in profiles}

    for s in subs:
        info = profile_map.get(s["user_id"], {})
        s["user_email"] = info.get("email", "")
        s["user_name"] = info.get("full_name", "")

    return {"subscriptions": subs, "total": len(subs)}


@router.get("/payments")
async def list_payments(
    admin_id: str = Depends(_require_admin),
    payment_status: str | None = Query(None, alias="status"),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    sb = get_supabase_admin()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    q = sb.table("payment_history").select("*").gte("created_at", cutoff)
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
    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()

    subs = (sb.table("subscriptions").select("plan,status,billing_cycle,created_at,cancelled_at").execute()).data or []
    payments = (sb.table("payment_history").select("amount,status,created_at").execute()).data or []

    total_revenue = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "captured")

    plan_counts: dict[str, int] = {}
    active_count = 0
    trialing_count = 0
    past_due_count = 0
    cancelled_30d = 0
    total_ever_subscribed = len(subs)
    paid_from_trial = 0

    for s in subs:
        p = s.get("plan", "free")
        plan_counts[p] = plan_counts.get(p, 0) + 1
        st = s.get("status", "")
        if st == "active":
            active_count += 1
            # Count users who moved from trial to paid
            paid_from_trial += 1
        elif st == "trialing":
            trialing_count += 1
        elif st == "past_due":
            past_due_count += 1
        elif st in ("cancelled", "canceled"):
            if s.get("cancelled_at", "") >= thirty_days_ago or s.get("created_at", "") >= thirty_days_ago:
                cancelled_30d += 1

    # MRR: plan prices in INR
    plan_prices = {"starter": 1499, "pro": 2999, "agency": 4999}
    mrr = 0
    for s in subs:
        if s.get("status") == "active":
            price = plan_prices.get(s.get("plan", ""), 0)
            if s.get("billing_cycle") == "annual":
                price = round(price * 0.8)
            mrr += price

    trial_to_paid_rate = round((paid_from_trial / max(total_ever_subscribed, 1)) * 100, 1)

    return {
        "mrr": mrr,
        "total_revenue": total_revenue,
        "plan_distribution": plan_counts,
        "active_count": active_count,
        "trialing_count": trialing_count,
        "past_due_count": past_due_count,
        "cancelled_30d": cancelled_30d,
        "trial_to_paid_rate": trial_to_paid_rate,
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
    # Don't filter by status in DB if we need effective_status filtering
    conns = (q.order("token_expires_at", desc=False).limit(500).execute()).data or []

    now = datetime.now(timezone.utc)
    seven_days = now + timedelta(days=7)

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

        # Compute effective_status based on token expiry
        exp_dt = _safe_parse_dt(c.get("token_expires_at"))
        if exp_dt and exp_dt < now:
            c["effective_status"] = "expired"
        elif exp_dt and exp_dt < seven_days:
            c["effective_status"] = "expiring_soon"
        else:
            c["effective_status"] = c.get("status", "unknown")

    # Filter by effective_status if requested
    if conn_status:
        conns = [c for c in conns if c.get("effective_status") == conn_status]

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

    user_ids = list({r["user_id"] for r in reports})
    client_ids = list({r["client_id"] for r in reports})

    email_map: dict[str, str] = {}
    if user_ids:
        profiles = (sb.table("profiles").select("id,email").in_("id", user_ids).execute()).data or []
        email_map = {p["id"]: p.get("email", "") for p in profiles}
    client_map: dict[str, str] = {}
    if client_ids:
        cl = (sb.table("clients").select("id,name").in_("id", client_ids).execute()).data or []
        client_map = {c["id"]: c["name"] for c in cl}

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

    # Need sections for template/language info
    all_reports = (sb.table("reports").select("id,status,created_at,sections").execute()).data or []

    today_count = sum(1 for r in all_reports if r.get("created_at", "") >= today_start)
    week_count = sum(1 for r in all_reports if r.get("created_at", "") >= week_ago)
    month_count = sum(1 for r in all_reports if r.get("created_at", "") >= month_start)
    failed_count = sum(1 for r in all_reports if r.get("status") == "failed")

    # Template + language distribution from sections JSONB
    template_dist: dict[str, int] = {}
    language_dist: dict[str, int] = {}
    for r in all_reports:
        sections = r.get("sections") or {}
        if isinstance(sections, dict):
            tmpl = sections.get("template") or sections.get("visual_template") or "unknown"
            template_dist[tmpl] = template_dist.get(tmpl, 0) + 1
            lang = sections.get("language") or "en"
            language_dist[lang] = language_dist.get(lang, 0) + 1

    return {
        "today": today_count,
        "this_week": week_count,
        "this_month": month_count,
        "all_time": len(all_reports),
        "failed": failed_count,
        "template_distribution": template_dist,
        "language_distribution": language_dist,
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
async def create_gdpr_request(body: dict, admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    user_email = body.get("user_email", "")
    request_type = body.get("request_type", "access")
    admin_notes = body.get("admin_notes", "")
    if not user_email:
        raise HTTPException(status_code=422, detail="user_email is required")
    if request_type not in ("access", "portability", "erasure", "rectification", "restriction"):
        raise HTTPException(status_code=422, detail="Invalid request_type")
    result = sb.table("gdpr_requests").insert({
        "user_email": user_email, "request_type": request_type, "admin_notes": admin_notes,
    }).execute()
    _log_action(admin_id, f"gdpr_{request_type}_request_created", target_user_email=user_email)
    return result.data[0] if result.data else {}


@router.patch("/gdpr/requests/{request_id}")
async def update_gdpr_request(request_id: str, body: dict, admin_id: str = Depends(_require_admin)) -> dict:
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
    result = sb.table("gdpr_requests").update(update).eq("id", request_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="GDPR request not found")
    _log_action(admin_id, "gdpr_request_updated", details={"request_id": request_id, **update})
    return result.data[0]


@router.get("/gdpr/inactive-users")
async def inactive_users(admin_id: str = Depends(_require_admin)) -> dict:
    sb = get_supabase_admin()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    profiles = (sb.table("profiles").select("id,email,full_name,updated_at,created_at").lt("updated_at", cutoff).execute()).data or []

    # Enrich with plan + counts
    user_ids = [p["id"] for p in profiles]
    sub_map: dict[str, str] = {}
    client_counts: dict[str, int] = {}
    report_counts: dict[str, int] = {}
    if user_ids:
        subs = (sb.table("subscriptions").select("user_id,plan").in_("user_id", user_ids).execute()).data or []
        sub_map = {s["user_id"]: s.get("plan", "free") for s in subs}
        clients = (sb.table("clients").select("user_id").eq("is_active", True).in_("user_id", user_ids).execute()).data or []
        for c in clients:
            client_counts[c["user_id"]] = client_counts.get(c["user_id"], 0) + 1
        reports = (sb.table("reports").select("user_id").in_("user_id", user_ids).execute()).data or []
        for r in reports:
            report_counts[r["user_id"]] = report_counts.get(r["user_id"], 0) + 1

    for p in profiles:
        p["plan"] = sub_map.get(p["id"], "free")
        p["client_count"] = client_counts.get(p["id"], 0)
        p["report_count"] = report_counts.get(p["id"], 0)

    return {"users": profiles, "total": len(profiles)}


@router.get("/gdpr/consent-records")
async def consent_records(admin_id: str = Depends(_require_admin)) -> dict:
    """All users with signup date (= consent timestamp) and email confirmation status."""
    sb = get_supabase_admin()
    profiles = (sb.table("profiles").select("id,email,full_name,created_at").order("created_at", desc=True).execute()).data or []

    # Get subscription plan for each
    user_ids = [p["id"] for p in profiles]
    sub_map: dict[str, str] = {}
    if user_ids:
        subs = (sb.table("subscriptions").select("user_id,plan").in_("user_id", user_ids).execute()).data or []
        sub_map = {s["user_id"]: s.get("plan", "free") for s in subs}

    records = []
    for p in profiles:
        records.append({
            "email": p.get("email", ""),
            "full_name": p.get("full_name", ""),
            "created_at": p.get("created_at", ""),
            "plan": sub_map.get(p["id"], "free"),
        })

    return {"records": records, "total": len(records)}
