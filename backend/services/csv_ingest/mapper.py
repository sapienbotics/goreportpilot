"""
AI column mapping.

Sends a bounded column profile to GPT-4.1 and gets back a proposed mapping,
validated against services.csv_ingest.schema before anything downstream sees it.

Cost characteristics: one call per *new* export format. Once a mapping is
confirmed it is fingerprinted and reused, so a client uploading the same
LinkedIn export every month pays for exactly one call, ever.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from openai import AsyncOpenAI
from pydantic import ValidationError

from config import settings
from services.csv_ingest.profiler import TableProfile
from services.csv_ingest.schema import (
    MAPPING_JSON_SCHEMA,
    Ambiguity,
    ColumnMapping,
    DateColumn,
    IgnoredColumn,
    MappingProposal,
)

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None

_MODEL = "gpt-4.1"
_MAX_ATTEMPTS = 2       # one retry when the model violates the schema


def _get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


SYSTEM_PROMPT = """You map columns from a marketing data export onto a reporting schema.

You will be given a COLUMN PROFILE: for each column, its header, inferred type, \
how many values are filled, how many are distinct, and up to 8 sample values \
drawn from the start, middle, and end of the file.

Your job is CLASSIFICATION ONLY. Name what each column is. Do not compute, \
convert, reformat, or infer any value. The application parses every number \
itself.

Decide first what shape the table is:
- "long_kpi"        one row per metric, with the value in another column \
(e.g. columns: Metric | Value | Previous)
- "wide_timeseries" one row per date, one column per metric \
(e.g. columns: Day | Impressions | Clicks | Spend)
- "wide_entity"     one row per campaign/ad/page/product, one column per metric \
(e.g. columns: Campaign | Impressions | Clicks | Spend)
- "unknown"         you genuinely cannot tell

Then, for every column that holds a METRIC, emit a mapping with:
- target_metric: a snake_case canonical name. Prefer these standard names when \
the column clearly means one of them: impressions, clicks, ctr, cpc, cpm, spend, \
cost_per_conversion, conversions, conversion_rate, revenue, roas, sessions, \
users, pageviews, bounce_rate, engagement_rate, reach, frequency, video_views, \
opens, open_rate, unsubscribes, orders, average_order_value, calls, leads, \
cost_per_lead. Otherwise invent a clear snake_case name from the header.
- label: how it should read on a slide, in title case (e.g. "Cost per Lead")
- unit: currency | percent | ratio | duration | number
- direction: higher_is_better, or lower_is_better for costs, bounce rate, \
unsubscribes, CPA/CPC/CPM and similar
- confidence: 0.0-1.0, honest. Use 0.8 or lower whenever the header is vague, \
abbreviated, or could plausibly mean more than one thing; above 0.8 means you \
are sure enough that no human needs to check it.
- reasoning: one short clause

Also identify:
- date_column: the column holding the time dimension, if any
- entity_column: the column naming the campaign / page / product, if any
- ignored_columns: columns that carry no reportable metric (IDs, currency codes, \
account names, status flags, constant metadata) with a one-clause reason

Raise an ambiguity — do not guess — when a column could mean materially \
different things. "Cost" that might be ad spend or might be cost of goods, \
"Value" with no other context, "Conv." that could be conversions or conversion \
rate. Ask a plain-English question a marketer can answer in one click.

Rules:
- Never map the same source column twice.
- Only reference column names exactly as given in the profile.
- A column of IDs or a column with one distinct value is not a metric.
- If the table is long_kpi, map the value-bearing columns \
(target_metric "current_value" / "previous_value") rather than every row.
- Be honest with confidence. A wrong mapping accepted silently puts a wrong \
number in front of someone's client."""


def build_user_prompt(profile: TableProfile, filename: str) -> str:
    """Render the bounded profile the model reasons over."""
    payload = {
        "filename": filename,
        "table": profile.for_prompt(),
    }
    if profile.warnings:
        payload["structural_notes"] = profile.warnings

    return (
        "Map this export. Respond with JSON matching exactly this schema:\n"
        f"{json.dumps(MAPPING_JSON_SCHEMA)}\n\n"
        "COLUMN PROFILE:\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}"
    )


