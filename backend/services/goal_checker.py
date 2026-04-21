"""
Phase 6 — Goals & Alerts.

Evaluates per-client metric goals against the latest cached data_snapshots
row and sends alert emails when a target is missed or at risk. Idempotent:
each (goal_id, period_key, alert_type) tuple fires at most one email.

Design rules (mirror the Phase 2 connection-health service):
  * Non-fatal. Any failure while evaluating ONE goal must not block the
    sweep. Exceptions are logged and the next goal is processed.
  * Read-only against snapshots. We never re-pull from platform APIs;
    we rely on data_snapshots the report pipeline already persists.
  * Idempotency lives in goals.alerts_sent JSONB, keyed by
    "{period_key}:{alert_type}" → ISO timestamp of the send. Same pattern
    as connections.alerts_sent from migration 013.
  * Status thresholds are applied symmetrically for gte/lte comparisons
    so bounce-rate and CPA goals behave the same as ROAS and sessions
    goals from the agency's point of view.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metric registry — the canonical catalog used by the UI, the evaluator,
# and the email templates. Paths are "platform.key" and resolve against
# data_snapshots.metrics, which stores each platform's normalised summary
# dict under metrics.summary.<key> for GA4 / Meta Ads / Google Ads and
# metrics.<key> for Search Console (which has no nested summary).
# ---------------------------------------------------------------------------

# direction = 'higher_is_better' means the default comparison is gte;
# 'lower_is_better' flips the on-track / at-risk logic for the same
# status thresholds (so a CPA goal "lte $30" at actual $25 is on-track).
METRIC_REGISTRY: dict[str, dict[str, Any]] = {
    # GA4
    "ga4.sessions":             {"label": "Sessions",             "platform": "ga4",            "unit": "int",     "direction": "higher_is_better"},
    "ga4.users":                {"label": "Users",                "platform": "ga4",            "unit": "int",     "direction": "higher_is_better"},
    "ga4.conversions":          {"label": "Conversions",          "platform": "ga4",            "unit": "int",     "direction": "higher_is_better"},
    "ga4.bounce_rate":          {"label": "Bounce Rate",          "platform": "ga4",            "unit": "percent", "direction": "lower_is_better"},
    # Meta Ads
    "meta_ads.spend":           {"label": "Ad Spend",             "platform": "meta_ads",       "unit": "currency","direction": "lower_is_better"},
    "meta_ads.roas":            {"label": "ROAS",                 "platform": "meta_ads",       "unit": "ratio",   "direction": "higher_is_better"},
    "meta_ads.cost_per_conversion": {"label": "Cost per Conversion (CPA)","platform": "meta_ads","unit": "currency","direction": "lower_is_better"},
    "meta_ads.ctr":             {"label": "Click-Through Rate",   "platform": "meta_ads",       "unit": "percent", "direction": "higher_is_better"},
    "meta_ads.revenue":         {"label": "Revenue",              "platform": "meta_ads",       "unit": "currency","direction": "higher_is_better"},
    # Google Ads — mirrors Meta for now; keys match google_ads summary shape
    "google_ads.spend":         {"label": "Google Ads Spend",     "platform": "google_ads",     "unit": "currency","direction": "lower_is_better"},
    "google_ads.roas":          {"label": "Google Ads ROAS",      "platform": "google_ads",     "unit": "ratio",   "direction": "higher_is_better"},
    "google_ads.cost_per_conversion": {"label": "Google Ads CPA", "platform": "google_ads",     "unit": "currency","direction": "lower_is_better"},
    "google_ads.ctr":           {"label": "Google Ads CTR",       "platform": "google_ads",     "unit": "percent", "direction": "higher_is_better"},
    # Search Console
    "search_console.clicks":    {"label": "Organic Clicks",       "platform": "search_console", "unit": "int",     "direction": "higher_is_better"},
    "search_console.impressions":{"label": "Organic Impressions", "platform": "search_console", "unit": "int",     "direction": "higher_is_better"},
    "search_console.ctr":       {"label": "Organic CTR",          "platform": "search_console", "unit": "percent", "direction": "higher_is_better"},
}

# Status thresholds (tuning knobs). All expressed as fractions of target.
# gte: actual / target; lte: target / actual (so "smaller than target" wins).
ON_TRACK_MIN_RATIO   = 1.00   # reaching 100% of target = on_track
AT_RISK_MIN_RATIO    = 0.80   # 80-99.9% = at_risk
# Below AT_RISK_MIN_RATIO = missed.


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_metrics() -> list[dict[str, Any]]:
    """Return the metric catalog for the UI dropdown."""
    return [
        {"key": key, **meta}
        for key, meta in METRIC_REGISTRY.items()
    ]


def period_key(period: str, ref_date: Optional[date] = None) -> str:
    """
    Build the idempotency period key for a goal.
      monthly → 'YYYY-MM'
      weekly  → 'YYYY-WNN'  (ISO week, NN zero-padded)
    """
    ref = ref_date or datetime.now(timezone.utc).date()
    if period == "weekly":
        iso_year, iso_week, _ = ref.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    return ref.strftime("%Y-%m")


def evaluate_status(
    actual: Optional[float],
    target: float,
    comparison: str,
    tolerance_pct: float = 5.0,
) -> str:
    """
    Map (actual, target, comparison) → 'on_track' | 'at_risk' | 'missed' | 'no_data'.

    comparison:
      gte — higher is better. ratio = actual / target.
            >=1.0 on_track, 0.8..1.0 at_risk, <0.8 missed.
      lte — lower is better. ratio = target / actual.
            Same thresholds applied to that inverted ratio.
      eq  — actual within tolerance_pct of target → on_track, else missed.
    """
    if actual is None:
        return "no_data"
    if target == 0:
        # A zero target is almost always a misconfiguration; report as on_track
        # if actual is also zero, else as missed. We don't want to divide by 0.
        return "on_track" if actual == 0 else ("missed" if comparison == "gte" else "on_track")

    if comparison == "eq":
        deviation_pct = abs(actual - target) / abs(target) * 100.0
        if deviation_pct <= tolerance_pct:
            return "on_track"
        if deviation_pct <= tolerance_pct * 2:
            return "at_risk"
        return "missed"

    if comparison == "lte":
        if actual <= 0:
            # Non-negative metrics only (spend, bounce_rate, cpa). Treat 0 as
            # on_track since the "ceiling" isn't breached.
            return "on_track"
        ratio = target / actual
    else:  # 'gte'
        ratio = actual / target

    if ratio >= ON_TRACK_MIN_RATIO:
        return "on_track"
    if ratio >= AT_RISK_MIN_RATIO:
        return "at_risk"
    return "missed"


# ---------------------------------------------------------------------------
# Snapshot reading
# ---------------------------------------------------------------------------

def _extract_metric_value(snapshot: dict, metric_key: str) -> Optional[float]:
    """
    Pull a numeric value out of a data_snapshots row for the given metric path.
    Returns None when the snapshot is missing the key (partial integration).
    """
    if not snapshot:
        return None
    metrics = snapshot.get("metrics") or {}

    # All pull services except Search Console store the headline KPIs under
    # metrics.summary.<key>. Search Console stores them flat (metrics.<key>).
    # Try summary first, then fall back to flat.
    _, _, leaf = metric_key.partition(".")
    summary = metrics.get("summary") if isinstance(metrics.get("summary"), dict) else None
    if summary and leaf in summary:
        val = summary[leaf]
    elif leaf in metrics:
        val = metrics[leaf]
    else:
        return None

    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _load_latest_snapshot(supabase, client_id: str, platform: str) -> Optional[dict]:
    """Most-recent snapshot for (client_id, platform), or None."""
    try:
        result = (
            supabase.table("data_snapshots")
            .select("*")
            .eq("client_id", client_id)
            .eq("platform", platform)
            .eq("is_valid", True)
            .order("period_end", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as exc:
        logger.warning(
            "goal_checker: failed to load snapshot for client=%s platform=%s: %s",
            client_id, platform, exc,
        )
        return None


# ---------------------------------------------------------------------------
# Single-goal evaluator
# ---------------------------------------------------------------------------

def evaluate_goal(
    supabase,
    goal: dict,
    ref_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Evaluate one goal and return a summary dict:
      {
        "goal_id":     <uuid>,
        "metric":      "ga4.sessions",
        "actual":      12345.0 | None,
        "target":      10000.0,
        "comparison":  "gte",
        "period_key":  "2026-04",
        "status":      "on_track" | "at_risk" | "missed" | "no_data",
      }

    Pure evaluation — does NOT send alerts or mutate the goal row.
    """
    metric = goal["metric"]
    meta = METRIC_REGISTRY.get(metric)
    if not meta:
        return {
            "goal_id":    goal["id"],
            "metric":     metric,
            "actual":     None,
            "target":     float(goal.get("target_value") or 0),
            "comparison": goal.get("comparison", "gte"),
            "period_key": period_key(goal.get("period", "monthly"), ref_date),
            "status":     "no_data",
        }

    snapshot = _load_latest_snapshot(supabase, goal["client_id"], meta["platform"])
    actual = _extract_metric_value(snapshot, metric) if snapshot else None

    status = evaluate_status(
        actual=actual,
        target=float(goal["target_value"]),
        comparison=goal.get("comparison", "gte"),
        tolerance_pct=float(goal.get("tolerance_pct") or 5),
    )

    return {
        "goal_id":    goal["id"],
        "metric":     metric,
        "metric_label": meta["label"],
        "actual":     actual,
        "target":     float(goal["target_value"]),
        "comparison": goal.get("comparison", "gte"),
        "period_key": period_key(goal.get("period", "monthly"), ref_date),
        "status":     status,
    }


