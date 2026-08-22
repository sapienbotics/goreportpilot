"""
The canonical source envelope.

Every source currently emits its own ad-hoc dict shape (GA4 uses ``x_change``,
Meta uses both ``prev_x`` and ``x_change``, ``traffic_sources`` is a dict while
every other breakdown is a list, only Meta carries ``platform``/``currency``).
Those legacy shapes are load-bearing — chart_generator, ai_narrative and
report_generator all read them by literal key — so this module does NOT replace
them. It sits alongside as a *projection*.

Use it for anything new (Track B connectors, the MCP surface, goal evaluation),
where a uniform shape removes a whole class of per-source special-casing. The
legacy dicts stay authoritative for rendering until a later cycle retires them.

    legacy = await adapter.pull(ctx)          # what the renderer consumes
    env    = project_ga4(legacy, period)      # what new code should consume
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Direction = Literal["higher_is_better", "lower_is_better"]
Unit = Literal["int", "float", "percent", "currency", "ratio", "seconds"]


@dataclass
class Metric:
    """One summary metric with its comparison built in."""

    current: float | None
    previous: float | None = None
    change_pct: float | None = None
    unit: Unit = "int"
    direction: Direction = "higher_is_better"
    label: str = ""

    @classmethod
    def of(
        cls,
        current: Any,
        previous: Any = None,
        *,
        unit: Unit = "int",
        direction: Direction = "higher_is_better",
        label: str = "",
        change_pct: Any = None,
    ) -> "Metric":
        """Build a Metric, deriving change_pct when it isn't supplied."""
        cur = _num(current)
        prev = _num(previous)
        chg = _num(change_pct)
        if chg is None and cur is not None and prev not in (None, 0):
            chg = round((cur - prev) / abs(prev) * 100, 1)
        return cls(
            current=cur, previous=prev, change_pct=chg,
            unit=unit, direction=direction, label=label,
        )


@dataclass
class Period:
    start: str
    end: str
    prev_start: str | None = None
    prev_end: str | None = None


@dataclass
class SourceEnvelope:
    """Uniform result shape for one source over one period."""

    source_id: str                                  # "ga4", "stripe", "csv:linkedin_ads"
    source_label: str
    kind: str
    period: Period
    currency: str = "USD"
    summary: dict[str, Metric] = field(default_factory=dict)
    series: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    breakdowns: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Projections from the legacy per-source dicts
# ---------------------------------------------------------------------------

# (legacy summary key, canonical key, unit, direction)
_GA4_METRICS: tuple[tuple[str, str, Unit, Direction], ...] = (
    ("sessions",             "sessions",             "int",     "higher_is_better"),
    ("users",                "users",                "int",     "higher_is_better"),
    ("pageviews",            "pageviews",            "int",     "higher_is_better"),
    ("conversions",          "conversions",          "int",     "higher_is_better"),
    ("bounce_rate",          "bounce_rate",          "percent", "lower_is_better"),
    ("avg_session_duration", "avg_session_duration", "seconds", "higher_is_better"),
)

_ADS_METRICS: tuple[tuple[str, str, Unit, Direction], ...] = (
    ("spend",               "spend",               "currency", "lower_is_better"),
    ("impressions",         "impressions",         "int",      "higher_is_better"),
    ("clicks",              "clicks",              "int",      "higher_is_better"),
    ("ctr",                 "ctr",                 "percent",  "higher_is_better"),
    ("cpc",                 "cpc",                 "currency", "lower_is_better"),
    ("cpm",                 "cpm",                 "currency", "lower_is_better"),
    ("conversions",         "conversions",         "int",      "higher_is_better"),
    ("cost_per_conversion", "cost_per_conversion", "currency", "lower_is_better"),
    ("revenue",             "revenue",             "currency", "higher_is_better"),
    ("roas",                "roas",                "ratio",    "higher_is_better"),
)

