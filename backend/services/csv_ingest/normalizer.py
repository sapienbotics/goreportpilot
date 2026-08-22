"""
Apply a confirmed mapping to a profiled table.

This is where the numbers are actually produced, and it is entirely
deterministic — the LLM's output is used only to decide *which* column means
*what*. Locale handling, date parsing, aggregation, and period comparison all
happen here in Python.

Output is the shape the report pipeline already consumes:

    {"source_name": str,
     "metrics": [{"name", "current_value", "previous_value", "unit", "change"}],
     "daily":   [{"date", <metric>: float, ...}]}      # when a date column exists

``metrics`` is what ``_populate_csv_slide`` renders as KPI cards and
``generate_csv_comparison_chart`` renders as bars. ``daily`` is new: the old
KPI-list format carried no time dimension at all, so a mapped upload can drive a
trend chart for the first time.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from services.csv_ingest.profiler import TableProfile, _parse_localized
from services.csv_ingest.schema import ColumnMapping, MappingProposal

logger = logging.getLogger(__name__)

# Slide capacity. More metrics than this are still stored and still available
# to the AI narrative; the slide shows the first six.
KPI_SLIDE_CAPACITY = 6
MAX_METRICS = 200


class NormalizationError(ValueError):
    """Raised when a confirmed mapping cannot be applied. Message is user-facing."""


def _to_iso_date(raw: str, fmt: str | None) -> str | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if fmt:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    # Values already in ISO form (openpyxl renders real dates this way).
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _column_index(profile: TableProfile, name: str) -> int | None:
    for column in profile.columns:
        if column.name == name:
            return column.index
    return None


def _decimal_mark(profile: TableProfile, name: str) -> str:
    for column in profile.columns:
        if column.name == name:
            return column.decimal_mark
    return "."


def _percent_scale(profile: TableProfile, mapping: ColumnMapping) -> float:
    """
    Return 100 when a percent-mapped column is stored as a fraction, else 1.

    Meta exports CTR as 0.0047 meaning 0.47%; Google Ads does the same for
    conversion rate. Rendered unscaled that reads "0.0047%" on a client's slide.

    Deliberately narrow: the column must be mapped as a percentage, must have no
    '%' anywhere in it, and every value must sit in [0, 1]. A column already
    written as "0.91%" carries the sign and is left alone.
    """
    if mapping.unit != "percent":
        return 1.0
    for column in profile.columns:
        if column.name == mapping.source_column:
            return 100.0 if column.looks_like_fraction else 1.0
    return 1.0


def _is_rate(mapping: ColumnMapping) -> bool:
    """
    Rates and ratios must be averaged across rows, never summed.

    Summing a CTR column across 30 days produces a number like 89% and puts it
    on a client's slide. This check is the difference between a correct report
    and an embarrassing one.
    """
    if mapping.unit in ("percent", "ratio"):
        return True
    name = f"{mapping.target_metric} {mapping.label}".lower()
    return any(
        token in name
        for token in (
            "rate", "ratio", "ctr", "cpc", "cpm", "cpa", "roas",
            "average", "avg", "per_", "per ", "position", "frequency",
        )
    )


def normalize(
    profile: TableProfile,
    mapping: MappingProposal,
    *,
    source_name: str = "",
    comparison_rows: int = 0,
) -> dict[str, Any]:
    """
    Turn a profiled table plus a confirmed mapping into report-pipeline data.

    ``comparison_rows`` splits a dated table into two halves so the report can
    show period-over-period change: when 0, the split is the midpoint of the
    date range, which is what a monthly export naturally wants.
    """
    if not mapping.columns:
        raise NormalizationError(
            "No columns are mapped to metrics yet. Choose at least one column "
            "to include in the report."
        )

    rows = profile._rows
    if profile.totals_row_index is not None:
        rows = [r for i, r in enumerate(rows) if i != profile.totals_row_index]
    if not rows:
        raise NormalizationError(
            "That file has headers but no data rows underneath them."
        )

    mappings = mapping.columns[:MAX_METRICS]
    label = source_name or mapping.source_label or "Custom Data"

    # A long-KPI table is one row per metric, so its rows must never be summed
    # together — "Impressions 45,200" and "Spend 1,850" are different things.
    # This is the shape the five bundled templates use, so it is also the path
    # every legacy upload takes.
    if mapping.table_shape == "long_kpi":
        return _normalize_long_kpi(profile, mapping, rows, label)

    date_index: int | None = None
    date_format: str | None = None
    if mapping.date_column:
        date_index = _column_index(profile, mapping.date_column.name)
        date_format = mapping.date_column.format

    # ── Read every mapped column once ────────────────────────────────────────
    columns: dict[str, list[float]] = {}
    dates: list[str | None] = []

    for row in rows:
        if date_index is not None:
            dates.append(_to_iso_date(row[date_index] if date_index < len(row) else "", date_format))

    scaled_columns: list[str] = []
    for column_mapping in mappings:
        index = _column_index(profile, column_mapping.source_column)
        if index is None:
            continue
        mark = _decimal_mark(profile, column_mapping.source_column)
        scale = _percent_scale(profile, column_mapping)
        if scale != 1.0:
            scaled_columns.append(column_mapping.label or column_mapping.source_column)
        values: list[float] = []
        for row in rows:
            value = _parse_localized(row[index] if index < len(row) else "", mark)
            values.append(value * scale if value is not None else float("nan"))
        columns[column_mapping.target_metric] = values

    # ── Split into current vs previous period ────────────────────────────────
    dated = date_index is not None and any(d for d in dates)
    if dated:
        order = sorted(
            (i for i, d in enumerate(dates) if d), key=lambda i: dates[i] or ""
        )
        split = comparison_rows or len(order) // 2
        previous_indices = order[:split]
        current_indices = order[split:]
        # A single-period export has nothing to compare against; show it whole.
        if not previous_indices or not current_indices:
            previous_indices, current_indices = [], order
    else:
        previous_indices, current_indices = [], list(range(len(rows)))

    # ── Aggregate ────────────────────────────────────────────────────────────
    metrics: list[dict[str, Any]] = []
    for column_mapping in mappings:
        values = columns.get(column_mapping.target_metric)
        if not values:
            continue
        average = _is_rate(column_mapping)
        current = _aggregate(values, current_indices, average=average)
        previous = _aggregate(values, previous_indices, average=average) if previous_indices else None
        if current is None:
            continue

        change = None
        if previous not in (None, 0):
            change = round((current - previous) / abs(previous) * 100, 2)

        metrics.append({
            "name":           column_mapping.label or column_mapping.source_column,
            "metric_key":     column_mapping.target_metric,
            "current_value":  round(current, 4),
            "previous_value": round(previous, 4) if previous is not None else None,
            "unit":           _slide_unit(column_mapping.unit),
            "direction":      column_mapping.direction,
            "change":         change,
        })

    if not metrics:
        raise NormalizationError(
            "None of the mapped columns contained numbers we could read. "
            "Check that the right columns are selected."
        )

    result: dict[str, Any] = {
        "source_name": label,
        "metrics":     metrics,
        "mapped_at":   datetime.utcnow().isoformat(),
        "row_count":   len(rows),
    }

    # Surface the scaling rather than doing it silently — the user should be
    # able to see why 0.0047 became 0.47%.
    if scaled_columns:
        result["warnings"] = [
            f"{', '.join(scaled_columns)} was stored as a decimal fraction "
            "(0.0047) and has been converted to a percentage (0.47%)."
        ]

    # ── Daily series, when the table is dated ────────────────────────────────
    if dated:
        series = _build_series(dates, columns)
        if series:
            result["daily"] = series

    if mapping.entity_column:
        breakdown = _build_entity_breakdown(profile, mapping, rows, columns)
        if breakdown:
            result["breakdown"] = breakdown

    return result


def _normalize_long_kpi(
    profile: TableProfile,
    mapping: MappingProposal,
    rows: list[list[str]],
    label: str,
) -> dict[str, Any]:
    """
    Normalise a one-row-per-metric table.

    Column roles:
      * metric name  — the entity column, or the first text column
      * current      — the column mapped to "current_value", else the first
                       mapped numeric column
      * previous     — the column mapped to "previous_value", if present
      * unit         — a literal unit column, when the file has one

    Values are read straight off each row. Nothing is summed or averaged,
    because each row is already a whole metric.
    """
    name_index = None
    if mapping.entity_column:
        name_index = _column_index(profile, mapping.entity_column.name)
    if name_index is None:
        name_index = next(
            (c.index for c in profile.columns if c.inferred_type == "text"), None
        )
    if name_index is None:
        raise NormalizationError(
            "This looks like a list of metrics, but we could not find the column "
            "holding the metric names. Pick it below."
        )

    by_target = {c.target_metric: c for c in mapping.columns}
    current_map = by_target.get("current_value") or next(
        (c for c in mapping.columns if c.target_metric != "previous_value"), None
    )
    if current_map is None:
        raise NormalizationError(
            "Choose which column holds the current value for each metric."
        )
    previous_map = by_target.get("previous_value")

    current_index = _column_index(profile, current_map.source_column)
    previous_index = (
        _column_index(profile, previous_map.source_column) if previous_map else None
    )
    if current_index is None:
        raise NormalizationError(
            f"Column '{current_map.source_column}' is no longer in this file."
        )

    current_mark = _decimal_mark(profile, current_map.source_column)
    previous_mark = (
        _decimal_mark(profile, previous_map.source_column) if previous_map else "."
    )
    # An explicit unit column, if the file carries one (the legacy templates do).
    unit_index = next(
        (
            c.index for c in profile.columns
            if c.name.strip().lower() in ("unit", "type", "format", "metric_type")
        ),
        None,
    )

    metrics: list[dict[str, Any]] = []
    for row in rows:
        name = (row[name_index] if name_index < len(row) else "").strip()
        if not name or name.startswith("#"):
            continue

        raw_current = row[current_index] if current_index < len(row) else ""
        current = _parse_localized(raw_current, current_mark)
        if current is None:
            continue

        previous = None
        if previous_index is not None and previous_index < len(row):
            previous = _parse_localized(row[previous_index], previous_mark)

        raw_unit = ""
        if unit_index is not None and unit_index < len(row):
            raw_unit = row[unit_index]
        unit = _resolve_row_unit(raw_unit, name, raw_current, current_map.unit)

        change = None
        if previous not in (None, 0):
            change = round((current - previous) / abs(previous) * 100, 2)

        metrics.append({
            "name":           name,
            "metric_key":     "".join(
                ch if ch.isalnum() else "_" for ch in name.lower()
            ).strip("_") or "metric",
            "current_value":  round(current, 4),
            "previous_value": round(previous, 4) if previous is not None else None,
            "unit":           unit,
            "direction":      current_map.direction,
            "change":         change,
        })
        if len(metrics) >= MAX_METRICS:
            break

    if not metrics:
        raise NormalizationError(
            "We found the metric-name column but none of the rows had a number "
            "we could read next to them."
        )

    return {
        "source_name": label,
        "metrics":     metrics,
        "mapped_at":   datetime.utcnow().isoformat(),
        "row_count":   len(metrics),
    }


def _resolve_row_unit(
    raw_unit: str, metric_name: str, raw_value: str, fallback: str
) -> str:
    """
    Per-row unit for a long-KPI table.

    Defers to services.csv_parser._normalise_unit, which already resolves an
    explicit unit column, then value symbols, then metric-name keywords — the
    exact behaviour the legacy templates rely on.
    """
    from services.csv_parser import _normalise_unit  # noqa: PLC0415

    resolved = _normalise_unit(raw_unit, metric_name, raw_value)
    return resolved or _slide_unit(fallback)


def _aggregate(
    values: list[float], indices: list[int], *, average: bool
) -> float | None:
    """Sum counts, average rates. NaN cells (unparseable) are skipped, not zeroed."""
    picked = [
        values[i] for i in indices
        if i < len(values) and values[i] == values[i]  # NaN != NaN
    ]
    if not picked:
        return None
    return sum(picked) / len(picked) if average else sum(picked)


def _slide_unit(unit: str) -> str:
    """
    Collapse the mapping unit onto the three the slide renderer understands.

    report_generator._fmt_csv_value only knows currency / percent / number.
    """
    if unit == "currency":
        return "currency"
    if unit in ("percent", "ratio"):
        return "percent"
    return "number"


def _build_series(
    dates: list[str | None], columns: dict[str, list[float]]
) -> list[dict[str, Any]]:
    """Collapse rows to one entry per date, summing duplicates."""
    by_date: dict[str, dict[str, float]] = {}
    for i, day in enumerate(dates):
        if not day:
            continue
        bucket = by_date.setdefault(day, {})
        for metric, values in columns.items():
            if i < len(values) and values[i] == values[i]:
                bucket[metric] = bucket.get(metric, 0.0) + values[i]

    return [
        {"date": day, **{k: round(v, 4) for k, v in metrics.items()}}
        for day, metrics in sorted(by_date.items())
    ]


def _build_entity_breakdown(
    profile: TableProfile,
    mapping: MappingProposal,
    rows: list[list[str]],
    columns: dict[str, list[float]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Top entities (campaigns, pages, products) by the first mapped metric."""
    if not mapping.entity_column:
        return []
    index = _column_index(profile, mapping.entity_column.name)
    if index is None:
        return []

    primary = mapping.columns[0].target_metric if mapping.columns else None
    totals: dict[str, dict[str, float]] = {}
    for i, row in enumerate(rows):
        name = (row[index] if index < len(row) else "").strip()
        if not name:
            continue
        bucket = totals.setdefault(name, {})
        for metric, values in columns.items():
            if i < len(values) and values[i] == values[i]:
                bucket[metric] = bucket.get(metric, 0.0) + values[i]

    entries = [{"name": name, **metrics} for name, metrics in totals.items()]
    if primary:
        entries.sort(key=lambda e: e.get(primary, 0.0), reverse=True)
    return entries[:limit]


