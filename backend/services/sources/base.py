"""
Source adapter contract — the single seam every data source implements.

Before this module each integration was bespoke: four pull functions with four
different signatures, three different failure conventions (raise / return {} /
return None) and two concurrency models, glued together by ~90 lines of
copy-pasted boilerplate per platform in routers/reports.py — duplicated across
_generate_report_internal and regenerate_report.

An adapter now owns everything source-specific:
    • which connections row columns it needs
    • how to turn stored credentials into an authenticated call
    • how to normalise the response
    • how to report health

and routers/reports.py owns nothing source-specific at all.

Rules for adapter authors
-------------------------
1. ``pull()`` raises ``SourceError`` on failure. Never return {} or None to
   signal an error — the orchestrator cannot tell that apart from "no data".
2. ``pull()`` returns the source's legacy report-pipeline dict (the shape
   chart_generator / ai_narrative / report_generator already consume).
   ``services.sources.canonical`` holds the forward-looking envelope; adapters
   opt into it via ``to_canonical()`` without disturbing rendering.
3. Adapters are async. Wrap synchronous SDK calls in ``asyncio.to_thread``
   inside the adapter, not at the call site.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


CredentialType = Literal["oauth", "api_key", "key_pair", "none"]
SourceKind = Literal[
    "analytics", "ads", "seo", "ecommerce", "email", "calls", "custom"
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class SourceError(Exception):
    """
    Raised by an adapter when a pull or probe cannot complete.

    ``reauth_required`` is the signal the connection-health layer cares about:
    it means the stored credential is dead and no retry will help — the user
    must reconnect. Everything else is treated as transient.
    """

    def __init__(
        self,
        message: str,
        *,
        source_id: str = "",
        reauth_required: bool = False,
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.source_id = source_id
        self.reauth_required = reauth_required
        self.retryable = retryable and not reauth_required


# ---------------------------------------------------------------------------
# Credential description — drives the generic Connections-page UI
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CredentialField:
    """One input in the credential dialog for an api_key / key_pair source."""

    name: str                       # key in the stored credential bundle
    label: str                      # UI label
    secret: bool = True             # render masked, never echo back to client
    placeholder: str = ""
    help_text: str = ""
    docs_url: str = ""              # deep link to where the user finds this value


# ---------------------------------------------------------------------------
# Pull context
# ---------------------------------------------------------------------------

@dataclass
class PullContext:
    """
    Everything an adapter needs for one period, assembled by the orchestrator.

    ``connection`` is the raw ``connections`` row. Adapters read the columns
    they declared in ``connection_columns`` and nothing else.
    """

    connection: dict[str, Any]
    client_id: str
    period_start: str               # "YYYY-MM-DD"
    period_end: str
    supabase: Any                   # admin client, for token write-back
    currency: str = "USD"
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def connection_id(self) -> str:
        return str(self.connection.get("id", ""))

    @property
    def account_id(self) -> str:
        return str(self.connection.get("account_id", ""))


@dataclass
class HealthResult:
    """Outcome of a lightweight credential check."""

    ok: bool
    detail: str = ""
    reauth_required: bool = False


# ---------------------------------------------------------------------------
# The adapter protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class SourceAdapter(Protocol):
    """Structural contract. Adapters are module-level singletons in the registry."""

    source_id: str                          # matches connections.platform
    label: str                              # human-readable, for UI + narrative
    kind: SourceKind
    credential_type: CredentialType
    required_fields: tuple[CredentialField, ...]
    connection_columns: tuple[str, ...]     # columns to SELECT for this source

    async def pull(self, ctx: PullContext) -> dict[str, Any]:
        """Return the legacy report-pipeline dict. Raise SourceError on failure."""
        ...

    async def probe(self, ctx: PullContext) -> HealthResult:
        """Cheap credential validity check. Must not raise."""
        ...


# ---------------------------------------------------------------------------
# Base implementation — adapters subclass this to inherit sane defaults
# ---------------------------------------------------------------------------

class BaseSourceAdapter:
    """Common defaults. Subclasses must set the class attributes and define pull()."""

    source_id: str = ""
    label: str = ""
    kind: SourceKind = "custom"
    credential_type: CredentialType = "oauth"
    required_fields: tuple[CredentialField, ...] = ()
    connection_columns: tuple[str, ...] = (
        "id",
        "account_id",
        "account_name",
        "access_token_encrypted",
        "refresh_token_encrypted",
        "token_expires_at",
    )

    async def pull(self, ctx: PullContext) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    async def probe(self, ctx: PullContext) -> HealthResult:
        """
        Default probe: attempt a pull and classify the outcome. Adapters with a
        cheaper validity endpoint should override this.
        """
        try:
            await self.pull(ctx)
            return HealthResult(ok=True)
        except SourceError as exc:
            return HealthResult(
                ok=False, detail=str(exc), reauth_required=exc.reauth_required
            )
        except Exception as exc:  # noqa: BLE001 — probe must never raise
            logger.exception("probe failed for %s", self.source_id)
            return HealthResult(ok=False, detail=str(exc))
