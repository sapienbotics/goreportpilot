"""
Admin-only analytics endpoint.

Builds a single aggregate payload for the ``/admin/analytics`` dashboard
from Supabase directly — NO Google Analytics API involvement. Everything
is sourced from the tables we already own:

  profiles          — signup trend, country derivation (from timezone),
                      user identity for the top-users table
  reports           — generation trend, per-user activity counts
  clients           — per-user client count
  connections       — platform breakdown (ga4 / meta_ads / google_ads /
                      search_console / csv_*)
  subscriptions     — plan mix, MRR, funnel "paid" stage

Never returns encrypted tokens, AI narrative, user_edits, or any other
sensitive payload — the queries are scoped to ID / count fields.
"""
import logging
import traceback
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from routers.admin import _require_admin
from services.plans import PLANS
from services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# PostgREST default row cap is 1000. Anything larger must be paginated
# via `.range(start, end)`. This helper walks the full table for us so
# the analytics numbers don't silently truncate once we cross 1000 users
# or 1000 reports.
_PAGE_SIZE = 1000


def _fetch_all(sb: Any, table: str, columns: str, *, filters: list[tuple[str, str, Any]] | None = None) -> list[dict]:
    """
    Paginated equivalent of ``sb.table(table).select(columns).execute().data``.

    Loops with ``.range(start, end)`` until a short page (< _PAGE_SIZE) is
    returned. Optional ``filters`` are ``(method, column, value)`` tuples
    applied in order — e.g. ``[("eq", "is_active", True)]``.
    """
    rows: list[dict] = []
    offset = 0
    while True:
        q = sb.table(table).select(columns)
        for method, column, value in filters or []:
            q = getattr(q, method)(column, value)
        batch = (q.range(offset, offset + _PAGE_SIZE - 1).execute()).data or []
        rows.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Pricing — read directly from services/plans.py so the analytics MRR can
# never drift from the pricing page. Eliminates the 9-rupee drift the
# first pass of this file had (9590 vs plans.py's 9599).
# ─────────────────────────────────────────────────────────────────────────────


