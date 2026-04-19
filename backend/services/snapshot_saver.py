"""
Data snapshot saver.

After every successful native-platform data pull (GA4, Meta Ads, Google Ads,
Search Console), call save_snapshot() to persist the period's metrics into
data_snapshots for future trend analysis (MoM / YoY / multi-period AI context).

Design rules:
  * Idempotent. Re-running a report for the same (connection_id, period_start,
    period_end) updates the existing row instead of inserting a duplicate.
  * Non-fatal. Any failure here MUST NOT break report generation — catches
    all exceptions and logs them.
  * Lightweight. No schema changes required; writes to the existing
    data_snapshots table defined in migration 001.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def save_snapshot(
    supabase: Any,
    *,
    connection_id: str,
    client_id: str,
    platform: str,
    period_start: str,
    period_end: str,
    metrics: dict,
    raw_response: Optional[dict] = None,
) -> None:
    """
    Upsert a row into data_snapshots, keyed by (connection_id, period_start, period_end).

    Arguments
    ---------
    supabase:
        A supabase-py admin client (from services.supabase_client.get_supabase_admin()).
    connection_id, client_id, platform, period_start, period_end:
        Identifiers matching the data_snapshots columns. period_* are ISO "YYYY-MM-DD".
    metrics:
        The parsed/normalised metrics dict returned by the pull service.
        Stored in the jsonb `metrics` column — rich enough for later trend analysis.
    raw_response:
        Optional raw API response. Defaults to empty dict.

    Returns
    -------
    None. Failures are logged but swallowed — the caller continues regardless.
    """
    try:
        # (connection_id, period_start, period_end) is the logical upsert key.
        # We do not have a DB unique constraint on this tuple today, so we
        # implement upsert explicitly with a SELECT + UPDATE/INSERT pattern
        # instead of relying on ON CONFLICT.
        existing = (
            supabase.table("data_snapshots")
            .select("id")
            .eq("connection_id", connection_id)
            .eq("period_start", period_start)
            .eq("period_end", period_end)
            .limit(1)
            .execute()
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        payload = {
            "connection_id": connection_id,
            "client_id":     client_id,
            "platform":      platform,
            "period_start":  period_start,
            "period_end":    period_end,
            "metrics":       metrics or {},
            "raw_response":  raw_response or {},
            "pulled_at":     now_iso,
            "is_valid":      True,
        }

        if existing.data:
            snapshot_id = existing.data[0]["id"]
            supabase.table("data_snapshots").update(payload).eq("id", snapshot_id).execute()
            logger.info(
                "data_snapshots updated (id=%s, platform=%s, period=%s..%s)",
                snapshot_id, platform, period_start, period_end,
            )
        else:
            supabase.table("data_snapshots").insert(payload).execute()
            logger.info(
                "data_snapshots inserted (platform=%s, connection=%s, period=%s..%s)",
                platform, connection_id, period_start, period_end,
            )
    except Exception as exc:
        # Non-fatal: snapshot is an analytics artefact — never break the report.
        logger.error(
            "save_snapshot failed (non-fatal) platform=%s connection=%s period=%s..%s err=%s",
            platform, connection_id, period_start, period_end, exc,
        )
