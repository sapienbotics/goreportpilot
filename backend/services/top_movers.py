"""
Top-Movers Extraction — Phase 4 Diagnostic Narrative v2.

Purpose
-------
Convert the raw pulled platform data (already present in the ``data`` dict
that the generator passes to ``generate_narrative``) into a small,
structured "diagnostic context" block. The GPT-4.1 prompt then injects
this block so the AI can write *causally*:

  Before: "Paid ads grew 18%."
  After:  "Paid ads grew 18% — driven by 'Q2 Summer Sale' (ROAS 4.2x,
           spend $3,200, 32% of total) which outperformed the account
           average by 2.1x."

The gap user research flagged (docs/USER-RESEARCH-APRIL-2026.md, Rec #1)
is that the AI was getting ONLY aggregated summaries in its prompt. The
richer fields — campaign lists, traffic sources, top pages, search
queries — were already present in ``data`` but never serialized into
the prompt. This module serializes them with deliberate rankings so the
AI can name specific entities as the *drivers* of headline changes.

What this is NOT
----------------
- Not a change-based mover (i.e. NOT "biggest gainers vs last month").
  Campaign-level prev-period data is not in the current pull shape.
  Change-based rankings would require joining to ``data_snapshots`` from
  the Phase 1 snapshot infra — deferred to Phase 5.
- Not a data fetcher. Operates purely on the in-memory ``data`` dict.
- Not an LLM call. Pure Python dict transforms. Unit-testable.

Return shape
------------
``compute_top_movers(data)`` returns a dict keyed by platform:

    {
        "meta_ads": {
            "best_by_roas":   [ {...}, ... ],
            "worst_by_roas":  [...],
            "highest_spend":  [...],
            "top_converters": [...],
        },
        "google_ads": { ... similar shape ... },
        "ga4": {
            "top_sources":   [ {"medium": "Organic", "sessions": 4521, "share_pct": 36.2}, ... ],
            "top_pages":     [...],
            "device_split":  [...],
        },
        "search_console": {
            "top_queries": [...],
            "top_pages":   [...],
        },
    }

Only dimensions with enough data return entries. Empty platforms are
omitted entirely so the caller's prompt stays tight.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─── Thresholds + ranking helpers ─────────────────────────────────────────────


# Minimum spend (fraction of total account spend) for a campaign to be
# eligible for ROAS ranking. Prevents $5 test campaigns with absurd
# ROAS numbers from dominating "best/worst" lists.
_ROAS_SPEND_SHARE_FLOOR = 0.05

# How many entries per ranking dimension.
_RANK_LIMIT = 3
_LONG_RANK_LIMIT = 5  # For GA4 sources / SC queries (users expect "top 5")


def _round(value: Any, digits: int = 2) -> float | None:
    """Coerce to rounded float, return None on bad/missing input."""
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _eligible_for_roas_ranking(
    campaign: dict, total_spend: float,
) -> bool:
    """Return True if this campaign's spend share ≥ _ROAS_SPEND_SHARE_FLOOR."""
    if total_spend <= 0:
        return True
    spend = float(campaign.get("spend") or 0.0)
    return (spend / total_spend) >= _ROAS_SPEND_SHARE_FLOOR


# ─── Per-platform extractors ──────────────────────────────────────────────────


