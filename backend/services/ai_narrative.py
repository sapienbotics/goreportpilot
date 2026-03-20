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


async def generate_narrative(
    data: Dict[str, Any],
    client_name: str,
    client_goals: Optional[str],
    tone: str = "professional",
) -> Dict[str, str]:
    """
    Generate AI narrative sections for a report.

    Returns a dict with keys:
        executive_summary, website_performance, paid_advertising,
        key_wins, concerns, next_steps
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — returning fallback narrative")
        return FALLBACK_NARRATIVE

    tone_modifier = TONE_MODIFIERS.get(tone, TONE_MODIFIERS["professional"])

    ga4 = data.get("ga4", {}).get("summary", {})
    meta = data.get("meta_ads", {}).get("summary", {})
    campaigns = data.get("meta_ads", {}).get("campaigns", [])
    traffic_sources = data.get("ga4", {}).get("traffic_sources", [])

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
Traffic Sources: {json.dumps(traffic_sources[:5]) if traffic_sources else 'N/A'}

META ADS DATA:
Total Spend: ${meta.get('spend', 'N/A')} (prev: ${meta.get('prev_spend', 'N/A')}, change: {meta.get('spend_change', 'N/A')}%)
Impressions: {meta.get('impressions', 'N/A')} (prev: {meta.get('prev_impressions', 'N/A')})
Clicks: {meta.get('clicks', 'N/A')} (prev: {meta.get('prev_clicks', 'N/A')})
CTR: {meta.get('ctr', 'N/A')}% (prev: {meta.get('prev_ctr', 'N/A')}%)
CPC: ${meta.get('cpc', 'N/A')} (prev: ${meta.get('prev_cpc', 'N/A')})
Conversions: {meta.get('conversions', 'N/A')} (prev: {meta.get('prev_conversions', 'N/A')}, change: {meta.get('conversions_change', 'N/A')}%)
Cost Per Conversion: ${meta.get('cost_per_conversion', 'N/A')} (prev: ${meta.get('prev_cost_per_conversion', 'N/A')})
ROAS: {meta.get('roas', 'N/A')}x (prev: {meta.get('prev_roas', 'N/A')}x)
Top Campaigns: {json.dumps(campaigns[:3]) if campaigns else 'N/A'}

TONE: {tone_modifier}

Generate the following sections as a JSON object with these exact keys:
1. "executive_summary" — 3-4 paragraphs (max 200 words) overview of the month
2. "website_performance" — 2-3 paragraphs analyzing website traffic and engagement
3. "paid_advertising" — 2-3 paragraphs analyzing Meta Ads performance
4. "key_wins" — 3-5 bullet points of wins (start each with "✓ ")
5. "concerns" — 2-3 bullet points of concerns with recommendations (start each with "⚠ ")
6. "next_steps" — 3-5 numbered action items for the next period

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