def _plan_monthly_revenue(plan: str, cycle: str) -> tuple[int, int]:
    """
    Return ``(inr_per_month, usd_per_month)`` for a subscription row.

    Annual cycles are normalised to their effective monthly rate by
    dividing the annual price by 12 so MRR correctly reflects recurring
    revenue rather than a single annual lump.
    """
    cfg = PLANS.get(plan) or {}
    if cycle == "annual":
        return (
            (cfg.get("annual_price_inr", 0) or 0) // 12,
            (cfg.get("annual_price_usd", 0) or 0) // 12,
        )
    return (
        cfg.get("monthly_price_inr", 0) or 0,
        cfg.get("monthly_price_usd", 0) or 0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Timezone → country mapping
# ─────────────────────────────────────────────────────────────────────────────

# Coarse IANA-prefix mapping so we can attribute users to a country without
# adding a `country` column or an external geoip service. The profiles.timezone
# column (added in migration 004) is the source. Unknown zones fall through to
# "Unknown".
_TZ_COUNTRY_MAP: dict[str, str] = {
    # India
    "Asia/Kolkata":   "India",
    "Asia/Calcutta":  "India",
    # North America
    "America/New_York":     "United States",
    "America/Chicago":      "United States",
    "America/Denver":       "United States",
    "America/Los_Angeles":  "United States",
    "America/Phoenix":      "United States",
    "America/Anchorage":    "United States",
    "America/Toronto":      "Canada",
    "America/Vancouver":    "Canada",
    "America/Mexico_City":  "Mexico",
    "America/Sao_Paulo":    "Brazil",
    "America/Buenos_Aires": "Argentina",
    # Europe
    "Europe/London":    "United Kingdom",
    "Europe/Dublin":    "Ireland",
    "Europe/Berlin":    "Germany",
    "Europe/Paris":     "France",
    "Europe/Madrid":    "Spain",
    "Europe/Rome":      "Italy",
    "Europe/Amsterdam": "Netherlands",
    "Europe/Warsaw":    "Poland",
    "Europe/Moscow":    "Russia",
    "Europe/Istanbul":  "Turkey",
    # Asia-Pacific
    "Asia/Dubai":      "United Arab Emirates",
    "Asia/Singapore":  "Singapore",
    "Asia/Hong_Kong":  "Hong Kong",
    "Asia/Tokyo":      "Japan",
    "Asia/Seoul":      "South Korea",
    "Asia/Shanghai":   "China",
    "Asia/Jakarta":    "Indonesia",
    "Asia/Manila":     "Philippines",
    "Asia/Bangkok":    "Thailand",
    "Asia/Karachi":    "Pakistan",
    "Asia/Dhaka":      "Bangladesh",
    "Australia/Sydney":    "Australia",
    "Australia/Melbourne": "Australia",
    "Pacific/Auckland":    "New Zealand",
    # Africa
    "Africa/Cairo":        "Egypt",
    "Africa/Lagos":        "Nigeria",
    "Africa/Johannesburg": "South Africa",
    "Africa/Nairobi":      "Kenya",
}


def _country_from_timezone(tz: str | None) -> str:
    if not tz:
        return "Unknown"
    return _TZ_COUNTRY_MAP.get(tz.strip(), "Unknown")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def admin_analytics(admin_id: str = Depends(_require_admin)) -> dict[str, Any]:
    """
    Aggregate analytics payload for the /admin/analytics dashboard.
    Runs 5 read-only table scans and produces a single JSON blob.
    """
    try:
        return await _build_payload()
    except HTTPException:
        raise
    except Exception:
        logger.error("Admin analytics endpoint failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to load analytics")


async def _build_payload() -> dict[str, Any]:
    sb = get_supabase_admin()
    now = datetime.now(timezone.utc)

    # Absolute cutoffs used for all "last N days" metrics. We compute them
    # once and reuse to keep the query count bounded.
    today_start   = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_7d     = now - timedelta(days=7)
    cutoff_30d    = now - timedelta(days=30)
    today_start_s = today_start.isoformat()
    cutoff_7d_s   = cutoff_7d.isoformat()
    cutoff_30d_s  = cutoff_30d.isoformat()

    # ── Profiles (one scan drives user counts + country breakdown) ────────
    profiles = _fetch_all(
        sb, "profiles",
        "id,email,name,agency_name,timezone,created_at,updated_at",
    )
    total_users = len(profiles)

    new_users_today = 0
    new_users_7d = 0
    new_users_30d = 0
    signups_by_day: dict[str, int] = defaultdict(int)
    country_counts: dict[str, int] = defaultdict(int)
    id_to_profile: dict[str, dict[str, Any]] = {}
    active_30d_from_profile: set[str] = set()
    active_7d_from_profile: set[str] = set()

    for p in profiles:
        pid = p["id"]
        id_to_profile[pid] = p

        created = _parse_iso(p.get("created_at"))
        if created is not None:
            if created >= today_start:
                new_users_today += 1
            if created >= cutoff_7d:
                new_users_7d += 1
            if created >= cutoff_30d:
                new_users_30d += 1
                # Initialise the per-day bucket for the 30-day trend.
                signups_by_day[created.date().isoformat()] += 1

        # Fallback activity signal — profile.updated_at updates whenever the
        # user touches settings, branding, etc. This becomes the baseline
        # active-users set before we layer in report-generation activity.
        updated = _parse_iso(p.get("updated_at"))
        if updated is not None:
            if updated >= cutoff_30d:
                active_30d_from_profile.add(pid)
            if updated >= cutoff_7d:
                active_7d_from_profile.add(pid)

        country_counts[_country_from_timezone(p.get("timezone"))] += 1

    # ── Reports (drives report metrics + top-users report counts) ─────────
    reports = _fetch_all(sb, "reports", "id,user_id,created_at")

    total_reports = len(reports)
    reports_today = 0
    reports_7d = 0
    reports_30d = 0
    reports_by_day: dict[str, int] = defaultdict(int)
    reports_by_user: dict[str, int] = defaultdict(int)
    active_from_reports_7d: set[str] = set()
    active_from_reports_30d: set[str] = set()
    last_active_by_user: dict[str, str] = {}

    for r in reports:
        uid = r.get("user_id")
        created = _parse_iso(r.get("created_at"))
        if uid:
            reports_by_user[uid] += 1
            if created is not None:
                iso_date = created.date().isoformat()
                prev = last_active_by_user.get(uid)
                if prev is None or iso_date > prev:
                    last_active_by_user[uid] = iso_date

        if created is None:
            continue
        if created >= today_start:
            reports_today += 1
        if created >= cutoff_7d:
            reports_7d += 1
            if uid:
                active_from_reports_7d.add(uid)
        if created >= cutoff_30d:
            reports_30d += 1
            reports_by_day[created.date().isoformat()] += 1
            if uid:
                active_from_reports_30d.add(uid)

    active_users_7d  = len(active_7d_from_profile | active_from_reports_7d)
    active_users_30d = len(active_30d_from_profile | active_from_reports_30d)

    # ── Clients per user (active only) ─────────────────────────────────────
    clients_rows = _fetch_all(
        sb, "clients", "id,user_id,is_active",
        filters=[("eq", "is_active", True)],
    )
    clients_by_user: dict[str, int] = defaultdict(int)
    for c in clients_rows:
        uid = c.get("user_id")
        if uid:
            clients_by_user[uid] += 1

    # ── Connections (platform breakdown) ──────────────────────────────────
    conn_rows = _fetch_all(sb, "connections", "platform,client_id")
    conn_counts = {
        "ga4":            0,
        "meta_ads":       0,
        "google_ads":     0,
        "search_console": 0,
        "csv":            0,
    }
    # A user is counted in the funnel's "connected_source" stage if any of
    # their clients has at least one connection. Build that set as we iterate.
    client_id_to_user: dict[str, str] = {c["id"]: c.get("user_id") for c in clients_rows if c.get("id")}
    users_with_connection: set[str] = set()
    for c in conn_rows:
        platform = (c.get("platform") or "").strip()
        if platform == "ga4":
            conn_counts["ga4"] += 1
        elif platform == "meta_ads":
            conn_counts["meta_ads"] += 1
        elif platform == "google_ads":
            conn_counts["google_ads"] += 1
        elif platform == "search_console":
            conn_counts["search_console"] += 1
        elif platform.startswith("csv_") or platform == "csv":
            conn_counts["csv"] += 1
        uid = client_id_to_user.get(c.get("client_id"))
        if uid:
            users_with_connection.add(uid)
    conn_counts["total"] = sum(
        v for k, v in conn_counts.items() if k != "total"
    )

    # ── Subscriptions (plan mix + MRR + paid funnel stage) ────────────────
    subs = _fetch_all(
        sb, "subscriptions",
        "user_id,plan,billing_cycle,status,trial_ends_at",
    )

    sub_breakdown = {
        "trial":         0,
        "trial_expired": 0,
        "starter":       0,
        "pro":           0,
        "agency":        0,
        "total_paying":  0,
    }
    mrr_inr = 0
    mrr_usd = 0
    paid_user_ids: set[str] = set()

    for s in subs:
        plan = (s.get("plan") or "").lower()
        status = (s.get("status") or "").lower()
        uid = s.get("user_id")

        if plan == "trial":
            if status in ("trialing", "active"):
                sub_breakdown["trial"] += 1
            else:
                sub_breakdown["trial_expired"] += 1
            continue

        # NOTE: "past_due" = card failed but subscription is still open. We
        # deliberately count these in total_paying + MRR because the agency
        # hasn't churned yet (Razorpay will retry). Revisit if the billing
        # dashboard needs a distinct "at risk" bucket.
        if plan in ("starter", "pro", "agency") and status in ("active", "trialing", "past_due"):
            sub_breakdown[plan] += 1
            sub_breakdown["total_paying"] += 1
            if uid:
                paid_user_ids.add(uid)

            cycle = (s.get("billing_cycle") or "monthly").lower()
            inr, usd = _plan_monthly_revenue(plan, cycle)
            mrr_inr += inr
            mrr_usd += usd

    sub_breakdown["mrr_inr"] = mrr_inr
    sub_breakdown["mrr_usd"] = mrr_usd

    # ── Signups / reports daily trend: fill zero-days for a clean X-axis ──
    signups_daily: list[dict[str, Any]] = []
    reports_daily: list[dict[str, Any]] = []
    for i in range(29, -1, -1):
        day = (today_start - timedelta(days=i)).date().isoformat()
        signups_daily.append({"date": day, "count": signups_by_day.get(day, 0)})
        reports_daily.append({"date": day, "count": reports_by_day.get(day, 0)})

    # ── Country breakdown (Unknowns last, biggest first) ──────────────────
    users_by_country = sorted(
        (
            {"country": c, "count": n}
            for c, n in country_counts.items()
        ),
        key=lambda r: (r["country"] == "Unknown", -r["count"]),
    )

    # ── Top 10 most active users (by report count, tiebreaker clients) ───
    ranked_uids = sorted(
        id_to_profile,
        key=lambda u: (reports_by_user.get(u, 0), clients_by_user.get(u, 0)),
        reverse=True,
    )
    # Map user → plan (for the table badge). Only one sub per user.
    plan_by_user: dict[str, str] = {
        s.get("user_id"): (s.get("plan") or "trial")
        for s in subs
        if s.get("user_id")
    }

    top_users: list[dict[str, Any]] = []
    for uid in ranked_uids[:10]:
        p = id_to_profile[uid]
        top_users.append({
            "email":             p.get("email", ""),
            "name":              (p.get("agency_name") or p.get("name") or "").strip(),
            "plan":              plan_by_user.get(uid, "trial"),
            "clients":           clients_by_user.get(uid, 0),
            "reports_generated": reports_by_user.get(uid, 0),
            "last_active":       last_active_by_user.get(
                uid,
                (_parse_iso(p.get("updated_at")) or now).date().isoformat(),
            ),
        })

    # ── Conversion funnel ─────────────────────────────────────────────────
    # reports_by_user is only populated inside an `if uid:` guard above, so
    # every key is already truthy — len() is enough.
    funnel = {
        "signed_up":        total_users,
        "connected_source": len(users_with_connection),
        "generated_report": len(reports_by_user),
        "paid":             len(paid_user_ids),
    }

    return {
        "total_users":        total_users,
        "active_users_7d":    active_users_7d,
        "active_users_30d":   active_users_30d,
        "new_users_today":    new_users_today,
        "new_users_7d":       new_users_7d,
        "new_users_30d":      new_users_30d,
        "signups_daily":      signups_daily,
        "subscriptions":      sub_breakdown,
        "total_reports":      total_reports,
        "reports_today":      reports_today,
        "reports_7d":         reports_7d,
        "reports_30d":        reports_30d,
        "reports_daily":      reports_daily,
        "connections":        conn_counts,
        "users_by_country":   users_by_country,
        "top_users":          top_users,
        "funnel":             funnel,
        "generated_at":       now.isoformat(),
    }


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
