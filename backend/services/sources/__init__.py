"""
Source registry and the single data-pull orchestrator.

``pull_all_sources`` replaces the two near-identical ~180-line blocks that used
to live in routers/reports.py (``_generate_report_internal`` and
``regenerate_report``). Those copies had already drifted apart — the regenerate
copy silently dropped CSV sources and themed its charts differently — which is
exactly the failure mode this module exists to prevent.

Adding a source is now: write an adapter, register it here, widen the
connections.platform CHECK constraint. No changes to the report router.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from services.sources.adapters import (
    CSVAdapter,
    GA4Adapter,
    GoogleAdsAdapter,
    MetaAdsAdapter,
    SearchConsoleAdapter,
)
from services.sources.base import (
    BaseSourceAdapter,
    CredentialField,
    HealthResult,
    PullContext,
    SourceError,
)

logger = logging.getLogger(__name__)

__all__ = [
    "REGISTRY",
    "PullContext",
    "PullOutcome",
    "SourceError",
    "CredentialField",
    "HealthResult",
    "get_adapter",
    "list_adapters",
    "pull_all_sources",
]


REGISTRY: dict[str, BaseSourceAdapter] = {
    adapter.source_id: adapter
    for adapter in (
        GA4Adapter(),
        MetaAdsAdapter(),
        GoogleAdsAdapter(),
        SearchConsoleAdapter(),
        CSVAdapter(),
    )
}

# Sources pulled from an API during report generation, in the order their data
# should appear in raw_data. CSV is excluded: it arrives with the request.
PULLABLE_SOURCE_IDS: tuple[str, ...] = (
    "ga4",
    "meta_ads",
    "google_ads",
    "search_console",
)


def get_adapter(source_id: str) -> BaseSourceAdapter | None:
    """Look up an adapter, tolerating the ``csv_<slug>`` platform convention."""
    if source_id in REGISTRY:
        return REGISTRY[source_id]
    if source_id.startswith("csv_"):
        return REGISTRY["csv"]
    return None


def list_adapters() -> list[BaseSourceAdapter]:
    return list(REGISTRY.values())


class PullOutcome:
    """
    Result of pulling every connected source for one client and period.

    ``data`` holds only sources that returned usable data, keyed the way the
    report pipeline already expects (``"ga4"``, ``"meta_ads"``, …).
    ``failures`` records sources that were connected but errored, so callers can
    surface a partial-data warning instead of silently shipping a thinner report.
    """

    def __init__(self) -> None:
        self.data: dict[str, dict[str, Any]] = {}
        self.failures: dict[str, str] = {}
        self.reauth_required: list[str] = []
        self.currency: str = "USD"

    @property
    def has_data(self) -> bool:
        return bool(self.data)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PullOutcome sources={list(self.data)} "
            f"failures={list(self.failures)} currency={self.currency}>"
        )


def _needed_columns() -> str:
    """Union of the columns every pullable adapter declares, as a select string."""
    columns: set[str] = {"id", "platform", "status"}
    for source_id in PULLABLE_SOURCE_IDS:
        adapter = REGISTRY[source_id]
        columns.update(adapter.connection_columns)
    return ",".join(sorted(columns))


async def pull_all_sources(
    *,
    supabase: Any,
    client_id: str,
    period_start: str,
    period_end: str,
) -> PullOutcome:
    """
    Pull every active connection for *client_id* concurrently.

    One source failing never fails the report — the failure is recorded and the
    remaining sources still render. That matches the previous per-platform
    ``try/except`` behaviour, but now it is written once instead of eight times.
    """
    outcome = PullOutcome()

    conn_result = (
        supabase.table("connections")
        .select(_needed_columns())
        .eq("client_id", client_id)
        .eq("status", "active")
        .execute()
    )
    connections = conn_result.data or []
    if not connections:
        return outcome

    # One connection per source; if a client somehow has duplicates, the first
    # active row wins — matching the previous .limit(1) behaviour.
    by_source: dict[str, dict[str, Any]] = {}
    for row in connections:
        source_id = row.get("platform") or ""
        if source_id in PULLABLE_SOURCE_IDS and source_id not in by_source:
            by_source[source_id] = row

    # Meta's account currency drives the currency symbol for the whole report.
    meta_row = by_source.get("meta_ads")
    if meta_row:
        outcome.currency = meta_row.get("currency") or "USD"

    async def _pull_one(source_id: str, row: dict[str, Any]) -> None:
        adapter = REGISTRY[source_id]
        ctx = PullContext(
            connection=row,
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
            supabase=supabase,
            currency=outcome.currency,
        )
        try:
            data = await adapter.pull(ctx)
        except SourceError as exc:
            logger.warning(
                "Pull failed for %s (client %s): %s", source_id, client_id, exc
            )
            outcome.failures[source_id] = str(exc)
            if exc.reauth_required:
                outcome.reauth_required.append(source_id)
            return
        except Exception as exc:  # noqa: BLE001 — an adapter bug must not kill the report
            logger.exception(
                "Unexpected error pulling %s for client %s", source_id, client_id
            )
            outcome.failures[source_id] = str(exc)
            return

        if not data:
            outcome.failures[source_id] = "Source returned no data for this period."
            return

        outcome.data[source_id] = data
        _save_snapshot(supabase, row, client_id, source_id, period_start, period_end, data)

    await asyncio.gather(
        *(_pull_one(source_id, row) for source_id, row in by_source.items())
    )

    logger.info(
        "Pulled sources for client %s: ok=%s failed=%s",
        client_id, list(outcome.data), list(outcome.failures),
    )
    return outcome


def _save_snapshot(
    supabase: Any,
    row: dict[str, Any],
    client_id: str,
    source_id: str,
    period_start: str,
    period_end: str,
    metrics: dict[str, Any],
) -> None:
    """Persist a snapshot for trend analysis. Always non-fatal."""
    try:
        from services.snapshot_saver import save_snapshot  # noqa: PLC0415

        save_snapshot(
            supabase,
            connection_id=row["id"],
            client_id=client_id,
            platform=source_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Snapshot save failed for %s / connection %s", source_id, row.get("id")
        )
