"""
Chart generator — creates PNG chart images for reports using matplotlib.
All functions are synchronous; call via asyncio.to_thread() in async contexts.
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

logger = logging.getLogger(__name__)

# ── Currency symbol lookup ───────────────────────────────────────────────────
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


# ── Default palette ──────────────────────────────────────────────────────────
_DEFAULT_PRIMARY   = "#4338CA"  # Indigo-700
_DEFAULT_SECONDARY = "#059669"  # Emerald-600
_DEFAULT_ACCENT    = "#D97706"  # Amber-600
_DEFAULT_DANGER    = "#E11D48"  # Rose-600
_GRAY              = "#64748B"  # Slate-500
_CHART_BG          = "#FAFAFA"  # Near-white chart background
_AXIS_COLOR        = "#475569"  # Slate-600 for axis labels


def _setup_chart_style(brand_color: str = _DEFAULT_PRIMARY) -> dict:
    """
    Apply consistent brand styling to all subsequent charts.
    Returns a colour palette dict for the caller to use.
    """
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.edgecolor": "#CBD5E1",      # slate-300
        "axes.grid": True,
        "grid.alpha": 0.2,
        "grid.linestyle": "-",
        "grid.color": "#E2E8F0",          # slate-200
        "figure.facecolor": _CHART_BG,
        "axes.facecolor": _CHART_BG,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.titlecolor": "#0F172A",     # slate-900
        "axes.titlepad": 14,
        "axes.labelsize": 11,
        "axes.labelcolor": _AXIS_COLOR,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "xtick.color": _AXIS_COLOR,
        "ytick.color": _AXIS_COLOR,
        "legend.fontsize": 10,
        "legend.framealpha": 0.9,
        "legend.edgecolor": "#E2E8F0",
    })
    return {
        "primary":   brand_color,
        "secondary": _DEFAULT_SECONDARY,
        "accent":    _DEFAULT_ACCENT,
        "danger":    _DEFAULT_DANGER,
        "gray":      _GRAY,
    }


def _save_fig(fig: Any, output_path: str) -> str:
    """Save figure at 200 DPI with tight layout and close it."""
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor=_CHART_BG)
    plt.close(fig)
    logger.info("Chart saved: %s", output_path)
    return output_path


def generate_sessions_chart(
    daily_data: List[Dict],
    output_path: str,
    brand_color: str = _DEFAULT_PRIMARY,
) -> str:
    """Smooth area line chart of daily sessions over the report period."""
    colors = _setup_chart_style(brand_color)

    dates    = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    sessions = [d["sessions"] for d in daily_data]

    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(dates, sessions,
            color=colors["primary"], linewidth=2.5,
            marker="o", markersize=4.5, zorder=3)
    ax.fill_between(dates, sessions, alpha=0.12, color=colors["primary"])

    ax.set_title("Sessions Over Time")
    ax.set_ylabel("Sessions", color=_AXIS_COLOR)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Readable date labels: every 7 days in "Mar 01" format
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")

    fig.tight_layout()
    return _save_fig(fig, output_path)


def generate_traffic_sources_chart(
    sources: List[Dict],
    output_path: str,
    brand_color: str = _DEFAULT_PRIMARY,
) -> str:
    """Horizontal bar chart of traffic sources by session count."""
    colors = _setup_chart_style(brand_color)

    labels = [s["source"] for s in sources]
    values = [s["sessions"] for s in sources]
    palette = [
        colors["primary"], colors["secondary"], colors["accent"],
        colors["gray"], colors["danger"],
    ]

    fig, ax = plt.subplots(figsize=(10, 4.2))
    bars = ax.barh(labels, values,
                   color=palette[: len(labels)],
                   height=0.55, edgecolor="none")

    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + max_val * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center", fontsize=10, color=_AXIS_COLOR,
        )

    ax.set_title("Traffic Sources")
    ax.set_xlabel("Sessions")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()

    fig.tight_layout()
    return _save_fig(fig, output_path)


def generate_spend_vs_conversions_chart(
    daily_data: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = _DEFAULT_PRIMARY,
) -> str:
    """Dual-axis chart: daily ad spend (bars) vs conversions (line)."""
    colors = _setup_chart_style(brand_color)

    dates       = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    spend       = [d["spend"] for d in daily_data]
    conversions = [d["conversions"] for d in daily_data]

    fig, ax1 = plt.subplots(figsize=(10, 4.2))

    ax1.bar(dates, spend,
            color=colors["primary"], alpha=0.75, width=0.75,
            label=f"Spend ({currency_symbol})", zorder=2)
    ax1.set_ylabel(f"Spend ({currency_symbol})", color=colors["primary"])
    ax1.tick_params(axis="y", labelcolor=colors["primary"])
    ax1.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f"{currency_symbol}{int(x):,}")
    )

    ax2 = ax1.twinx()
    ax2.plot(dates, conversions,
             color=colors["secondary"], linewidth=2.5,
             marker="o", markersize=4.5, label="Conversions", zorder=3)
    ax2.set_ylabel("Conversions", color=colors["secondary"])
    ax2.tick_params(axis="y", labelcolor=colors["secondary"])
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color("#CBD5E1")

    ax1.set_title("Daily Spend vs Conversions")

    # Merge legends from both axes
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30, ha="right")

    fig.tight_layout()
    return _save_fig(fig, output_path)


def generate_campaign_performance_chart(
    campaigns: List[Dict],
    output_path: str,
    currency_symbol: str = "$",
    brand_color: str = _DEFAULT_PRIMARY,
) -> str:
    """Grouped bar chart — top 5 campaigns by spend and conversions."""
    colors = _setup_chart_style(brand_color)

    top = campaigns[:5]
    names = [
        (c["name"].split(" - ")[-1] if " - " in c["name"] else c["name"])[:26]
        for c in top
    ]
    spend       = [c["spend"] for c in top]
    conversions = [c["conversions"] for c in top]

    fig, ax1 = plt.subplots(figsize=(10, 4.2))
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
    ax2.bar([i + width / 2 for i in x], conversions, width,
            label="Conversions",
            color=colors["secondary"], edgecolor="none", alpha=0.85)
    ax2.set_ylabel("Conversions", color=colors["secondary"])
    ax2.tick_params(axis="y", labelcolor=colors["secondary"])
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color("#CBD5E1")

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(names, rotation=20, ha="right")
    ax1.set_title("Campaign Performance (Top 5)")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")

    fig.tight_layout()
    return _save_fig(fig, output_path)


def generate_all_charts(
    data: Dict[str, Any],
    output_dir: str,
    brand_color: str = "#4338CA",
) -> Dict[str, str]:
    """
    Generate all report charts; return {chart_name: file_path}.
    Synchronous — call via asyncio.to_thread() in async contexts.
    brand_color: Agency brand hex colour for the primary data series.
    """
    os.makedirs(output_dir, exist_ok=True)

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
            )
    except Exception as exc:
        logger.error("Sessions chart failed: %s", exc)

    try:
        if ga4.get("traffic_sources"):
            charts["traffic_sources"] = generate_traffic_sources_chart(
                ga4["traffic_sources"],
                os.path.join(output_dir, "traffic_sources.png"),
                brand_color=brand_color,
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
            )
    except Exception as exc:
        logger.error("Campaign performance chart failed: %s", exc)

    logger.info("Generated %d charts in %s", len(charts), output_dir)
    return charts