async def propose_mapping(
    profile: TableProfile,
    filename: str,
    *,
    source_label_hint: str = "",
) -> MappingProposal:
    """
    Ask GPT-4.1 to map *profile*.

    Never raises on a model failure: an unusable response degrades to an empty
    proposal carrying a warning, which the UI renders as the manual mapping
    screen. The user always has a way through.
    """
    client = _get_openai_client()
    user_prompt = build_user_prompt(profile, filename)
    last_error = ""

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        if attempt > 1 and last_error:
            messages.append({
                "role": "user",
                "content": (
                    "Your previous response did not match the schema: "
                    f"{last_error}\nRespond again with valid JSON only."
                ),
            })

        try:
            response = await client.chat.completions.create(
                model=_MODEL,
                messages=messages,
                temperature=0.1,          # classification, not composition
                response_format={"type": "json_object"},
                max_tokens=3000,
            )
            raw = response.choices[0].message.content or "{}"
            proposal = MappingProposal.model_validate(json.loads(raw))
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)[:500]
            logger.warning(
                "Mapping proposal failed schema validation (attempt %d/%d): %s",
                attempt, _MAX_ATTEMPTS, last_error,
            )
            continue
        except Exception as exc:  # noqa: BLE001
            logger.exception("Mapping call to OpenAI failed")
            return _empty_proposal(
                profile,
                warning=(
                    "The automatic column mapper is unavailable right now "
                    f"({exc}). Map the columns manually below — your data is fine."
                ),
            )

        return _finalise(proposal, profile, source_label_hint)

    return _empty_proposal(
        profile,
        warning=(
            "We could not automatically work out what the columns in this file "
            "mean. Map them manually below — nothing is wrong with your file."
        ),
    )


