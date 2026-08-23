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

So every rate declares what it is made of, here, once. ``RATE_DERIVATIONS``
is that declaration, and ``aggregate`` below is the only place any metric is
reduced over a set of rows — used both for the period totals and for the
per-entity breakdown, so the two cannot drift apart. They previously did:
the period aggregate averaged rates while the entity breakdown summed them,
which is how a per-campaign conversion rate of 178.8% became possible.

Adding a rate metric means adding a line to ``RATE_DERIVATIONS``. The
import-time check at the bottom of this file refuses to load if an alias
points at a rate with no declared derivation.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RateDerivation:
    """A ratio metric expressed as numerator / denominator × scale."""

    numerator: str
    denominator: str
    scale: float = 1.0


# ── The registry ────────────────────────────────────────────────────────────
# Keyed by canonical rate name. Numerator/denominator name *canonical
# components*, resolved against whatever the upload actually calls them by
# _COMPONENT_ALIASES below.
RATE_DERIVATIONS: dict[str, RateDerivation] = {
    "ctr":                 RateDerivation("clicks",      "impressions", 100.0),
    "cpc":                 RateDerivation("spend",       "clicks"),
    "cpm":                 RateDerivation("spend",       "impressions", 1000.0),
    "conversion_rate":     RateDerivation("conversions", "clicks",      100.0),
    "cost_per_conversion": RateDerivation("spend",       "conversions"),
    "cost_per_lead":       RateDerivation("spend",       "leads"),
    "roas":                RateDerivation("revenue",     "spend"),
    "aov":                 RateDerivation("revenue",     "conversions"),
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
                    "purchases"),
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


def canonical_rate(metric_key: str) -> str | None:
    """The canonical rate name for a target_metric slug, or None."""
    return _RATE_ALIASES.get((metric_key or "").strip().lower())


def rate_derivation(metric_key: str) -> RateDerivation | None:
    """How this metric derives from its components, if it is a declared rate."""
    name = canonical_rate(metric_key)
    return RATE_DERIVATIONS.get(name) if name else None


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


@dataclass
class Derived:
    """One metric reduced over a set of rows, and how."""

    value: float | None
    # "sum" | "recomputed" | "weighted_mean" | "unweighted_mean"
    method: str
    weighted_by: str | None = None
    detail: str = ""


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

    for key in metric_keys:
        values = columns.get(key)
        if not values:
            continue

        if not is_rate(key, units.get(key, ""), labels.get(key, "")):
            out[key] = Derived(sums.get(key), "sum")
            continue

        derivation = rate_derivation(key)

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
    missing = sorted(set(_RATE_ALIASES.values()) - set(RATE_DERIVATIONS))
    if missing:
        raise RuntimeError(
            "csv_ingest.derivations: these rates are aliased but have no "
            f"declared numerator/denominator: {missing}. Add them to "
            "RATE_DERIVATIONS — a rate with no derivation would silently fall "
            "back to a weighted mean."
        )
    unknown_components = sorted({
        component
        for derivation in RATE_DERIVATIONS.values()
        for component in (derivation.numerator, derivation.denominator)
        if component not in _COMPONENT_ALIASES
    })
    if unknown_components:
        raise RuntimeError(
            "csv_ingest.derivations: these components are used by a rate but "
            f"have no alias list: {unknown_components}. Add them to "
            "_COMPONENT_ALIASES so they can be resolved against real uploads."
        )


_check_registry()
