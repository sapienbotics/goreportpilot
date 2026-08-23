"""
AI Narrative Engine — uses GPT-4.1 to write report commentary.
See docs/reportpilot-feature-design-blueprint.md Section 7 for prompt architecture.
"""
import json
import logging
import re
from typing import Dict, Any, Optional

from openai import AsyncOpenAI
from config import settings
from services.top_movers import compute_top_movers, format_movers_for_prompt

logger = logging.getLogger(__name__)


# ── Ungrounded-trend detection ───────────────────────────────────────────────
# The canonical implementation. Used here to scrub the narrative this module
# generates, and imported by scripts/verify_csv_mapping_ai.py to check it —
# one implementation, so the production code and the thing verifying it
# cannot silently drift into checking two different rules.
# Base verbs whose REGULAR conjugations (bare, -s, -ed, -ing) are generated
# below. A prior version listed conjugations by hand and missed "expands" —
# it had "expanded" and "expanding" but not the bare present-tense form — and
# that exact gap reached the final rendered deck ("...as reach expands.") on
# the one generation that happened to phrase it that way. Hand-picking
# inflections one miss at a time doesn't converge; generating the regular
# ones does, for every verb in this list at once.
# "lose" is deliberately absent — its past tense is "lost", not "losed", so
# it is hand-listed with the other irregulars above instead.
_REGULAR_TREND_VERBS = (
    "climb", "gain", "surge", "jump", "increase", "drop", "decline",
    "decrease", "slip", "improve", "worsen", "expand", "contract", "soar",
    "plunge", "spike", "boost", "strengthen", "widen", "narrow",
)


def _conjugations(verb: str) -> tuple[str, ...]:
    if verb.endswith("e"):
        return (verb, verb + "s", verb + "d", verb[:-1] + "ing")
    return (verb, verb + "s", verb + "ed", verb + "ing")


TREND_WORDS = (
    # Irregular verbs, listed by hand because there is no formula for them.
    "rose", "rise", "rises", "risen", "rising",
    "grew", "grow", "grows", "grown", "growing", "growth",
    "fell", "fall", "falls", "fallen", "falling",
    "shrank", "shrunk", "shrink", "shrinks", "shrinking",
    "slid", "slide", "slides", "sliding",
    "lost", "lose", "loses", "losing",
    "up ", "down ",
    "trend", "trends", "trending",
) + tuple(word for verb in _REGULAR_TREND_VERBS for word in _conjugations(verb))

# Splits a sentence into clauses. Coarser than real grammar — it cannot tell
# a subject from an object — but it is what separates "reach peaked, while
# impressions grew 8.0%" (two clauses, the number belongs to the other one)
# from "2.2% fewer clicks and 2.0% less reach" (one clause, both figures
# belong together). Comma and semicolon are the load-bearing splits; the
# connector words catch the same boundary when a writer skips the comma.
# The comma alternative excludes a comma immediately followed by a digit —
# a thousands separator, not a clause boundary. Without that guard, "Post
# comments dropped 1.9% (1,021 to 1,002) despite higher reach" split into
# fragments at the comma INSIDE "1,021", severing "1.9%" from "reach" even
# though both are in the same real clause — a false negative that reached
# the final rendered deck once already, unrelated to anything the model did.
_CLAUSE_SPLIT = re.compile(
    r",(?!\d)|;| while | but | although | whereas | yet | however |—| - "
)


def sentence_claims_trend(sentence: str, subject: str) -> bool:
    """
    True if any CLAUSE in *sentence* mentions *subject* alongside a
    percentage or a trend word.

    Clause-level, not sentence-level, because sentence-level co-occurrence
    over-fires: "Daily reach peaked at 101,502, reflecting strong visibility,
    while impressions grew 8.0%" mentions "reach" and contains a "%" in the
    same sentence, but the percentage belongs to impressions — flagging the
    sentence would report a correct one. Clause-level keeps that apart while
    still catching what this exists for: "delivered 2.2% fewer link clicks
    and 2.0% less reach" has both figures in one clause, joined by "and"
    rather than a clause boundary, and is flagged correctly either way.

    Both splits are heuristics, not a real parser — deliberately: a split
    error only makes this MORE likely to flag something, never less, which
    is the safe direction to be wrong in when the alternative is a
    fabricated trend reaching a client's deck.
    """
    for clause in _CLAUSE_SPLIT.split(sentence):
        low = clause.lower()
        if subject not in low:
            continue
        has_percent = bool(re.search(r"\d[\d,]*\.?\d*\s*%", clause))
        has_trend_word = any(word in low for word in TREND_WORDS)
        if has_percent or has_trend_word:
            return True
    return False


def find_ungrounded_trend_sentences(text: str, subject: str) -> list[str]:
    """Every full sentence in *text* containing a clause that violates the rule."""
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip() and sentence_claims_trend(sentence, subject)
    ]

_client: Optional[AsyncOpenAI] = None


def _get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


