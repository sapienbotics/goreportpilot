"""
Verify the REAL AI column-mapping path, including the GPT-4.1 call.

scripts/verify_csv_ingest.py deliberately stubs the mapping step so it can run
offline — which leaves the actual feature unverified. This script closes that
gap: each fixture goes through profile -> propose_mapping (real OpenAI call) ->
normalize, and every PASS condition is asserted against the result.

Requires OPENAI_API_KEY, read through the normal config path (backend/.env).
Costs roughly 5 requests of ~8k tokens each per full run.

    cd backend && python scripts/verify_csv_mapping_ai.py
    cd backend && python scripts/verify_csv_mapping_ai.py --cache-test
    cd backend && python scripts/verify_csv_mapping_ai.py --stub

--cache-test additionally exercises the saved-mapping fingerprint cache against
the live database, asserting that a repeat upload makes NO OpenAI call. That
part requires migration 020 to have been applied.

--stub replaces the model response with a recorded mapping from
tests/fixtures/csv_ingest/stub_mappings.json. This exists so the deterministic
half stays verifiable when the OpenAI account is out of credit. It is NOT a
substitute: assertions that depend on the model's judgement are reported as
UNVERIFIED rather than PASS, because a stub can only verify the code around the
model, never the model itself.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402
from services.csv_ingest import templates as mapping_store  # noqa: E402
from services.csv_ingest.mapper import propose_mapping  # noqa: E402
from services.csv_ingest.normalizer import normalize  # noqa: E402
from services.csv_ingest.profiler import profile_file  # noqa: E402
from services.csv_ingest.schema import CONFIDENCE_THRESHOLD, MappingProposal  # noqa: E402
from services.csv_parser import parse_kpi_csv  # noqa: E402

FIXTURES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "fixtures", "csv_ingest",
)

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []
UNVERIFIED: list[str] = []

# Set from --stub. When true, propose_mapping is replaced by a recorded response.
STUB_MODE = False

# ── Multi-run verification ──────────────────────────────────────────────────
# A single passing run proves the model CAN produce the right answer, not that
# it does so reliably. Running one Meta export five times showed GPT-4.1
# dropping the date column in 3 of them and picking a different entity column
# in 3 of them — neither visible from one run, and both changing what the deck
# contains. Every assertion is therefore evaluated on every run and reported by
# its distribution: N/N is a pass, anything less is UNSTABLE and named as such.
RUNS = 1
RUN_INDEX = 0
# name -> list of (passed, detail), one entry per run
RESULTS: dict[str, list[tuple[bool, str]]] = {}
_ORDER: list[str] = []
# Assertions registered through check_model(), tracked so the summary can say
# which unstable ones are the model's judgement rather than our arithmetic.
_MODEL_ASSERTIONS: set[str] = set()
# Which fixture is running, so assertion keys stay distinct across files.
CURRENT_FIXTURE = ""


def _key(name: str) -> str:
    return f"[{CURRENT_FIXTURE}] {name}" if CURRENT_FIXTURE else name


def _record(name: str, condition: bool, detail: str) -> bool:
    # Keyed by fixture as well as name: several fixtures share an assertion
    # name ("low-confidence mappings are flagged"), and merging them would let
    # a failure in one file hide inside passes from the other four.
    name = _key(name)
    if name not in RESULTS:
        RESULTS[name] = []
        _ORDER.append(name)
    RESULTS[name].append((bool(condition), detail))
    if RUN_INDEX == 0:
        # Only the first run prints, so the transcript stays readable; the
        # remaining runs are reflected in the distribution at the end.
        if condition:
            print(f"    PASS  {name}")
        else:
            print(f"    FAIL  {name}")
            if detail:
                print(f"          {detail}")
    return bool(condition)


def check(name: str, condition: bool, detail: str = "") -> bool:
    """
    A deterministic assertion — but still evaluated on every run.

    Deterministic code consuming model output is only as stable as that output,
    so these are measured too. One that varies is a finding in itself.
    """
    return _record(name, condition, detail)


def check_model(name: str, condition: bool, detail: str = "") -> bool:
    """
    An assertion about the MODEL's judgement, not about our code.

    In stub mode these are recorded as UNVERIFIED: passing them would only prove
    the fixture agrees with itself.
    """
    _MODEL_ASSERTIONS.add(_key(name))
    if STUB_MODE:
        if name not in UNVERIFIED:
            UNVERIFIED.append(name)
            print(f"    ----  {name}  (UNVERIFIED — stub mode, model not called)")
        return True
    return _record(name, condition, detail)


async def get_mapping(profile, filename: str) -> MappingProposal:
    """Real GPT-4.1 call, or the recorded stand-in under --stub."""
    if not STUB_MODE:
        return await propose_mapping(profile, filename)

    with open(os.path.join(FIXTURES, "stub_mappings.json"), encoding="utf-8") as handle:
        stubs = json.load(handle)
    payload = stubs.get(filename)
    if payload is None:
        raise SystemExit(f"no stub mapping recorded for {filename}")
    proposal = MappingProposal.model_validate(payload)
    proposal.sheet_name = profile.sheet_name
    proposal.column_fingerprint = profile.column_fingerprint
    proposal.origin = "ai"
    proposal.warnings = list(profile.warnings)
    return proposal


def load(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as handle:
        return handle.read()


def report_mapping(proposal: MappingProposal, profile) -> None:
    """Print everything the model decided, so a failure is diagnosable."""
    print(f"    table_shape:   {proposal.table_shape}")
    print(f"    source_label:  {proposal.source_label}")
    if proposal.date_column:
        print(f"    date column:   {proposal.date_column.name} "
              f"(format {proposal.date_column.format}, "
              f"conf {proposal.date_column.confidence:.2f})")
    else:
        print("    date column:   none")
    if proposal.entity_column:
        print(f"    entity column: {proposal.entity_column.name} "
              f"(conf {proposal.entity_column.confidence:.2f})")
    print("    columns:")
    for column in proposal.columns:
        flag = "  <-- NEEDS CONFIRMATION" if column.needs_confirmation else ""
        print(f"      {column.source_column:24} -> {column.target_metric:22} "
              f"{column.unit:9} {column.direction:17} conf={column.confidence:.2f}{flag}")
    if proposal.ignored_columns:
        print("    ignored:")
        for ignored in proposal.ignored_columns:
            print(f"      {ignored.name:24} ({ignored.reason})")
    if proposal.ambiguities:
        print("    ambiguities:")
        for ambiguity in proposal.ambiguities:
            print(f"      {ambiguity.column}: {ambiguity.question}")
            if ambiguity.candidates:
                print(f"        candidates: {ambiguity.candidates}")
    else:
        print("    ambiguities:   none")
    if profile.warnings:
        print(f"    profile notes: {profile.warnings}")


def report_metrics(source: dict) -> None:
    print("    normalized metrics:")
    for metric in source["metrics"]:
        print(f"      {metric['name']:24} current={metric['current_value']:<14} "
              f"previous={str(metric['previous_value']):<14} "
              f"unit={metric['unit']:9} change={metric['change']}")
    if source.get("daily"):
        print(f"    daily series:  {len(source['daily'])} points")
    if source.get("warnings"):
        print(f"    warnings:      {source['warnings']}")


def assert_no_low_confidence_auto_accepted(proposal: MappingProposal) -> None:
    """
    The server refuses to commit any mapping still below threshold. Assert the
    proposal correctly flags those rather than presenting them as settled.
    """
    low = [c.source_column for c in proposal.columns if c.needs_confirmation]
    check(
        "low-confidence mappings are flagged, not auto-accepted",
        (not low) or proposal.requires_user_input,
        f"below threshold {low} but requires_user_input is False",
    )


def assert_no_rate_summed(source: dict, profile, proposal: MappingProposal) -> None:
    """
    A rate must never exceed what averaging could produce.

    Concretely: for any percent/ratio metric, the aggregated value must sit
    within the min..max range of its own column. A summed rate lands far above
    the column maximum, which is exactly the "89% CTR" failure.
    """
    by_source_column = {c.target_metric: c.source_column for c in proposal.columns}
    column_ranges = {c.name: (c.min_value, c.max_value) for c in profile.columns}
    offenders: list[str] = []
    for metric in source["metrics"]:
        if metric["unit"] != "percent":
            continue
        source_column = by_source_column.get(metric.get("metric_key", ""))
        bounds = column_ranges.get(source_column or "")
        if not bounds or bounds[1] is None:
            continue
        low, high = bounds
        # Fraction columns are scaled x100 at normalisation time.
        scale = 100.0 if high is not None and high <= 1.0 else 1.0
        ceiling = high * scale * 1.01
        if metric["current_value"] > ceiling:
            offenders.append(
                f"{metric['name']}={metric['current_value']} exceeds column max "
                f"{high} (scaled {high * scale})"
            )
    check("no rate or percentage metric was summed", not offenders, "; ".join(offenders))


# ---------------------------------------------------------------------------
# Fixture 1 — LinkedIn, wide timeseries, US format
# ---------------------------------------------------------------------------

async def fixture_linkedin() -> None:
    print("\n[1] linkedin_ads_export.csv — wide timeseries, US format")
    raw = load("linkedin_ads_export.csv")
    profile = profile_file(raw, "linkedin_ads_export.csv")[0]
    proposal = await get_mapping(profile, "linkedin_ads_export.csv")
    report_mapping(proposal, profile)

    check_model("table_shape is wide_timeseries", proposal.table_shape == "wide_timeseries",
          f"got {proposal.table_shape}")
    check_model("date column detected",
          proposal.date_column is not None
          and proposal.date_column.name == "Start Date (in UTC)",
          str(proposal.date_column))
    check_model("date format is ISO",
          proposal.date_column is not None and proposal.date_column.format == "%Y-%m-%d",
          str(proposal.date_column.format if proposal.date_column else None))

    ctr = next((c for c in proposal.columns if c.source_column == "Click Through Rate"), None)
    check_model("CTR mapped as a percentage", ctr is not None and ctr.unit == "percent",
          str(ctr.unit if ctr else "not mapped"))

    assert_no_low_confidence_auto_accepted(proposal)

    source = normalize(profile, proposal, source_name="LinkedIn Ads")
    report_metrics(source)
    by_key = {m["metric_key"]: m for m in source["metrics"]}

    ctr_metric = by_key.get("ctr") or next(
        (m for m in source["metrics"] if "click through" in m["name"].lower()
         or m["name"].lower() == "ctr"), None,
    )
    # Sigma clicks / Sigma impressions = 1531 / 131,650 = 1.1629%.
    # The unweighted mean of the CTR column is 1.1600% and summing it gives
    # 11.60%. The old tolerance here was +/-0.02 around 1.16, which accepted
    # the recomputed and the unweighted-mean answers equally — tight enough
    # now to tell them apart.
    check("CTR recomputed from components (1.1629%), not averaged (1.1600%)",
          ctr_metric is not None and abs(ctr_metric["current_value"] - 1.1629) < 0.001,
          str(ctr_metric["current_value"] if ctr_metric else "CTR not produced"))

    impressions = by_key.get("impressions")
    check("impressions SUM over the whole period (131,650)",
          impressions is not None
          and impressions["current_value"] == 131650.0
          and impressions["first_half_value"] == 62550.0
          and impressions["second_half_value"] == 69100.0,
          str(impressions))

    clicks = by_key.get("clicks")
    check("clicks SUM over the whole period (1,531)",
          clicks is not None and clicks["current_value"] == 1531.0
          and clicks["first_half_value"] == 727.0
          and clicks["second_half_value"] == 804.0, str(clicks))

    spend = next((m for m in source["metrics"] if m["unit"] == "currency"), None)
    check("spend SUM over the whole period (2,942.20)",
          spend is not None and abs(spend["current_value"] - 2942.20) < 0.01, str(spend))

    check("no invented previous period",
          impressions is not None and impressions["previous_value"] is None,
          str(impressions))

    check("daily series produced for the trend chart",
          len(source.get("daily", [])) == 10, str(len(source.get("daily", []))))

    assert_no_rate_summed(source, profile, proposal)

    from services.chart_generator import generate_all_charts  # noqa: PLC0415
    import tempfile

    charts = generate_all_charts(
        {"client_name": "T", "period_start": "2026-07-01", "period_end": "2026-07-10",
         "csv_sources": [source]},
        tempfile.mkdtemp(), "#4338CA", "modern_clean",
    )
    check("trend chart renders", any(k.startswith("csv_") for k in charts), str(list(charts)))


# ---------------------------------------------------------------------------
# Fixture 2 — Google Ads, German locale, totals row
# ---------------------------------------------------------------------------

async def fixture_german() -> None:
    print("\n[2] google_ads_de_export.csv — German locale, semicolons, totals row")
    raw = load("google_ads_de_export.csv")
    profile = profile_file(raw, "google_ads_de_export.csv")[0]

    check("totals row detected and excluded before profiling",
          profile.totals_row_index is not None and profile.data_row_count == 5,
          f"totals_row_index={profile.totals_row_index}, rows={profile.data_row_count}")
    tag = profile.columns[0]
    check("date column survives totals-row removal",
          tag.inferred_type == "date" and tag.date_format == "%d.%m.%Y",
          f"{tag.inferred_type} / {tag.date_format}")

    proposal = await get_mapping(profile, "google_ads_de_export.csv")
    report_mapping(proposal, profile)

    check_model("date column mapped",
          proposal.date_column is not None and proposal.date_column.name == "Tag",
          str(proposal.date_column))
    assert_no_low_confidence_auto_accepted(proposal)

    source = normalize(profile, proposal, source_name="Google Ads DE")
    report_metrics(source)

    kosten = next(
        (m for m in source["metrics"]
         if "kosten" in m["name"].lower() or m.get("metric_key") in ("spend", "cost", "kosten")),
        None,
    )
    if kosten is None:
        check("Kosten mapped", False, f"metrics were {[m['name'] for m in source['metrics']]}")
    else:
        total = kosten["current_value"] + (kosten["previous_value"] or 0.0)
        check("Kosten totals 8,276.85 — dot-thousands NOT eaten (would be 827,685)",
              abs(total - 8276.85) < 0.01, f"got {total}")
        check("no Kosten value anywhere near 827,685",
              kosten["current_value"] < 100_000, str(kosten["current_value"]))

    impressionen = next(
        (m for m in source["metrics"] if "impress" in m["name"].lower()), None
    )
    if impressionen:
        total = impressionen["current_value"] + (impressionen["previous_value"] or 0)
        check("Impressionen totals 55,011 (not 55.011)", abs(total - 55011) < 1, str(total))

    check("daily series produced from German dates",
          len(source.get("daily", [])) == 5, str(len(source.get("daily", []))))
    assert_no_rate_summed(source, profile, proposal)


# ---------------------------------------------------------------------------
# Fixture 3 — Meta multi-sheet xlsx with a decoy sheet
# ---------------------------------------------------------------------------

async def fixture_meta_xlsx() -> None:
    print("\n[3] meta_ads_multisheet.xlsx — decoy sheet, fractional CTR")
    raw = load("meta_ads_multisheet.xlsx")
    profiles = profile_file(raw, "meta_ads_multisheet.xlsx")
    profile = profiles[0]

    check("real data sheet chosen over the decoy",
          profile.sheet_name == "Campaign Performance",
          f"picked {profile.sheet_name} from {[p.sheet_name for p in profiles]}")

    proposal = await get_mapping(profile, "meta_ads_multisheet.xlsx")
    report_mapping(proposal, profile)
    assert_no_low_confidence_auto_accepted(proposal)

    source = normalize(profile, proposal, source_name="Meta Ads")
    report_metrics(source)

    spend = next((m for m in source["metrics"] if m["unit"] == "currency"), None)
    if spend is None:
        check("spend mapped as currency", False,
              str([(m["name"], m["unit"]) for m in source["metrics"]]))
    else:
        total = spend["current_value"] + (spend["previous_value"] or 0)
        check("spend totals ~332,892 INR", abs(total - 332892.00) < 1.0, str(total))

    ctr = next(
        (m for m in source["metrics"]
         if "ctr" in m["name"].lower() or m.get("metric_key") == "ctr"), None
    )
    if ctr is None:
        check("CTR mapped", False, str([m["name"] for m in source["metrics"]]))
    else:
        check("CTR renders as a percentage (~0.49%), not the raw 0.0047",
              ctr["unit"] == "percent" and 0.3 < ctr["current_value"] < 0.7,
              f"unit={ctr['unit']} value={ctr['current_value']}")
        check("fraction scaling is disclosed, not silent",
              bool(source.get("warnings")), str(source.get("warnings")))

    assert_no_rate_summed(source, profile, proposal)


# ---------------------------------------------------------------------------
# Fixture 3b - Meta Ads Manager export, the full daily shape
# ---------------------------------------------------------------------------

async def fixture_meta_csv() -> None:
    """
    The real Meta export shape: a redundant date pair, currency in the header,
    CTR as a bare fraction, "Results" instead of conversions, em-dash nulls and
    a campaign/ad set/ad hierarchy.

    This file is why the multi-run harness exists. On a single run it mapped
    perfectly; across five, GPT-4.1 returned no date column in three of them
    and switched entity level in three. Both are now settled deterministically,
    and these assertions are what keeps them settled.
    """
    print("")
    print("[3b] meta_ads_export_july2026.csv - date pair, (USD) header, em-dash nulls")
    raw = load("meta_ads_export_july2026.csv")
    profile = profile_file(raw, "meta_ads_export_july2026.csv")[0]
    proposal = await get_mapping(profile, "meta_ads_export_july2026.csv")
    report_mapping(proposal, profile)

    # The instability that motivated this harness. Deliberately check() and
    # not check_model(): the date column is now decided by measurement when
    # the model declines to name one, so it must hold on every run whatever
    # the model said.
    check("a date column is resolved on every run",
          proposal.date_column is not None
          and proposal.date_column.name == "Reporting starts",
          str(proposal.date_column))
    check("entity resolves to the coarsest hierarchy level",
          proposal.entity_column is not None
          and proposal.entity_column.name == "Campaign name",
          str(proposal.entity_column))

    check_model("'Results' is questioned rather than silently mapped",
          any(a.column.strip().lower() == "results" for a in proposal.ambiguities)
          or any(c.needs_confirmation for c in proposal.columns
                 if c.source_column == "Results"),
          "Results was accepted with no question raised")

    assert_no_low_confidence_auto_accepted(proposal)

    answered = {"Results", "Cost per result (USD)"}
    for column in proposal.columns:
        if column.source_column in answered:
            column.confidence = 1.0
    proposal.ambiguities = [
        a for a in proposal.ambiguities if a.column not in answered
    ]

    source = normalize(profile, proposal, source_name="Meta Ads")
    report_metrics(source)
    by_key = {m["metric_key"]: m for m in source["metrics"]}

    check("currency read from the (USD) column header",
          source.get("currency") == "USD",
          "%r via %r" % (source.get("currency"), source.get("currency_source")))
    check("all 124 rows read despite em-dash nulls",
          source.get("row_count") == 124, str(source.get("row_count")))
    check("impressions total 6,921,544",
          by_key.get("impressions", {}).get("current_value") == 6921544.0,
          str(by_key.get("impressions")))
    check("link clicks total 74,372",
          by_key.get("clicks", {}).get("current_value") == 74372.0,
          str(by_key.get("clicks")))

    ctr = by_key.get("ctr", {}).get("current_value")
    check("CTR recomputed to 1.0745%, not the raw 0.0107 fraction",
          ctr is not None and abs(ctr - 1.0745) < 0.001, str(ctr))

    cpr = by_key.get("cost_per_result") or by_key.get("cost_per_conversion") or {}
    check("cost per result recomputed to 14.49, not weighted to 101.06",
          cpr.get("current_value") is not None
          and abs(cpr["current_value"] - 14.4927) < 0.01,
          str(cpr.get("current_value")))

    reach = next((m for m in source["metrics"] if m["metric_key"] == "reach"), None)
    check("reach is not summed across days",
          reach is not None and reach["current_value"] != 5186231.0,
          str(reach.get("current_value") if reach else "reach missing"))
    check("reach is the peak day, relabelled to say so",
          reach is not None and reach["current_value"] == 101502.0
          and reach["name"].lower().startswith("peak daily"),
          str(reach))
    check("frequency is withheld, not divided by a summed reach",
          "frequency" not in by_key, str(by_key.get("frequency")))
    check("no multiplier metric renders as a percent",
          all(m["unit"] != "percent" for m in source["metrics"]
              if m["metric_key"] in ("frequency", "roas")),
          str([(m["metric_key"], m["unit"]) for m in source["metrics"]]))

    assert_no_rate_summed(source, profile, proposal)


# ---------------------------------------------------------------------------
# Fixture 4 — Semrush, adversarial structure + ambiguous "Cost"
# ---------------------------------------------------------------------------

async def fixture_semrush() -> None:
    print("\n[4] messy_semrush_export.csv — preamble, blank rows, ambiguous Cost")
    raw = load("messy_semrush_export.csv")
    profile = profile_file(raw, "messy_semrush_export.csv")[0]

    check("header found on row 3 despite the preamble",
          profile.header_row_index == 2, str(profile.header_row_index))
    check("blank rows skipped — 6 data rows",
          profile.data_row_count == 6, str(profile.data_row_count))
    check("columns read correctly",
          [c.name for c in profile.columns]
          == ["Date", "Keyword", "Position", "Search Volume", "Traffic %", "Cost", "CPC"],
          str([c.name for c in profile.columns]))

    proposal = await get_mapping(profile, "messy_semrush_export.csv")
    report_mapping(proposal, profile)

    cost_ambiguity = any(
        a.column.strip().lower() == "cost" for a in proposal.ambiguities
    )
    cost_mapping = next(
        (c for c in proposal.columns if c.source_column == "Cost"), None
    )
    # Ask the schema whether this needs confirming rather than re-deriving
    # the comparison here. This line used to read `confidence <
    # CONFIDENCE_THRESHOLD`, a second copy of the boundary that kept saying
    # "fine" after the real one was tightened to `<=` — so the test reported a
    # failure that the code had already fixed.
    cost_low_confidence = (
        cost_mapping is not None and cost_mapping.needs_confirmation
    )
    check_model(
        "'Cost' is questioned rather than silently mapped",
        cost_ambiguity or cost_low_confidence,
        f"ambiguity={cost_ambiguity}, "
        f"confidence={cost_mapping.confidence if cost_mapping else 'unmapped'} "
        "— it was accepted at high confidence with no question raised",
    )
    assert_no_low_confidence_auto_accepted(proposal)

    check("blocked from committing until the user resolves it",
          proposal.requires_user_input,
          "requires_user_input is False, so Confirm would be enabled")


# ---------------------------------------------------------------------------
# Fixture 5 — legacy KPI regression guard
# ---------------------------------------------------------------------------

async def fixture_legacy() -> None:
    print("\n[5] legacy_kpi_format.csv — regression guard vs parse_kpi_csv")
    raw = load("legacy_kpi_format.csv")
    profile = profile_file(raw, "legacy_kpi_format.csv")[0]
    proposal = await get_mapping(profile, "legacy_kpi_format.csv")
    report_mapping(proposal, profile)

    check_model("recognised as a long-KPI table",
          proposal.table_shape == "long_kpi", f"got {proposal.table_shape}")

    source = normalize(profile, proposal, source_name="Legacy KPIs")
    report_metrics(source)

    legacy = parse_kpi_csv(raw, "legacy_kpi_format.csv")
    print("    parse_kpi_csv (reference):")
    for metric in legacy["metrics"]:
        print(f"      {metric['name']:24} current={metric['current_value']:<14} "
              f"previous={str(metric['previous_value']):<14} "
              f"unit={metric['unit']:9} change={metric['change']}")

    new_by_name = {m["name"]: m for m in source["metrics"]}
    check("same metric count", len(source["metrics"]) == len(legacy["metrics"]),
          f"{len(source['metrics'])} vs {len(legacy['metrics'])}")

    mismatches: list[str] = []
    compared_fields = ("current_value", "previous_value", "unit", "change")
    for reference in legacy["metrics"]:
        fresh = new_by_name.get(reference["name"])
        if fresh is None:
            mismatches.append(f"missing {reference['name']!r}")
            continue
        for field in compared_fields:
            if fresh[field] != reference[field]:
                mismatches.append(
                    f"{reference['name']}.{field}: {fresh[field]!r} != {reference[field]!r}"
                )
    check("every value identical to parse_kpi_csv", not mismatches, "; ".join(mismatches))

    extra = sorted(set(source["metrics"][0]) - set(legacy["metrics"][0]))
    print(f"    (new path adds non-conflicting keys: {extra})")


# ---------------------------------------------------------------------------
# Fingerprint cache — asserts a repeat upload makes NO OpenAI call
# ---------------------------------------------------------------------------

async def fixture_cache() -> None:
    print("\n[6] fingerprint cache — repeat upload must make NO OpenAI call")
    from services.supabase_client import get_supabase_admin  # noqa: PLC0415

    supabase = get_supabase_admin()

    client_result = (
        supabase.table("clients").select("id,user_id,name").limit(1).execute()
    )
    if not client_result.data:
        check("a client exists to scope the mapping to", False,
              "no rows in clients — cannot exercise persistence")
        return
    client = client_result.data[0]
    client_id, user_id = client["id"], client["user_id"]
    print(f"    using client {client['name']!r} ({client_id})")

    raw = load("linkedin_ads_export.csv")
    profile = profile_file(raw, "linkedin_ads_export.csv")[0]
    fingerprint = profile.column_fingerprint

    # First pass — real call, then persist the confirmed mapping.
    proposal = await get_mapping(profile, "linkedin_ads_export.csv")
    for column in proposal.columns:
        column.confidence = 1.0
    saved = mapping_store.save(
        supabase, user_id=user_id, client_id=client_id,
        name="verify: LinkedIn monthly export",
        fingerprint=fingerprint, proposal=proposal,
    )
    check("mapping persisted to csv_mappings", bool(saved), str(saved)[:200])

    # Second pass — the OpenAI client is replaced with a tripwire. Any call
    # fails the test rather than quietly costing money.
    calls = {"count": 0}

    class Tripwire:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                async def create(*args, **kwargs):
                    calls["count"] += 1
                    raise AssertionError("OpenAI was called on a cache hit")

    import services.csv_ingest.mapper as mapper_module  # noqa: PLC0415

    original = mapper_module._client
    mapper_module._client = Tripwire()
    try:
        row = mapping_store.find_by_fingerprint(
            supabase, user_id=user_id, client_id=client_id, fingerprint=fingerprint
        )
        check("saved mapping found by column fingerprint", row is not None,
              f"fingerprint {fingerprint} not found")
        if row:
            replayed = mapping_store.load_proposal(row)
            check("stored mapping rehydrates", replayed is not None)
            check("replayed mapping is marked as reused, not AI",
                  replayed is not None and replayed.origin == "saved_template",
                  str(replayed.origin if replayed else None))
            if replayed:
                source = normalize(profile, replayed, source_name="LinkedIn Ads")
                check("replayed mapping still normalizes correctly",
                      len(source["metrics"]) == len(proposal.columns),
                      f"{len(source['metrics'])} vs {len(proposal.columns)}")
        check("NO OpenAI call on the repeat upload", calls["count"] == 0,
              f"{calls['count']} calls made")
    finally:
        mapper_module._client = original
        if saved:
            try:
                supabase.table("csv_mappings").delete().eq(
                    "column_fingerprint", fingerprint
                ).eq("client_id", client_id).execute()
                print("    cleaned up the test mapping row")
            except Exception as exc:  # noqa: BLE001
                print(f"    WARNING: could not clean up test mapping: {exc}")


# ---------------------------------------------------------------------------

async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-test", action="store_true",
                        help="also exercise saved-mapping persistence against the live DB")
    parser.add_argument("--stub", action="store_true",
                        help="use recorded mappings instead of calling GPT-4.1")
    parser.add_argument("--runs", type=int, default=5,
                        help="how many times to run each assertion "
                             "(default 5; a single run proves an answer is "
                             "possible, not that it is reliable)")
    args = parser.parse_args()

    global STUB_MODE
    STUB_MODE = args.stub

    if not settings.OPENAI_API_KEY:
        print("OPENAI_API_KEY is not set — cannot verify the AI mapping path.")
        return 2

    if not STUB_MODE:
        # Preflight. Without it a dead account produces five cascading failures
        # that read like mapping bugs instead of one clear external cause.
        reachable, why = await _preflight()
        if not reachable:
            print("PREFLIGHT FAILED — the model was never called.")
            print(f"  {why}")
            print()
            print("  This is an account/billing state, not a code fault: the API key")
            print("  authenticates fine, the account has no credit.")
            print("  Re-run once credits are restored:")
            print("      python scripts/verify_csv_mapping_ai.py")
            print("  To verify the deterministic half meanwhile:")
            print("      python scripts/verify_csv_mapping_ai.py --stub")
            return 2

    mode = "RECORDED STUB — model NOT called" if STUB_MODE else "real GPT-4.1 calls"
    print(f"AI column-mapping verification ({mode})")
    print("=" * 72)
    print(f"confidence threshold: {CONFIDENCE_THRESHOLD}")

    global RUNS, RUN_INDEX, CURRENT_FIXTURE
    RUNS = 1 if STUB_MODE else max(1, args.runs)
    print("runs per assertion:   %d%s" % (
        RUNS, "" if RUNS > 1 else "  (single run - proves possible, not reliable)"))

    for index in range(RUNS):
        RUN_INDEX = index
        if index:
            print("")
            print("--- repeat run %d/%d (stability check) ---" % (index + 1, RUNS))
        for _label, _fixture in (
            ("linkedin", fixture_linkedin),
            ("google_ads_de", fixture_german),
            ("meta_xlsx", fixture_meta_xlsx),
            ("meta_csv", fixture_meta_csv),
            ("semrush", fixture_semrush),
            ("legacy_kpi", fixture_legacy),
        ):
            CURRENT_FIXTURE = _label
            await _fixture()
        CURRENT_FIXTURE = ""
    if args.cache_test:
        RUN_INDEX = 0
        await fixture_cache()

    # -- Verdict by distribution ------------------------------------------
    stable_pass: list[str] = []
    stable_fail: list[tuple[str, str]] = []
    unstable: list[tuple[str, int, int, str]] = []
    for name in _ORDER:
        outcomes = RESULTS[name]
        passes = sum(1 for ok, _ in outcomes if ok)
        total = len(outcomes)
        if passes == total:
            stable_pass.append(name)
        elif passes == 0:
            stable_fail.append((name, outcomes[0][1]))
        else:
            failing = next(d for ok, d in outcomes if not ok)
            unstable.append((name, passes, total, failing))

    PASSED.extend(stable_pass)
    FAILED.extend(stable_fail)

    print("")
    print("=" * 72)
    summary = "%d passed, %d failed" % (len(stable_pass), len(stable_fail))
    if unstable:
        summary += ", %d UNSTABLE" % len(unstable)
    if UNVERIFIED:
        summary += ", %d UNVERIFIED (stub mode)" % len(UNVERIFIED)
    print(summary + "   (each assertion run %dx)" % RUNS)

    for name, detail in stable_fail:
        print("  FAILED: %s" % name)
        if detail:
            print("          %s" % detail)

    if unstable:
        print("")
        print("  UNSTABLE - passed on some runs and not others. The mapper")
        print("  does not reliably produce these; one run would hide it:")
        for name, passes, total, detail in unstable:
            kind = ("model judgement" if name in _MODEL_ASSERTIONS
                    else "derived from model output")
            print("    %d/%d  %s   [%s]" % (passes, total, name, kind))
            if detail:
                print("           e.g. %s" % detail)

    if UNVERIFIED:
        print("")
        print("  These depend on the model judgement and were NOT verified.")
        print("  A stub cannot check them - re-run without --stub:")
        for name in UNVERIFIED:
            print("    - %s" % name)

    # An unstable assertion is a failure: what ships depends on the reliable
    # answer, not the achievable one.
    return 1 if (stable_fail or unstable) else 0


async def _preflight() -> tuple[bool, str]:
    """Confirm the model is reachable before running five fixtures against it."""
    from openai import AsyncOpenAI  # noqa: PLC0415

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        await client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {str(exc)[:240]}"


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
