"""
Cover Customisation — Option F v1.

Philosophy
----------
The chosen theme (= one of the 6 visual templates) owns the cover's
design. This module applies only MINIMAL, well-defined overrides on
top of that design:

  1. Headline replace   — substitutes {{client_name}} with the user's
                          custom title when set.
  2. Subtitle append    — appends " — <subtitle>" after {{report_period}}
                          so the real period stays visible.
  3. Header-band tint   — recolours the theme's header band with the
                          user's brand primary. Only applied for themes
                          whose `brand_tint_strategy` is "header_band".
                          For themes with multi-colour decoration
                          (colorful_agency, bold_geometric, minimal_elegant)
                          this is skipped — brand colour still flows to
                          the chart palette via `branding['brand_color']`.
  4. Accent bar         — draws a 0.10" horizontal stripe at the bottom
                          of the header band when an accent colour is set.
                          Skipped for themes without a band.

What this module does NOT do
----------------------------
  * No shape stripping / deletion.
  * No text repositioning.
  * No font-size override.
  * No hero image (v1 drops the hero concept).
  * No preset-specific palette recolouring of every text run.

Logos are placed by `report_generator._embed_logos` using the per-
client position + size overrides — unchanged from Phase 3.

Must run BEFORE the generator's text-substitution pass so {{client_name}}
and {{report_period}} tokens are still intact when we locate / modify them.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from services.theme_layout import get as get_theme_layout
from services.theme_layout import supports_brand_tint

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def apply_cover_customization(
    prs: Any,
    *,
    theme: str,
    headline: Optional[str],
    subtitle: Optional[str],
    brand_primary_color: Optional[str] = None,
    accent_color: Optional[str] = None,
) -> None:
    """
    Apply the 4 override types to slide[0]. Safe to call even when all
    overrides are None — it's a no-op in that case.

    Invoked from `generate_pptx_report` BEFORE the generic placeholder
    substitution pass.
    """
    try:
        cover = prs.slides[0]
    except Exception as exc:
        logger.warning("Cover customisation: no cover slide: %s", exc)
        return

    brand_hex = _normalise_hex(brand_primary_color)
    accent_hex = _normalise_hex(accent_color)

    # 1. Header-band tint (only for themes that support it).
    if brand_hex and supports_brand_tint(theme):
        try:
            _recolor_header_band(prs, cover, theme, brand_hex)
        except Exception as exc:
            logger.debug("Cover: header-band tint failed: %s", exc)

    # 2. Accent bar (only for themes with a band, since it sits at its edge).
    if accent_hex and supports_brand_tint(theme):
        try:
            _draw_accent_bar(prs, cover, theme, accent_hex)
        except Exception as exc:
            logger.debug("Cover: accent bar draw failed: %s", exc)

    # 3/4. Text substitutions — runs on every call, including when no
    # colours are set, because headline/subtitle overrides are independent
    # of brand colours.
    _substitute_cover_text(cover, headline=headline, subtitle=subtitle)


# ---------------------------------------------------------------------------
# Step 1 — recolour the theme's header band
# ---------------------------------------------------------------------------


def _recolor_header_band(prs: Any, cover: Any, theme: str, hex_str: str) -> None:
    """
    Set the header band's fill to the user's brand primary. The band
    is identified via the heuristic (topmost full-width non-text non-pic
    shape in the top third of the slide). If the heuristic fails, falls
    back to matching against the theme's known header_band coordinates.
    """
    from pptx.dml.color import RGBColor  # noqa: PLC0415

    rgb = _hex_to_rgb(hex_str)
    band = _find_header_band(cover, prs, theme)
    if band is None:
        logger.debug("Cover: header band not found for theme %s; skipping tint", theme)
        return
    try:
        band.fill.solid()
        band.fill.fore_color.rgb = RGBColor(*rgb)
        try:
            band.line.fill.background()
        except Exception:
            pass
        logger.info("Cover: header band tinted with brand %s (theme=%s)", hex_str, theme)
    except Exception as exc:
        logger.debug("Cover: failed to set header-band fill: %s", exc)


def _find_header_band(cover: Any, prs: Any, theme: str) -> Optional[Any]:
    """
    Heuristic: topmost non-picture non-text full-width shape in top third.
    Works for modern_clean / dark_executive / gradient_modern.

    Falls back to coordinate match against the theme layout if the
    heuristic picks nothing. Some templates have shape z-ordering that
    pushes the band down the spTree.
    """
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    min_w   = int(slide_w * 0.6)
    top_cap = int(slide_h * 0.33)

    # Phase 1 — heuristic.
    candidates: list[Any] = []
    for shape in cover.shapes:
        if getattr(shape, "shape_type", None) == 13:  # PICTURE
            continue
        if shape.has_text_frame and (shape.text_frame.text or "").strip():
            continue
        try:
            if (shape.width and shape.width >= min_w
                and shape.top is not None and shape.top <= top_cap):
                candidates.append(shape)
        except Exception:
            continue
    if candidates:
        candidates.sort(key=lambda s: (int(s.top or 0), -int(s.width or 0)))
        return candidates[0]

    # Phase 2 — coordinate fallback. Match against the theme's known band.
    band_spec = get_theme_layout(theme).get("header_band")
    if band_spec is None:
        return None
    EMU = 914400
    target_x = int(band_spec["x"] * EMU)
    target_y = int(band_spec["y"] * EMU)
    target_w = int(band_spec["w"] * EMU)
    for shape in cover.shapes:
        try:
            if (shape.left is not None and shape.top is not None
                and abs(int(shape.left) - target_x) < EMU * 0.05
                and abs(int(shape.top)  - target_y) < EMU * 0.1
                and shape.width and abs(int(shape.width) - target_w) < EMU * 0.2):
                return shape
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Step 2 — accent bar
# ---------------------------------------------------------------------------


def _draw_accent_bar(prs: Any, cover: Any, theme: str, hex_str: str) -> None:
    """
    Thin (0.10") accent bar at the bottom of the theme's header band.
    Skipped if the theme has no band.
    """
    from pptx.dml.color import RGBColor  # noqa: PLC0415
    from pptx.util import Emu, Inches    # noqa: PLC0415

    band_spec = get_theme_layout(theme).get("header_band")
    if band_spec is None:
        return

    rgb = _hex_to_rgb(hex_str)
    EMU = 914400
    bar_h_emu = int(Inches(0.10))
    bar_top_emu = int((band_spec["y"] + band_spec["h"]) * EMU) - bar_h_emu
    bar_left_emu = int(band_spec["x"] * EMU)
    bar_width_emu = int(band_spec["w"] * EMU)

    bar = cover.shapes.add_shape(
        1,  # MSO_SHAPE.RECTANGLE
        Emu(bar_left_emu), Emu(bar_top_emu),
        Emu(bar_width_emu), Emu(bar_h_emu),
    )
    try:
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor(*rgb)
        bar.line.fill.background()
    except Exception as exc:
        logger.debug("Cover: accent bar fill failed: %s", exc)


# ---------------------------------------------------------------------------
# Step 3 — text substitutions (headline replace, subtitle append)
# ---------------------------------------------------------------------------


# The SINGLE tokens we touch. Deliberately narrow — we don't touch
# {{report_type}}, {{agency_name}}, {{agency_logo}}, {{client_logo}}.
_HEADLINE_TOKEN = "{{client_name}}"
_SUBTITLE_TOKEN = "{{report_period}}"


def _substitute_cover_text(
    cover: Any,
    *,
    headline: Optional[str],
    subtitle: Optional[str],
) -> None:
    """
    Headline REPLACES {{client_name}}. Subtitle APPENDS " — {subtitle}"
    after {{report_period}} — the token stays in the run so the
    generator's later pass substitutes the real period. Net effect:
      original run:  "{{report_period}}"
      after append:  "{{report_period}} — Test Sub"
      after gen:     "April 2026 — Test Sub"

    Both operations preserve run formatting (font, size, colour).
    """
    if not headline and not subtitle:
        return

    for shape in cover.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                txt = run.text or ""
                if headline and _HEADLINE_TOKEN in txt:
                    run.text = txt.replace(_HEADLINE_TOKEN, headline)
                    txt = run.text or ""
                if subtitle and _SUBTITLE_TOKEN in txt:
                    run.text = txt.replace(_SUBTITLE_TOKEN, f"{_SUBTITLE_TOKEN} — {subtitle}")
                    txt = run.text or ""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _normalise_hex(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip()
    if v.startswith("#"):
        v = v[1:]
    if len(v) == 6:
        try:
            int(v, 16)
            return v.upper()
        except ValueError:
            return None
    return None


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = _normalise_hex(hex_str) or "4338CA"
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