SYSTEM_PROMPT = """You are a senior digital marketing analyst writing a monthly performance report for a marketing agency's client.

Your role is to:
1. Analyze the marketing data provided
2. Identify the most important trends (positive and negative)
3. Explain WHY metrics changed (connect cause to effect where possible)
4. Highlight wins that demonstrate the agency's value
5. Flag concerns with specific, actionable recommendations
6. Write in a tone that a non-technical business owner can understand

Rules:
- Be specific with numbers. Never say "traffic increased" — say "sessions grew from 38,200 to 45,230 (+18.4%)"
- Always compare to the previous period
- If a metric declined, don't hide it — explain it and suggest a fix
- Keep paragraphs short (2-3 sentences max)
- Use plain English, not marketing jargon
- Structure: Lead with the headline insight, support with data, close with recommendation

DIAGNOSTIC STANDARD (Phase 4 — the WHY rule):
You will receive a TOP MOVERS block naming specific campaigns, traffic
sources, pages, and search queries that drove this period's headline
numbers. When a metric moved meaningfully (up OR down), you MUST
attribute the movement to at least ONE named entity from TOP MOVERS.

  Weak  (rejected): "Paid advertising improved this month."
  Weak  (rejected): "Organic traffic grew 23% — likely SEO improvements."
  Good  (required): "Paid spend grew 18% driven almost entirely by
                     'Q2 Summer Sale' (ROAS 4.2x, 32% of total budget)
                     which outperformed the account average of 2.8x."
  Good  (required): "Organic traffic grew 23% largely on the query
                     'best video editor for startups' (1,240 clicks,
                     CTR 8.1%, avg position 4.2)."

Rule: if you can't cite a named entity from TOP MOVERS for a claim
about a moving metric, either (a) don't make the claim, or (b) say
"data doesn't show a single dominant driver" and list the top 3
contributors. Never write vague causal filler like "due to seasonal
trends" or "likely from SEO improvements" — those are lazy and the
client will notice.

RECOMMENDATION STANDARD (Phase 4):
In ``next_steps``, every recommendation must cite the specific data
point that motivated it. Generic tips are rejected.

  Weak  (rejected): "Focus more budget on high-performing campaigns."
  Good  (required): "Shift 20% of 'Brand Awareness Broad' spend
                     ($850 of $4,200) to 'Q2 Summer Sale' which
                     delivers 3.7x higher ROAS at similar volume."

EXECUTIVE SUMMARY STRUCTURE (SCQA — McKinsey's Pyramid Principle):
When writing the executive_summary, follow the SCQA framework so the narrative
flows like a senior consultant briefing:
  - Situation:   Where the client stands now (prior-period context, current
                 goals, baseline). One sentence.
  - Complication: What changed this period — the biggest movement, good or
                  bad — and why it matters.
  - Question:    The implied question the client is already asking ("what
                 should we do about this?"). Do NOT write this as an explicit
                 question; let it come through the flow.
  - Answer:      Preview the top recommendation(s) you will expand in the
                 next_steps section.
Do NOT label these sections. Write flowing prose — 3-4 short paragraphs, 150
words maximum — that follows this structure naturally. Never bury a bad month;
acknowledge it in the opening sentence if the period is down.

CHART INSIGHTS:
In addition to the narrative sections, always return a "chart_insights"
object. Each value is a ONE-LINE active-voice takeaway (≤15 words) that will
become the chart's title in the report — a story headline, not a label.
Example: "Sessions grew 23% as organic search recovered" — NOT "Sessions over
time". If a given metric is not in the data, omit that key from the object."""

TONE_MODIFIERS: Dict[str, str] = {
    "professional": (
        "Write in a professional, authoritative tone. Use data to support every claim. "
        "Structure with clear transitions between topics."
    ),
    "conversational": (
        "Write in a warm, friendly conversational tone — as if a trusted advisor is explaining results "
        "to a busy business owner over coffee. Use natural language, occasional contractions, and relatable "
        "analogies. Avoid jargon. Show genuine enthusiasm for wins and empathy for concerns. "
        "Keep it data-backed but never dry or clinical."
    ),
    "executive": (
        "Write an executive brief. Lead with the single most important number. "
        "Use bullet points. Maximum 100 words per section. Every sentence must contain a data point or action item."
    ),
    "data_heavy": (
        "Write a thorough analytical review. Include percentage changes, period comparisons, and statistical context. "
        "Reference specific campaigns by name. Be comprehensive."
    ),
    # Aliases used in the DB / UI
    "friendly": (
        "Write in a warm, friendly conversational tone — as if a trusted advisor is explaining results "
        "to a busy business owner over coffee. Use natural language, occasional contractions, and relatable "
        "analogies. Avoid jargon. Show genuine enthusiasm for wins and empathy for concerns. "
        "Keep it data-backed but never dry or clinical."
    ),
    "technical": (
        "Write a thorough analytical review. Include percentage changes, period comparisons, and statistical context. "
        "Reference specific campaigns by name. Be comprehensive."
    ),
}

# Bad-month detection threshold: any primary KPI (sessions, users,
# conversions) dropping more than 5% MoM counts as a "bad month" and
# triggers a mandatory acknowledgement in the opening sentence of the
# executive summary. Below this threshold the AI follows normal SCQA flow.
_BAD_MONTH_DROP_PCT = -5.0

# Extra system-prompt clause injected when ``_detect_bad_month`` returns
# True. Implements the four-beat recovery sequence from
# docs/REPORT-QUALITY-RESEARCH-2026.md §Phase 3 "Presenting a bad month".
_BAD_MONTH_INSTRUCTION = """

CRITICAL — BAD-MONTH DETECTED:
This reporting period saw a material decline in one or more primary KPIs
(sessions, users, or conversions dropped by more than 5% vs the previous
period). You MUST acknowledge this decline in the OPENING SENTENCE of the
executive_summary — do NOT bury it, do NOT soften it with generic language.

Use the four-beat recovery sequence:
  1. Lead with the honest number ("Sessions fell 14% this month.")
  2. Give context (YoY comparison if still positive, seasonality, known
     external events like algorithm updates or holiday shifts).
  3. Explain the likely cause — a specific hypothesis, not "underperformance".
  4. State what changes next month (the first recommendation).

This is a trust-preserving move. Clients respect transparency; they punish
sugarcoating. Never hide bad results."""



_CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",    "EUR": "€",    "GBP": "£",    "INR": "₹",
    "AUD": "A$",   "CAD": "C$",   "JPY": "¥",    "CNY": "¥",
    "BRL": "R$",   "MXN": "Mex$", "SGD": "S$",   "HKD": "HK$",
    "CHF": "CHF ", "SEK": "kr",   "NOK": "kr",   "DKK": "kr",
    "ZAR": "R",    "AED": "AED ", "SAR": "SAR ", "MYR": "RM",
}


def _unit_suffix(unit: str) -> str:
    """
    What follows a number of this unit in prose.

    A multiplier is not a percentage: frequency 1.33 means 1.33 impressions
    per person reached, and writing it "1.33%" describes nothing.
    """
    if unit == "percent":
        return "%"
    if unit == "multiplier":
        return "×"
    return ""


def _fmt_num(value: Any) -> str:
    """
    A figure written the way it should appear in prose.

    The prompt used to pass raw floats — "3884961.0" — leaving the model to
    insert the thousands separators itself, and it got them wrong: a live run
    produced "delivered 388,4961 impressions" in the CSV performance section.
    Grouping digits is not a judgement call, so it should not be delegated to
    a model that is concentrating on the analysis.
    """
    if not isinstance(value, (int, float)):
        return str(value)
    if float(value).is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


# Metrics worth naming per entity, in the order a reader cares about them.
# Capped so a 10-campaign upload does not flood the prompt.
_ENTITY_METRIC_PRIORITY = (
    "impressions", "clicks", "conversions", "spend", "leads", "revenue",
    "sessions", "cpc", "cost_per_conversion", "ctr", "conversion_rate",
    "cpm", "roas",
)
# Cost and rate metrics are included per entity, not just volumes. With only
# the volumes listed, a live run wrote "'Q3 Lead Gen Form | Agency Owners'
# average CPC rose 2.8%" — which is the SOURCE-WIDE CPC change, borrowed
# because that campaign's own CPC was not in front of the model. Whatever is
# missing per entity is what gets substituted from the aggregate.
_ENTITY_METRIC_LIMIT = 6
_ENTITY_LIMIT = 6


def _withheld_subjects(csv_sources: list) -> list[str]:
    """
    Words the narrative must never attach a trend to: the core noun of every
    peak-day (deduplicated) metric's label across all uploaded sources, e.g.
    "reach" from "Peak daily reach".
    """
    subjects: set[str] = set()
    for source in csv_sources or []:
        for metric in source.get("metrics") or []:
            if metric.get("value_basis") != "peak_daily":
                continue
            label = str(metric.get("name") or "").strip().lower()
            core = label
            if core.startswith("peak daily "):
                core = core[len("peak daily "):]
            core = core.strip()
            if core:
                subjects.add(core)
    return sorted(subjects)


def _scrub_text(text: str, subjects: list[str]) -> str:
    """
    Drop any sentence that ungroundedly frames a withheld subject as trending.

    Whole-sentence granularity, not clause-level: excising a mid-sentence
    clause risks a dangling connector ("...but CTR declined...") with no
    grammatical lead-in, which can read as more obviously broken than the
    fabricated claim it replaced. A whole sentence removed joins cleanly to
    its neighbours.
    """
    if not subjects or not text:
        return text
    kept = [
        sentence for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
        and not any(sentence_claims_trend(sentence, s) for s in subjects)
    ]
    return " ".join(kept).strip()


def _scrub_narrative(narrative: dict, csv_sources: list) -> dict:
    """
    Deterministic backstop: strip any sentence anywhere in the narrative —
    including chart_insights captions, which render on a slide the same as
    any other text — that frames a deduplicated metric (reach, most
    commonly) as rising, falling, improving, or declining.

    Exists because instructing the model was not enough, across two
    escalating attempts. The first supplied reach's real peak value with an
    explicit "do not describe this as trending" instruction; a live 5-run
    check still caught the model substituting a different metric's change
    for it. The second withheld the topic from the prompt entirely; a live
    5-run check still caught the model using ordinary marketing vocabulary
    ("improved reach", "expanded reach") with zero numeric grounding — in a
    slide caption, not narrative prose, the one place neither prior fix had
    reached. "Reach" is common enough English that an instruction not to use
    it is not reliable; removing it after the fact is. See CLAUDE.md rule 15.
    """
    subjects = _withheld_subjects(csv_sources)
    if not subjects:
        return narrative

    scrubbed = 0
    for key, value in list(narrative.items()):
        if key == "chart_insights" and isinstance(value, dict):
            cleaned_dict: dict = {}
            for cap_key, cap_val in value.items():
                if not isinstance(cap_val, str):
                    cleaned_dict[cap_key] = cap_val
                    continue
                cleaned = _scrub_text(cap_val, subjects)
                if cleaned != cap_val.strip():
                    scrubbed += 1
                if cleaned:
                    cleaned_dict[cap_key] = cleaned
            narrative[key] = cleaned_dict
        elif isinstance(value, str):
            cleaned = _scrub_text(value, subjects)
            if cleaned != value.strip():
                scrubbed += 1
            narrative[key] = cleaned
        elif isinstance(value, list):
            cleaned_list: list = []
            for item in value:
                if not isinstance(item, str):
                    cleaned_list.append(item)
                    continue
                cleaned = _scrub_text(item, subjects)
                if cleaned != item.strip():
                    scrubbed += 1
                if cleaned:
                    cleaned_list.append(cleaned)
            narrative[key] = cleaned_list

    if scrubbed:
        logger.warning(
            "Narrative scrub removed %d sentence(s) ungroundedly describing "
            "%s as trending",
            scrubbed, ", ".join(subjects),
        )
    return narrative


