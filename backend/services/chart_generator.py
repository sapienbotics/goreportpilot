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
}

# Chart dimensions — exactly matches the PPTX chart placeholder size
_FIGSIZE = (5.6, 3.0)
_DPI = 300


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
        # Spines
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.spines.left":   True,
        "axes.spines.bottom": True,
        "axes.edgecolor":     theme["spine_color"],
        # Grid
        "axes.grid":          True,
        "grid.alpha":         theme["grid_alpha"],
        "grid.linestyle":     "-",
        "grid.color":         theme["grid_color"],
        # Backgrounds
        "figure.facecolor":   theme["fig_bg"],
        "axes.facecolor":     theme["axes_bg"],
        # Title
        "axes.titlesize":     12,
        "axes.titleweight":   "bold",
        "axes.titlecolor":    theme["title_color"],
        "axes.titlepad":      10,
        # Labels and ticks
        "axes.labelsize":     10,
        "axes.labelcolor":    theme["text_color"],
        "xtick.labelsize":    9,
        "ytick.labelsize":    9,
        "xtick.color":        theme["text_color"],
        "ytick.color":        theme["text_color"],
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
        "primary":   primary,
        "secondary": theme["secondary_color"],
        "accent":    theme["accent_color"],
        "danger":    theme["danger_color"],
        "gray":      theme["gray_color"],
        "fig_bg":    theme["fig_bg"],
    }


def _save_fig(fig: Any, output_path: str, fig_bg: str = "#FAFAFA") -> str:
    """Save figure at 300 DPI with tight layout and close it."""
    fig.savefig(output_path, dpi=_DPI, bbox_inches="tight", facecolor=fig_bg)
    plt.close(fig)
    logger.info("Chart saved: %s", output_path)
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Individual chart generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_sessions_chart(
    daily_data: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
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

    ax.set_title("Sessions Over Time")
    ax.set_ylabel("Sessions")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Readable date labels: "Mar 01" format, auto-spaced
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")

    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_traffic_sources_chart(
    sources: List[Dict],
    output_path: str,
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str:
    """Horizontal bar chart of traffic sources by session count."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    labels = [s["source"] for s in sources]
    values = [s["sessions"] for s in sources]
    palette = [
        colors["primary"], colors["secondary"], colors["accent"],
        colors["gray"], colors["danger"],
    ]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.set_facecolor(theme["axes_bg"])
    bars = ax.barh(labels, values,
                   color=palette[:len(labels)],
                   height=0.55, edgecolor="none")

    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + max_val * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center", fontsize=9, color=theme["text_color"],
        )

    ax.set_title("Traffic Sources")
    ax.set_xlabel("Sessions")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()

    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_spend_vs_conversions_chart(
    daily_data: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = "#4338CA",
    theme_name: str = "light",
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

    ax1.set_title("Daily Spend vs Conversions")

    # Merge legends from both axes
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")

    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


def generate_campaign_performance_chart(
    campaigns: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = "#4338CA",
    theme_name: str = "light",
) -> str:
    """Grouped bar chart — top 5 campaigns by spend and conversions."""
    theme = CHART_THEMES.get(theme_name, CHART_THEMES["light"])
    colors = _setup_chart_style(theme, brand_color)

    top = campaigns[:5]
    names = [
        (c["name"].split(" - ")[-1] if " - " in c["name"] else c["name"])[:26]
        for c in top
    ]
    spend       = [c["spend"] for c in top]
    conversions = [c["conversions"] for c in top]

    fig, ax1 = plt.subplots(figsize=_FIGSIZE)
    ax1.set_facecolor(theme["axes_bg"])
    x     = range(len(names))
    width = 0.35

    ax1.bar([i - width / 2 for i in x], spend, width,
            label=f"Spend ({currency_symbol})",
            color=colors["primary"], edgecolor="none", alpha=0.85)
    ax1.set_ylabel(f"Spend ({currency_symbol})", color=colors["primary"])
    ax1.tick_params(axis="y", labelcolor=colors["primary"])
    ax1.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{currency_symbol}{int(x):,}")
    )

    ax2 = ax1.twinx()
    ax2.set_facecolor(theme["axes_bg"])
    ax2.bar([i + width / 2 for i in x], conversions, width,
            label="Conversions",
            color=colors["secondary"], edgecolor="none", alpha=0.85)
    ax2.set_ylabel("Conversions", color=colors["secondary"])
    ax2.tick_params(axis="y", labelcolor=colors["secondary"])
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(theme["spine_color"])

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax1.set_title("Campaign Performance (Top 5)")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")

    fig.tight_layout()
    return _save_fig(fig, output_path, fig_bg=theme["fig_bg"])


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_charts(
    data: Dict[str, Any],
    output_dir: str,
    brand_color: str = "#4338CA",
    visual_template: str = "modern_clean",
) -> Dict[str, str]:
    """
    Generate all report charts; return {chart_name: file_path}.
    Synchronous — call via asyncio.to_thread() in async contexts.

    brand_color:     Agency brand hex colour (overrides theme primary for GA4 charts).
    visual_template: "modern_clean" | "dark_executive" | "colorful_agency"
                     Maps to a colour theme so charts match slide backgrounds.
    """
    os.makedirs(output_dir, exist_ok=True)

    theme_name = _VISUAL_TO_THEME.get(visual_template, "light")
    charts: Dict[str, str] = {}
    ga4  = data.get("ga4", {})
    meta = data.get("meta_ads", {})
    cur_sym = _get_currency_symbol(data)

    try:
        if ga4.get("daily"):
            charts["sessions"] = generate_sessions_chart(
                ga4["daily"],
                os.path.join(output_dir, "sessions.png"),
                brand_color=brand_color,
                theme_name=theme_name,
            )
    except Exception as exc:
        logger.error("Sessions chart failed: %s", exc)

    try:
        if ga4.get("traffic_sources"):
            charts["traffic_sources"] = generate_traffic_sources_chart(
                ga4["traffic_sources"],
                os.path.join(output_dir, "traffic_sources.png"),
                brand_color=brand_color,
                theme_name=theme_name,
            )
    except Exception as exc:
        logger.error("Traffic sources chart failed: %s", exc)

    try:
        if meta.get("daily"):
            charts["spend_conversions"] = generate_spend_vs_conversions_chart(
                meta["daily"],
                os.path.join(output_dir, "spend_conversions.png"),
                currency_symbol=cur_sym,
                brand_color=brand_color,
                theme_name=theme_name,
            )
    except Exception as exc:
        logger.error("Spend/conversions chart failed: %s", exc)

    try:
        if meta.get("campaigns"):
            charts["campaigns"] = generate_campaign_performance_chart(
                meta["campaigns"],
                os.path.join(output_dir, "campaigns.png"),
                currency_symbol=cur_sym,
                brand_color=brand_color,
                theme_name=theme_name,
            )
    except Exception as exc:
        logger.error("Campaign performance chart failed: %s", exc)

    logger.info(
        "Generated %d charts in %s (template=%s, theme=%s)",
        len(charts), output_dir, visual_template, theme_name,
    )
    return charts
