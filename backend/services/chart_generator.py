"""
Chart generator — creates PNG chart images for reports using matplotlib.
All functions are synchronous; call via asyncio.to_thread() in async endpoints.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — must be set before importing pyplot
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

logger = logging.getLogger(__name__)

# ── Brand colour palette ────────────────────────────────────────────────────
CHART_COLORS = {
    "primary":   "#4338CA",  # Indigo-700
    "secondary": "#059669",  # Emerald-600
    "accent":    "#D97706",  # Amber-600
    "danger":    "#E11D48",  # Rose-600
    "gray":      "#64748B",  # Slate-500
}


def _setup_chart_style() -> None:
    """Apply consistent brand styling to all charts."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def generate_sessions_chart(daily_data: List[Dict], output_path: str) -> str:
    """Line chart of daily sessions over the report period."""
    _setup_chart_style()

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    sessions = [d["sessions"] for d in daily_data]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, sessions, color=CHART_COLORS["primary"], linewidth=2, marker="o", markersize=3)
    ax.fill_between(dates, sessions, alpha=0.08, color=CHART_COLORS["primary"])

    ax.set_title("Sessions Over Time", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Sessions")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    logger.info("Sessions chart saved: %s", output_path)
    return output_path


def generate_traffic_sources_chart(sources: List[Dict], output_path: str) -> str:
    """Horizontal bar chart of traffic sources by session count."""
    _setup_chart_style()

    labels = [s["source"] for s in sources]
    values = [s["sessions"] for s in sources]
    bar_colors = [
        CHART_COLORS["primary"],
        CHART_COLORS["secondary"],
        CHART_COLORS["accent"],
        CHART_COLORS["gray"],
        CHART_COLORS["danger"],
    ]

    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.barh(labels, values, color=bar_colors[: len(labels)], height=0.6, edgecolor="none")

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + max(values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center",
            fontsize=10,
        )

    ax.set_title("Traffic Sources", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Sessions")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.invert_yaxis()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    logger.info("Traffic sources chart saved: %s", output_path)
    return output_path


def generate_spend_vs_conversions_chart(daily_data: List[Dict], output_path: str) -> str:
    """Dual-axis chart: daily ad spend (bars) vs conversions (line)."""
    _setup_chart_style()

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_data]
    spend = [d["spend"] for d in daily_data]
    conversions = [d["conversions"] for d in daily_data]

    fig, ax1 = plt.subplots(figsize=(10, 4))

    ax1.bar(dates, spend, color=CHART_COLORS["primary"], alpha=0.7, width=0.8, label="Spend ($)")
    ax1.set_ylabel("Spend ($)", color=CHART_COLORS["primary"])
    ax1.tick_params(axis="y", labelcolor=CHART_COLORS["primary"])
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${int(x):,}"))

    ax2 = ax1.twinx()
    ax2.plot(
        dates, conversions,
        color=CHART_COLORS["secondary"], linewidth=2, marker="o", markersize=3, label="Conversions",
    )
    ax2.set_ylabel("Conversions", color=CHART_COLORS["secondary"])
    ax2.tick_params(axis="y", labelcolor=CHART_COLORS["secondary"])
    ax2.spines["right"].set_visible(True)

    ax1.set_title("Daily Spend vs Conversions", fontsize=14, fontweight="bold", pad=15)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    logger.info("Spend vs conversions chart saved: %s", output_path)
    return output_path


def generate_campaign_performance_chart(campaigns: List[Dict], output_path: str) -> str:
    """Grouped bar chart of campaign spend and conversions."""
    _setup_chart_style()

    top_campaigns = campaigns[:5]
    # Shorten names: take everything after " - " if present
    names = [
        c["name"].split(" - ")[-1] if " - " in c["name"] else c["name"]
        for c in top_campaigns
    ]
    spend = [c["spend"] for c in top_campaigns]
    conversions = [c["conversions"] for c in top_campaigns]

    fig, ax1 = plt.subplots(figsize=(10, 4))

    x = range(len(names))
    width = 0.35

    ax1.bar(
        [i - width / 2 for i in x], spend, width,
        label="Spend ($)", color=CHART_COLORS["primary"], edgecolor="none",
    )
    ax1.set_ylabel("Spend ($)", color=CHART_COLORS["primary"])
    ax1.tick_params(axis="y", labelcolor=CHART_COLORS["primary"])
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${int(x):,}"))

    ax2 = ax1.twinx()
    ax2.bar(
        [i + width / 2 for i in x], conversions, width,
        label="Conversions", color=CHART_COLORS["secondary"], edgecolor="none",
    )
    ax2.set_ylabel("Conversions", color=CHART_COLORS["secondary"])
    ax2.tick_params(axis="y", labelcolor=CHART_COLORS["secondary"])
    ax2.spines["right"].set_visible(True)

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(names, rotation=15, ha="right")
    ax1.set_title("Campaign Performance", fontsize=14, fontweight="bold", pad=15)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    logger.info("Campaign performance chart saved: %s", output_path)
    return output_path


def generate_all_charts(data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """
    Generate all report charts and return a dict of {chart_name: file_path}.
    This is a synchronous function — call via asyncio.to_thread() in async contexts.
    """
    os.makedirs(output_dir, exist_ok=True)

    charts: Dict[str, str] = {}
    ga4 = data.get("ga4", {})
    meta = data.get("meta_ads", {})

    try:
        if ga4.get("daily"):
            charts["sessions"] = generate_sessions_chart(
                ga4["daily"], os.path.join(output_dir, "sessions.png")
            )
    except Exception as exc:
        logger.error("Failed to generate sessions chart: %s", exc)

    try:
        if ga4.get("traffic_sources"):
            charts["traffic_sources"] = generate_traffic_sources_chart(
                ga4["traffic_sources"], os.path.join(output_dir, "traffic_sources.png")
            )
    except Exception as exc:
        logger.error("Failed to generate traffic sources chart: %s", exc)

    try:
        if meta.get("daily"):
            charts["spend_conversions"] = generate_spend_vs_conversions_chart(
                meta["daily"], os.path.join(output_dir, "spend_conversions.png")
            )
    except Exception as exc:
        logger.error("Failed to generate spend/conversions chart: %s", exc)

    try:
        if meta.get("campaigns"):
            charts["campaigns"] = generate_campaign_performance_chart(
                meta["campaigns"], os.path.join(output_dir, "campaigns.png")
            )
    except Exception as exc:
        logger.error("Failed to generate campaigns chart: %s", exc)

    logger.info("Generated %d charts in %s", len(charts), output_dir)
    return charts