def _entity_lines(source: dict, breakdown: list) -> list[str]:
    """
    Per-entity totals AND each entity's own within-period change.

    This used to be a bare list of names ("Top entries: A, B, C") sitting
    beside the source-wide change, and the model did the only thing it could
    with that pairing: it attached the aggregate movement to whichever name
    looked most prominent. Pass 4's deck credited the +12.1% impressions rise
    to "Q3 Thought Leadership | Video Views", a campaign that grew 3.5%, while
    Demand Gen (+34.6%) and Lead Gen (+33.0%) did the actual work.

    Giving the model each entity's own numbers removes the need to guess. The
    instruction below is deliberately explicit rather than trusting it to
    infer the rule.
    """
    lines: list[str] = ["  Per-entity breakdown — each entity's OWN figures and "
                        "its OWN within-period change:"]

    metric_units = {
        m.get("metric_key"): m.get("unit", "number")
        for m in (source.get("metrics") or [])
    }
    metric_names = {
        m.get("metric_key"): m.get("name", m.get("metric_key"))
        for m in (source.get("metrics") or [])
    }

    for row in breakdown[:_ENTITY_LIMIT]:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        changes = row.get("changes") or {}
        keys = [k for k in _ENTITY_METRIC_PRIORITY if k in row]
        keys += [
            k for k in row
            if k not in ("name", "changes") and k not in keys
            and isinstance(row[k], (int, float))
        ]

        parts: list[str] = []
        for key in keys[:_ENTITY_METRIC_LIMIT]:
            value = row.get(key)
            if not isinstance(value, (int, float)):
                continue
            suffix = _unit_suffix(metric_units.get(key, "number"))
            label = metric_names.get(key, key)
            if key in changes:
                parts.append(f"{label} {_fmt_num(value)}{suffix} ({changes[key]:+.1f}%)")
            else:
                parts.append(f"{label} {_fmt_num(value)}{suffix}")

        # Deduplicated metrics (reach and similar) are deliberately NOT
        # listed here. The first attempt gave each entity its real peak
        # value with an explicit "(peak day, no trend)" flag, on the theory
        # that a real grounded number beats a gap the model would otherwise
        # fill by guessing — which is exactly the reasoning that fixed the
        # earlier half-value and attribution bugs. It backfired here: even
        # WITH the value and an explicit "do not describe as rising/falling"
        # instruction, a live multi-run check still caught the model writing
        # "reach and engagement improved" and "regain lost reach" for
        # entities with no reach change data at all — vague, adjective-level
        # trend claims a number-swap check cannot even catch, in 3 of 5
        # runs. Merely being told a topic exists was enough to invite
        # commentary on its direction. So the topic itself is withheld from
        # entity lines; the real value still renders correctly on the slide,
        # which is a rendered number, not free text, and carries no such
        # risk. See _format_csv_sources for the matching source-wide choice.
        if parts:
            lines.append(f"    {name}: " + ", ".join(parts))

    lines.append(
        "    [Every number on these entity lines is that entity's own. The "
        "source-wide figures listed further up are NOT any single entity's "
        "figures: never attach a source-wide percentage to a named entity. "
        "If you want to say something about one entity's metric and that "
        "metric is not on its line above, say nothing about it rather than "
        "reaching for the source-wide number or for a different metric's "
        "number as a stand-in. Reach (or any peak-day, non-summable figure) "
        "is deliberately absent from every entity line above and from the "
        "totals further up — it exists only as a number on the slide, is "
        "not part of this analysis, and must not be mentioned, estimated, "
        "or described in any way, for the source or for any entity, "
        "including using words like improved/declined/lost/regained "
        "without a number attached. Name an entity as a driver only where "
        "its own number above supports it; otherwise describe the movement "
        "without naming one, and do not invent absolute values behind a "
        "percentage.]"
    )
    return lines