def _finalise(
    proposal: MappingProposal,
    profile: TableProfile,
    source_label_hint: str,
) -> MappingProposal:
    """
    Reconcile the model's answer with what the profiler actually measured.

    The profiler is authoritative on anything measurable. Where the model
    disagrees with measured fact, the measurement wins and the disagreement is
    surfaced rather than silently resolved.
    """
    known = {c.name: c for c in profile.columns}

    # Drop hallucinated columns and de-duplicate.
    seen: set[str] = set()
    kept: list[ColumnMapping] = []
    for mapping in proposal.columns:
        if mapping.source_column not in known:
            logger.info(
                "Dropping mapping for unknown column %r", mapping.source_column
            )
            continue
        if mapping.source_column in seen:
            continue
        seen.add(mapping.source_column)

        column = known[mapping.source_column]

        # Measured units beat guessed ones.
        if column.has_percent_sign and mapping.unit == "number":
            mapping.unit = "percent"
        elif column.has_currency_symbol and mapping.unit == "number":
            mapping.unit = "currency"

        # A column the profiler read as text cannot carry a numeric metric.
        if column.inferred_type in ("text", "date", "empty"):
            proposal.ignored_columns.append(
                IgnoredColumn(
                    name=mapping.source_column,
                    reason=f"holds {column.inferred_type} values, not numbers",
                )
            )
            continue

        if not mapping.label:
            mapping.label = mapping.source_column
        kept.append(mapping)

    proposal.columns = kept

    # The profiler's date-format detection is measured against the whole
    # column; the model only saw eight samples. Trust the measurement.
    if proposal.date_column and proposal.date_column.name in known:
        detected = known[proposal.date_column.name].date_format
        if detected:
            proposal.date_column.format = detected
        elif known[proposal.date_column.name].inferred_type != "date":
            proposal.ambiguities.append(
                Ambiguity(
                    column=proposal.date_column.name,
                    question=(
                        f"We could not read '{proposal.date_column.name}' as dates. "
                        "Is it the date column, and what format are the dates in?"
                    ),
                )
            )
            proposal.date_column = None
    elif proposal.date_column:
        proposal.date_column = None

    # A date column whose day/month order could not be settled from the data is
    # a confirmation question, not a silent guess — getting it wrong scrambles
    # an entire time series.
    if proposal.date_column and proposal.date_column.format in (
        "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
    ):
        column = known[proposal.date_column.name]
        if not _day_month_settled(column.samples, proposal.date_column.format):
            proposal.ambiguities.append(
                Ambiguity(
                    column=proposal.date_column.name,
                    candidates=["day/month/year", "month/day/year"],
                    question=(
                        f"Dates like '{column.samples[0] if column.samples else ''}' "
                        "could be day/month or month/day. Which is it?"
                    ),
                )
            )

    # Recover a time dimension the model declined to name.
    #
    # Meta's export heads its date pair "Reporting starts" / "Reporting ends",
    # which reads like report metadata — the window the report covers — rather
    # than a per-row dimension, and at account level that is exactly what it
    # is. On a daily breakdown it is the day. GPT-4.1 cannot tell those apart
    # from eight samples and returned no date column in 3 of 5 live runs on the
    # same file, taking the trend chart, every change badge and all trend
    # language in the narrative with it — the deck still rendered, just flat,
    # with nothing to indicate anything was missing.
    #
    # The profiler already measured what the model was guessing at: whether a
    # date column's values actually VARY. A column of 31 distinct dates across
    # 124 rows is a time dimension whatever its header says. Deciding that is
    # measurement, not classification, so it belongs here and not in a prompt.
    if proposal.date_column is None:
        candidates = [
            column for column in profile.columns
            if column.inferred_type == "date"
            and column.date_format
            and column.distinct_count > 1
        ]
        if candidates:
            # Most distinct values wins: on a start/end pair the two are
            # usually identical, and where they differ the finer-grained one
            # is the real dimension. Ties fall to the leftmost column, which
            # is the "starts" side of every export that carries a pair.
            chosen = min(candidates, key=lambda c: (-c.distinct_count, c.index))
            proposal.date_column = DateColumn(
                name=chosen.name, format=chosen.date_format, confidence=0.75
            )
            proposal.ignored_columns = [
                ignored for ignored in proposal.ignored_columns
                if ignored.name != chosen.name
            ]
            logger.info(
                "Model named no date column; using measured date column %r "
                "(%d distinct values, format %s)",
                chosen.name, chosen.distinct_count, chosen.date_format,
            )

    if proposal.entity_column and proposal.entity_column.name not in known:
        proposal.entity_column = None

    proposal.sheet_name = profile.sheet_name
    proposal.column_fingerprint = profile.column_fingerprint
    proposal.origin = "ai"
    proposal.warnings = list(profile.warnings)
    if source_label_hint and proposal.source_label in ("", "Custom Data"):
        proposal.source_label = source_label_hint

    if not proposal.columns:
        proposal.warnings.append(
            "We found columns but none of them looked like a metric we can "
            "chart. Pick the ones you want below."
        )
    return proposal


def _day_month_settled(samples: list[str], fmt: str) -> bool:
    """True when some sample proves which component is the day."""
    separator = "/" if "/" in fmt else "-"
    for raw in samples:
        parts = raw.split(separator)
        if len(parts) < 2:
            continue
        try:
            if int(parts[0]) > 12 or int(parts[1]) > 12:
                return True
        except ValueError:
            continue
    return False


def _empty_proposal(profile: TableProfile, *, warning: str) -> MappingProposal:
    """A proposal that maps nothing but carries enough context for manual mapping."""
    return MappingProposal(
        table_shape="unknown",
        source_label="Custom Data",
        columns=[],
        sheet_name=profile.sheet_name,
        column_fingerprint=profile.column_fingerprint,
        origin="manual",
        warnings=[*profile.warnings, warning],
    )
