"""
AI Narrative Engine — uses GPT-4.1 to write report commentary.
See docs/reportpilot-feature-design-blueprint.md Section 7 for prompt architecture.
"""
import json
import logging
from typing import Dict, Any, Optional

from openai import AsyncOpenAI
from config import settings
from services.top_movers import compute_top_movers, format_movers_for_prompt

logger = logging.getLogger(__name__)

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
    "concerns":           '"{key}" — EXACTLY 3 bullet points. Each must (a) name a specific entity from TOP MOVERS, (b) state its underperformance with numbers, (c) give a concrete fix tied to that entity. Start each with "\u26A0 "',
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
    _currency_symbols: Dict[str, str] = {
        "USD": "$",    "EUR": "€",    "GBP": "£",    "INR": "₹",
        "AUD": "A$",   "CAD": "C$",   "JPY": "¥",    "CNY": "¥",
        "BRL": "R$",   "MXN": "Mex$", "SGD": "S$",   "HKD": "HK$",
        "CHF": "CHF ", "SEK": "kr",   "NOK": "kr",   "DKK": "kr",
        "ZAR": "R",    "AED": "AED ", "SAR": "SAR ",  "MYR": "RM",
    }
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

CSV SOURCES: {len(csv_sources)} additional data source(s) connected

{_movers_block}

TONE: {tone_modifier}

IMPORTANT — CURRENCY: All monetary amounts for Meta Ads must use the {currency_code} currency symbol ({cur_sym}). \
Never use "$" for Meta Ads figures unless the currency is USD.

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
        logger.info("AI narrative generated successfully for client: %s", client_name)
        return narrative

    except Exception as exc:
        logger.error("AI narrative generation failed: %s", exc)
        return {
            "executive_summary": (
                f"Report for {client_name} covering {data.get('period_start')} to {data.get('period_end')}. "
                f"AI narrative generation failed: {exc}. Please try regenerating."
            ),
            "website_performance": "Website performance data is available. AI narrative could not be generated.",
            "paid_advertising": "Paid advertising data is available. AI narrative could not be generated.",
            "key_wins": "✓ Data collected successfully\n✓ Report file generated",
            "concerns": "⚠ AI narrative generation encountered an error. Please regenerate.",
            "next_steps": "1. Regenerate this report to get AI insights",
        }