def evaluate_goals_for_client(
    supabase,
    client_id: str,
    ref_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Batch convenience used by the GET endpoint to render status in the UI."""
    try:
        result = (
            supabase.table("goals")
            .select("*")
            .eq("client_id", client_id)
            .eq("is_active", True)
            .execute()
        )
        goals = result.data or []
    except Exception as exc:
        logger.error("goal_checker: failed to load goals for client %s: %s", client_id, exc)
        return []

    return [evaluate_goal(supabase, g, ref_date) for g in goals]


# ---------------------------------------------------------------------------
# Alert sweep
# ---------------------------------------------------------------------------

def _alert_type_for_status(status: str) -> Optional[str]:
    """Map a status to an alert type. Only 'at_risk' and 'missed' fire alerts."""
    if status == "missed":
        return "missed"
    if status == "at_risk":
        return "approach"
    return None


def _resolve_alert_recipients(
    supabase,
    goal: dict,
) -> list[str]:
    """
    Determine who gets the alert email.
    Priority:
      1. goal.alert_emails override (non-empty JSONB array)
      2. profile.agency_email (profile of goal.user_id)
      3. profile.email (the auth email) as a last resort
    """
    override = goal.get("alert_emails") or []
    if isinstance(override, list) and override:
        return [e for e in override if isinstance(e, str) and "@" in e]

    try:
        profile_result = (
            supabase.table("profiles")
            .select("email,agency_email")
            .eq("id", goal["user_id"])
            .maybe_single()
            .execute()
        )
        p = (profile_result.data if profile_result else {}) or {}
    except Exception as exc:
        logger.warning("goal_checker: profile lookup failed for user=%s: %s", goal["user_id"], exc)
        p = {}

    for key in ("agency_email", "email"):
        val = p.get(key)
        if val and "@" in val:
            return [val]
    return []


async def _send_goal_alert(
    *,
    goal: dict,
    client_name: str,
    evaluation: dict,
    recipients: list[str],
) -> None:
    """Build and send the alert email via the shared Resend helper."""
    from services.email_service import build_goal_alert_email_html, send_report_email  # noqa: PLC0415

    alert_type = _alert_type_for_status(evaluation["status"]) or "missed"
    metric_label = evaluation.get("metric_label") or evaluation["metric"]
    subject_verb = "at risk" if alert_type == "approach" else "missed"
    subject = f"Goal {subject_verb}: {metric_label} — {client_name}"

    html_body = build_goal_alert_email_html(
        client_name=client_name,
        metric_label=metric_label,
        actual=evaluation["actual"],
        target=evaluation["target"],
        comparison=evaluation["comparison"],
        status=evaluation["status"],
        period_key=evaluation["period_key"],
    )

    await send_report_email(
        to_emails=recipients,
        subject=subject,
        html_body=html_body,
        sender_name="GoReportPilot Alerts",
    )


async def check_and_send_alerts(ref_date: Optional[date] = None) -> dict[str, int]:
    """
    Main sweep — called by the scheduler. Iterates every active goal,
    evaluates it, and sends a single alert email per (goal, period_key,
    alert_type) tuple. Returns a counts dict useful for logging.
    """
    from services.supabase_client import get_supabase_admin  # noqa: PLC0415

    supabase = get_supabase_admin()
    counts = {"evaluated": 0, "alerts_sent": 0, "skipped_idempotent": 0, "errors": 0}

    try:
        result = (
            supabase.table("goals")
            .select("*, clients(name,is_active)")
            .eq("is_active", True)
            .execute()
        )
        goals = result.data or []
    except Exception as exc:
        logger.error("goal_checker: failed to load goals for sweep: %s", exc)
        return counts

    now_iso = datetime.now(timezone.utc).isoformat()

    for goal in goals:
        try:
            client = goal.get("clients") or {}
            if not client.get("is_active"):
                continue  # skip goals whose client has been soft-deleted

            evaluation = evaluate_goal(supabase, goal, ref_date)
            counts["evaluated"] += 1

            # Stamp last_evaluated_at regardless of whether we alert.
            supabase.table("goals").update({
                "last_evaluated_at": now_iso,
            }).eq("id", goal["id"]).execute()

            alert_type = _alert_type_for_status(evaluation["status"])
            if not alert_type:
                continue

            period_k = evaluation["period_key"]
            key = f"{period_k}:{alert_type}"
            alerts_sent = goal.get("alerts_sent") or {}
            if key in alerts_sent:
                counts["skipped_idempotent"] += 1
                continue

            recipients = _resolve_alert_recipients(supabase, goal)
            if not recipients:
                logger.warning(
                    "goal_checker: no recipients resolved for goal %s — skipping alert",
                    goal["id"],
                )
                continue

            await _send_goal_alert(
                goal=goal,
                client_name=client.get("name") or "Your client",
                evaluation=evaluation,
                recipients=recipients,
            )
            counts["alerts_sent"] += 1

            # Persist idempotency key AFTER successful send, so transient
            # email failures are retried on the next sweep.
            alerts_sent[key] = now_iso
            supabase.table("goals").update({
                "alerts_sent": alerts_sent,
            }).eq("id", goal["id"]).execute()

        except Exception as exc:
            counts["errors"] += 1
            logger.error(
                "goal_checker: goal %s failed evaluation — %s",
                goal.get("id"), exc,
            )

    logger.info(
        "goal_checker sweep done — evaluated=%d sent=%d skipped=%d errors=%d",
        counts["evaluated"], counts["alerts_sent"],
        counts["skipped_idempotent"], counts["errors"],
    )
    return counts