_GSC_METRICS: tuple[tuple[str, str, Unit, Direction], ...] = (
    ("clicks",       "clicks",       "int",     "higher_is_better"),
    ("impressions",  "impressions",  "int",     "higher_is_better"),
    ("ctr",          "ctr",          "percent", "higher_is_better"),
    ("avg_position", "avg_position", "float",   "lower_is_better"),
)


def _summary_from(
    legacy_summary: dict[str, Any],
    spec: tuple[tuple[str, str, Unit, Direction], ...],
) -> dict[str, Metric]:
    """
    Read a legacy summary dict against a metric spec, tolerating both
    conventions: ``prev_<key>`` for the previous value and ``<key>_change`` for
    a pre-computed delta. Missing metrics are omitted, not zero-filled.
    """
    out: dict[str, Metric] = {}
    for legacy_key, key, unit, direction in spec:
        if legacy_key not in legacy_summary:
            continue
        out[key] = Metric.of(
            legacy_summary.get(legacy_key),
            legacy_summary.get(f"prev_{legacy_key}"),
            change_pct=legacy_summary.get(f"{legacy_key}_change"),
            unit=unit,
            direction=direction,
        )
    return out


def project(
    source_id: str,
    label: str,
    kind: str,
    legacy: dict[str, Any],
    period: Period,
    *,
    currency: str = "USD",
) -> SourceEnvelope:
    """Project any legacy source dict into the canonical envelope."""
    spec = {
        "ga4":            _GA4_METRICS,
        "meta_ads":       _ADS_METRICS,
        "google_ads":     _ADS_METRICS,
        "search_console": _GSC_METRICS,
    }.get(source_id, _ADS_METRICS)

    summary = _summary_from(legacy.get("summary") or {}, spec)

    breakdowns: dict[str, list[dict[str, Any]]] = {}
    for key, value in legacy.items():
        if key in ("summary", "daily", "platform", "currency", "period"):
            continue
        if isinstance(value, list):
            breakdowns[key] = value
        elif isinstance(value, dict):
            # GA4's traffic_sources is {label: count}; normalise to a list so
            # consumers never have to branch on container type.
            breakdowns[key] = [{"label": k, "value": v} for k, v in value.items()]

    return SourceEnvelope(
        source_id=source_id,
        source_label=label,
        kind=kind,
        period=period,
        currency=legacy.get("currency") or currency,
        summary=summary,
        series={"daily": legacy.get("daily") or []},
        breakdowns=breakdowns,
    )


def project_csv_source(csv_src: dict[str, Any], period: Period) -> SourceEnvelope:
    """
    Project one entry of ``raw_data["csv_sources"]`` into the canonical envelope.

    CSV metrics are user-named, so the canonical key is a slug of the label and
    ``direction`` is inferred from the metric name the same way the CSV chart
    generator does it.
    """
    name = csv_src.get("source_name") or csv_src.get("name") or "Custom Data"
    summary: dict[str, Metric] = {}
    for row in csv_src.get("metrics") or []:
        raw_label = str(row.get("name") or "").strip()
        if not raw_label:
            continue
        key = "".join(c if c.isalnum() else "_" for c in raw_label.lower()).strip("_")
        lowered = raw_label.lower()
        lower_is_better = any(
            token in lowered
            for token in ("cost", "bounce", "unsubscribe", "cpc", "cpa", "cpm", "spend")
        )
        summary[key] = Metric.of(
            row.get("current_value"),
            row.get("previous_value"),
            change_pct=row.get("change"),
            unit=_CSV_UNIT_MAP.get(str(row.get("unit") or "number").lower(), "float"),
            direction="lower_is_better" if lower_is_better else "higher_is_better",
            label=raw_label,
        )

    return SourceEnvelope(
        source_id=f"csv:{name.lower().replace(' ', '_')}",
        source_label=name,
        kind="custom",
        period=period,
        summary=summary,
        series={"daily": csv_src.get("daily") or []},
    )


_CSV_UNIT_MAP: dict[str, Unit] = {
    "currency": "currency",
    "percent":  "percent",
    "number":   "float",
    "ratio":    "ratio",
}