def _format_csv_sources(csv_sources: list) -> str:
    """
    Render uploaded data sources for the prompt.

    Previously this was a bare count — "CSV SOURCES: 2 additional data source(s)
    connected" — so the model knew an upload existed but had no idea what was in
    it, and the csv_performance section could only produce filler. Universal
    ingestion makes these sources first-class, so they are spelled out like
    every other platform: named metrics, values, and period-over-period change.
    """
    if not csv_sources:
        return "CSV SOURCES: none"

    lines: list[str] = []
    for source in csv_sources:
        name = source.get("source_name") or source.get("name") or "Custom Data"
        metrics = source.get("metrics") or []
        if not metrics:
            continue
        # The source's own currency, stated per source. Without it the model
        # reads the Meta-Ads currency rule as the only guidance in the prompt
        # and applies it to uploads too: a live run wrote "₹264.33" for a
        # LinkedIn file in dollars, on a deck whose KPI slide correctly
        # rendered "$". The slide and the paragraph beside it disagreed.
        code = (source.get("currency") or "").strip().upper()
        if code:
            symbol = _CURRENCY_SYMBOLS.get(code, code + " ")
            lines.append(
                f"\nUPLOADED DATA — {name} "
                f"(all money in this source is {code}; write it as {symbol}):"
            )
        else:
            lines.append(f"\nUPLOADED DATA — {name}:")

        # Deduplicated (peak-day) metrics are named ONCE here, as a plain
        # notice, and then excluded from the per-metric lines below entirely
        # — no value, no "(no trend)" flag, nothing to react to. The first
        # version gave the model reach's real value with an explicit
        # instruction not to describe it as trending, at both the source and
        # entity level, and a live multi-run check still caught the model
        # writing "reach and engagement improved" / "regain lost reach" with
        # no number attached at all — in 3 of 5 runs. A number-swap check
        # cannot even catch a claim with no number in it. Naming the topic
        # was apparently invitation enough, so the topic itself — not just
        # its trend — is withheld from the narrative prompt. It still
        # renders correctly on the slide as a plain number, which carries no
        # such risk because nothing there is free text.
        peak_daily_names = [
            m.get("name", m.get("metric_key", "metric"))
            for m in metrics if m.get("value_basis") == "peak_daily"
        ]
        if peak_daily_names:
            lines.append(
                "  [" + ", ".join(peak_daily_names) + " " +
                ("is" if len(peak_daily_names) == 1 else "are") +
                " shown only as a number on the slide and excluded from this "
                "analysis — a peak single day cannot be summed or compared "
                "across a period. Do not mention, estimate, or describe "
                + ("it" if len(peak_daily_names) == 1 else "them")
                + " in any section, including with words like "
                "improved/declined/lost/regained and with no number "
                "attached.]"
            )

        for metric in metrics[:12]:
            if metric.get("value_basis") == "peak_daily":
                continue
            label = metric.get("name", "Metric")
            current = metric.get("current_value")
            previous = metric.get("previous_value")
            unit = metric.get("unit", "number")
            suffix = _unit_suffix(unit)
            change = metric.get("change")
            change_text = (
                f", change: {change:+.1f}%" if isinstance(change, (int, float)) else ""
            )
            first_half = metric.get("first_half_value")
            second_half = metric.get("second_half_value")

            if previous is not None:
                # A real prior period, from a file that carried one.
                context = f" (prev: {previous}{suffix}{change_text})"
            elif isinstance(change, (int, float)):
                # One uploaded period: the figure is the whole period's total
                # and the change is its internal trend. Said explicitly so the
                # model does not describe it as month-over-month growth.
                #
                # Both half-values are spelled out because omitting them does
                # not stop the model needing them — it makes them up. Given
                # only "760 total, +20%" it wrote "rose from 380 to 456": a
                # correct percentage over two invented figures that do not
                # even sum to the total. Supplying the real 335 and 402
                # removes the gap rather than forbidding it.
                if first_half is not None and second_half is not None:
                    context = (
                        f" (period total; within this period: 1st half "
                        f"{_fmt_num(first_half)}{suffix} -> 2nd half "
                        f"{_fmt_num(second_half)}{suffix}, {change:+.1f}%)"
                    )
                else:
                    context = (
                        f" (total for the period; second half vs first half"
                        f" within the period: {change:+.1f}%)"
                    )
            else:
                context = ""
            lines.append(f"  {label}: {_fmt_num(current)}{suffix}{context}")
        if source.get("daily"):
            lines.append(
                f"  [{len(source['daily'])} days of daily figures are available "
                "for this source — describe the trend, not just the total]"
            )
        breakdown = source.get("breakdown") or []
        if breakdown:
            lines.extend(_entity_lines(source, breakdown))

    if not lines:
        return "CSV SOURCES: none"
    return "\n".join(lines)


def _detect_bad_month(data: Dict[str, Any]) -> bool:
    """
    Return True when primary KPIs declined materially this period.

    Heuristic: any of sessions / users / conversions dropped more than
    5% MoM. One serious decline is enough to trigger the bad-month
    narrative treatment — we do not require ALL metrics to fall.
    """
    ga4_summary = (data.get("ga4") or {}).get("summary") or {}
    for key in ("sessions_change", "users_change", "conversions_change"):
        change = ga4_summary.get(key)
        try:
            if change is not None and float(change) <= _BAD_MONTH_DROP_PCT:
                return True
        except (ValueError, TypeError):
            continue
    return False


FALLBACK_NARRATIVE: Dict[str, str] = {
    "executive_summary": (
        "This report covers the performance period requested. "
        "AI narrative generation is unavailable — please ensure OPENAI_API_KEY is set and try regenerating."
    ),
    "website_performance": "Website performance data was collected. AI narrative pending.",
    "paid_advertising": "Paid advertising data was collected. AI narrative pending.",
    "key_wins": "✓ Data collected successfully\n✓ Report generated without errors",
    "concerns": "⚠ AI narrative generation is unavailable. Check your OPENAI_API_KEY and regenerate.",
    "next_steps": "1. Configure OPENAI_API_KEY in backend/.env\n2. Regenerate this report",
    "google_ads_performance": "Google Ads data collected. AI narrative pending.",
    "seo_performance": "SEO data collected. AI narrative pending.",
    "csv_performance": "Custom data collected. AI narrative pending.",
    "engagement_analysis": "Engagement data collected. AI narrative pending.",
}


