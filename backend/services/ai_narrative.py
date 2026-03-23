"""
AI Narrative Engine — uses GPT-4o to write report commentary.
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
- Structure: Lead with the headline insight, support with data, close with recommendation"""

TONE_MODIFIERS: Dict[str, str] = {
    "professional": (
        "Write in a professional, authoritative tone. Use data to support every claim. "
        "Structure with clear transitions between topics."
    ),
    "conversational": (
        "Write conversationally, as if explaining to a busy business owner over coffee. "
        "Avoid jargon. Use analogies where helpful. Keep it warm but data-backed."
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
        "Write conversationally, as if explaining to a busy business owner over coffee. "
        "Avoid jargon. Use analogies where helpful. Keep it warm but data-backed."
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
}


_SECTION_INSTRUCTIONS: Dict[str, str] = {
    "executive_summary":  '"{key}" — 3-4 paragraphs (max 200 words) overview of the period',
    "website_performance": '"{key}" — 2-3 paragraphs analyzing website traffic and engagement',
    "paid_advertising":   '"{key}" — 2-3 paragraphs analyzing Meta Ads performance',
    "key_wins":           '"{key}" — 3-5 bullet points of wins (start each with "✓ ")',
    "concerns":           '"{key}" — 2-3 bullet points of concerns with recommendations (start each with "⚠ ")',
    "next_steps":         '"{key}" — 3-5 numbered action items for the next period',
}


def _build_section_instructions(sections: list[str]) -> str:
    """Build the numbered section list for the GPT-4o prompt."""
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
        # Full (default): all 6 sections
        requested_sections = [
            "executive_summary", "website_performance", "paid_advertising",
            "key_wins", "concerns", "next_steps",
        ]

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

TONE: {tone_modifier}

IMPORTANT — CURRENCY: All monetary amounts for Meta Ads must use the {currency_code} currency symbol ({cur_sym}). \
Never use "$" for Meta Ads figures unless the currency is USD.

Generate ONLY the following sections as a JSON object (include only these keys, nothing else):
{section_instructions}

Return ONLY valid JSON, no markdown code blocks, no explanation outside the JSON."""

    try:
        ai = _get_openai_client()
        response = await ai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
