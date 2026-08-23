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

from services.csv_ingest import currency as currency_detect
from services.csv_ingest import derivations
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

    Triggers on "percent" OR "ratio" mapping units. Found by the real model:
    my hand-written stub fixture guessed the model would call Meta's "CTR
    (all)" column "percent" — it called it "ratio" instead, arguably the more
    precise reading of a column with no '%' sign in it. _slide_unit() already
    collapses percent and ratio to the same rendered "%" display; this had a
    narrower trigger than that and only checked "percent" literally, so a
    ratio-labelled fraction rendered as "%" without ever being scaled —
    "0.0047%" instead of "0.47%". Widened to match _slide_unit's grouping.

    Deliberately narrow otherwise: the column must have no '%' anywhere in it,
    and every value must sit in [0, 1]. A column already written as "0.91%"
    carries the sign and is left alone.
    """
    if mapping.unit not in ("percent", "ratio"):
        return 1.0
    for column in profile.columns:
        if column.name == mapping.source_column:
            return 100.0 if column.looks_like_fraction else 1.0
    return 1.0


def _is_rate(mapping: ColumnMapping) -> bool:
    """
    Rates and ratios must never be summed — and never plainly averaged either.

    Delegates to services.csv_ingest.derivations, which owns both the question
    "is this a rate" and the answer "then how does it combine". Averaging was
    the previous answer here and it was wrong: the arithmetic mean of daily
    CTRs ignores that days carry different volumes.
    """
    return derivations.is_rate(mapping.target_metric, mapping.unit, mapping.label)


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

    # ── Work out the period, and the halves used for the trend ───────────────
    #
    # A single dated upload is ONE period, not two. The headline figure is
    # therefore the whole uploaded period — a July export of 3,884,961
    # impressions must read 3,884,961, not the 2,053,132 of its second half.
    # The halves still exist, but only to compute the change badge, which is a
    # within-period trend and is labelled as one.
    dated = date_index is not None and any(d for d in dates)
    if dated:
        order = sorted(
            (i for i, d in enumerate(dates) if d), key=lambda i: dates[i] or ""
        )
        if comparison_rows:
            first_half = order[:comparison_rows]
            second_half = order[comparison_rows:]
        else:
            # Split on a DATE boundary, not at the midpoint of the row list.
            #
            # An entity-per-day export has several rows per date, so a row
            # midpoint lands mid-day: on this fixture (4 campaigns x 31 days)
            # index 62 falls inside 2026-07-16, giving two campaigns 16 days
            # "before" and 15 "after" while the other two got the reverse.
            # Every per-entity change was then measured over a different span
            # than its neighbour's, which quietly flatters some campaigns and
            # penalises others — and those per-entity changes are exactly what
            # the narrative now attributes growth by. Splitting on the date
            # gives every entity the identical two windows.
            # The two windows are also equal in LENGTH. An odd number of days
            # cannot be halved, so the middle day is left out of the
            # comparison — it still counts in the period total, it just is not
            # allowed to land on one side and inflate it. July's 31 days
            # compare the 1st-15th against the 17th-31st; splitting 15-against-
            # 16 instead reported +19.4% impressions where an even comparison
            # gives +12.9%, most of that gap being nothing but the extra day.
            unique_dates = sorted({dates[i] for i in order if dates[i]})
            half = len(unique_dates) // 2
            if half:
                early = set(unique_dates[:half])
                late = set(unique_dates[len(unique_dates) - half:])
                first_half = [i for i in order if dates[i] in early]
                second_half = [i for i in order if dates[i] in late]
            else:
                first_half, second_half = [], order
        if not first_half or not second_half:
            first_half, second_half = [], order
        whole_period = order
    else:
        first_half, second_half = [], list(range(len(rows)))
        whole_period = list(range(len(rows)))

    # ── Aggregate ────────────────────────────────────────────────────────────
    # Every reduction goes through derivations.aggregate — counts sum, declared
    # rates recompute from their components against these totals. The entity
    # breakdown below calls the same function, so a per-campaign CTR and the
    # headline CTR cannot be computed two different ways.
    metric_keys = [m.target_metric for m in mappings]
    units = {m.target_metric: m.unit for m in mappings}
    labels = {m.target_metric: m.label or m.source_column for m in mappings}

    full = derivations.aggregate(metric_keys, units, labels, columns, whole_period)
    recent = (
        derivations.aggregate(metric_keys, units, labels, columns, second_half)
        if first_half else {}
    )
    earlier = (
        derivations.aggregate(metric_keys, units, labels, columns, first_half)
        if first_half else {}
    )

    metrics: list[dict[str, Any]] = []
    derivation_report: dict[str, dict[str, Any]] = {}
    metric_warnings: list[str] = []
    for column_mapping in mappings:
        key = column_mapping.target_metric
        derived = full.get(key)
        if derived is None or derived.value is None:
            # A metric withheld on purpose says so, rather than vanishing.
            if derived is not None and derived.method == "suppressed":
                metric_warnings.append(
                    f"{column_mapping.label or column_mapping.source_column} is "
                    f"not shown: {derived.detail}."
                )
                derivation_report[key] = {
                    "method": derived.method, "weighted_by": None,
                    "detail": derived.detail,
                }
            continue

        # A deduplicated metric — and anything derived from one — gets NO
        # period-over-period change. "Peak daily reach" is a maximum, not a
        # sum: comparing the highest day of one half against the highest day
        # of the other is two order statistics, not a trend. A single strong
        # day early in the period can manufacture a "decline" that never
        # happened, and unlike the earlier reach-summing bug this one produces
        # a real, individually-correct number at each end — it is the framing
        # of the pair as a trend that is false, which is why it survived the
        # sum fix and had to be caught separately.
        #
        # This is not special-cased to reach: it is keyed off the same
        # is_deduplicated() flag that decided the value itself is a peak, so
        # any current or future dedup metric — and any rate whose derivation
        # touches one — is covered by construction rather than by name.
        change = None
        before = after = None
        no_comparison = derivations.is_deduplicated(key)
        if not no_comparison:
            before = earlier.get(key)
            after = recent.get(key)
            if before is not None and after is not None:
                if before.value not in (None, 0) and after.value is not None:
                    change = round(
                        (after.value - before.value) / abs(before.value) * 100, 2
                    )

        # A figure that is not a period total must not be read as one. The
        # label carries the correction, because the number appears on a slide
        # with nothing else around it to explain itself.
        name = column_mapping.label or column_mapping.source_column
        if derived.basis == "peak_daily":
            name = _peak_daily_label(name)
            metric_warnings.append(
                f"{name} is the highest single day, not a period total — "
                f"{derived.detail}."
            )
            metric_warnings.append(
                f"{name} has no period-over-period comparison: it is a peak "
                "value, not a sum, so comparing two maxima would manufacture "
                "a trend from a single strong or weak day rather than "
                "measuring one."
            )

        metrics.append({
            "name":           name,
            "metric_key":     key,
            "current_value":  round(derived.value, 4),
            # No prior period exists inside a single upload. Left absent rather
            # than filled with the first half, which would make the comparison
            # chart draw a full-period bar against a half-period one.
            "previous_value": None,
            # The registry's declared display wins over the unit the mapper
            # inferred from the column: "percent" and "multiplier" both reach
            # here as "ratio", and only the registry knows which this is.
            "unit":           derivations.display_unit(
                key, _slide_unit(column_mapping.unit)
            ),
            "direction":      column_mapping.direction,
            "change":         change,
            "change_basis":   "within_period" if change is not None else None,
            "value_basis":    derived.basis,
            "first_half_value":  round(before.value, 4) if before and before.value is not None else None,
            "second_half_value": round(after.value, 4) if after and after.value is not None else None,
            "derivation":     derived.method,
        })
        derivation_report[key] = {
            "method":      derived.method,
            "weighted_by": derived.weighted_by,
            "detail":      derived.detail,
        }

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
        # How each metric was reduced, so a report can state which figures were
        # recomputed from components and which fell back to a weighted mean.
        "derivations": derivation_report,
    }

    detected_currency, currency_source = _detect_currency(profile, mappings)
    if detected_currency:
        result["currency"] = detected_currency
        result["currency_source"] = currency_source

    # Surface the scaling rather than doing it silently — the user should be
    # able to see why 0.0047 became 0.47%.
    warnings: list[str] = []
    if scaled_columns:
        warnings.append(
            f"{', '.join(scaled_columns)} was stored as a decimal fraction "
            "(0.0047) and has been converted to a percentage (0.47%)."
        )
    # Relabelled and withheld metrics explain themselves here, so the reason a
    # figure is not what someone expected is attached to the source rather than
    # left for them to work out from the slide.
    warnings.extend(metric_warnings)
    if warnings:
        result["warnings"] = warnings

    # ── Daily series, when the table is dated ────────────────────────────────
    if dated:
        series = _build_series(dates, columns)
        if series:
            result["daily"] = series

    if mapping.entity_column:
        breakdown = _build_entity_breakdown(
            profile, mapping, rows, columns,
            first_half=first_half, second_half=second_half,
        )
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


def _detect_currency(
    profile: TableProfile, mappings: list[ColumnMapping]
) -> tuple[str | None, str]:
    """
    The currency this file's money columns are in, if it says.

    Only the columns actually mapped to money are inspected — a stray "$" in a
    campaign name must not decide the currency of the whole report.
    """
    money_columns = {m.source_column for m in mappings if m.unit == "currency"}
    headers: list[str] = []
    samples: list[str] = []
    for column in profile.columns:
        if column.name in money_columns:
            headers.append(column.name)
            samples.extend(column.samples[:8])
    return currency_detect.detect(
        getattr(profile, "_preamble_rows", []) or [], headers, samples
    )


def _peak_daily_label(label: str) -> str:
    """
    "Reach" -> "Peak daily reach". Leaves an already-corrected label alone.

    Chosen over dropping the metric because the relabelling is clean and the
    number stays real: peak daily reach is a figure the client can look up in
    their own Ads Manager for that day and find it agrees. Suppressing reach
    entirely would leave a hole on the one slide a Meta advertiser looks at
    first, and would replace a checkable number with nothing.
    """
    stripped = label.strip()
    if stripped.lower().startswith("peak daily"):
        return stripped
    if not stripped:
        return "Peak daily value"
    return "Peak daily " + stripped[0].lower() + stripped[1:]


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
    first_half: list[int] | None = None,
    second_half: list[int] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Top entities (campaigns, pages, products) by the first mapped metric.

    Goes through derivations.aggregate, exactly as the period totals do. This
    used to sum every column per entity, rates included, which produced a
    per-campaign conversion rate of 178.8% on the LinkedIn fixture — the same
    defect as the headline CTR, in a different shape. Fixing one and not the
    other is why they are now one function.
    """
    if not mapping.entity_column:
        return []
    index = _column_index(profile, mapping.entity_column.name)
    if index is None:
        return []

    primary = mapping.columns[0].target_metric if mapping.columns else None
    metric_keys = [m.target_metric for m in mapping.columns]
    units = {m.target_metric: m.unit for m in mapping.columns}
    labels = {m.target_metric: m.label or m.source_column for m in mapping.columns}

    row_indices: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        name = (row[index] if index < len(row) else "").strip()
        if not name:
            continue
        row_indices.setdefault(name, []).append(i)

    # Each entity's OWN within-period trend. Without this the narrative has
    # only the source-wide change and a list of entity names, and the model
    # pins the one onto the other: Pass 4's deck credited "Q3 Thought
    # Leadership | Video Views" with the whole source's +12.1% impressions
    # growth when that campaign grew 3.5%.
    first_set = set(first_half or [])
    second_set = set(second_half or [])

    entries: list[dict[str, Any]] = []
    for name, indices in row_indices.items():
        derived = derivations.aggregate(metric_keys, units, labels, columns, indices)
        entry: dict[str, Any] = {"name": name}
        for key, value in derived.items():
            if value.value is not None:
                entry[key] = round(value.value, 4)

        own_first = [i for i in indices if i in first_set]
        own_second = [i for i in indices if i in second_set]
        if own_first and own_second:
            before = derivations.aggregate(metric_keys, units, labels, columns, own_first)
            after = derivations.aggregate(metric_keys, units, labels, columns, own_second)
            changes: dict[str, float] = {}
            for key in metric_keys:
                # Same rule as the period totals, and for the same reason: an
                # entity's peak day in one half against its peak day in the
                # other is still two maxima, not a trend, whichever entity it
                # is. Keyed off is_deduplicated(), not "reach" by name.
                if derivations.is_deduplicated(key):
                    continue
                b, a = before.get(key), after.get(key)
                if b is None or a is None:
                    continue
                if b.value in (None, 0) or a.value is None:
                    continue
                changes[key] = round((a.value - b.value) / abs(b.value) * 100, 2)
            if changes:
                entry["changes"] = changes
        entries.append(entry)

    if primary:
        entries.sort(key=lambda e: e.get(primary) or 0.0, reverse=True)
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