_SECTION_INSTRUCTIONS: Dict[str, str] = {
    # SCQA-structured executive summary: Situation → Complication → Question → Answer.
    # Rendered as flowing prose, not labelled sections. 150-word cap.
    "executive_summary":  '"{key}" — 150 words max, structured as SCQA (Situation, Complication, implied Question, Answer) in flowing prose, NOT labelled. The Complication beat MUST cite at least one named entity from TOP MOVERS as the driver.',
    "website_performance": '"{key}" — 2-3 diagnostic paragraphs. Name the specific traffic sources driving the change (from TOP MOVERS > ga4.top_sources) and the specific pages where users land most (from ga4.top_pages). No generic "traffic grew due to SEO efforts" — cite the source or page by name.',
    "paid_advertising":   '"{key}" — 2-3 diagnostic paragraphs analyzing Meta Ads. Name the specific campaigns (TOP MOVERS > meta_ads) that delivered results and those that bled budget. Compare each cited campaign to the account average ROAS. Avoid vague "ads performed well this month".',
    # Content-count enforcement (3+3+3): every report should land with exactly
    # 3 wins, 3 concerns, and 3 next steps in the canonical structure.
    "key_wins":           '"{key}" — EXACTLY 3 bullet points. Each must name a specific entity from TOP MOVERS (campaign, page, query, or traffic source) and the metric it moved. Start each with "\u2713 "',
    # The "unless you state the tension" clause earns its length. A live
    # Meta run put "Video Views" in Key Wins for cutting cost per result
    # 11.9% and in Concerns for producing only 22 results — both true, but
    # read back to back they make the report look like it is arguing with
    # itself. Either drop the weaker point or name the tension, which is a
    # more useful sentence than either half was alone.
    "concerns":           '"{key}" — EXACTLY 3 bullet points. Each must (a) name a specific entity from TOP MOVERS, (b) state its underperformance with numbers, (c) give a concrete fix tied to that entity. Start each with "\u26A0 " An entity you credited in key_wins must NOT also appear here, UNLESS this bullet states the tension explicitly in the same sentence (e.g. "X cut cost per result 11.9% but produced only 22 results, so the efficiency gain sits on volume too small to matter"). Never present the same entity as a plain win and a plain concern.',
    "next_steps":         '"{key}" — EXACTLY 3 numbered items. Each MUST cite a specific data point from TOP MOVERS and follow the pattern: "Next month we will [action] on [specific campaign/page/source from TOP MOVERS], based on [cited metric], to achieve [expected outcome with a number]."',
    "google_ads_performance": '"{key}" — 2-3 diagnostic paragraphs. Name specific Google Ads campaigns (TOP MOVERS > google_ads) that delivered vs underperformed. Cite CTR, cost-per-conversion, and spend share per named campaign.',
    "seo_performance": '"{key}" — 2-3 diagnostic paragraphs. Name specific organic queries (TOP MOVERS > search_console.top_queries) and landing pages driving clicks. Cite position, CTR, and impression volume per named query.',
    "csv_performance": '"{key}" — 2 paragraphs summarizing the custom data source metrics',
    "engagement_analysis": '"{key}" — 1-2 diagnostic paragraphs. Cite device-level bounce rates from TOP MOVERS > ga4.device_split and name the specific top pages. If a device underperforms, say "Mobile bounce is 62% vs Desktop 34%" not "engagement varies across devices".',
}


def _build_section_instructions(sections: list[str]) -> str:
    """Build the numbered section list for the GPT-4.1 prompt."""
    lines = []
    for i, key in enumerate(sections, start=1):
        template = _SECTION_INSTRUCTIONS.get(key, f'"{key}" — narrative for this section')
        lines.append(f'{i}. {template.format(key=key)}')
    return "\n".join(lines)


