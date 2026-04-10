"""
Chart generator — creates PNG chart images for reports using matplotlib.
All functions are synchronous; call via asyncio.to_thread() in async contexts.

Phase 2 upgrades:
  - Theme-aware colours (light / dark / colorful) so charts match slide backgrounds
  - 300 DPI for crisp high-resolution output
  - 5.6 × 3.0 inch figsize — matches the PPTX chart placeholder exactly
  - Calibri / Arial font with proper size scale (12 title, 10 labels, 9 ticks)
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — must be set before importing pyplot
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

# ── Font detection ─────────────────────────────────────────────────────────────
# Try Calibri first (common on Windows), fall back to Arial then DejaVu Sans
_CHART_FONT = "DejaVu Sans"
for _font_candidate in ["Calibri", "Arial", "Liberation Sans"]:
    try:
        fm.findfont(_font_candidate, fallback_to_default=False)
        _CHART_FONT = _font_candidate
        break
    except Exception:
        continue
logger.debug("Chart font resolved to: %s", _CHART_FONT)

# ── Currency symbol lookup ────────────────────────────────────────────────────
_CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",    "EUR": "€",    "GBP": "£",    "INR": "₹",
    "AUD": "A$",   "CAD": "C$",   "JPY": "¥",    "CNY": "¥",
    "BRL": "R$",   "MXN": "Mex$", "SGD": "S$",   "HKD": "HK$",
    "CHF": "CHF ", "SEK": "kr",   "NOK": "kr",   "DKK": "kr",
    "ZAR": "R",    "AED": "AED ", "SAR": "SAR ",  "MYR": "RM",
}


def _get_currency_symbol(data: Dict[str, Any]) -> str:
    """Extract currency symbol from the report data dict."""
    code = (data.get("meta_ads", {}).get("currency") or "USD").upper()
    return _CURRENCY_SYMBOLS.get(code, code + " ")


# ── Chart themes ──────────────────────────────────────────────────────────────
# Each theme defines all colours needed by _setup_chart_style().
# "primary_color" is the default data series colour; brand_color overrides it.
CHART_THEMES: Dict[str, Dict[str, Any]] = {
    "light": {
        "fig_bg":          "#FAFAFA",
        "axes_bg":         "#FAFAFA",
        "text_color":      "#475569",   # slate-600
        "title_color":     "#0F172A",   # slate-900
        "grid_color":      "#E2E8F0",   # slate-200
        "grid_alpha":      0.3,
        "spine_color":     "#CBD5E1",   # slate-300
        "primary_color":   "#4338CA",   # indigo-700
        "secondary_color": "#06B6D4",   # cyan-500
        "accent_color":    "#F59E0B",   # amber-400
        "danger_color":    "#E11D48",   # rose-600
        "gray_color":      "#64748B",   # slate-500
    },
    "dark": {
        "fig_bg":          "#1E293B",   # slate-800 — matches dark_executive card bg
        "axes_bg":         "#1E293B",
        "text_color":      "#CBD5E1",   # slate-300
        "title_color":     "#F8FAFC",   # slate-50
        "grid_color":      "#334155",   # slate-700
        "grid_alpha":      0.4,
        "spine_color":     "#475569",   # slate-600
        "primary_color":   "#06B6D4",   # cyan-500 (bright on dark)
        "secondary_color": "#10B981",   # emerald-500
        "accent_color":    "#F59E0B",   # amber-400
        "danger_color":    "#F87171",   # red-400 (lighter for contrast)
        "gray_color":      "#94A3B8",   # slate-400
    },
    "colorful": {
        "fig_bg":          "#FFFFFF",
        "axes_bg":         "#FFFFFF",
        "text_color":      "#475569",
        "title_color":     "#0F172A",
        "grid_color":      "#E2E8F0",
        "grid_alpha":      0.3,
        "spine_color":     "#CBD5E1",
        "primary_color":   "#F97316",   # orange-500 (coral)
        "secondary_color": "#8B5CF6",   # violet-500
        "accent_color":    "#14B8A6",   # teal-500
        "danger_color":    "#E11D48",   # rose-600
        "gray_color":      "#64748B",
    },
}

# Map visual_template names to theme names
_VISUAL_TO_THEME: Dict[str, str] = {
    "modern_clean":    "light",
    "dark_executive":  "dark",
    "colorful_agency": "colorful",
    "bold_geometric":  "light",
    "minimal_elegant": "light",
    "gradient_modern": "colorful",
}

# Chart dimensions — exactly matches the PPTX chart placeholder size
_FIGSIZE = (5.6, 3.0)
_DPI = 300

# ── Okabe-Ito color-blind-safe categorical palette ────────────────────────────
# Nature Methods' recommended qualitative palette (remains distinguishable
# under protanopia, deuteranopia, and tritanopia). Used as the default
# multi-series cycle in charts with ≥3 categorical dimensions. Single-series
# charts keep the brand/primary color. Order chosen for maximum perceptual
# distance between adjacent colors.
OKABE_ITO: list[str] = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # bluish green
    "#CC79A7",  # reddish purple
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
]

# Muted "de-emphasized" gray used by the highlight-one-bar strategy in
# plot_campaign_performance() — draws the eye to the top performer by
# graying everything else out.
_MUTED_BAR = "#CBD5E1"  # slate-300

# GA4 channel / source label cleanup. The raw API returns ugly parenthesized
# sentinels like "(none)" for direct traffic and "(not set)" when a medium is
# missing. Rewrite these to human-friendly labels before plotting.
_SOURCE_LABEL_MAP: Dict[str, str] = {
    "(none)":         "Direct",
    "(direct)":       "Direct",
    "direct":         "Direct",
    "(not set)":      "Other",
    "(not provided)": "Other",
}


def _clean_source_label(label: str) -> str:
    """
    Map ugly GA4 source sentinels to human-friendly labels.

    Raw lowercase channel names ("referral", "organic") are title-cased so
    the chart axis shows "Referral" / "Organic" instead of stretched-out
    lowercase. Already-mapped labels (e.g. "Direct") are returned as-is.
    """
    if not label:
        return "Other"
    key = str(label).strip().lower()
    mapped = _SOURCE_LABEL_MAP.get(key)
    if mapped is not None:
        return mapped
    return str(label).title()


def _setup_chart_style(theme: Dict[str, Any], brand_color: str | None = None) -> Dict[str, Any]:
    """
    Apply consistent brand styling to all subsequent charts using the given theme dict.
    brand_color overrides theme's primary_color when provided.
    Returns a colour palette dict for the caller to use.
    """
    primary = brand_color or theme["primary_color"]

    plt.rcParams.update({
        "font.family":        _CHART_FONT,
        "font.size":          9,
        # Spines — hide top/right, keep thin bottom/left only
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.spines.left":   True,
        "axes.spines.bottom": True,
        "axes.edgecolor":     theme["spine_color"],
        "axes.linewidth":     0.5,
        # Grid — horizontal (y-axis) only, very muted. See Tufte data-ink
        # ratio and the Phase 2 research doc.
        "axes.grid":          True,
        "axes.grid.axis":     "y",
        "grid.alpha":         0.3,
        "grid.linestyle":     "-",
        "grid.linewidth":     0.5,
        "grid.color":         theme["grid_color"],
        # Backgrounds
        "figure.facecolor":   theme["fig_bg"],
        "axes.facecolor":     theme["axes_bg"],
        # Title
        "axes.titlesize":     12,
        "axes.titleweight":   "bold",
        "axes.titlecolor":    theme["title_color"],
        "axes.titlepad":      10,
        # Labels and ticks (tick marks removed; labels kept)
        "axes.labelsize":     10,
        "axes.labelcolor":    theme["text_color"],
        "xtick.labelsize":    9,
        "ytick.labelsize":    9,
        "xtick.color":        theme["text_color"],
        "ytick.color":        theme["text_color"],
        "xtick.major.size":   0,
        "ytick.major.size":   0,
        "xtick.minor.size":   0,
        "ytick.minor.size":   0,
        # Legend
        "legend.fontsize":    9,
        "legend.framealpha":  0.85,
        "legend.edgecolor":   theme["spine_color"],
        "legend.facecolor":   theme["fig_bg"],
        "legend.labelcolor":  theme["text_color"],
        # Text
        "text.color":         theme["text_color"],
    })
    return {
        "primary":    primary,
        "secondary":  theme["secondary_color"],
        "accent":     theme["accent_color"],
        "danger":     theme["danger_color"],
        "gray":       theme["gray_color"],
        "fig_bg":     theme["fig_bg"],
        "okabe_ito":  OKABE_ITO,
    }


def _save_fig(fig: Any, output_path: str, fig_bg: str = "#FAFAFA") -> str:
    """Save figure at 300 DPI with tight layout and close it."""
    fig.savefig(output_path, dpi=_DPI, bbox_inches="tight", facecolor=fig_bg)
    plt.close(fig)
    logger.info("Chart saved: %s", output_path)
    return output_path


def _apply_caption(fig: Any, caption: str | None) -> None:
    """
    Render an optional italic one-line caption below the plot area.
    The caption carries the chart's "takeaway" — e.g. an AI-generated insight
    from the narrative engine's ``chart_insights`` dict. See the Phase 2
    research doc for the rationale (every chart should have a takeaway).
    """
    if not caption:
        return
    # Reserve room at the bottom for the caption text.
    fig.subplots_adjust(bottom=0.18)
    fig.text(
        0.5, 0.02, caption,
        ha="center", va="bottom",
        fontsize=8, fontstyle="italic", color="#64748B",
    )


# Max character length for AI-generated chart action titles. Longer strings
# would overflow the plot area — especially after the font-size bump. Any
# overrun is truncated at the last space before the cap and terminated with
# an ellipsis so the break reads naturally.
_CHART_TITLE_MAX_CHARS = 80
# Font size used for action titles (AI ``chart_insights``). Smaller than the
# default 12pt because insight titles are longer sentences, not labels.
_ACTION_TITLE_FONTSIZE = 10


def plot_sparkline(
    values: List[float],
    output_path: str,
    color: str = "#4338CA",
) -> str | None:
    """
    Render a minimal sparkline PNG for use inside a KPI card.

    Tufte definition: "small, high-resolution graphics embedded in a context
    of words, numbers, images." No axes, no gridlines, no title — just the
    line itself with a dot at the most recent point. Designed for ~2" × 0.3"
    embedding under a KPI big number.

    Returns the output_path on success, None if insufficient data.
    """
    # Need at least 3 points to form a meaningful sparkline. 1-2 points
    # would render as a dot or tiny stub and add visual noise.
    if not values or len(values) < 3:
        return None
    # Filter out obviously invalid points.
    clean = [float(v) for v in values if v is not None]
    if len(clean) < 3:
        return None

    fig, ax = plt.subplots(figsize=(2.0, 0.35))
    fig.patch.set_alpha(0.0)         # transparent background — PNG alpha
    ax.set_facecolor("none")
    ax.plot(range(len(clean)), clean,
            color=color, linewidth=1.2, solid_capstyle="round")
    # Dot on the most recent value so the reader sees "current position".
    ax.plot(len(clean) - 1, clean[-1],
            marker="o", markersize=3.0, color=color, zorder=3)
    # Strip every chart decoration — a sparkline has no axes.
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    # Tight margins so the line uses the entire 2" × 0.35" area.
    ax.margins(x=0.02, y=0.25)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    try:
        fig.savefig(output_path, dpi=_DPI, transparent=True,
                    bbox_inches="tight", pad_inches=0.02)
    finally:
        plt.close(fig)
    return output_path


def _truncate_chart_title(title: str | None) -> str | None:
    """
    Clamp an AI-generated chart title to ``_CHART_TITLE_MAX_CHARS``.

    When the input is shorter than the cap it is returned unchanged.
    When longer, it is truncated at the last space before the cap and
    an ellipsis ``…`` is appended. If no space exists inside the cap,
    a hard cut at the cap length is used instead.
    """
    if not title or len(title) <= _CHART_TITLE_MAX_CHARS:
        return title
    cut = title[:_CHART_TITLE_MAX_CHARS].rfind(" ")
    if cut <= 0:
        cut = _CHART_TITLE_MAX_CHARS
    return title[:cut].rstrip() + "\u2026"


# ─────────────────────────────────────────────────────────────────────────────
# Individual chart generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_sessions_chart(
    daily_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str:
    """Smooth area line chart of daily sessions over the report period."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    dates    = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    sessions = [d["sessions"] for d in daily_data]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    ax.plot(dates, sessions,
            color=colors["primary"], linewidth=2.0,
            marker="o", markersize=3.5, zorder=3)
    ax.fill_between(dates, sessions, alpha=0.12, color=colors["primary"])

    _ti = _truncate_chart_title(title_override)
    if _ti:
        ax.set_title(_ti, loc="left", fontsize=_ACTION_TITLE_FONTSIZE)
    else:
        ax.set_title("Sessions Over Time", loc="left")
    ax.set_ylabel("Sessions")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Readable date labels: "Mar 01" format, auto-spaced
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")

    fig.tight_layout()
    _apply_caption(fig, caption)
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_traffic_sources_chart(
    sources: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str | None:
    """Horizontal bar chart of traffic sources by session count."""
    # A single traffic source doesn't make a useful comparison chart
    if isinstance(sources, (list, tuple)) and len(sources) < 2:
        return None
    if isinstance(sources, dict) and len(sources) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    # Normalise: real GA4 returns dict[str, int]; mock returns list[dict]
    if isinstance(sources, dict):
        sources = [
            {"source": k, "sessions": v}
            for k, v in sorted(sources.items(), key=lambda x: x[1], reverse=True)
        ]

    # Clean up raw GA4 sentinels like "(none)" → "Direct".
    # Merge values when multiple raw labels collapse to the same clean label.
    _merged: Dict[str, int] = {}
    for s in sources:
        clean = _clean_source_label(s["source"])
        _merged[clean] = _merged.get(clean, 0) + int(s.get("sessions", 0) or 0)
    # Re-sort by value descending so the biggest source is at the top.
    _ordered = sorted(_merged.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in _ordered]
    values = [v for _, v in _ordered]
    # Okabe-Ito color-blind-safe multi-series palette — cycle if more
    # labels than colors.
    palette = (OKABE_ITO * ((len(labels) // len(OKABE_ITO)) + 1))[:len(labels)]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    bars = ax.barh(labels, values,
                   color=palette[:len(labels)],
                   height=0.55, edgecolor="none")

    # ── Direct-label vs y-axis-label strategy ──────────────────────────────
    # Knaflic / McKinsey convention: when there are 4 or fewer categories,
    # put the name + value directly next to each bar and suppress the y-axis
    # tick labels. This removes the "legend lookup" cognitive hop. For 5+
    # categories, fall back to y-axis tick labels + inline value only.
    _direct_label = len(labels) <= 4
    max_val = max(values) if values else 1

    if _direct_label:
        # Hide y-axis tick labels entirely — the bar is self-explaining.
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels([""] * len(labels))
        for bar, lbl, val in zip(bars, labels, values):
            ax.text(
                bar.get_width() + max_val * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{lbl}  —  {val:,}",
                va="center", fontsize=9,
                color=theme["text_color"], fontweight="bold",
            )
    else:
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + max_val * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}",
                va="center", fontsize=9, color=theme["text_color"],
            )

    _ti = _truncate_chart_title(title_override)
    if _ti:
        ax.set_title(_ti, loc="left", fontsize=_ACTION_TITLE_FONTSIZE)
    else:
        ax.set_title("Traffic Sources", loc="left")
    ax.set_xlabel("Sessions")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()

    # Give the inline labels headroom so they don't clip the plot right edge.
    if _direct_label:
        ax.set_xlim(0, max_val * 1.35)

    fig.tight_layout()
    _apply_caption(fig, caption)
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_spend_vs_conversions_chart(
    daily_data: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str:
    """Dual-axis chart: daily ad spend (bars) vs conversions (line)."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    dates       = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    spend       = [d["spend"] for d in daily_data]
    conversions = [d["conversions"] for d in daily_data]

    fig, ax1 = plt.subplots(figsize=_FIGSIZE)
    ax1.set_facecolor(theme["axes_bg"])

    ax1.bar(dates, spend,
            color=colors["primary"], alpha=0.75, width=0.75,
            label=f"Spend ({currency_symbol})", zorder=2)
    ax1.set_ylabel(f"Spend ({currency_symbol})", color=colors["primary"])
    ax1.tick_params(axis="y", labelcolor=colors["primary"])
    ax1.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{currency_symbol}{int(x):,}")
    )

    ax2 = ax1.twinx()
    ax2.set_facecolor(theme["axes_bg"])
    ax2.plot(dates, conversions,
             color=colors["secondary"], linewidth=2.0,
             marker="o", markersize=3.5, label="Conversions", zorder=3)
    ax2.set_ylabel("Conversions", color=colors["secondary"])
    ax2.tick_params(axis="y", labelcolor=colors["secondary"])
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(theme["spine_color"])

    # When every day has zero conversions, matplotlib auto-scales the axis
    # to tiny fractional labels like "-0.04" / "0.00" / "0.04". Force a
    # sensible 0..1 range and show only the "0" tick so the empty series
    # reads cleanly as "no conversions this period".
    _max_conv = max(conversions) if conversions else 0
    if _max_conv == 0:
        ax2.set_ylim(0, 1)
        ax2.set_yticks([0])

    _ti = _truncate_chart_title(title_override)
    if _ti:
        ax1.set_title(_ti, loc="left", fontsize=_ACTION_TITLE_FONTSIZE)
    else:
        ax1.set_title("Daily Spend vs Conversions", loc="left")

    # Merge legends from both axes
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")

    fig.tight_layout()
    _apply_caption(fig, caption)
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_campaign_performance_chart(
    campaigns: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str | None:
    """Grouped bar chart — top 5 campaigns by spend and conversions."""
    if not campaigns or len(campaigns) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    top = campaigns[:5]
    # Truncate campaign names to 25 chars (add ellipsis) so the rotated
    # x-axis labels stay inside the plot area and don't overlap.
    _raw_names = [
        c["name"].split(" - ")[-1] if " - " in c["name"] else c["name"]
        for c in top
    ]
    names = [
        (n[:25] + "\u2026") if len(n) > 25 else n
        for n in _raw_names
    ]
    spend       = [c["spend"] for c in top]
    conversions = [c["conversions"] for c in top]

    fig, ax1 = plt.subplots(figsize=_FIGSIZE)
    ax1.set_facecolor(theme["axes_bg"])
    x     = range(len(names))
    width = 0.35

    # ── Highlight-one strategy ──────────────────────────────────────────────
    # Identify the top campaign by conversions (fallback to spend) and keep it
    # in the brand/secondary color; mute every other bar to draw the eye to
    # the winner (Cole Knaflic "focus color" principle).
    if any(v > 0 for v in conversions):
        top_idx = max(range(len(conversions)), key=lambda i: conversions[i])
    else:
        top_idx = max(range(len(spend)), key=lambda i: spend[i])

    spend_bar_colors = [
        colors["primary"] if i == top_idx else _MUTED_BAR for i in range(len(spend))
    ]
    conv_bar_colors = [
        colors["secondary"] if i == top_idx else _MUTED_BAR for i in range(len(conversions))
    ]

    ax1.bar([i - width / 2 for i in x], spend, width,
            label=f"Spend ({currency_symbol})",
            color=spend_bar_colors, edgecolor="none", alpha=0.9)
    ax1.set_ylabel(f"Spend ({currency_symbol})", color=colors["primary"])
    ax1.tick_params(axis="y", labelcolor=colors["primary"])
    ax1.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{currency_symbol}{int(x):,}")
    )

    ax2 = ax1.twinx()
    ax2.set_facecolor(theme["axes_bg"])
    ax2.bar([i + width / 2 for i in x], conversions, width,
            label="Conversions",
            color=conv_bar_colors, edgecolor="none", alpha=0.9)
    ax2.set_ylabel("Conversions", color=colors["secondary"])
    ax2.tick_params(axis="y", labelcolor=colors["secondary"])
    ax2.spines["right"].set_visible(True)

    # When every campaign has zero conversions, matplotlib auto-scales the
    # secondary axis to tiny fractional labels like "-0.04". Force a clean
    # 0..1 range and show only the "0" tick so "no conversions yet" reads
    # honestly.
    _max_conv = max(conversions) if conversions else 0
    if _max_conv == 0:
        ax2.set_ylim(0, 1)
        ax2.set_yticks([0])
    ax2.spines["right"].set_color(theme["spine_color"])

    ax1.set_xticks(list(x))
    # Steeper rotation (35°) and smaller font (7pt) so long campaign names
    # fit without overlapping — pairs with the 25-char truncation above.
    ax1.set_xticklabels(names, rotation=35, ha="right", fontsize=7)
    _ti = _truncate_chart_title(title_override)
    if _ti:
        ax1.set_title(_ti, loc="left", fontsize=_ACTION_TITLE_FONTSIZE)
    else:
        ax1.set_title("Campaign Performance (Top 5)", loc="left")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")

    fig.tight_layout()
    _apply_caption(fig, caption)
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


# ─────────────────────────────────────────────────────────────────────────────
# NEW CHART TYPES — Phase 2 expansion
# ─────────────────────────────────────────────────────────────────────────────

def generate_device_breakdown_chart(
    device_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str | None:
    """Donut chart of sessions by device type (Desktop/Mobile/Tablet)."""
    if not device_data or len(device_data) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    labels = [d["device"] for d in device_data]
    values = [d["sessions"] for d in device_data]
    # Okabe-Ito palette for color-blind safety on the 3-slice donut.
    chart_colors = OKABE_ITO[:len(labels)]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    fig.set_facecolor(theme["fig_bg"])
    wedges, texts, autotexts = ax.pie(
        values, labels=None, colors=chart_colors,
        autopct="%1.1f%%", startangle=90, pctdistance=0.78,
        wedgeprops={"width": 0.45, "edgecolor": theme["fig_bg"], "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(10)
        t.set_fontweight("bold")
        t.set_color(theme["text_color"])

    # Add legend instead of labels on wedges
    total = sum(values)
    legend_labels = [f"{l}  ({v:,} — {v/total*100:.1f}%)" for l, v in zip(labels, values)]
    ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(0.85, 0.5),
              fontsize=9, frameon=False)
    _ti = _truncate_chart_title(title_override)
    if _ti:
        ax.set_title(_ti, fontsize=_ACTION_TITLE_FONTSIZE, fontweight="bold",
                     color=theme["title_color"], loc="left")
    else:
        ax.set_title("Sessions by Device", fontsize=12, fontweight="bold",
                     color=theme["title_color"], loc="left")

    fig.tight_layout()
    _apply_caption(fig, caption)
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_top_pages_chart(
    pages_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str | None:
    """Horizontal bar chart of top landing pages by sessions."""
    if not pages_data or len(pages_data) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    top = pages_data[:7]
    # Truncate URLs to path only, max 30 chars
    labels = [(p["page"][:30] + "..." if len(p["page"]) > 30 else p["page"]) for p in top]
    values = [p["sessions"] for p in top]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    bars = ax.barh(labels, values, color=colors["primary"], height=0.55, alpha=0.85, edgecolor="none")

    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max_val * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=9, color=theme["text_color"])

    _ti = _truncate_chart_title(title_override)
    if _ti:
        ax.set_title(_ti, loc="left", fontsize=_ACTION_TITLE_FONTSIZE)
    else:
        ax.set_title("Top Landing Pages", loc="left")
    ax.set_xlabel("Sessions")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()
    fig.tight_layout()
    _apply_caption(fig, caption)
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_new_vs_returning_chart(
    nvr_data: Dict,
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str:
    """Grouped bar chart comparing new vs returning users: sessions + conversions."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    categories = ["Sessions", "Conversions"]
    new_vals = [nvr_data["new"]["sessions"], nvr_data["new"]["conversions"]]
    ret_vals = [nvr_data["returning"]["sessions"], nvr_data["returning"]["conversions"]]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    x = range(len(categories))
    width = 0.3

    bars1 = ax.bar([i - width / 2 for i in x], new_vals, width,
                   label="New Users", color=colors["primary"], edgecolor="none", alpha=0.85)
    bars2 = ax.bar([i + width / 2 for i in x], ret_vals, width,
                   label="Returning Users", color=colors["secondary"], edgecolor="none", alpha=0.85)

    # Add value labels on bars
    for bar in list(bars1) + list(bars2):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(new_vals) * 0.02,
                f"{int(bar.get_height()):,}", ha="center", va="bottom", fontsize=9,
                color=theme["text_color"])

    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_title("New vs Returning Users")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.legend(loc="upper right")
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_top_countries_chart(
    countries_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str | None:
    """Horizontal bar chart of top countries by sessions."""
    if not countries_data or len(countries_data) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    top = countries_data[:7]
    labels = [c["country"] for c in top]
    values = [c["sessions"] for c in top]
    # Okabe-Ito palette, cycled to cover up to 7 bars.
    bar_colors = (OKABE_ITO * 2)[:len(labels)]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    bars = ax.barh(labels, values, color=bar_colors, height=0.55, edgecolor="none")

    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max_val * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=9, color=theme["text_color"])

    ax.set_title("Top Countries by Sessions")
    ax.set_xlabel("Sessions")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_audience_demographics_chart(
    age_gender_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str | None:
    """Grouped bar chart: age groups x gender, by conversions."""
    if not age_gender_data or len(age_gender_data) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    # Group by age
    ages: Dict[str, Dict[str, int]] = {}
    for item in age_gender_data:
        age = item["age"]
        if age not in ages:
            ages[age] = {"male": 0, "female": 0}
        ages[age][item["gender"]] = item.get("conversions", 0)

    age_labels = list(ages.keys())
    male_vals = [ages[a]["male"] for a in age_labels]
    female_vals = [ages[a]["female"] for a in age_labels]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    x = range(len(age_labels))
    width = 0.35

    # Okabe-Ito blue + vermillion for the two gender series (color-blind safe).
    ax.bar([i - width / 2 for i in x], male_vals, width,
           label="Male", color=OKABE_ITO[0], edgecolor="none", alpha=0.85)
    ax.bar([i + width / 2 for i in x], female_vals, width,
           label="Female", color=OKABE_ITO[1], edgecolor="none", alpha=0.85)

    ax.set_xticks(list(x))
    ax.set_xticklabels(age_labels, fontsize=9)
    _ti = _truncate_chart_title(title_override)
    if _ti:
        ax.set_title(_ti, loc="left", fontsize=_ACTION_TITLE_FONTSIZE)
    else:
        ax.set_title("Conversions by Age & Gender", loc="left")
    ax.set_ylabel("Conversions")
    ax.legend(loc="upper right")
    fig.tight_layout()
    _apply_caption(fig, caption)
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_placements_chart(
    placements_data: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str | None:
    """Horizontal bar chart of ad placements by spend."""
    if not placements_data or len(placements_data) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    labels = [p["placement"] for p in placements_data]
    values = [p["spend"] for p in placements_data]
    # Okabe-Ito palette for color-blind-safe multi-series placements.
    bar_colors = (OKABE_ITO * 2)[:len(labels)]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    bars = ax.barh(labels, values, color=bar_colors, height=0.55, edgecolor="none")

    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max_val * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{currency_symbol}{val:,.0f}", va="center", fontsize=9, color=theme["text_color"])

    ax.set_title("Spend by Placement")
    ax.set_xlabel(f"Spend ({currency_symbol})")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{currency_symbol}{int(x):,}"))
    ax.invert_yaxis()
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_bounce_rate_trend_chart(
    daily_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str:
    """Line chart of daily bounce rate with average reference line."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    bounce_rates = [d.get("bounce_rate", 0) for d in daily_data]
    avg_bounce = sum(bounce_rates) / max(len(bounce_rates), 1)

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    ax.plot(dates, bounce_rates, color=colors["accent"], linewidth=2.0,
            marker="o", markersize=3.5, zorder=3)
    ax.axhline(y=avg_bounce, color=colors["gray"], linestyle="--", linewidth=1.0, alpha=0.7,
               label=f"Average: {avg_bounce:.1f}%")
    ax.fill_between(dates, bounce_rates, alpha=0.08, color=colors["accent"])

    ax.set_title("Bounce Rate Trend")
    ax.set_ylabel("Bounce Rate (%)")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")
    ax.legend(loc="upper right")
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_conversion_funnel_chart(
    funnel_data: Dict[str, int],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str:
    """Horizontal decreasing bars (funnel): Sessions → Users → Conversions."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    stages = list(funnel_data.keys())
    values = list(funnel_data.values())
    # Okabe-Ito progression: blue → vermillion → bluish green for the
    # 3-stage funnel. Color-blind safe and reads as a natural progression.
    bar_colors = OKABE_ITO[:len(stages)]

    fig, ax = plt.subplots(figsize=(10.0, 3.5))
    ax.set_facecolor(theme["axes_bg"])
    fig.set_facecolor(theme["fig_bg"])
    bars = ax.barh(stages, values, color=bar_colors, height=0.6, edgecolor="none")

    max_val = max(values) if values else 1
    for i, (bar, val) in enumerate(zip(bars, values)):
        pct = f"  ({val/values[0]*100:.1f}%)" if i > 0 and values[0] > 0 else ""
        ax.text(bar.get_width() + max_val * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:,}{pct}", va="center", fontsize=10, fontweight="bold",
                color=theme["text_color"])
        # Add drop-off annotation between stages
        if i > 0 and values[i - 1] > 0:
            drop = round((1 - val / values[i - 1]) * 100, 1)
            mid_y = bar.get_y() + bar.get_height() + 0.15
            ax.annotate(f"↓ {drop}% drop-off", xy=(val / 2, mid_y),
                        fontsize=8, color=colors["danger"], ha="center")

    ax.set_title("Conversion Funnel", fontsize=12, fontweight="bold")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


# ─────────────────────────────────────────────────────────────────────────────
# Google Ads chart types
# ─────────────────────────────────────────────────────────────────────────────

def generate_gads_spend_conversions_chart(
    daily_data: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = "#4338CA",
    theme_name: str = "light",
    title_override: str | None = None,
    caption: str | None = None,
) -> str:
    """Dual-axis chart: daily Google Ads spend (bars) vs conversions (line)."""
    # Reuse the same pattern as Meta spend chart
    return generate_spend_vs_conversions_chart(
        daily_data, output_path, currency_symbol, brand_color, theme_name,
        title_override=title_override, caption=caption,
    )


def generate_search_terms_chart(
    search_terms: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str | None:
    """Horizontal bar chart of top search terms by clicks with impressions overlay."""
    if not search_terms or len(search_terms) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    top = search_terms[:10]
    labels = [(t["term"][:35] + "..." if len(t["term"]) > 35 else t["term"]) for t in top]
    clicks = [t["clicks"] for t in top]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    bars = ax.barh(labels, clicks, color=colors["primary"], height=0.55, alpha=0.85, edgecolor="none")

    max_val = max(clicks) if clicks else 1
    for bar, val in zip(bars, clicks):
        ax.text(bar.get_width() + max_val * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", fontsize=9, color=theme["text_color"])

    ax.set_title("Top Search Terms by Clicks")
    ax.set_xlabel("Clicks")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


# ─────────────────────────────────────────────────────────────────────────────
# Search Console (SEO) chart types
# ─────────────────────────────────────────────────────────────────────────────

def generate_seo_clicks_trend_chart(
    daily_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str:
    """Dual-axis line: organic clicks (primary) + impressions (secondary) over time."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    clicks = [d["clicks"] for d in daily_data]
    impressions = [d["impressions"] for d in daily_data]

    fig, ax1 = plt.subplots(figsize=_FIGSIZE)
    ax1.set_facecolor(theme["axes_bg"])
    ax1.plot(dates, clicks, color=colors["primary"], linewidth=2.0,
             marker="o", markersize=3.5, label="Clicks", zorder=3)
    ax1.fill_between(dates, clicks, alpha=0.10, color=colors["primary"])
    ax1.set_ylabel("Clicks", color=colors["primary"])
    ax1.tick_params(axis="y", labelcolor=colors["primary"])
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    ax2 = ax1.twinx()
    ax2.set_facecolor(theme["axes_bg"])
    ax2.plot(dates, impressions, color=colors["secondary"], linewidth=1.5,
             linestyle="--", alpha=0.7, label="Impressions", zorder=2)
    ax2.set_ylabel("Impressions", color=colors["secondary"])
    ax2.tick_params(axis="y", labelcolor=colors["secondary"])
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(theme["spine_color"])

    ax1.set_title("Organic Search: Clicks & Impressions")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_top_queries_chart(
    queries_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str | None:
    """Horizontal bar chart of top search queries by clicks with CTR annotation."""
    if not queries_data or len(queries_data) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    top = queries_data[:10]
    labels = [(q["query"][:30] + "..." if len(q["query"]) > 30 else q["query"]) for q in top]
    clicks = [q["clicks"] for q in top]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    bars = ax.barh(labels, clicks, color=colors["primary"], height=0.55, alpha=0.85, edgecolor="none")

    max_val = max(clicks) if clicks else 1
    for bar, val, q in zip(bars, clicks, top):
        ctr = q.get("ctr", 0)
        ax.text(bar.get_width() + max_val * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{val:,}  (CTR: {ctr:.1f}%)", va="center", fontsize=8, color=theme["text_color"])

    ax.set_title("Top Organic Queries by Clicks")
    ax.set_xlabel("Clicks")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


# ─────────────────────────────────────────────────────────────────────────────
# CSV data chart
# ─────────────────────────────────────────────────────────────────────────────

def generate_csv_comparison_chart(
    csv_source: Dict,
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str | None:
    """Horizontal bar chart: current vs previous values. Green for improved, red for declined."""
    metrics_raw = csv_source.get("metrics", [])
    if not metrics_raw or len(metrics_raw) < 2:
        return None
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    metrics = metrics_raw[:6]
    labels = [m["name"] for m in metrics]
    current = [m["current_value"] for m in metrics]
    previous = [m.get("previous_value", 0) for m in metrics]

    # Use a wider, taller figsize than default so the horizontal bars
    # are readable when placed on the slide (avoids the squeezed 5:1 look).
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_facecolor(theme["axes_bg"])
    x = range(len(labels))
    width = 0.35

    ax.barh([i - width / 2 for i in x], previous, width,
            label="Previous", color=colors["gray"], alpha=0.5, edgecolor="none")
    # WCAG AA: emerald-700 (#047857, 5.1:1) rather than emerald-600 (#059669, 3.8:1)
    bar_colors = []
    for c, p in zip(current, previous):
        # For metrics where lower is better (cost, bounces), invert
        name_lower = labels[current.index(c)].lower() if c in current else ""
        if "cost" in name_lower or "bounce" in name_lower or "unsubscribe" in name_lower:
            bar_colors.append("#047857" if c <= p else "#E11D48")
        else:
            bar_colors.append("#047857" if c >= p else "#E11D48")

    for i, (c_val, color) in enumerate(zip(current, bar_colors)):
        ax.barh(i + width / 2, c_val, width, color=color, alpha=0.85, edgecolor="none")

    ax.set_yticks(list(x))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title(f"{csv_source.get('source_name', csv_source.get('name', 'Custom'))} — Current vs Previous")
    ax.legend(["Previous", "Current"], loc="lower right")
    ax.invert_yaxis()
    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def _build_sparkline_series(data: Dict[str, Any]) -> Dict[str, List[float]]:
    """
    Derive per-metric daily time series for sparkline rendering.

    Returns a dict keyed by the KPI label (matching the labels in
    ``slide_selector.select_kpis``) so the orchestrator can look up the
    correct series for each card.
    """
    series: Dict[str, List[float]] = {}

    ga4_daily = (data.get("ga4") or {}).get("daily") or []
    if ga4_daily:
        _sessions = [float(d.get("sessions") or 0) for d in ga4_daily]
        _users    = [float(d.get("users") or 0) for d in ga4_daily]
        if any(_sessions):
            series["SESSIONS"] = _sessions
        if any(_users):
            series["USERS"] = _users
        # Daily conversions — present on some GA4 pulls
        _convs = [float(d.get("conversions") or 0) for d in ga4_daily]
        if any(_convs):
            series["CONVERSIONS"] = _convs
        # Bounce rate / pageviews as secondary candidates
        _pv = [float(d.get("pageviews") or 0) for d in ga4_daily]
        if any(_pv):
            series["PAGEVIEWS"] = _pv

    meta_daily = (data.get("meta_ads") or {}).get("daily") or []
    if meta_daily:
        _spend = [float(d.get("spend") or 0) for d in meta_daily]
        _mconv = [float(d.get("conversions") or 0) for d in meta_daily]
        _clicks = [float(d.get("clicks") or 0) for d in meta_daily]
        if any(_spend):
            series["AD SPEND"] = _spend
        if any(_mconv):
            series["AD CONVERSIONS"] = _mconv
        if any(_clicks):
            series["AD CLICKS"] = _clicks

    gads_daily = (data.get("google_ads") or {}).get("daily") or []
    if gads_daily:
        _gspend = [float(d.get("spend") or 0) for d in gads_daily]
        _gconv  = [float(d.get("conversions") or 0) for d in gads_daily]
        _gclicks = [float(d.get("clicks") or 0) for d in gads_daily]
        if any(_gspend):
            series["SEARCH SPEND"] = _gspend
        if any(_gconv):
            series["SEARCH CONV."] = _gconv
        if any(_gclicks):
            series["SEARCH CLICKS"] = _gclicks

    gsc_daily = (data.get("search_console") or {}).get("daily") or []
    if gsc_daily:
        _oclicks = [float(d.get("clicks") or 0) for d in gsc_daily]
        _oimpr   = [float(d.get("impressions") or 0) for d in gsc_daily]
        if any(_oclicks):
            series["ORGANIC CLICKS"] = _oclicks
        if any(_oimpr):
            series["SEARCH IMPRESSIONS"] = _oimpr

    return series


def generate_all_charts(
    data: Dict[str, Any],
    output_dir: str,
    brand_color: str = "#4338CA",
    visual_template: str = "modern_clean",
    chart_insights: Dict[str, str] | None = None,
) -> Dict[str, str]:
    """
    Generate ONLY charts that have sufficient data — never generate empty charts.
    Returns {chart_name: file_path}.
    Synchronous — call via asyncio.to_thread() in async contexts.

    ``chart_insights`` (optional) is the per-chart "action title" dict from the
    AI narrative engine — e.g. ``{"sessions_trend": "Sessions grew 23% in
    March, driven by the new landing pages"}``. When a key matches a chart,
    the insight replaces the generic chart title so the reader sees a
    takeaway headline rather than a descriptive label. See Phase 2 Gap
    analysis items 1, 2, 9 in ``docs/REPORT-QUALITY-RESEARCH-2026.md``.
    """
    os.makedirs(output_dir, exist_ok=True)

    theme_name = _VISUAL_TO_THEME.get(visual_template, "light")
    charts: Dict[str, str] = {}
    insights = chart_insights or {}
    ga4 = data.get("ga4", {})
    meta = data.get("meta_ads", {})
    gads = data.get("google_ads", {})
    gsc = data.get("search_console", {})
    cur_sym = _get_currency_symbol(data)

    def _try(name: str, fn, *args, **kwargs):
        try:
            charts[name] = fn(*args, **kwargs)
        except Exception as exc:
            logger.error("Chart '%s' failed: %s", name, exc)

    # ── GA4 charts ──────────────────────────────────────────────────────────
    if ga4.get("daily") and len(ga4["daily"]) >= 3:
        _try("sessions", generate_sessions_chart,
             ga4["daily"], os.path.join(output_dir, "sessions.png"),
             brand_color=brand_color, theme_name=theme_name,
             title_override=insights.get("sessions_trend"))

    if ga4.get("traffic_sources") and len(ga4["traffic_sources"]) >= 2:
        _try("traffic_sources", generate_traffic_sources_chart,
             ga4["traffic_sources"], os.path.join(output_dir, "traffic_sources.png"),
             brand_color=brand_color, theme_name=theme_name,
             title_override=insights.get("traffic_sources"))

    if ga4.get("device_breakdown") and len(ga4["device_breakdown"]) >= 2:
        _try("device_breakdown", generate_device_breakdown_chart,
             ga4["device_breakdown"], os.path.join(output_dir, "device_breakdown.png"),
             brand_color=brand_color, theme_name=theme_name,
             title_override=insights.get("device_breakdown"))

    if ga4.get("top_pages") and len(ga4["top_pages"]) >= 2:
        _try("top_pages", generate_top_pages_chart,
             ga4["top_pages"], os.path.join(output_dir, "top_pages.png"),
             brand_color=brand_color, theme_name=theme_name,
             title_override=insights.get("top_pages"))

    if ga4.get("new_vs_returning"):
        nvr = ga4["new_vs_returning"]
        if nvr.get("new", {}).get("sessions", 0) > 0:
            _try("new_vs_returning", generate_new_vs_returning_chart,
                 nvr, os.path.join(output_dir, "new_vs_returning.png"),
                 brand_color=brand_color, theme_name=theme_name)

    if ga4.get("top_countries") and len(ga4["top_countries"]) >= 2:
        _try("top_countries", generate_top_countries_chart,
             ga4["top_countries"], os.path.join(output_dir, "top_countries.png"),
             brand_color=brand_color, theme_name=theme_name)

    # Bounce rate: only if daily data has bounce_rate field
    if ga4.get("daily") and any(d.get("bounce_rate") for d in ga4["daily"]):
        _try("bounce_rate_trend", generate_bounce_rate_trend_chart,
             ga4["daily"], os.path.join(output_dir, "bounce_rate_trend.png"),
             brand_color=brand_color, theme_name=theme_name)

    # Conversion funnel
    ga4_summary = ga4.get("summary", {})
    if ga4_summary.get("sessions", 0) > 0 and ga4_summary.get("conversions", 0) > 0:
        funnel = {
            "Sessions": ga4_summary["sessions"],
            "Users": ga4_summary.get("users", 0),
            "Conversions": ga4_summary["conversions"],
        }
        _try("conversion_funnel", generate_conversion_funnel_chart,
             funnel, os.path.join(output_dir, "conversion_funnel.png"),
             brand_color=brand_color, theme_name=theme_name)

    # ── Meta Ads charts — only if there's actual spend ──────────────────────
    meta_spend = meta.get("summary", {}).get("spend", 0)
    if meta_spend and meta_spend > 0:
        if meta.get("daily") and len(meta["daily"]) >= 3:
            _try("spend_conversions", generate_spend_vs_conversions_chart,
                 meta["daily"], os.path.join(output_dir, "spend_conversions.png"),
                 currency_symbol=cur_sym, brand_color=brand_color, theme_name=theme_name,
                 title_override=insights.get("spend_conversions"))

        if meta.get("campaigns") and len(meta["campaigns"]) >= 1:
            _try("campaigns", generate_campaign_performance_chart,
                 meta["campaigns"], os.path.join(output_dir, "campaigns.png"),
                 currency_symbol=cur_sym, brand_color=brand_color, theme_name=theme_name,
                 title_override=insights.get("campaign_performance"))

        if meta.get("age_gender") and len(meta["age_gender"]) >= 2:
            _try("audience_demographics", generate_audience_demographics_chart,
                 meta["age_gender"], os.path.join(output_dir, "audience_demographics.png"),
                 brand_color=brand_color, theme_name=theme_name,
                 title_override=insights.get("audience_demographics"))

        if meta.get("placements") and len(meta["placements"]) >= 2:
            _try("placements", generate_placements_chart,
                 meta["placements"], os.path.join(output_dir, "placements.png"),
                 currency_symbol=cur_sym, brand_color=brand_color, theme_name=theme_name)

    # ── Google Ads charts — only if connected AND has spend ─────────────────
    gads_spend = gads.get("summary", {}).get("spend", 0)
    if gads_spend and gads_spend > 0:
        if gads.get("daily") and len(gads["daily"]) >= 3:
            _try("gads_spend_conversions", generate_gads_spend_conversions_chart,
                 gads["daily"], os.path.join(output_dir, "gads_spend_conversions.png"),
                 currency_symbol=cur_sym, brand_color=brand_color, theme_name=theme_name)

        if gads.get("campaigns") and len(gads["campaigns"]) >= 1:
            _try("gads_campaigns", generate_campaign_performance_chart,
                 gads["campaigns"], os.path.join(output_dir, "gads_campaigns.png"),
                 currency_symbol=cur_sym, brand_color=brand_color, theme_name=theme_name,
                 title_override=insights.get("campaign_performance"))

        if gads.get("search_terms") and len(gads["search_terms"]) >= 3:
            _try("search_terms_bar", generate_search_terms_chart,
                 gads["search_terms"], os.path.join(output_dir, "search_terms.png"),
                 brand_color=brand_color, theme_name=theme_name)

    # ── Search Console charts — only if connected AND has clicks ────────────
    if gsc.get("summary", {}).get("clicks", 0) > 0:
        if gsc.get("daily") and len(gsc["daily"]) >= 3:
            _try("seo_clicks_trend", generate_seo_clicks_trend_chart,
                 gsc["daily"], os.path.join(output_dir, "seo_clicks_trend.png"),
                 brand_color=brand_color, theme_name=theme_name)

        if gsc.get("top_queries") and len(gsc["top_queries"]) >= 3:
            _try("top_queries", generate_top_queries_chart,
                 gsc["top_queries"], os.path.join(output_dir, "top_queries.png"),
                 brand_color=brand_color, theme_name=theme_name)

    # ── CSV source charts — one per source ──────────────────────────────────
    for csv_source in data.get("csv_sources", []):
        if csv_source.get("metrics") and len(csv_source["metrics"]) >= 2:
            safe_name = csv_source.get("source_name", csv_source.get("name", "custom")).lower().replace(" ", "_").replace("/", "_")
            _try(f"csv_{safe_name}", generate_csv_comparison_chart,
                 csv_source, os.path.join(output_dir, f"csv_{safe_name}.png"),
                 brand_color=brand_color, theme_name=theme_name)

    # ── Sparklines — one per KPI that has a daily series ───────────────────
    # Emitted with the "sparkline__<LABEL>" key so ``_embed_kpi_sparklines``
    # can look them up by the selected KPI labels (from slide_selector).
    _sparkline_dir = os.path.join(output_dir, "sparklines")
    _series = _build_sparkline_series(data)
    if _series:
        os.makedirs(_sparkline_dir, exist_ok=True)
        _spark_color = brand_color or "#4338CA"
        for label, values in _series.items():
            _safe = label.replace(" ", "_").replace("/", "").replace(".", "").lower()
            _path = os.path.join(_sparkline_dir, f"spark_{_safe}.png")
            try:
                result = plot_sparkline(values, _path, color=_spark_color)
                if result:
                    charts[f"sparkline__{label}"] = result
            except Exception as exc:
                logger.error("Sparkline '%s' failed: %s", label, exc)

    logger.info(
        "Generated %d charts in %s (template=%s, theme=%s)",
        len(charts), output_dir, visual_template, theme_name,
    )
    return charts
