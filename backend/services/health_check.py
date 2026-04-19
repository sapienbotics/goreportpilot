"""
Connection Health Monitor — Phase 2.

Runs periodic probes against every active OAuth connection to detect:
  * broken tokens (probe fails) → health_status = 'broken'
  * imminent expiry (≤ 7 days)  → health_status = 'expiring_soon'
  * healthy (probe OK, expiry far away) → health_status = 'healthy'

The 'warning' status is set out-of-band by snapshot_saver when a pull
returns zero data after 2 prior non-zero pulls (suspicious_zero_data).

Scheduling: called from services.scheduler.check_and_run_health_checks()
which is invoked on every tick of the main scheduler loop. Internal
cadence tracking short-circuits when less than 6 hours have passed since
the last probe sweep.

Email alerts: fire idempotently. Each connection tracks per-alert
timestamps in its alerts_sent jsonb; the same alert does not re-fire
for the same breach-streak. When the connection recovers, the
corresponding alert timestamp is cleared so future transitions re-alert.
"""
import asyncio
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote

import httpx

from config import settings
from services.encryption import decrypt_token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

BATCH_SIZE = 50               # connections probed in parallel per batch
BATCH_JITTER_SECONDS = 30     # sleep between batches to spread API load
EXPIRY_WARNING_DAYS = 7       # token expires in ≤ this many days → expiring_soon
PROBE_TIMEOUT_SECONDS = 15    # per-probe HTTP timeout

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def check_all_connections_health(supabase: Any) -> dict:
    """
    Probe every active connection across all users and update health_status.

    Returns a summary dict for logging / observability:
        {
          "total":          N,
          "healthy":        N,
          "warning":        N,
          "broken":         N,
          "expiring_soon":  N,
          "skipped":        N,
          "alerts_sent":    N,
        }
    """
    started_at = time.monotonic()

    # Fetch every connection that could plausibly need probing.
    # We intentionally do NOT filter by status='active' — if a connection
    # was flagged 'expired' earlier but the user quietly reconnected via a
    # separate flow, we want to probe it and clear the flag.
    result = (
        supabase.table("connections")
        .select(
            "id,client_id,platform,account_id,account_name,"
            "access_token_encrypted,refresh_token_encrypted,"
            "token_expires_at,health_status,alerts_sent,consecutive_failures,"
            "clients(user_id,name,primary_contact_email)"
        )
        # CSV connections don't have real OAuth tokens — skip them.
        .not_.like("platform", "csv\\_%")
        .execute()
    )

    all_conns = result.data or []
    if not all_conns:
        logger.info("Health check: no connections to probe")
        return {"total": 0, "healthy": 0, "warning": 0, "broken": 0,
                "expiring_soon": 0, "skipped": 0, "alerts_sent": 0}

    logger.info("Health check: probing %d connection(s)", len(all_conns))

    stats = {
        "total":         len(all_conns),
        "healthy":       0,
        "warning":       0,
        "broken":        0,
        "expiring_soon": 0,
        "skipped":       0,
        "alerts_sent":   0,
    }

    # Batch probing with jitter between batches.
    for batch_idx, i in enumerate(range(0, len(all_conns), BATCH_SIZE)):
        batch = all_conns[i:i + BATCH_SIZE]
        await asyncio.gather(*[
            _probe_one_connection(conn, supabase, stats)
            for conn in batch
        ], return_exceptions=False)

        # Sleep between batches to avoid rate-limiting downstream APIs.
        # Skip sleep after the final batch.
        if (i + BATCH_SIZE) < len(all_conns):
            await asyncio.sleep(BATCH_JITTER_SECONDS)

    elapsed = time.monotonic() - started_at
    logger.info(
        "Health check complete in %.1fs — %s",
        elapsed, {k: v for k, v in stats.items() if v},
    )
    return stats


# ---------------------------------------------------------------------------
# Per-connection probe
# ---------------------------------------------------------------------------