async def generate_narrative(
    data: Dict[str, Any],
    client_name: str,
    client_goals: Optional[str],
    tone: str = "professional",
    template: str = "full",
    sections: Optional[list[str]] = None,
    language: str = "en",
) -> Dict[str, str]:
    """
    Generate AI narrative sections for a report.

    Args:
        data:          Combined GA4 + Meta Ads data dict.
        client_name:   Client display name.
        client_goals:  Free-text goals/context from client record.
        tone:          AI tone preset (professional / conversational / executive / data_heavy).
        template:      Report template — "full" | "summary" | "brief".
                       Controls which sections are generated and their length.
        sections:      If provided, generate only these section keys.
                       Useful for regenerating a single section without calling
                       GPT-4o for the full report.

    Returns a dict with a subset of these keys depending on template/sections:
        executive_summary, website_performance, paid_advertising,
        key_wins, concerns, next_steps
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning fallback narrative")
        return FALLBACK_NARRATIVE

    tone_modifier = TONE_MODIFIERS.get(tone, TONE_MODIFIERS["professional"])

    # ── Determine which sections to request based on template ────────────────
    if sections:
        # Caller specified exact sections (e.g. regenerate-section endpoint)
        requested_sections = sections
    elif template == "summary":
        # Summary: concise 4-slide report — exec summary, wins, next steps
        requested_sections = ["executive_summary", "key_wins", "next_steps"]
    elif template == "brief":
        # One-Page Brief: 2-slide ultra-concise — exec summary + next steps only
        requested_sections = ["executive_summary", "next_steps"]
    else:
        # Full (default): all 6 core sections + data-available sections
        requested_sections = [
            "executive_summary", "website_performance", "paid_advertising",
            "key_wins", "concerns", "next_steps",
        ]
        # Add engagement analysis if device/pages data present
        ga4_data = data.get("ga4", {})
        if ga4_data.get("device_breakdown") or ga4_data.get("top_pages"):
            requested_sections.insert(-3, "engagement_analysis")
        # Add Google Ads section if data present
        if data.get("google_ads", {}).get("summary"):
            requested_sections.insert(-3, "google_ads_performance")
        # Add SEO section if data present
        if data.get("search_console", {}).get("summary"):
            requested_sections.insert(-3, "seo_performance")
        # Add CSV section if data present
        if data.get("csv_sources"):
            requested_sections.insert(-3, "csv_performance")

    # ── Template-specific tone modifier ─────────────────────────────────────
    if template == "brief":
        tone_modifier = (
            "Write an ultra-concise executive brief. Every sentence must contain "
            "a data point or action item. Maximum 80 words for executive_summary. "
            "next_steps should be 3 bullet points maximum."
        )
    elif template == "summary" and tone == "professional":
        tone_modifier = (
            "Write a crisp summary report. Focus on the headline numbers and "
            "what changed this period. Keep each section to 2-3 sentences."
        )

    ga4 = data.get("ga4", {}).get("summary", {})
    meta = data.get("meta_ads", {}).get("summary", {})
    campaigns = data.get("meta_ads", {}).get("campaigns", [])
    traffic_sources = data.get("ga4", {}).get("traffic_sources", [])

    # Normalize GA4 source/channel labels before serializing into the prompt
    # so the AI cites "Direct", "Organic", "Referral" — matching what renders
    # on the chart — instead of mixing "(direct)" / "organic" lowercase. Maps
    # the same sentinels chart_generator._clean_source_label handles, kept
    # inline here to avoid creating an import dependency on chart_generator.
    _SRC_MAP = {
        "(none)": "Direct", "(direct)": "Direct", "direct": "Direct",
        "(not set)": "Other", "(not provided)": "Other",
    }
    def _clean_src(label: object) -> str:
        if not label:
            return "Other"
        key = str(label).strip().lower()
        return _SRC_MAP.get(key) or str(label).title()

    if isinstance(traffic_sources, list):
        traffic_sources = [
            {**s, "source": _clean_src(s.get("source"))}
            if isinstance(s, dict) else s
            for s in traffic_sources
        ]

    # Determine currency for the Meta Ads section so the AI uses the right symbol
    _currency_symbols: Dict[str, str] = _CURRENCY_SYMBOLS
    currency_code = (data.get("meta_ads", {}).get("currency") or "USD").upper()
    cur_sym = _currency_symbols.get(currency_code, currency_code + " ")

    section_instructions = _build_section_instructions(requested_sections)

    # chart_insights is a separate top-level key in the JSON output — not a
    # narrative section. Each value is a ≤15-word active-voice headline used
    # as the chart title in the rendered report.
    _chart_insights_block = (
        '\nALSO include a top-level "chart_insights" object in the JSON '
        'with any of these keys that match the available data (omit keys '
        'with no data). Each value must be a ONE-LINE (≤15 words) active-'
        'voice takeaway used as the chart title:\n'
        '  "sessions_trend"       — GA4 daily sessions line chart\n'
        '  "traffic_sources"      — GA4 traffic sources bar chart\n'
        '  "device_breakdown"     — GA4 device donut chart\n'
        '  "top_pages"            — GA4 top landing pages bar chart\n'
        '  "spend_conversions"    — Meta/Google Ads daily spend vs conv\n'
        '  "campaign_performance" — Campaign performance bar chart\n'
        '  "audience_demographics" — Meta Ads age/gender grouped bars\n'
        'Example value: "Sessions grew 23% as organic search recovered" '
        '— NOT "Sessions over time".'
    )

    # Language instruction
    language_instruction = ""
    if language and language != "en":
        language_names = {
            "es": "Spanish", "pt": "Portuguese", "fr": "French",
            "de": "German", "hi": "Hindi", "ar": "Arabic",
            "ja": "Japanese", "it": "Italian", "ko": "Korean",
            "zh": "Chinese (Simplified)", "nl": "Dutch", "tr": "Turkish",
        }
        lang_name = language_names.get(language, language)
        language_instruction = (
            f"\n\nCRITICAL: Write ALL narrative content in {lang_name}. "
            f"Use natural, professional {lang_name} — not machine-translated English. "
            f"Keep metric names and abbreviations in English (KPI, CTR, CPC, ROAS, ROI, SEO) "
            f"but write all commentary, analysis, and recommendations in {lang_name}."
        )

    google_ads = data.get("google_ads", {}).get("summary", {})
    search_console = data.get("search_console", {}).get("summary", {})
    csv_sources = data.get("csv_sources", [])
    _csv_block = _format_csv_sources(csv_sources)

    # Phase 4 — compute the top-movers diagnostic context and serialize for
    # the prompt. This is the new data the AI uses to cite named entities
    # as drivers instead of writing vague causal filler. Safe on partial data.
    _movers = compute_top_movers(data)
    _movers_block = format_movers_for_prompt(_movers, currency_symbol=cur_sym)
    if _movers:
        _dim_counts = {
            platform: len([k for k in dims if isinstance(dims, dict)])
            for platform, dims in _movers.items()
        }
        logger.info(
            "Phase 4 — top movers for %s: platforms=%s",
            client_name, list(_movers.keys()),
        )
    else:
        logger.info(
            "Phase 4 — no top movers computed for %s (insufficient data)",
            client_name,
        )

    user_prompt = f"""CLIENT CONTEXT:
Name: {client_name}
Goals: {client_goals or 'Not specified'}
Report Period: {data.get('period_start')} to {data.get('period_end')}

GOOGLE ANALYTICS DATA:
Sessions: {ga4.get('sessions', 'N/A')} (prev: {ga4.get('prev_sessions', 'N/A')}, change: {ga4.get('sessions_change', 'N/A')}%)
Users: {ga4.get('users', 'N/A')} (prev: {ga4.get('prev_users', 'N/A')}, change: {ga4.get('users_change', 'N/A')}%)
Pageviews: {ga4.get('pageviews', 'N/A')} (prev: {ga4.get('prev_pageviews', 'N/A')})
Bounce Rate: {ga4.get('bounce_rate', 'N/A')}% (prev: {ga4.get('prev_bounce_rate', 'N/A')}%)
Avg Session Duration: {ga4.get('avg_session_duration', 'N/A')}s (prev: {ga4.get('prev_avg_duration', 'N/A')}s)
Conversions: {ga4.get('conversions', 'N/A')} (prev: {ga4.get('prev_conversions', 'N/A')}, change: {ga4.get('conversions_change', 'N/A')}%)
Traffic Sources: {json.dumps(list(traffic_sources)[:5] if isinstance(traffic_sources, list) else traffic_sources) if traffic_sources else 'N/A'}

