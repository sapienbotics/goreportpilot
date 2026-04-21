"""
Rewrites raw agency-entered business context into a concise 2–3 sentence
paragraph optimised for downstream use in AI-generated marketing reports.

Used by the clients router's /enhance-context endpoint. Kept as its own
module rather than bolted onto ai_narrative.py so the report-generation
prompt stays focused on its own job.
"""
from __future__ import annotations

import logging

from services.ai_narrative import _get_openai_client

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "Rewrite this business context into a concise 2-3 sentence paragraph "
    "optimized for use in AI-generated marketing reports. Extract: "
    "business type, target audience, primary goals, key metrics that matter. "
    "Return only the rewritten text — no preface, no bullet points, no "
    "quotation marks, no trailing commentary."
)

# Soft ceiling on the enhanced output. Matches the 500-char UI counter;
# gives the model room to finish a thought but prevents runaway drafts.
_MAX_OUTPUT_TOKENS = 220


async def enhance_business_context(text: str) -> str:
    """
    Call GPT-4.1 to rewrite the user's raw context. Never mutates the input;
    returns a brand-new string. Raises on network/API errors so the endpoint
    can surface them to the caller.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        # Defensive — the endpoint already rejects empty payloads, but guard
        # here too so a direct service-level caller can't burn an API call.
        raise ValueError("text is empty")

    client = _get_openai_client()
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": cleaned},
        ],
        # Low temperature — this is a rewriting task, not a creative one.
        # We want the model to stick tight to the user's facts rather than
        # invent new goals or metrics.
        temperature=0.3,
        max_tokens=_MAX_OUTPUT_TOKENS,
    )
    enhanced = (response.choices[0].message.content or "").strip()

    # Strip stray leading/trailing quote marks the model sometimes emits
    # despite being told not to.
    for quote in ('"', '"', '"', "'"):
        if enhanced.startswith(quote) and enhanced.endswith(quote):
            enhanced = enhanced[1:-1].strip()
            break

    if not enhanced:
        raise RuntimeError("Model returned empty output")

    logger.info(
        "Business context enhanced: %d chars in → %d chars out",
        len(cleaned), len(enhanced),
    )
    return enhanced