async def _probe_one_connection(conn: dict, supabase: Any, stats: dict) -> None:
    """Probe a single connection, update health_status, fire alerts as needed."""
    conn_id  = conn["id"]
    platform = conn["platform"]

    try:
        token_expires_unix = _parse_token_expiry(conn.get("token_expires_at"))
        expires_soon = _is_expiring_soon(platform, token_expires_unix)

        # Run the platform probe.
        probe_ok, error_msg = await _probe_platform(platform, conn, supabase)

        # Compute new health_status.
        if not probe_ok:
            new_status = "broken"
            stats["broken"] += 1
        elif expires_soon:
            new_status = "expiring_soon"
            stats["expiring_soon"] += 1
        else:
            new_status = "healthy"
            stats["healthy"] += 1

        old_status = conn.get("health_status") or "healthy"
        alerts_sent = (conn.get("alerts_sent") or {}).copy()
        consecutive_failures = int(conn.get("consecutive_failures") or 0)

        # Update consecutive_failures counter.
        if probe_ok:
            consecutive_failures = 0
        else:
            consecutive_failures += 1

        # Decide which alerts to fire.
        alerts_fired = 0

        if new_status == "broken" and old_status != "broken":
            # Transition into broken → send one email.
            sent = await _send_broken_alert(conn)
            if sent:
                alerts_sent["broken"] = _now_iso()
                alerts_fired += 1
        elif new_status != "broken" and "broken" in alerts_sent:
            # Recovered → clear the broken alert so future transitions re-fire.
            alerts_sent.pop("broken", None)

        if new_status == "expiring_soon" and "expiring" not in alerts_sent:
            # Only send once per expiry cycle. When the user reconnects, the
            # new token_expires_at pushes expiry out and `expires_soon` becomes
            # False → alerts_sent["expiring"] is cleared below.
            sent = await _send_expiring_alert(conn, token_expires_unix)
            if sent:
                alerts_sent["expiring"] = _now_iso()
                alerts_fired += 1
        elif new_status != "expiring_soon" and "expiring" in alerts_sent:
            alerts_sent.pop("expiring", None)

        stats["alerts_sent"] += alerts_fired

        # Persist result.
        supabase.table("connections").update({
            "health_status":        new_status,
            "last_health_check_at": _now_iso(),
            "last_error_message":   error_msg,
            "consecutive_failures": consecutive_failures,
            "alerts_sent":          alerts_sent,
        }).eq("id", conn_id).execute()

    except Exception as exc:
        # Never let one bad probe break the whole sweep.
        stats["skipped"] += 1
        logger.error(
            "Health probe failed for connection %s (%s): %s",
            conn_id, platform, exc,
        )


# ---------------------------------------------------------------------------
# Platform probes — thin wrappers around each platform's lightest API call
# ---------------------------------------------------------------------------


async def _probe_platform(platform: str, conn: dict, supabase: Any) -> tuple[bool, Optional[str]]:
    """
    Run a cheap probe for the connection's platform.

    Returns (ok, error_message). On success: (True, None). On failure:
    (False, short human-readable error for last_error_message column).
    """
    try:
        if platform == "ga4":
            return await _probe_ga4(conn, supabase)
        if platform == "meta_ads":
            return await _probe_meta(conn)
        if platform == "google_ads":
            return await _probe_google_ads(conn)
        if platform == "search_console":
            return await _probe_search_console(conn, supabase)
        # Unknown / CSV platforms skip probing and remain healthy by default.
        return True, None
    except Exception as exc:
        return False, f"Probe exception: {str(exc)[:200]}"


async def _probe_ga4(conn: dict, supabase: Any) -> tuple[bool, Optional[str]]:
    """List GA4 properties accessible to the token — confirms token validity."""
    from services.google_analytics import _get_valid_access_token  # noqa: PLC0415

    try:
        token_expires_at = _parse_token_expiry(conn.get("token_expires_at"))
        access_token = await _get_valid_access_token(
            access_token_encrypted=conn["access_token_encrypted"],
            refresh_token_encrypted=conn["refresh_token_encrypted"],
            token_expires_at=token_expires_at,
            supabase=supabase,
            connection_id=conn["id"],
        )
    except Exception as exc:
        return False, f"GA4 token refresh failed: {str(exc)[:200]}"

    # Cheapest valid call: GET the property's metadata.
    property_id = conn.get("account_id") or ""
    url = f"https://analyticsadmin.googleapis.com/v1beta/{property_id}"
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {access_token}"}
            )
    except Exception as exc:
        return False, f"GA4 probe HTTP error: {str(exc)[:200]}"

    if resp.status_code == 200:
        return True, None
    if resp.status_code in (401, 403):
        return False, f"GA4 auth rejected ({resp.status_code})"
    return False, f"GA4 probe returned {resp.status_code}"


