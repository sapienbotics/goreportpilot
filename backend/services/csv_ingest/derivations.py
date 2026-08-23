"""
How every metric aggregates. The single source of truth.

A ratio metric can never be summed, and — the subtler half — can never be
averaged across rows either. The arithmetic mean of 31 daily CTRs weights a
1,000-impression Sunday the same as a 200,000-impression Tuesday. On the
LinkedIn fixture that produced 1.04% against a true 0.70%, and a CPM of 73
against a true 51.34, both rendered onto a client's slide.

A ratio is only correct when recomputed from its components against the
period totals:

    CTR = Σclicks / Σimpressions        — never mean(daily CTR)

So every rate declares what it is made of, here, once. ``METRICS``
is that declaration, and ``aggregate`` below is the only place any metric is
reduced over a set of rows — used both for the period totals and for the
per-entity breakdown, so the two cannot drift apart. They previously did:
the period aggregate averaged rates while the entity breakdown summed them,
which is how a per-campaign conversion rate of 178.8% became possible.

Adding a metric means adding a line to ``METRICS``, which also declares how
it is written (percent vs multiplier — indistinguishable from the values) and
whether it counts people rather than events. The import-time check at the
bottom refuses to load if any of that is missing.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


# How a metric should be written when it reaches a slide.
#
# "percent" and "multiplier" both arrive from the model as unit "ratio", and
# collapsing them was wrong in a way no value inspection can fix: CTR scales to
# 1.07 and a retargeting CTR is 4.12, while frequency is 1.33 — so "a ratio
# above 1 is a multiplier" would render a real percentage as "4.12×". The
# distinction is a property of the metric, not of its value, so it is declared.
DisplayUnit = str  # "number" | "currency" | "percent" | "multiplier" | "duration"

_VALID_DISPLAY_UNITS = frozenset(
    {"number", "currency", "percent", "multiplier", "duration"}
)


@dataclass(frozen=True)
class RateDerivation:
    """A ratio metric expressed as numerator / denominator × scale."""

    numerator: str
    denominator: str
    scale: float = 1.0


@dataclass(frozen=True)
class MetricSpec:
    """
    Everything the pipeline needs to know about a metric it recognises.

    ``display`` is mandatory — a metric that reaches a slide without a declared
    way to be written is the FREQUENCY "1.33%" defect, and the import-time
    check below refuses to load without it.

    ``deduplicated`` marks a count of PEOPLE rather than of events. Those can
    never be summed: reach counts distinct people, and the same person recurs
    on day two, so 31 daily rows added together can overstate a month's reach
    two- or three-fold. See ``aggregate`` for what happens instead.
    """

    display: DisplayUnit
    derivation: RateDerivation | None = None
    deduplicated: bool = False


# ── The registry ────────────────────────────────────────────────────────────
# Keyed by canonical metric name. A derivation's numerator/denominator name
# *canonical components*, resolved against whatever the upload actually calls
# them by _COMPONENT_ALIASES below.
METRICS: dict[str, MetricSpec] = {
    # ── Rates ───────────────────────────────────────────────────────────────
    "ctr":                 MetricSpec("percent",    RateDerivation("clicks",      "impressions", 100.0)),
    "cpc":                 MetricSpec("currency",   RateDerivation("spend",       "clicks")),
    "cpm":                 MetricSpec("currency",   RateDerivation("spend",       "impressions", 1000.0)),
    "conversion_rate":     MetricSpec("percent",    RateDerivation("conversions", "clicks",      100.0)),
    "cost_per_conversion": MetricSpec("currency",   RateDerivation("spend",       "conversions")),
    "cost_per_lead":       MetricSpec("currency",   RateDerivation("spend",       "leads")),
    "aov":                 MetricSpec("currency",   RateDerivation("revenue",     "conversions")),
    # A 3.5x return on ad spend is not "3.5%".
    "roas":                MetricSpec("multiplier", RateDerivation("revenue",     "spend")),
    # Meta reports impressions and reach separately, so frequency is derivable
    # rather than approximable — but only over a basis where reach is real.
    # 1.33 means each reached person saw the ad 1.33 times; "1.33%" is not a
    # quantity that exists.
    "frequency":           MetricSpec("multiplier", RateDerivation("impressions", "reach")),

    # ── Deduplicated people-counts ──────────────────────────────────────────
    "reach":               MetricSpec("number", deduplicated=True),
    "unique_clicks":       MetricSpec("number", deduplicated=True),
    "unique_link_clicks":  MetricSpec("number", deduplicated=True),
    "unique_users":        MetricSpec("number", deduplicated=True),
    "users":               MetricSpec("number", deduplicated=True),

    # ── Plain event counts, declared so their display is not inferred ───────
    "impressions":         MetricSpec("number"),
    "clicks":              MetricSpec("number"),
    "conversions":         MetricSpec("number"),
    "leads":               MetricSpec("number"),
    "sessions":            MetricSpec("number"),
    "spend":               MetricSpec("currency"),
    "revenue":             MetricSpec("currency"),
}

# An upload's own name for a rate → the canonical rate above.
_RATE_ALIASES: dict[str, str] = {
    "ctr": "ctr",
    "click_through_rate": "ctr",
    "clickthrough_rate": "ctr",
    "click_thru_rate": "ctr",
    "link_ctr": "ctr",
    "unique_ctr": "ctr",

    "cpc": "cpc",
    "cost_per_click": "cpc",
    "average_cpc": "cpc",
    "avg_cpc": "cpc",

    "cpm": "cpm",
    "average_cpm": "cpm",
    "avg_cpm": "cpm",
    "cost_per_mille": "cpm",
    "cost_per_1000_impressions": "cpm",
    "cost_per_thousand_impressions": "cpm",

    "conversion_rate": "conversion_rate",
    "conv_rate": "conversion_rate",
    "cvr": "conversion_rate",

    "cost_per_conversion": "cost_per_conversion",
    "cost_per_acquisition": "cost_per_conversion",
    "cpa": "cost_per_conversion",

    "cost_per_lead": "cost_per_lead",
    "cpl": "cost_per_lead",

    # Meta calls a conversion a "result" and its cost "Cost per result". Same
    # arithmetic as cost per conversion, and "results" resolves as a
    # conversions component below. Missing this, the Meta fixture reported a
    # cost per result of 101.06 against a true 14.49 — the weighted-mean
    # fallback was dominated by an awareness campaign with enormous
    # impressions and almost no results.
    "cost_per_result": "cost_per_conversion",
    "cost_per_purchase": "cost_per_conversion",

    "frequency": "frequency",

    "roas": "roas",
    "return_on_ad_spend": "roas",

    "aov": "aov",
    "average_order_value": "aov",
}

# Canonical component → the target_metric slugs an upload might use for it.
# Deliberately tight: resolving a component wrongly produces a wrong number,
# which is the exact failure this module exists to prevent. "reach" is not an
# impressions alias, "sessions" is not a clicks alias.
_COMPONENT_ALIASES: dict[str, tuple[str, ...]] = {
    "impressions": ("impressions", "impression", "impr", "imprs", "total_impressions"),
    "clicks":      ("clicks", "click", "link_clicks", "total_clicks", "all_clicks"),
    "spend":       ("spend", "ad_spend", "cost", "costs", "spent", "total_spent",
                    "total_spend", "amount_spent", "total_cost"),
    "conversions": ("conversions", "conversion", "total_conversions", "results",
                    "purchases", "result"),
    # Distinct from impressions, deliberately: reach counts people, impressions
    # count deliveries, and conflating them would silently redefine frequency.
    "reach":       ("reach", "unique_reach", "people_reached", "accounts_reached"),
    "leads":       ("leads", "lead", "form_submissions", "form_completions"),
    "revenue":     ("revenue", "total_revenue", "conversion_value", "purchase_value",
                    "sales", "gross_revenue"),
}

# When a rate has no declared components present in the upload, its rows are
# combined as a weighted mean. These are the volume columns worth weighting
# by, most preferred first.
_FALLBACK_WEIGHTS: tuple[str, ...] = (
    "impressions", "clicks", "sessions", "users", "conversions", "spend",
)

# Name fragments that mark a metric as a rate even when it is not in the
# registry — an AI-named column like "avg_time_on_page" or "traffic_percent"
# still must not be summed.
_RATE_NAME_TOKENS: tuple[str, ...] = (
    "rate", "ratio", "ctr", "cpc", "cpm", "cpa", "cpl", "roas", "roi",
    "average", "avg", "median", "per_", "per ", "position", "frequency",
    "percent", "share_of",
)


# Names for registry metrics that the component aliases do not already cover —
# chiefly the deduplicated people-counts, which are not components of anything.
_EXTRA_ALIASES: dict[str, str] = {
    "unique_clicks":      "unique_clicks",
    "unique_link_clicks": "unique_link_clicks",
    "unique_users":       "unique_users",
    "unique_reach":       "reach",
    "users":              "users",
    "unique_visitors":    "unique_users",
    "sessions":           "sessions",
    "visits":             "sessions",
}


def _build_metric_aliases() -> dict[str, str]:
    """
    One lookup from an upload's metric slug to a canonical registry name.

    Component aliases come first so "results" resolves to conversions and
    "link_clicks" to clicks; rate aliases are applied over the top because a
    name like "unique_ctr" is a rate, not a people-count.
    """
    out: dict[str, str] = {}
    for canonical, aliases in _COMPONENT_ALIASES.items():
        for alias in aliases:
            out.setdefault(alias, canonical)
    for alias, canonical in _EXTRA_ALIASES.items():
        out.setdefault(alias, canonical)
    out.update(_RATE_ALIASES)
    return out


_METRIC_ALIASES: dict[str, str] = _build_metric_aliases()


def canonical_rate(metric_key: str) -> str | None:
    """The canonical rate name for a target_metric slug, or None."""
    return _RATE_ALIASES.get((metric_key or "").strip().lower())


def canonical_metric(metric_key: str) -> str | None:
    """The canonical registry name for any metric slug, or None if unknown."""
    key = (metric_key or "").strip().lower()
    if key in METRICS:
        return key
    return _METRIC_ALIASES.get(key)


def metric_spec(metric_key: str) -> MetricSpec | None:
    """What the registry knows about this metric, if anything."""
    name = canonical_metric(metric_key)
    return METRICS.get(name) if name else None


def rate_derivation(metric_key: str) -> RateDerivation | None:
    """How this metric derives from its components, if it is a declared rate."""
    spec = metric_spec(metric_key)
    return spec.derivation if spec else None


def display_unit(metric_key: str, fallback: str) -> str:
    """
    How to write this metric, preferring the registry's declaration.

    ``fallback`` is what the mapper guessed from the column — used only for
    metrics the registry has never heard of, where an inferred unit is the
    best available answer.
    """
    spec = metric_spec(metric_key)
    return spec.display if spec else fallback


def is_deduplicated(metric_key: str) -> bool:
    """True for a count of people, which must never be summed across rows."""
    spec = metric_spec(metric_key)
    return bool(spec and spec.deduplicated)


def is_rate(metric_key: str, unit: str = "", label: str = "") -> bool:
    """
    True when this metric must not be summed.

    Three independent signals, any of which is sufficient: it is a declared
    rate, its unit is a proportion, or its name reads like a rate.
    """
    if rate_derivation(metric_key):
        return True
    if unit in ("percent", "ratio"):
        return True
    haystack = f"{metric_key} {label}".lower()
    return any(token in haystack for token in _RATE_NAME_TOKENS)


def _resolve_component(component: str, available: set[str]) -> str | None:
    """Find which of the upload's metric keys carries a canonical component."""
    for alias in _COMPONENT_ALIASES.get(component, (component,)):
        if alias in available:
            return alias
    return None


