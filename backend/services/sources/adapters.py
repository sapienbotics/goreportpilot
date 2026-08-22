"""
Adapters for the four existing sources.

Each one wraps its service module unchanged — ``pull_ga4_data`` and friends keep
their current signatures and bodies, so there is no behavioural risk here. What
the adapter adds is uniformity: one signature, one failure convention, one place
that knows which connections columns the source needs.

New sources (Track B) implement BaseSourceAdapter directly rather than wrapping
a legacy function.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from services.sources.base import (
    BaseSourceAdapter,
    CredentialField,
    HealthResult,
    PullContext,
    SourceError,
)
from services.sources.oauth_refresh import parse_expiry

logger = logging.getLogger(__name__)


def _require(ctx: PullContext, column: str, source_id: str) -> str:
    """Read a required connections column, failing loudly rather than pulling with junk."""
    value = ctx.connection.get(column)
    if not value:
        raise SourceError(
            f"Connection {ctx.connection_id} is missing '{column}' — reconnect the account.",
            source_id=source_id,
            reauth_required=True,
        )
    return str(value)


# ---------------------------------------------------------------------------
# Google Analytics 4
# ---------------------------------------------------------------------------

class GA4Adapter(BaseSourceAdapter):
    source_id = "ga4"
    label = "Google Analytics"
    kind = "analytics"
    credential_type = "oauth"

    async def pull(self, ctx: PullContext) -> dict[str, Any]:
        from services.google_analytics import pull_ga4_data  # noqa: PLC0415

        try:
            return await pull_ga4_data(
                access_token_encrypted=ctx.connection["access_token_encrypted"],
                refresh_token_encrypted=ctx.connection.get("refresh_token_encrypted"),
                token_expires_at=parse_expiry(ctx.connection.get("token_expires_at")),
                property_id=_require(ctx, "account_id", self.source_id),
                period_start=ctx.period_start,
                period_end=ctx.period_end,
                connection_id=ctx.connection_id,
                supabase=ctx.supabase,
            )
        except SourceError:
            raise
        except PermissionError as exc:
            raise SourceError(
                str(exc), source_id=self.source_id, reauth_required=True
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise SourceError(str(exc), source_id=self.source_id) from exc


# ---------------------------------------------------------------------------
# Meta Ads
# ---------------------------------------------------------------------------

class MetaAdsAdapter(BaseSourceAdapter):
    source_id = "meta_ads"
    label = "Meta Ads"
    kind = "ads"
    credential_type = "oauth"
    connection_columns = (
        "id",
        "account_id",
        "account_name",
        "currency",
        "access_token_encrypted",
        "refresh_token_encrypted",
        "token_expires_at",
    )

    async def pull(self, ctx: PullContext) -> dict[str, Any]:
        from services.meta_ads import pull_meta_ads_data  # noqa: PLC0415

        try:
            data = await pull_meta_ads_data(
                account_id=_require(ctx, "account_id", self.source_id),
                access_token_encrypted=ctx.connection["access_token_encrypted"],
                period_start=ctx.period_start,
                period_end=ctx.period_end,
                connection_id=ctx.connection_id,
                currency=ctx.currency,
            )
        except SourceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SourceError(str(exc), source_id=self.source_id) from exc

        # The caller used to re-stamp currency after the pull; do it here so
        # the orchestrator stays source-agnostic.
        data["currency"] = ctx.currency
        return data


# ---------------------------------------------------------------------------
# Google Ads
# ---------------------------------------------------------------------------

class GoogleAdsAdapter(BaseSourceAdapter):
    source_id = "google_ads"
    label = "Google Ads"
    kind = "ads"
    credential_type = "oauth"

    async def pull(self, ctx: PullContext) -> dict[str, Any]:
        from services.google_ads import pull_google_ads_data  # noqa: PLC0415

        try:
            # Synchronous SDK — kept off the event loop inside the adapter so
            # the orchestrator does not need to know.
            result = await asyncio.to_thread(
                pull_google_ads_data,
                access_token_encrypted=ctx.connection["access_token_encrypted"],
                refresh_token_encrypted=ctx.connection.get("refresh_token_encrypted"),
                customer_id=_require(ctx, "account_id", self.source_id),
                period_start=ctx.period_start,
                period_end=ctx.period_end,
                token_expires_at=parse_expiry(ctx.connection.get("token_expires_at")),
            )
        except SourceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SourceError(str(exc), source_id=self.source_id) from exc

        # Legacy convention: {} meant failure. Convert to the uniform one.
        if not result:
            raise SourceError(
                "Google Ads returned no data for this period.", source_id=self.source_id
            )
        return result


# ---------------------------------------------------------------------------
# Search Console
# ---------------------------------------------------------------------------

class SearchConsoleAdapter(BaseSourceAdapter):
    source_id = "search_console"
    label = "Search Console"
    kind = "seo"
    credential_type = "oauth"

    async def pull(self, ctx: PullContext) -> dict[str, Any]:
        from services.search_console import pull_search_console_data  # noqa: PLC0415

        try:
            result = await pull_search_console_data(
                access_token_encrypted=ctx.connection["access_token_encrypted"],
                refresh_token_encrypted=ctx.connection.get("refresh_token_encrypted"),
                site_url=_require(ctx, "account_id", self.source_id),
                period_start=ctx.period_start,
                period_end=ctx.period_end,
                token_expires_at=parse_expiry(ctx.connection.get("token_expires_at")),
            )
        except SourceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SourceError(str(exc), source_id=self.source_id) from exc

        if not result:
            raise SourceError(
                "Search Console returned no data for this period.",
                source_id=self.source_id,
            )
        return result


# ---------------------------------------------------------------------------
# CSV — not pulled from an API, but registered so the UI and narrative layers
# can describe it through the same interface as everything else.
# ---------------------------------------------------------------------------

class CSVAdapter(BaseSourceAdapter):
    source_id = "csv"
    label = "CSV / spreadsheet upload"
    kind = "custom"
    credential_type = "none"
    required_fields: tuple[CredentialField, ...] = ()
    connection_columns = ("id", "account_id", "account_name", "platform")

    async def pull(self, ctx: PullContext) -> dict[str, Any]:
        raise SourceError(
            "CSV sources are supplied with the generation request, not pulled.",
            source_id=self.source_id,
            retryable=False,
        )

    async def probe(self, ctx: PullContext) -> HealthResult:
        # An uploaded file cannot go stale the way a credential can.
        return HealthResult(ok=True, detail="CSV upload — no credential to verify.")