def _meta_ads_movers(meta: dict) -> dict[str, Any]:
    """Rank Meta Ads campaigns along four dimensions."""
    campaigns = meta.get("campaigns") or []
    if not campaigns:
        return {}

    total_spend = float((meta.get("summary") or {}).get("spend") or 0.0)
    if total_spend <= 0:
        total_spend = sum(float(c.get("spend") or 0.0) for c in campaigns)

    def _summarise(c: dict) -> dict:
        return {
            "name":        c.get("name", "Unknown"),
            "spend":       _round(c.get("spend"), 2),
            "clicks":      _safe_int(c.get("clicks")),
            "conversions": _safe_int(c.get("conversions")),
            "cpc":         _round(c.get("cpc"), 2),
            "roas":        _round(c.get("roas"), 2),
            "spend_share_pct": (
                round((float(c.get("spend") or 0.0) / total_spend) * 100, 1)
                if total_spend > 0 else None
            ),
        }

    # Campaigns eligible for ROAS ranking (above spend-share floor AND roas > 0)
    eligible = [c for c in campaigns
                if _eligible_for_roas_ranking(c, total_spend)
                and float(c.get("roas") or 0.0) > 0]

    out: dict[str, Any] = {}

    # Best by ROAS — highest performing at meaningful spend.
    if eligible:
        best = sorted(eligible, key=lambda c: float(c.get("roas") or 0.0),
                      reverse=True)
        out["best_by_roas"] = [_summarise(c) for c in best[:_RANK_LIMIT]]

    # Worst by ROAS — bleed-out campaigns at meaningful spend.
    if len(eligible) >= 2:
        worst = sorted(eligible, key=lambda c: float(c.get("roas") or 0.0))
        out["worst_by_roas"] = [_summarise(c) for c in worst[:_RANK_LIMIT]]

    # Highest spend — budget hogs (any roas, shows the account's priorities).
    by_spend = sorted(campaigns, key=lambda c: float(c.get("spend") or 0.0),
                      reverse=True)
    out["highest_spend"] = [_summarise(c) for c in by_spend[:_RANK_LIMIT]]

    # Top converters — who actually delivers volume.
    with_conv = [c for c in campaigns if _safe_int(c.get("conversions")) > 0]
    if with_conv:
        by_conv = sorted(with_conv, key=lambda c: _safe_int(c.get("conversions")),
                         reverse=True)
        out["top_converters"] = [_summarise(c) for c in by_conv[:_RANK_LIMIT]]

    return out


def _google_ads_movers(google: dict) -> dict[str, Any]:
    """Rank Google Ads campaigns — schema mirrors Meta Ads."""
    campaigns = google.get("campaigns") or []
    if not campaigns:
        return {}

    total_spend = float((google.get("summary") or {}).get("spend") or 0.0)
    if total_spend <= 0:
        total_spend = sum(float(c.get("spend") or 0.0) for c in campaigns)

    def _summarise(c: dict) -> dict:
        return {
            "name":        c.get("name", "Unknown"),
            "spend":       _round(c.get("spend"), 2),
            "clicks":      _safe_int(c.get("clicks")),
            "conversions": _safe_int(c.get("conversions")),
            "ctr":         _round(c.get("ctr"), 2),
            "cpc":         _round(c.get("cpc"), 2),
            "spend_share_pct": (
                round((float(c.get("spend") or 0.0) / total_spend) * 100, 1)
                if total_spend > 0 else None
            ),
        }

    out: dict[str, Any] = {}

    # Highest spend
    by_spend = sorted(campaigns, key=lambda c: float(c.get("spend") or 0.0),
                      reverse=True)
    out["highest_spend"] = [_summarise(c) for c in by_spend[:_RANK_LIMIT]]

    # Top converters (Google Ads has conversions field)
    with_conv = [c for c in campaigns if _safe_int(c.get("conversions")) > 0]
    if with_conv:
        by_conv = sorted(with_conv, key=lambda c: _safe_int(c.get("conversions")),
                         reverse=True)
        out["top_converters"] = [_summarise(c) for c in by_conv[:_RANK_LIMIT]]

    # Best / worst by CTR at meaningful spend (Google Ads schema has no ROAS
    # unless conversion-value tracking is configured — fall back to CTR).
    eligible = [c for c in campaigns
                if _eligible_for_roas_ranking(c, total_spend)]
    if len(eligible) >= 2:
        by_ctr = sorted(eligible, key=lambda c: float(c.get("ctr") or 0.0),
                        reverse=True)
        out["best_by_ctr"]  = [_summarise(c) for c in by_ctr[:_RANK_LIMIT]]
        out["worst_by_ctr"] = [_summarise(c) for c in by_ctr[-_RANK_LIMIT:][::-1]]

    return out