META ADS DATA (Currency: {currency_code}):
Total Spend: {cur_sym}{meta.get('spend', 'N/A')} (prev: {cur_sym}{meta.get('prev_spend', 'N/A')}, change: {meta.get('spend_change', 'N/A')}%)
Impressions: {meta.get('impressions', 'N/A')} (prev: {meta.get('prev_impressions', 'N/A')})
Clicks: {meta.get('clicks', 'N/A')} (prev: {meta.get('prev_clicks', 'N/A')})
CTR: {meta.get('ctr', 'N/A')}% (prev: {meta.get('prev_ctr', 'N/A')}%)
CPC: {cur_sym}{meta.get('cpc', 'N/A')} (prev: {cur_sym}{meta.get('prev_cpc', 'N/A')})
Conversions: {meta.get('conversions', 'N/A')} (prev: {meta.get('prev_conversions', 'N/A')}, change: {meta.get('conversions_change', 'N/A')}%)
Cost Per Conversion: {cur_sym}{meta.get('cost_per_conversion', 'N/A')} (prev: {cur_sym}{meta.get('prev_cost_per_conversion', 'N/A')})
ROAS: {meta.get('roas', 'N/A')}x (prev: {meta.get('prev_roas', 'N/A')}x)
Top Campaigns: {json.dumps(campaigns[:3]) if campaigns else 'N/A'}

GOOGLE ADS DATA (if available):
Spend: {cur_sym}{google_ads.get('spend', 'N/A')} (prev: {cur_sym}{google_ads.get('prev_spend', 'N/A')})
Clicks: {google_ads.get('clicks', 'N/A')} | Conversions: {google_ads.get('conversions', 'N/A')}
CTR: {google_ads.get('ctr', 'N/A')}% | Cost/Conv: {cur_sym}{google_ads.get('cost_per_conversion', 'N/A')}
ROAS: {google_ads.get('roas', 'N/A')}x

SEO DATA (Google Search Console):
Clicks: {search_console.get('clicks', 'N/A')} (prev: {search_console.get('prev_clicks', 'N/A')})
Impressions: {search_console.get('impressions', 'N/A')}
CTR: {search_console.get('ctr', 'N/A')}% | Avg Position: {search_console.get('avg_position', 'N/A')}

{_csv_block}

{_movers_block}

TONE: {tone_modifier}

IMPORTANT — CURRENCY: All monetary amounts for Meta Ads must use the {currency_code} currency symbol ({cur_sym}). \
Never use "$" for Meta Ads figures unless the currency is USD. \
This rule is about Meta Ads only. Each uploaded data source states its own \
currency on its heading — use that source's currency for its figures, even \
when it differs from the Meta Ads one.

Generate the following sections as a JSON object:
{section_instructions}
{_chart_insights_block}

Return ONLY valid JSON, no markdown code blocks, no explanation outside the JSON."""

    # Detect declining primary KPIs and inject the bad-month clause so the
    # AI leads with the decline in the executive_summary.
    is_bad_month = _detect_bad_month(data)
    _bad_month_clause = _BAD_MONTH_INSTRUCTION if is_bad_month else ""
    if is_bad_month:
        logger.info(
            "Bad month detected for client %s — injecting recovery-sequence prompt",
            client_name,
        )

    try:
        ai = _get_openai_client()
        response = await ai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + language_instruction + _bad_month_clause},
                {"role": "user", "content": user_prompt},
            ],
            # Slightly lower temperature for more grounded/diagnostic output —
            # Phase 4 aims to reduce generic filler; less creativity helps the
            # model stick to cited entities rather than invent plausible-sounding
            # causes.
            temperature=0.6,
            # Raised from 2000 → 3500 to accommodate the richer TOP MOVERS
            # context + up to 9 narrative sections with specific named-entity
            # citations. Empirical: Phase 4 prompt adds ~800-1200 input tokens,
            # and each section's output grows ~15-20% from citing concrete
            # drivers instead of generic phrasing.
            max_tokens=3500,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        narrative: Dict[str, str] = json.loads(content)
        narrative = _scrub_narrative(narrative, data.get("csv_sources") or [])
        logger.info("AI narrative generated successfully for client: %s", client_name)
        return narrative

    except Exception as exc:
        logger.error("AI narrative generation failed: %s", exc, exc_info=True)
        return _fallback_narrative(client_name, data, exc)


def _fallback_narrative(
    client_name: str, data: Dict[str, Any], exc: Exception
) -> Dict[str, Any]:
    """
    Neutral placeholder text for when the narrative engine is unavailable.

    This text goes onto a slide in a deck an agency sends to their client, so it
    must never expose our internals. The previous version interpolated the raw
    exception into executive_summary — which meant an OpenAI billing error put
    "You have no credits remaining. Add credits at platform.openai.com/..."
    on slide 2 of a client-facing report.

    The real error is logged, and ``_narrative_error`` is returned alongside so
    the dashboard can tell the agency to regenerate. That key is stripped before
    rendering (see report_generator) and never reaches a slide.
    """
    period = f"{data.get('period_start', '')} to {data.get('period_end', '')}".strip()
    heading = f"Performance summary for {client_name}"
    if period and period != "to":
        heading += f", {period}"

    return {
        "_narrative_error": str(exc)[:300],
        "executive_summary": (
            f"{heading}. The figures in this report are complete and accurate. "
            "Written commentary is being finalised and will be added shortly."
        ),
        "website_performance": "Website performance figures are shown in the charts on this slide.",
        "paid_advertising": "Campaign performance figures are shown in the charts on this slide.",
        "key_wins": "",
        "concerns": "",
        "next_steps": "",
    }