def _sum_over(values: list[float], indices: Sequence[int]) -> float | None:
    """Sum, skipping unparseable cells rather than treating them as zero."""
    picked = [
        values[i] for i in indices
        if i < len(values) and values[i] == values[i]  # NaN != NaN
    ]
    return sum(picked) if picked else None


def _weighted_mean(
    values: list[float], weights: list[float], indices: Sequence[int]
) -> float | None:
    """Mean of *values* weighted by *weights*. Rows missing either are skipped."""
    total_weight = 0.0
    total = 0.0
    for i in indices:
        if i >= len(values) or i >= len(weights):
            continue
        value, weight = values[i], weights[i]
        if value != value or weight != weight:  # NaN
            continue
        total += value * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return total / total_weight


def _unweighted_mean(values: list[float], indices: Sequence[int]) -> float | None:
    picked = [
        values[i] for i in indices
        if i < len(values) and values[i] == values[i]
    ]
    return sum(picked) / len(picked) if picked else None


def _peak_over(values: list[float], indices: Sequence[int]) -> float | None:
    """The largest single row's value. Used where summing would double-count."""
    picked = [
        values[i] for i in indices
        if i < len(values) and values[i] == values[i]
    ]
    return max(picked) if picked else None


@dataclass
class Derived:
    """One metric reduced over a set of rows, and how."""

    value: float | None
    # "sum" | "recomputed" | "weighted_mean" | "unweighted_mean" | "peak" |
    # "suppressed"
    method: str
    weighted_by: str | None = None
    detail: str = ""
    # Set when the figure is NOT a period total and must be relabelled before
    # a reader sees it — "Reach" becoming "Peak daily reach".
    basis: str | None = None