def _ga4_movers(ga4: dict) -> dict[str, Any]:
    """Extract GA4 movers — sources, pages, devices."""
    out: dict[str, Any] = {}

    # Traffic sources (dict medium → sessions). Convert to ranked list
    # with share-of-total for diagnostic context.
    sources = ga4.get("traffic_sources") or {}
    if isinstance(sources, dict) and sources:
        total = sum(int(v or 0) for v in sources.values())
        ranked = sorted(sources.items(), key=lambda kv: int(kv[1] or 0),
                        reverse=True)
        out["top_sources"] = [
            {
                "medium":     medium,
                "sessions":   int(sessions or 0),
                "share_pct":  round((int(sessions or 0) / total) * 100, 1)
                               if total > 0 else None,
            }
            for medium, sessions in ranked[:_LONG_RANK_LIMIT]
        ]

    # Top pages by pageviews (preferred) then sessions.
    top_pages = ga4.get("top_pages") or []
    if top_pages:
        ranked = sorted(top_pages,
                        key=lambda p: int(p.get("pageviews") or p.get("sessions") or 0),
                        reverse=True)
        out["top_pages"] = [
            {
                "page":      p.get("page", "Unknown"),
                "pageviews": _safe_int(p.get("pageviews")),
                "sessions":  _safe_int(p.get("sessions")),
            }
            for p in ranked[:_LONG_RANK_LIMIT]
        ]

    # Device split with best / worst engagement (bounce_rate).
    devices = ga4.get("device_breakdown") or []
    if devices:
        total_sessions = sum(int(d.get("sessions") or 0) for d in devices)
        split = [
            {
                "device":      d.get("device", "Other"),
                "sessions":    _safe_int(d.get("sessions")),
                "share_pct":   round((int(d.get("sessions") or 0) / total_sessions) * 100, 1)
                                if total_sessions > 0 else None,
                "bounce_rate": _round(d.get("bounce_rate"), 1),
            }
            for d in devices
        ]
        split.sort(key=lambda d: d["sessions"] or 0, reverse=True)
        out["device_split"] = split

    return out


def _search_console_movers(sc: dict) -> dict[str, Any]:
    """Extract Search Console movers — top queries + top pages."""
    out: dict[str, Any] = {}

    queries = sc.get("top_queries") or []
    if queries:
        ranked = sorted(queries, key=lambda q: int(q.get("clicks") or 0),
                        reverse=True)
        out["top_queries"] = [
            {
                "query":       q.get("query", "Unknown"),
                "clicks":      _safe_int(q.get("clicks")),
                "impressions": _safe_int(q.get("impressions")),
                "ctr":         _round(q.get("ctr"), 2),
                "position":    _round(q.get("position"), 1),
            }
            for q in ranked[:_LONG_RANK_LIMIT]
        ]

    pages = sc.get("top_pages") or []
    if pages:
        ranked = sorted(pages, key=lambda p: int(p.get("clicks") or 0),
                        reverse=True)
        out["top_pages"] = [
            {
                "page":        p.get("page", "Unknown"),
                "clicks":      _safe_int(p.get("clicks")),
                "impressions": _safe_int(p.get("impressions")),
                "ctr":         _round(p.get("ctr"), 2),
            }
            for p in ranked[:_LONG_RANK_LIMIT]
        ]

    return out


# ─── Public entrypoint ────────────────────────────────────────────────────────