async def _probe_meta(conn: dict) -> tuple[bool, Optional[str]]:
    """Meta Graph API /me?fields=id — validates the access token."""
    try:
        token = decrypt_token(conn["access_token_encrypted"])
    except Exception as exc:
        return False, f"Meta token decrypt failed: {str(exc)[:200]}"

    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                "https://graph.facebook.com/v21.0/me",
                params={"access_token": token, "fields": "id"},
            )
    except Exception as exc:
        return False, f"Meta probe HTTP error: {str(exc)[:200]}"

    if resp.status_code == 200:
        return True, None
    return False, f"Meta probe returned {resp.status_code}: {resp.text[:200]}"


async def _probe_google_ads(conn: dict) -> tuple[bool, Optional[str]]:
    """list_accessible_customers — cheapest call to verify Google Ads auth."""
    # Run the sync client in a thread.
    def _sync_probe() -> tuple[bool, Optional[str]]:
        try:
            from google.ads.googleads.client import GoogleAdsClient  # type: ignore  # noqa: PLC0415

            access_token  = decrypt_token(conn["access_token_encrypted"])
            refresh_token = decrypt_token(conn["refresh_token_encrypted"]) if conn.get("refresh_token_encrypted") else ""
            creds: dict = {
                "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
                "client_id":       settings.GOOGLE_CLIENT_ID,
                "client_secret":   settings.GOOGLE_CLIENT_SECRET,
                "refresh_token":   refresh_token,
                "access_token":    access_token,
                "use_proto_plus":  True,
            }
            if settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID:
                creds["login_customer_id"] = settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID
            client = GoogleAdsClient.load_from_dict(creds)
            customer_service = client.get_service("CustomerService")
            customer_service.list_accessible_customers()
            return True, None
        except Exception as exc:
            return False, f"Google Ads probe failed: {str(exc)[:200]}"

    return await asyncio.to_thread(_sync_probe)


async def _probe_search_console(conn: dict, supabase: Any) -> tuple[bool, Optional[str]]:
    """
    sites.list — cheapest call to verify Search Console auth.

    Google OAuth access tokens expire after 1 hour. The 6-hour probe cadence
    means the stored token is frequently expired at probe time → 401.
    Reuse the GA4 helper that refreshes + writes back to the DB so every
    probe gets a valid token. Search Console uses the same Google OAuth
    flow as GA4, so the refresh mechanics are identical.
    """
    from services.google_analytics import _get_valid_access_token  # noqa: PLC0415
    try:
        token_expires_at = _parse_token_expiry(conn.get("token_expires_at"))
        access_token = await _get_valid_access_token(
            access_token_encrypted=conn["access_token_encrypted"],
            refresh_token_encrypted=conn["refresh_token_encrypted"],
            token_expires_at=token_expires_at,
            supabase=supabase,
            connection_id=conn["id"],
        )
    except Exception as exc:
        return False, f"SC token refresh failed: {str(exc)[:200]}"

    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                "https://www.googleapis.com/webmasters/v3/sites",
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except Exception as exc:
        return False, f"SC probe HTTP error: {str(exc)[:200]}"

    if resp.status_code == 200:
        return True, None
    if resp.status_code in (401, 403):
        return False, f"SC auth rejected ({resp.status_code}): {resp.text[:200]}"
    return False, f"SC probe returned {resp.status_code}"


# ---------------------------------------------------------------------------
# Zero-data suspicion helper (called from snapshot_saver)
# ---------------------------------------------------------------------------


_ZERO_METRIC_KEYS = {
    "ga4":            ("summary", "sessions"),
    "meta_ads":       ("summary", "impressions"),
    "google_ads":     ("summary", "impressions"),
    "search_console": ("summary", "impressions"),
}


def _is_zero_metric(platform: str, metrics: dict) -> bool:
    """Return True if this pull's primary metric is zero for a platform."""
    path = _ZERO_METRIC_KEYS.get(platform)
    if not path:
        return False
    cur: Any = metrics or {}
    for key in path:
        if not isinstance(cur, dict):
            return False
        cur = cur.get(key)
    try:
        return float(cur or 0) == 0.0
    except (TypeError, ValueError):
        return False