def preview_rows(
    profile: TableProfile, mapping: MappingProposal, limit: int = 5
) -> list[dict[str, Any]]:
    """
    Render the first few rows exactly as they will be parsed.

    This is what the confirmation dialog shows — the user sees "₹1.234,56 →
    1234.56" before committing, which catches a wrong locale reading in one
    glance rather than one client report.
    """
    rows = profile._rows[:limit]
    out: list[dict[str, Any]] = []
    for row in rows:
        rendered: dict[str, Any] = {}
        if mapping.date_column:
            index = _column_index(profile, mapping.date_column.name)
            if index is not None:
                raw = row[index] if index < len(row) else ""
                rendered[mapping.date_column.name] = {
                    "raw": raw,
                    "parsed": _to_iso_date(raw, mapping.date_column.format),
                }
        for column_mapping in mapping.columns:
            index = _column_index(profile, column_mapping.source_column)
            if index is None:
                continue
            raw = row[index] if index < len(row) else ""
            parsed = _parse_localized(
                raw, _decimal_mark(profile, column_mapping.source_column)
            )
            # The preview must show the value the report will actually use,
            # scaling included — that is the whole point of showing it.
            scale = _percent_scale(profile, column_mapping)
            rendered[column_mapping.source_column] = {
                "raw": raw,
                "parsed": round(parsed * scale, 6) if parsed is not None else None,
            }
        out.append(rendered)
    return out