def aggregate(
    metric_keys: Sequence[str],
    units: dict[str, str],
    labels: dict[str, str],
    columns: dict[str, list[float]],
    indices: Sequence[int],
) -> dict[str, Derived]:
    """
    Reduce every mapped metric over *indices*. The only reduction in the app.

    Counts sum. Declared rates recompute from their components against the
    period totals. A rate whose components are missing falls back to a
    volume-weighted mean — never an unweighted one, which is the bug this
    replaces. A zero denominator yields None, never 0 and never infinity,
    because "no conversions this period" is not "a cost per conversion of 0".
    """
    available = set(columns)
    out: dict[str, Derived] = {}

    # Sums are needed both as answers in their own right and as the
    # components every declared rate recomputes from.
    sums: dict[str, float | None] = {
        key: _sum_over(values, indices) for key, values in columns.items()
    }

    # The weight column used when a rate cannot be recomputed. Chosen once so
    # every fallback rate in one source is weighted consistently.
    fallback_weight: str | None = None
    for preferred in _FALLBACK_WEIGHTS:
        resolved = _resolve_component(preferred, available)
        if resolved and not is_rate(resolved, units.get(resolved, ""), labels.get(resolved, "")):
            fallback_weight = resolved
            break
    if fallback_weight is None:
        # No recognised volume column: use the largest non-rate column as a
        # volume proxy rather than falling straight to an unweighted mean.
        candidates = [
            (total, key) for key, total in sums.items()
            if total is not None
            and not is_rate(key, units.get(key, ""), labels.get(key, ""))
        ]
        if candidates:
            fallback_weight = max(candidates)[1]

    # More than one row means summing a people-count would count the same
    # person once per row. One row is safe.
    multi_row = len([i for i in indices]) > 1

    for key in metric_keys:
        values = columns.get(key)
        if not values:
            continue

        # ── Deduplicated people-counts ──────────────────────────────────────
        # Reach is distinct people, and the same person is reached again
        # tomorrow. Adding 31 daily rows can overstate a month two- or
        # threefold — and it is a number the client can check against their own
        # Ads Manager, so it fails visibly and expensively. The peak day is a
        # real, verifiable figure; it is returned with a basis so the label can
        # say what it actually is before anyone reads it as a period total.
        if is_deduplicated(key):
            if multi_row:
                out[key] = Derived(
                    _peak_over(values, indices), "peak", basis="peak_daily",
                    detail="deduplicated people-count; summing would "
                           "double-count anyone reached on more than one day",
                )
            else:
                out[key] = Derived(sums.get(key), "sum")
            continue

        if not is_rate(key, units.get(key, ""), labels.get(key, "")):
            out[key] = Derived(sums.get(key), "sum")
            continue

        derivation = rate_derivation(key)

        # A rate whose denominator is a people-count has no honest period
        # value: frequency is impressions per person, and dividing a month of
        # impressions by a summed reach is dividing by a number that does not
        # mean anything. Peak-day frequency would be a different metric wearing
        # the same label, so it is withheld rather than approximated.
        if derivation and multi_row and is_deduplicated(derivation.denominator):
            out[key] = Derived(
                None, "suppressed",
                detail=f"needs {derivation.denominator}, which is deduplicated "
                       "and has no meaningful multi-day total",
            )
            continue

        if derivation:
            numerator = _resolve_component(derivation.numerator, available)
            denominator = _resolve_component(derivation.denominator, available)

            if numerator and denominator:
                num_total = _sum_over(columns[numerator], indices)
                den_total = _sum_over(columns[denominator], indices)
                if num_total is None or den_total is None:
                    out[key] = Derived(None, "recomputed",
                                       detail=f"{numerator}/{denominator} unavailable")
                elif den_total == 0:
                    # Not 0, not inf — undefined, and shown as absent.
                    out[key] = Derived(None, "recomputed",
                                       detail=f"{denominator} is zero")
                else:
                    out[key] = Derived(
                        num_total / den_total * derivation.scale,
                        "recomputed",
                        detail=f"Σ{numerator}/Σ{denominator}"
                               + (f"×{derivation.scale:g}" if derivation.scale != 1 else ""),
                    )
                continue

            if denominator:
                # Weighting the given rate by its own denominator is
                # algebraically the same answer as recomputing it, since
                # Σ(rateᵢ·denᵢ)/Σdenᵢ == Σnumᵢ/Σdenᵢ. Exact, not an estimate.
                out[key] = Derived(
                    _weighted_mean(values, columns[denominator], indices),
                    "weighted_mean",
                    weighted_by=denominator,
                    detail=f"weighted by {denominator} (its own denominator — exact)",
                )
                continue

        if fallback_weight and fallback_weight in columns:
            out[key] = Derived(
                _weighted_mean(values, columns[fallback_weight], indices),
                "weighted_mean",
                weighted_by=fallback_weight,
                detail=f"no components in upload; weighted by {fallback_weight}",
            )
        else:
            out[key] = Derived(
                _unweighted_mean(values, indices),
                "unweighted_mean",
                detail="no volume column available to weight by",
            )

    return out