def compute_top_movers(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract a structured diagnostic-movers context from a pulled data dict.

    Safe to call on partial data — each platform is optional. Platforms
    with no rankable content are omitted from the returned dict.

    Args:
        data: The combined ``data`` dict passed to ``generate_narrative``.
            Same shape the generator receives from the router.

    Returns:
        Dict keyed by platform. See module docstring for full shape.
    """
    if not isinstance(data, dict):
        return {}

    result: dict[str, Any] = {}

    meta = data.get("meta_ads") or {}
    if meta:
        meta_block = _meta_ads_movers(meta)
        if meta_block:
            result["meta_ads"] = meta_block

    google = data.get("google_ads") or {}
    if google:
        google_block = _google_ads_movers(google)
        if google_block:
            result["google_ads"] = google_block

    ga4 = data.get("ga4") or {}
    if ga4:
        ga4_block = _ga4_movers(ga4)
        if ga4_block:
            result["ga4"] = ga4_block

    sc = data.get("search_console") or {}
    if sc:
        sc_block = _search_console_movers(sc)
        if sc_block:
            result["search_console"] = sc_block

    return result


# ─── Serialiser for prompt injection ──────────────────────────────────────────


def format_movers_for_prompt(
    movers: dict[str, Any],
    currency_symbol: str = "$",
) -> str:
    """
    Render the movers dict as a compact, readable prompt block.

    The AI parses this better as prose bullets than as raw JSON — GPT-4.1
    empirically follows specific-number-citation instructions more
    reliably when the source data is formatted close to how it should
    appear in the output.
    """
    if not movers:
        return ""

    lines: list[str] = ["TOP MOVERS (specific entities behind the headline numbers — cite these by name in your analysis):"]

    # Meta Ads
    meta = movers.get("meta_ads") or {}
    if meta:
        lines.append("")
        lines.append("  META ADS CAMPAIGN-LEVEL RANKINGS:")
        for key, label in (
            ("best_by_roas",   "Best ROAS campaigns"),
            ("worst_by_roas",  "Worst ROAS campaigns (at meaningful spend)"),
            ("highest_spend",  "Highest-spend campaigns"),
            ("top_converters", "Top converting campaigns"),
        ):
            rows = meta.get(key) or []
            if not rows:
                continue
            lines.append(f"    {label}:")
            for r in rows:
                lines.append(
                    f"      - {r['name']}: "
                    f"spend={currency_symbol}{r['spend']}, "
                    f"ROAS={r.get('roas', 'N/A')}x, "
                    f"conv={r['conversions']}, "
                    f"share={r.get('spend_share_pct', 'N/A')}%"
                )

    # Google Ads
    google = movers.get("google_ads") or {}
    if google:
        lines.append("")
        lines.append("  GOOGLE ADS CAMPAIGN-LEVEL RANKINGS:")
        for key, label in (
            ("highest_spend",  "Highest-spend campaigns"),
            ("top_converters", "Top converting campaigns"),
            ("best_by_ctr",    "Best CTR campaigns (at meaningful spend)"),
            ("worst_by_ctr",   "Worst CTR campaigns (at meaningful spend)"),
        ):
            rows = google.get(key) or []
            if not rows:
                continue
            lines.append(f"    {label}:")
            for r in rows:
                lines.append(
                    f"      - {r['name']}: "
                    f"spend={currency_symbol}{r['spend']}, "
                    f"CTR={r.get('ctr', 'N/A')}%, "
                    f"conv={r['conversions']}, "
                    f"share={r.get('spend_share_pct', 'N/A')}%"
                )

    # GA4
    ga4 = movers.get("ga4") or {}
    if ga4:
        lines.append("")
        lines.append("  GA4 TRAFFIC / ENGAGEMENT RANKINGS:")
        if ga4.get("top_sources"):
            lines.append("    Top traffic sources:")
            for r in ga4["top_sources"]:
                lines.append(
                    f"      - {r['medium']}: {r['sessions']} sessions "
                    f"({r.get('share_pct', 'N/A')}% of total)"
                )
        if ga4.get("top_pages"):
            lines.append("    Top landing pages:")
            for r in ga4["top_pages"]:
                lines.append(
                    f"      - {r['page']}: {r['pageviews']} views, "
                    f"{r['sessions']} sessions"
                )
        if ga4.get("device_split"):
            lines.append("    Device split:")
            for r in ga4["device_split"]:
                lines.append(
                    f"      - {r['device']}: {r['sessions']} sessions "
                    f"({r.get('share_pct', 'N/A')}%), "
                    f"bounce={r.get('bounce_rate', 'N/A')}%"
                )

    # Search Console
    sc = movers.get("search_console") or {}
    if sc:
        lines.append("")
        lines.append("  SEO (SEARCH CONSOLE) RANKINGS:")
        if sc.get("top_queries"):
            lines.append("    Top organic queries:")
            for r in sc["top_queries"]:
                lines.append(
                    f"      - \"{r['query']}\": {r['clicks']} clicks, "
                    f"{r['impressions']} impr, "
                    f"CTR={r.get('ctr', 'N/A')}%, pos={r.get('position', 'N/A')}"
                )
        if sc.get("top_pages"):
            lines.append("    Top organic landing pages:")
            for r in sc["top_pages"]:
                lines.append(
                    f"      - {r['page']}: {r['clicks']} clicks, "
                    f"{r['impressions']} impr, CTR={r.get('ctr', 'N/A')}%"
                )

    return "\n".join(lines)