def check_suspicious_zero_data(
    supabase: Any,
    connection_id: str,
    platform: str,
    current_metrics: dict,
) -> None:
    """
    If current pull returned zero for the primary metric AND the two prior
    snapshots were non-zero, flag health_status='warning' and fire a
    zero-data alert once.

    Synchronous: snapshot_saver calls this inline after a successful upsert.
    """
    try:
        if not _is_zero_metric(platform, current_metrics):
            # Current pull has data — clear any prior zero-data alert flag.
            _clear_zero_data_alert(supabase, connection_id)
            return

        # Look at the last 3 snapshots (may include the one we just wrote).
        recent = (
            supabase.table("data_snapshots")
            .select("metrics,period_start")
            .eq("connection_id", connection_id)
            .order("period_start", desc=True)
            .limit(3)
            .execute()
        )
        rows = recent.data or []
        # Drop the most-recent row if it matches current (just written).
        # We only care whether the PRIOR two were non-zero.
        prior = rows[1:] if len(rows) > 1 else []
        if len(prior) < 2:
            # Not enough history to call this suspicious yet.
            return
        if all(not _is_zero_metric(platform, r.get("metrics") or {}) for r in prior):
            # 2+ prior non-zero pulls + current zero → suspicious.
            _mark_warning_and_alert(supabase, connection_id, platform)
    except Exception as exc:
        logger.error(
            "check_suspicious_zero_data failed for connection %s: %s",
            connection_id, exc,
        )


def _mark_warning_and_alert(supabase: Any, connection_id: str, platform: str) -> None:
    """Set health_status='warning' and fire a zero-data alert once."""
    conn_result = (
        supabase.table("connections")
        .select(
            "id,client_id,platform,account_name,alerts_sent,health_status,"
            "clients(user_id,name,primary_contact_email)"
        )
        .eq("id", connection_id)
        .single()
        .execute()
    )
    conn = conn_result.data
    if not conn:
        return

    alerts_sent = (conn.get("alerts_sent") or {}).copy()
    if "zero_data" in alerts_sent:
        # Already alerted on this zero-data streak — just keep status='warning'.
        supabase.table("connections").update({
            "health_status": "warning",
        }).eq("id", connection_id).execute()
        return

    # Fire the alert email. Run the async send in a new event loop if
    # we're called from a sync context.
    try:
        try:
            asyncio.get_event_loop()
            asyncio.ensure_future(_send_zero_data_alert(conn))
        except RuntimeError:
            asyncio.run(_send_zero_data_alert(conn))
    except Exception as exc:
        logger.error("Zero-data alert send failed: %s", exc)

    alerts_sent["zero_data"] = _now_iso()
    supabase.table("connections").update({
        "health_status": "warning",
        "alerts_sent":   alerts_sent,
    }).eq("id", connection_id).execute()


def _clear_zero_data_alert(supabase: Any, connection_id: str) -> None:
    """Clear the zero_data flag so future transitions will re-alert."""
    try:
        conn_result = (
            supabase.table("connections")
            .select("alerts_sent,health_status")
            .eq("id", connection_id)
            .single()
            .execute()
        )
        conn = conn_result.data
        if not conn:
            return
        alerts_sent = (conn.get("alerts_sent") or {}).copy()
        if "zero_data" in alerts_sent:
            alerts_sent.pop("zero_data", None)
            # Downgrade warning → healthy ONLY if current warning came from zero_data.
            updates: dict = {"alerts_sent": alerts_sent}
            if conn.get("health_status") == "warning":
                updates["health_status"] = "healthy"
            supabase.table("connections").update(updates).eq("id", connection_id).execute()
    except Exception as exc:
        logger.debug("_clear_zero_data_alert skipped: %s", exc)


# ---------------------------------------------------------------------------
# Alert emails
# ---------------------------------------------------------------------------


_PLATFORM_LABELS = {
    "ga4":            "Google Analytics",
    "meta_ads":       "Meta Ads",
    "google_ads":     "Google Ads",
    "search_console": "Search Console",
}