def _check_registry() -> None:
    """Every alias must point at a rate that declares how it derives."""
    missing = sorted(set(_RATE_ALIASES.values()) - set(METRICS))
    if missing:
        raise RuntimeError(
            "csv_ingest.derivations: these rates are aliased but have no "
            f"registry entry: {missing}. Add them to METRICS — a rate with no "
            "derivation would silently fall back to a weighted mean."
        )

    # Every declared rate must actually declare how it derives.
    no_derivation = sorted(
        name for name in set(_RATE_ALIASES.values())
        if METRICS[name].derivation is None
    )
    if no_derivation:
        raise RuntimeError(
            "csv_ingest.derivations: these rates have a registry entry but no "
            f"numerator/denominator: {no_derivation}."
        )

    # Every metric must say how it is written. A metric that reaches a slide
    # without a declared display unit is the FREQUENCY "1.33%" defect, where a
    # multiplier was rendered as a percentage because "ratio" collapsed onto
    # "percent". Inferring it from the value cannot work — CTR scales above 1
    # and a retargeting CTR of 4.12% would read "4.12x" — so it is declared,
    # and refusing to load is how it stays declared.
    undeclared = sorted(
        name for name, spec in METRICS.items()
        if spec.display not in _VALID_DISPLAY_UNITS
    )
    if undeclared:
        raise RuntimeError(
            "csv_ingest.derivations: these metrics have no valid display unit: "
            f"{undeclared}. Declare one of {sorted(_VALID_DISPLAY_UNITS)} — "
            "percent and multiplier both arrive as 'ratio' from the model and "
            "cannot be told apart from their values."
        )

    unknown_components = sorted({
        component
        for spec in METRICS.values() if spec.derivation
        for component in (spec.derivation.numerator, spec.derivation.denominator)
        if component not in _COMPONENT_ALIASES
    })
    if unknown_components:
        raise RuntimeError(
            "csv_ingest.derivations: these components are used by a rate but "
            f"have no alias list: {unknown_components}. Add them to "
            "_COMPONENT_ALIASES so they can be resolved against real uploads."
        )

    # A metric named as a component must be resolvable to a registry entry, so
    # is_deduplicated() can answer for it — that is how frequency knows its
    # denominator is people rather than events.
    unresolvable = sorted(
        component for component in _COMPONENT_ALIASES
        if canonical_metric(component) is None
    )
    if unresolvable:
        raise RuntimeError(
            "csv_ingest.derivations: these components resolve to no METRICS "
            f"entry: {unresolvable}."
        )


_check_registry()
