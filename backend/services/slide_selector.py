"""
Smart slide selection and KPI scoring for adaptive report generation.

Core principle: NEVER show a slide with missing data.
The system analyzes available data, selects relevant slides,
and picks the best KPIs — all automatically.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE POOL — all possible slides and their data requirements
# ═══════════════════════════════════════════════════════════════════════════════

# Slide IDs map to template slide indices (0-based).
# Templates contain ALL possible slides; generator deletes unused ones.

SLIDE_INDEX = {
    "cover": 0,
    "executive_summary": 1,
    "kpi_scorecard": 2,
    "website_traffic": 3,
    "website_engagement": 4,
    "website_audience": 5,
    "bounce_rate_analysis": 6,
    "meta_ads_overview": 7,
    "meta_ads_audience": 8,
    "meta_ads_creative": 9,
    "google_ads_overview": 10,
    "google_ads_keywords": 11,
    "seo_overview": 12,
    "csv_data": 13,          # template slide — duplicated per CSV source
    "conversion_funnel": 14,
    "key_wins": 15,
    "concerns": 16,
    "next_steps": 17,
    "custom_section": 18,
}

TOTAL_TEMPLATE_SLIDES = 19


def _has_ga4(data: dict) -> bool:
    return bool(data.get("ga4", {}).get("summary", {}).get("sessions"))


def _has_meta(data: dict) -> bool:
    return bool(data.get("meta_ads", {}).get("summary", {}).get("spend"))


def _has_gads(data: dict) -> bool:
    return bool(data.get("google_ads", {}).get("summary", {}).get("spend"))


def _has_gsc(data: dict) -> bool:
    return bool(data.get("search_console", {}).get("summary", {}).get("clicks"))


def _has_csv(data: dict) -> bool:
    return bool(data.get("csv_sources"))


# Each entry: (slide_id, data_check_fn, detail_levels)
SLIDE_POOL = [
    # ALWAYS INCLUDED
    ("cover",             lambda d: True,     ["full", "summary", "brief"]),
    ("executive_summary", lambda d: True,     ["full", "summary", "brief"]),
    ("kpi_scorecard",     lambda d: True,     ["full", "summary", "brief"]),

    # GA4 slides
    ("website_traffic",     lambda d: _has_ga4(d) and bool(d.get("ga4", {}).get("daily")),
     ["full", "summary"]),
    ("website_engagement",  lambda d: _has_ga4(d) and (bool(d.get("ga4", {}).get("device_breakdown")) or bool(d.get("ga4", {}).get("top_pages"))),
     ["full"]),
    ("website_audience",    lambda d: _has_ga4(d) and (bool(d.get("ga4", {}).get("top_countries")) or bool(d.get("ga4", {}).get("new_vs_returning"))),
     ["full"]),
    ("bounce_rate_analysis", lambda d: _has_ga4(d) and any(day.get("bounce_rate") for day in d.get("ga4", {}).get("daily", [])),
     ["full"]),

    # Meta Ads slides
    ("meta_ads_overview",   lambda d: _has_meta(d),  ["full", "summary"]),
    ("meta_ads_audience",   lambda d: _has_meta(d) and (bool(d.get("meta_ads", {}).get("age_gender")) or bool(d.get("meta_ads", {}).get("placements"))),
     ["full"]),
    ("meta_ads_creative",   lambda d: _has_meta(d) and bool(d.get("meta_ads", {}).get("top_ads")),
     ["full"]),

    # Google Ads slides
    ("google_ads_overview",  lambda d: _has_gads(d),  ["full", "summary"]),
    ("google_ads_keywords",  lambda d: _has_gads(d) and bool(d.get("google_ads", {}).get("search_terms")),
     ["full"]),

    # SEO slides
    ("seo_overview",         lambda d: _has_gsc(d),   ["full", "summary"]),

    # CSV slides (dynamic — one per source)
    ("csv_data",             lambda d: _has_csv(d),   ["full", "summary"]),

    # Funnel
    ("conversion_funnel",    lambda d: _has_ga4(d) and d.get("ga4", {}).get("summary", {}).get("conversions", 0) > 0,
     ["full"]),

    # ALWAYS INCLUDED — conclusions
    ("key_wins",    lambda d: True,  ["full", "summary"]),
    ("concerns",    lambda d: True,  ["full", "summary"]),
    ("next_steps",  lambda d: True,  ["full", "summary", "brief"]),
]


def select_slides(
    data: dict,
    detail_level: str = "full",
    custom_section: dict | None = None,
    narrative: dict | None = None,
) -> list[str]:
    """
    Select which slides to include based on available data and detail level.

    Returns a list of slide IDs that should be KEPT.
    All other slides will be deleted from the template.
    """
    selected: list[str] = []

    for slide_id, data_check, levels in SLIDE_POOL:
        # Skip if not for this detail level
        if detail_level not in levels:
            continue

        # Skip if data check fails
        if not data_check(data):
            continue

        # CSV: add one entry per source
        if slide_id == "csv_data":
            for csv_source in data.get("csv_sources", []):
                selected.append(f"csv_data_{csv_source.get('source_name', csv_source.get('name', 'custom'))}")
            continue

        selected.append(slide_id)

    # Custom section: only if has content
    cs = custom_section or {}
    if cs.get("title") and cs.get("text", "").strip():
        selected.append("custom_section")

    # Remove narrative-dependent slides if narrative is empty
    if narrative:
        for key in ("key_wins", "concerns"):
            content = narrative.get(key, "")
            if isinstance(content, list):
                if not content:
                    selected = [s for s in selected if s != key]
            elif isinstance(content, str):
                if not content.strip():
                    selected = [s for s in selected if s != key]

    logger.info(
        "Slide selection: detail=%s, data_sources=[%s], selected=%d slides: %s",
        detail_level,
        ", ".join(s for s, fn in [
            ("GA4", _has_ga4), ("Meta", _has_meta),
            ("GAds", _has_gads), ("GSC", _has_gsc), ("CSV", _has_csv),
        ] if fn(data)),
        len(selected),
        selected,
    )
    return selected


def get_slides_to_delete(
    selected_slides: list[str],
    num_csv_sources: int = 0,
) -> set[int]:
    """
    Given the list of selected slide IDs, return the set of slide INDICES
    to delete from the template.
    """
    # Build set of indices to KEEP
    keep_indices: set[int] = set()
    for slide_id in selected_slides:
        if slide_id.startswith("csv_data_"):
            # All CSV slides use the csv_data template (index 13)
            keep_indices.add(SLIDE_INDEX["csv_data"])
        elif slide_id in SLIDE_INDEX:
            keep_indices.add(SLIDE_INDEX[slide_id])

    # Delete everything NOT in keep set
    all_indices = set(range(TOTAL_TEMPLATE_SLIDES))
    return all_indices - keep_indices


# ═══════════════════════════════════════════════════════════════════════════════
# SMART KPI SELECTION — pick the 6 most relevant KPIs from available data
# ═══════════════════════════════════════════════════════════════════════════════

def select_kpis(data: dict, currency_symbol: str = "$") -> list[dict]:
    """
    Select the 6 most relevant KPIs from available data.
    Never shows N/A or zero-value KPIs. Priority-sorted.

    Returns list of dicts: {label, value, change, is_currency}
    """
    all_kpis: list[dict] = []

    ga4 = data.get("ga4", {}).get("summary", {})
    meta = data.get("meta_ads", {}).get("summary", {})
    gads = data.get("google_ads", {}).get("summary", {})
    gsc = data.get("search_console", {}).get("summary", {})

    def _fmt_num(v):
        """
        KPI-card big-number formatter — compact K/M/B notation.
        Used only for scorecard hero numbers; detailed values keep full precision.
        """
        try:
            num = float(v)
        except (ValueError, TypeError):
            return str(v) if v else "0"
        abs_num = abs(num)
        if abs_num < 1_000:
            return f"{int(num):,}" if num == int(num) else f"{num:,.1f}"
        if abs_num < 1_000_000:
            return f"{num / 1_000:.1f}K"
        if abs_num < 1_000_000_000:
            return f"{num / 1_000_000:.1f}M"
        return f"{num / 1_000_000_000:.1f}B"

    def _fmt_change(v):
        """
        Format change with direction glyph + ±1% neutral band.
          positive  -> "▲ +X.X%"
          negative  -> "▼ -X.X%"
          neutral   -> "▬ ±X.X%"
        """
        if v is None:
            return None
        if abs(v) < 1.0:
            sign = "+" if v >= 0 else ""
            return f"\u25AC {sign}{v:.1f}%"
        if v >= 0:
            return f"\u25B2 +{v:.1f}%"
        return f"\u25BC {v:.1f}%"

    # ── GA4 KPIs ────────────────────────────────────────────────────────────
    if ga4.get("sessions"):
        all_kpis.append({
            "label": "SESSIONS", "value": _fmt_num(ga4["sessions"]),
            "change": _fmt_change(ga4.get("sessions_change")), "priority": 10,
        })
    if ga4.get("users"):
        all_kpis.append({
            "label": "USERS", "value": _fmt_num(ga4["users"]),
            "change": _fmt_change(ga4.get("users_change")), "priority": 9,
        })
    if ga4.get("conversions") and ga4["conversions"] > 0:
        all_kpis.append({
            "label": "CONVERSIONS", "value": _fmt_num(ga4["conversions"]),
            "change": _fmt_change(ga4.get("conversions_change")), "priority": 10,
        })
    if ga4.get("bounce_rate"):
        all_kpis.append({
            "label": "BOUNCE RATE", "value": f"{float(ga4['bounce_rate']):.1f}%",
            "change": _fmt_change(ga4.get("bounce_rate_change")), "priority": 6,
        })
    if ga4.get("conversion_rate") and ga4.get("conversions", 0) > 0:
        all_kpis.append({
            "label": "CONV. RATE", "value": f"{float(ga4['conversion_rate']):.2f}%",
            "change": _fmt_change(ga4.get("conversion_rate_change")), "priority": 8,
        })
    if ga4.get("new_users"):
        all_kpis.append({
            "label": "NEW USERS", "value": _fmt_num(ga4["new_users"]),
            "change": None, "priority": 5,
        })

    # ── Meta Ads KPIs — only if spend > 0 ──────────────────────────────────
    if meta.get("spend") and meta["spend"] > 0:
        all_kpis.append({
            "label": "AD SPEND", "value": f"{currency_symbol}{_fmt_num(meta['spend'])}",
            "change": _fmt_change(meta.get("spend_change")), "priority": 9,
        })
        if meta.get("roas") and meta["roas"] > 0:
            all_kpis.append({
                "label": "ROAS", "value": f"{meta['roas']:.1f}x",
                "change": None, "priority": 8,
            })
        if meta.get("conversions") and meta["conversions"] > 0:
            all_kpis.append({
                "label": "AD CONVERSIONS", "value": _fmt_num(meta["conversions"]),
                "change": _fmt_change(meta.get("conversions_change")), "priority": 7,
            })
        if meta.get("cost_per_conversion") and meta["cost_per_conversion"] > 0:
            all_kpis.append({
                "label": "COST / CONV.", "value": f"{currency_symbol}{meta['cost_per_conversion']:.2f}",
                "change": None, "priority": 6,
            })
        if meta.get("ctr"):
            all_kpis.append({
                "label": "CTR", "value": f"{float(meta['ctr']):.2f}%",
                "change": None, "priority": 5,
            })

    # ── Google Ads KPIs ─────────────────────────────────────────────────────
    if gads.get("spend") and gads["spend"] > 0:
        all_kpis.append({
            "label": "SEARCH SPEND", "value": f"{currency_symbol}{_fmt_num(gads['spend'])}",
            "change": _fmt_change(gads.get("spend_change")), "priority": 8,
        })
        if gads.get("conversions"):
            all_kpis.append({
                "label": "SEARCH CONV.", "value": _fmt_num(gads["conversions"]),
                "change": _fmt_change(gads.get("conversions_change")), "priority": 7,
            })
        if gads.get("roas") and gads["roas"] > 0:
            all_kpis.append({
                "label": "SEARCH ROAS", "value": f"{gads['roas']:.1f}x",
                "change": None, "priority": 6,
            })

    # ── SEO KPIs ────────────────────────────────────────────────────────────
    if gsc.get("clicks"):
        all_kpis.append({
            "label": "ORGANIC CLICKS", "value": _fmt_num(gsc["clicks"]),
            "change": _fmt_change(gsc.get("clicks_change")), "priority": 7,
        })
        if gsc.get("average_position"):
            all_kpis.append({
                "label": "AVG POSITION", "value": f"{gsc['average_position']:.1f}",
                "change": _fmt_change(gsc.get("position_change")), "priority": 6,
            })

    # ── CSV KPIs — max 2 per source ─────────────────────────────────────────
    for csv_source in data.get("csv_sources", []):
        for metric in csv_source.get("metrics", [])[:2]:
            prev = metric.get("previous_value")
            curr = metric["current_value"]
            if prev and prev > 0:
                change_pct = round((curr - prev) / prev * 100, 1)
            else:
                change_pct = None
            unit = metric.get("unit", "number")
            if unit == "currency":
                val_str = f"{currency_symbol}{curr:,.0f}" if isinstance(curr, (int, float)) else str(curr)
            elif unit == "percent":
                val_str = f"{curr}%"
            else:
                val_str = f"{curr:,}" if isinstance(curr, (int, float)) else str(curr)
            all_kpis.append({
                "label": metric["name"].upper(),
                "value": val_str,
                "change": _fmt_change(change_pct),
                "priority": 4,
            })

    # Sort by priority descending and take top 6
    all_kpis.sort(key=lambda x: x["priority"], reverse=True)
    selected = all_kpis[:6]

    logger.info("Selected %d KPIs from %d candidates: %s",
                len(selected), len(all_kpis),
                [k["label"] for k in selected])
    return selected