async def _send_broken_alert(conn: dict) -> bool:
    """Send the 'connection broken' email to the agency owner."""
    return await _send_alert_email(
        conn,
        alert_key="broken",
        subject_fmt="Connection broken: {platform} for {client_name}",
        body_lines=[
            "Heads up — the {platform} connection for {client_name} is no longer responding.",
            "We last tried at {timestamp} and got: {error}",
            "Open the integrations page to reconnect. Until you do, we'll skip this platform when generating reports for {client_name}.",
        ],
    )


async def _send_expiring_alert(conn: dict, token_expires_unix: Optional[float]) -> bool:
    """Send the 'token expires soon' email (fires once per expiry cycle)."""
    days_left = 7
    if token_expires_unix:
        days_left = max(0, int((token_expires_unix - time.time()) / 86400))
    return await _send_alert_email(
        conn,
        alert_key="expiring",
        subject_fmt="{platform} connection expires in {days} days ({client_name})",
        body_lines=[
            "The OAuth token for your {platform} connection on {client_name} expires in about {days} days.",
            "Reconnect before expiry so scheduled reports don't get sent without this platform's data.",
            "Open the integrations page and click Reconnect.",
        ],
        days=days_left,
    )


async def _send_zero_data_alert(conn: dict) -> bool:
    """Send the 'suspicious zero data' email."""
    return await _send_alert_email(
        conn,
        alert_key="zero_data",
        subject_fmt="{platform} returned zero data for {client_name}",
        body_lines=[
            "We just pulled {platform} data for {client_name} and it came back empty — zero sessions/impressions.",
            "The previous two pulls had real data, so this is unusual. Likely causes: the tracking tag was removed, the account was disconnected, or there's a platform outage.",
            "Worth a quick check before your next scheduled report.",
        ],
    )


