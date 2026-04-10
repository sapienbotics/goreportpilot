"""
AI Narrative Engine — uses GPT-4.1 to write report commentary.
See docs/reportpilot-feature-design-blueprint.md Section 7 for prompt architecture.
"""
import json
import logging
from typing import Dict, Any, Optional

from openai import AsyncOpenAI
from config import settings

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
    "executive_summary":  '"{key}" — 150 words max, structured as SCQA (Situation, Complication, implied Question, Answer) in flowing prose, NOT labelled',
    "website_performance": '"{key}" — 2-3 paragraphs analyzing website traffic and engagement',
    "paid_advertising":   '"{key}" — 2-3 paragraphs analyzing Meta Ads performance',
    # Content-count enforcement (3+3+3): every report should land with exactly
    # 3 wins, 3 concerns, and 3 next steps in the canonical structure.
    "key_wins":           '"{key}" — EXACTLY 3 bullet points. Each must reference a specific metric with numbers. Start each with "\u2713 "',
    "concerns":           '"{key}" — EXACTLY 3 bullet points. Each must state an observation, a likely cause, and a specific recommendation. Start each with "\u26A0 "',
    "next_steps":         '"{key}" — EXACTLY 3 numbered items. Each MUST follow the pattern: "Next month we will [action] on [channel], based on [data point], to achieve [expected outcome]."',
    "google_ads_performance": '"{key}" — 2-3 paragraphs analyzing Google Ads search campaign performance',
    "seo_performance": '"{key}" — 2-3 paragraphs analyzing organic search performance from Google Search Console',
    "csv_performance": '"{key}" — 2 paragraphs summarizing the custom data source metrics',
    "engagement_analysis": '"{key}" — 1-2 paragraphs analyzing website engagement: device breakdown (mobile vs desktop vs tablet), top pages by views/engagement, and user behavior insights',
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

TONE: {tone_modifier}

IMPORTANT — CURRENCY: All monetary amounts for Meta Ads must use the {currency_code} currency symbol ({cur_sym}). \
Never use "$" for Meta Ads figures unless the currency is USD.

Generate the following sections as a JSON object:
{section_instructions}
{_chart_insights_block}

Return ONLY valid JSON, no markdown code blocks, no explanation outside the JSON."""

    try:
        ai = _get_openai_client()
        response = await ai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + language_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
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