async def _send_alert_email(
    conn: dict,
    *,
    alert_key: str,
    subject_fmt: str,
    body_lines: list[str],
    **extra_fmt: Any,
) -> bool:
    """
    Low-level email builder used by the three alert types.
    Returns True if an email was actually dispatched; False if skipped.
    """
    from services.email_service import send_report_email  # noqa: PLC0415

    # Recipient = agency owner's primary email (profiles.email).
    # Fallback chain: profiles.agency_email → profiles.email. If neither
    # resolves, we skip rather than silently drop.
    client_row = conn.get("clients") or {}
    user_id = client_row.get("user_id")
    if not user_id:
        logger.debug("Alert %s skipped — no user_id on connection %s", alert_key, conn.get("id"))
        return False

    try:
        from services.supabase_client import get_supabase_admin  # noqa: PLC0415
        supabase = get_supabase_admin()
        profile_resp = (
            supabase.table("profiles")
            .select("email,agency_name,agency_email,sender_name")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        profile = profile_resp.data or {}
    except Exception as exc:
        logger.error("Alert %s — profile lookup failed: %s", alert_key, exc)
        return False

    to_email = (profile.get("agency_email") or profile.get("email") or "").strip()
    if not to_email:
        logger.debug("Alert %s skipped — no recipient for user %s", alert_key, user_id)
        return False

    platform_label = _PLATFORM_LABELS.get(conn.get("platform", ""), conn.get("platform", ""))
    client_name    = client_row.get("name", "—")
    agency_name    = profile.get("agency_name") or "GoReportPilot"
    sender_name    = profile.get("sender_name") or agency_name

    fmt_ctx = {
        "platform":    platform_label,
        "client_name": client_name,
        "timestamp":   _now_iso(),
        "error":       (conn.get("last_error_message") or "—")[:200],
        **extra_fmt,
    }

    subject = subject_fmt.format(**fmt_ctx)
    body_html = _build_alert_html(
        subject=subject,
        paragraphs=[line.format(**fmt_ctx) for line in body_lines],
        agency_name=agency_name,
    )

    try:
        await send_report_email(
            to_emails=[to_email],
            subject=subject,
            html_body=body_html,
            sender_name=sender_name,
        )
        logger.info(
            "Alert %s sent to %s (connection=%s, platform=%s)",
            alert_key, to_email, conn.get("id"), conn.get("platform"),
        )
        return True
    except Exception as exc:
        logger.error(
            "Alert %s send failed for connection %s: %s",
            alert_key, conn.get("id"), exc,
        )
        return False


def _build_alert_html(*, subject: str, paragraphs: list[str], agency_name: str) -> str:
    """Minimal branded HTML for health alert emails."""
    body_html = "".join(
        f'<p style="margin:0 0 12px 0;color:#334155;font-size:14px;line-height:1.6;">{p}</p>'
        for p in paragraphs
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" /><title>{subject}</title></head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:Inter,Segoe UI,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#F8FAFC;">
    <tr><td align="center" style="padding:32px 16px;">
      <table width="560" cellpadding="0" cellspacing="0" role="presentation"
             style="background:#ffffff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);max-width:560px;width:100%;">
        <tr><td style="background:#B45309;padding:20px 24px;">
          <p style="margin:0;color:#FEF3C7;font-size:11px;font-weight:700;
                    letter-spacing:0.08em;text-transform:uppercase;">Connection health alert</p>
          <h1 style="margin:6px 0 0 0;color:#ffffff;font-size:18px;font-weight:700;line-height:1.3;">
            {subject}
          </h1>
        </td></tr>
        <tr><td style="padding:24px 28px;">{body_html}</td></tr>
        <tr><td style="padding:12px 28px 18px;border-top:1px solid #F1F5F9;">
          <p style="margin:0;font-size:11px;color:#94A3B8;">
            Sent by {agency_name} via GoReportPilot.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_token_expiry(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _is_expiring_soon(platform: str, token_expires_unix: Optional[float]) -> bool:
    """
    Decide whether a connection should be flagged 'expiring_soon'.

    For Google platforms (GA4, Google Ads, Search Console), token_expires_at
    stores the ACCESS token's 1-hour lifetime, NOT the refresh_token's life.
    Access tokens are auto-refreshed on every probe via the refresh_token,
    so their expiry is a non-event. Flagging Google connections as
    'expiring_soon' whenever the 7-day threshold was crossed meant every
    Google connection flipped to 'expiring_soon' the moment it was
    reconnected (expires in 1h < 7 days = true). That's the bug this fix
    addresses.

    Only Meta's access_token is the long-lived credential (~60-day life).
    Warning the user 7 days before expiry is useful there because Meta
    CANNOT be auto-refreshed the way Google can.
    """
    if platform != "meta_ads":
        return False
    if not token_expires_unix:
        return False
    now = time.time()
    return 0 < (token_expires_unix - now) <= EXPIRY_WARNING_DAYS * 86400


# ---------------------------------------------------------------------------
# Single-connection probe (public — called on reconnect + manual triggers)
# ---------------------------------------------------------------------------


async def probe_one_connection_now(supabase: Any, connection_id: str) -> dict:
    """
    Probe one connection right now, bypassing the 6-hour sweep cadence.

    Used by:
      * POST /api/connections (reconnect path) — give the user instant
        ground truth instead of stale 'broken' from before the OAuth
        round-trip.
      * POST /api/connections/{id}/probe (manual trigger endpoint).

    Reuses _probe_one_connection() — same status-transition + alert-email
    logic as the batch sweep, keeping the two paths consistent.

    Returns the per-probe stats dict (useful for callers that want to
    know what transitioned). Non-fatal: all errors are logged.
    """
    stats: dict = {
        "total":         0,
        "healthy":       0,
        "warning":       0,
        "broken":        0,
        "expiring_soon": 0,
        "skipped":       0,
        "alerts_sent":   0,
    }

    try:
        conn_result = (
            supabase.table("connections")
            .select(
                "id,client_id,platform,account_id,account_name,"
                "access_token_encrypted,refresh_token_encrypted,"
                "token_expires_at,health_status,alerts_sent,consecutive_failures,"
                "clients(user_id,name,primary_contact_email)"
            )
            .eq("id", connection_id)
            .single()
            .execute()
        )
        conn = conn_result.data
    except Exception as exc:
        logger.error("probe_one_connection_now: load failed for %s: %s", connection_id, exc)
        return stats

    if not conn:
        logger.warning("probe_one_connection_now: connection %s not found", connection_id)
        return stats

    # CSV platforms have no OAuth to probe — leave them alone.
    if str(conn.get("platform", "")).startswith("csv_"):
        return stats

    stats["total"] = 1
    await _probe_one_connection(conn, supabase, stats)
    return stats
