"""
Cover Page Presets — Minimal Intervention Edition.

Philosophy
----------
The template designer placed every cover shape where it looks good.
Presets should RECOLOUR those shapes, not move or delete them. Custom
headline / subtitle SUBSTITUTE into existing placeholder slots. Hero
preset is the most invasive change — it puts an image behind everything
and clears the header band's fill so the image shows through the
top area.

Nothing else is stripped, repositioned, resized, or restyled. The
template keeps its designed layout; presets only change colours +
optionally the background.

What the user gets per preset
-----------------------------
  * default    — no-op. Template renders as-is.
  * minimal    — white header + body, dark text.
  * bold       — brand-colour full-bleed, white text.
  * corporate  — dark-navy header, white body, white header text.
  * hero       — hero image full-bleed; header band fill cleared so
                 the image shows through.
  * gradient   — brand header, dark body, white text.

Text overrides (run regardless of preset)
-----------------------------------------
  * headline  → REPLACES {{client_name}}. Primary title.
  * subtitle  → APPENDS after {{report_period}} as
                "{{report_period}} — {subtitle}". So the generator's
                later pass renders e.g. "April 2026 — Test Sub".
                Period stays visible; subtitle is additive.

History
-------
This file went through v2..v9 iterations where we tried to strip the
template's chrome, reposition shapes, darken images etc. Every attempt
introduced more visual bugs than it fixed. v10 reverts to this
simpler contract: touch fills + text content only.
"""
from __future__ import annotations

import io
import logging
from typing import Any, Optional

import httpx
from lxml import etree

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Preset style configs
# ---------------------------------------------------------------------------
#
# Fields (all optional):
#   header_fill     — hex (no '#') or the sentinel "brand" (→ brand_color).
#                     None → leave the header band's fill alone.
#   page_bg         — hex for the slide background fill. None → leave it.
#   headline_color  — hex for runs containing {{client_name}} / {{report_type}}.
#   subtitle_color  — hex for runs containing {{report_period}} / {{report_date}}
#                     / {{agency_name}} / {{agency_email}}.
#   use_hero_image  — if True AND a hero_image_url is provided, a full-slide
#                     picture is inserted at the back of z-order and the
#                     header band's fill is cleared so the image shows
#                     through.

PRESETS: dict[str, Optional[dict[str, Any]]] = {
    "default": None,

    "minimal": {
        "header_fill":    "FFFFFF",
        "page_bg":        "FFFFFF",
        "headline_color": "0F172A",
        "subtitle_color": "64748B",
        "use_hero_image": False,
    },

    "bold": {
        "header_fill":    "brand",
        "page_bg":        "brand",
        "headline_color": "FFFFFF",
        "subtitle_color": "F1F5F9",
        "use_hero_image": False,
    },

    "corporate": {
        "header_fill":    "1E293B",
        "page_bg":        "FFFFFF",
        "headline_color": "FFFFFF",
        "subtitle_color": "CBD5E1",
        "use_hero_image": False,
    },

    "hero": {
        "header_fill":    None,
        "page_bg":        None,
        "headline_color": "FFFFFF",
        "subtitle_color": "F1F5F9",
        "use_hero_image": True,
    },

    "gradient": {
        "header_fill":    "brand",
        "page_bg":        "0F172A",
        "headline_color": "FFFFFF",
        "subtitle_color": "E2E8F0",
        "use_hero_image": False,
    },
}


# Token groups used for:
#   * _SUB (substitution — text content changes)
#   * _COLOR (run recolouring — broader match)
_HEADLINE_SUB_TOKENS   = ("{{client_name}}",)
_SUBTITLE_SUB_TOKENS   = ("{{report_period}}",)
_HEADLINE_COLOR_TOKENS = ("{{client_name}}", "{{report_type}}")
_SUBTITLE_COLOR_TOKENS = (
    "{{report_period}}", "{{report_date}}",
    "{{agency_name}}", "{{agency_email}}",
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def apply_cover_preset(
    prs: Any,
    *,
    preset: str,
    headline: Optional[str],
    subtitle: Optional[str],
    hero_image_url: Optional[str],
    brand_color: Optional[str] = None,
    accent_color: Optional[str] = None,
) -> None:
    """
    Apply a cover preset to slide[0]. MUST run BEFORE the generator's
    text-substitution pass so recolour + subtitute can target the
    template's {{...}} tokens.
    """
    try:
        cover = prs.slides[0]
    except Exception as exc:
        logger.warning("Cover preset: no cover slide available: %s", exc)
        return

    brand_hex = _normalise_hex(brand_color) or "4338CA"
    accent_hex = _normalise_hex(accent_color)
    config = PRESETS.get(preset or "default")

    if config is not None:
        # 1. Header band + slide background colours. Modifies existing
        #    template shapes in place; no new shapes added.
        try:
            _apply_header_and_bg_colours(prs, cover, config, brand_hex)
        except Exception as exc:
            logger.debug("Cover preset: header/bg colour apply failed: %s", exc)

        # 2. Recolour text runs for preset palette. Runs are matched by
        #    placeholder token presence (tokens still intact at this
        #    point). Colours persist when the generator's later pass
        #    substitutes the tokens.
        try:
            _recolour_cover_text(
                cover,
                headline_hex=config.get("headline_color"),
                subtitle_hex=config.get("subtitle_color"),
            )
        except Exception as exc:
            logger.debug("Cover preset: text recolour failed: %s", exc)

        # 3. Hero image — insert behind everything + clear the header
        #    band fill so the image shows through the top area. The
        #    template's other shapes (title, subtitle, agency name,
        #    labels) remain in place on top of the image.
        is_hero = bool(config.get("use_hero_image")) and bool(hero_image_url)
        if is_hero:
            try:
                _insert_hero_image(prs, cover, hero_image_url)
            except Exception as exc:
                logger.debug("Cover preset: hero insert failed: %s", exc)

    # 4. Substitute custom headline/subtitle (works on every preset,
    #    including 'default', so users can change the title without
    #    changing visual styling).
    _substitute_cover_text(cover, headline=headline, subtitle=subtitle)

    # 5. Accent bar for non-hero presets when an accent colour is set.
    if config is not None and accent_hex and not (
        bool(config.get("use_hero_image")) and bool(hero_image_url)
    ):
        try:
            _draw_accent_bar(prs, cover, accent_hex)
        except Exception as exc:
            logger.debug("Cover preset: accent bar failed: %s", exc)


# ---------------------------------------------------------------------------
# Header band + slide background colours
# ---------------------------------------------------------------------------


def _apply_header_and_bg_colours(
    prs: Any, cover: Any, config: dict, brand_hex: str,
) -> None:
    """Recolour the header band shape + slide background. In-place only."""
    from pptx.dml.color import RGBColor  # noqa: PLC0415

    page_bg = config.get("page_bg")
    if page_bg:
        rgb = _hex_to_rgb(_resolve_brand(page_bg, brand_hex))
        try:
            bg = cover.background
            bg.fill.solid()
            bg.fill.fore_color.rgb = RGBColor(*rgb)
        except Exception as exc:
            logger.debug("Cover: slide background fill failed: %s", exc)

    header_fill = config.get("header_fill")
    if header_fill:
        rgb = _hex_to_rgb(_resolve_brand(header_fill, brand_hex))
        band = _find_header_band(cover, prs)
        if band is not None:
            try:
                band.fill.solid()
                band.fill.fore_color.rgb = RGBColor(*rgb)
                try:
                    band.line.fill.background()
                except Exception:
                    pass
            except Exception as exc:
                logger.debug("Cover: header-band recolour failed: %s", exc)


def _find_header_band(cover: Any, prs: Any) -> Optional[Any]:
    """
    Heuristic: topmost non-picture non-text-bearing shape that spans
    ≥60% of slide width and sits in the top third. Identifies the
    decorative header rectangle across all six visual templates.
    """
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    min_w   = int(slide_w * 0.6)
    top_cap = int(slide_h * 0.33)

    candidates = []
    for shape in cover.shapes:
        if getattr(shape, "shape_type", None) == 13:  # MSO_SHAPE_TYPE.PICTURE
            continue
        if shape.has_text_frame and (shape.text_frame.text or "").strip():
            continue
        try:
            if shape.width and shape.width >= min_w and shape.top is not None and shape.top <= top_cap:
                candidates.append(shape)
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda s: (int(s.top or 0), -int(s.width or 0)))
    return candidates[0]


# ---------------------------------------------------------------------------
# Text recolour (runs matched by placeholder tokens)
# ---------------------------------------------------------------------------


def _recolour_cover_text(
    cover: Any,
    *,
    headline_hex: Optional[str],
    subtitle_hex: Optional[str],
) -> None:
    """
    Recolour runs on the cover slide based on which placeholder tokens
    they contain. Runs keep their new colour through the generator's
    later text-substitution pass.
    """
    if not headline_hex and not subtitle_hex:
        return
    from pptx.dml.color import RGBColor  # noqa: PLC0415

    head_rgb = _hex_to_rgb(headline_hex) if headline_hex else None
    sub_rgb  = _hex_to_rgb(subtitle_hex) if subtitle_hex else None

    for shape in cover.shapes:
        if not shape.has_text_frame:
            continue
        frame_text = (shape.text_frame.text or "")
        if not frame_text.strip():
            continue
        # Skip logo placeholders handled by _embed_logos.
        if "agency_logo" in frame_text.lower() or "client_logo" in frame_text.lower():
            continue

        target_rgb = None
        if head_rgb and any(t in frame_text for t in _HEADLINE_COLOR_TOKENS):
            target_rgb = head_rgb
        elif sub_rgb and any(t in frame_text for t in _SUBTITLE_COLOR_TOKENS):
            target_rgb = sub_rgb
        elif head_rgb:
            target_rgb = head_rgb

        if target_rgb is None:
            continue

        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                try:
                    run.font.color.rgb = RGBColor(*target_rgb)
                except Exception:
                    continue


# ---------------------------------------------------------------------------
# Text substitution (headline / subtitle overrides)
# ---------------------------------------------------------------------------


def _substitute_cover_text(
    cover: Any,
    *,
    headline: Optional[str],
    subtitle: Optional[str],
) -> None:
    """
    * Headline REPLACES {{client_name}}.
    * Subtitle APPENDS to {{report_period}} via " — " so the real
      period date range stays visible once the generator substitutes
      the token. Example:
          Run before: "{{report_period}}"
          With subtitle 'Test Sub': "{{report_period}} — Test Sub"
          Generator substitutes: "April 2026 — Test Sub"
      No subtitle → token untouched → period renders as-is.
    """
    if not headline and not subtitle:
        return

    for shape in cover.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                txt = run.text or ""
                if headline:
                    for token in _HEADLINE_SUB_TOKENS:
                        if token in txt:
                            run.text = txt.replace(token, headline)
                            txt = run.text or ""
                if subtitle:
                    for token in _SUBTITLE_SUB_TOKENS:
                        if token in txt:
                            run.text = txt.replace(token, f"{token} — {subtitle}")
                            txt = run.text or ""


# ---------------------------------------------------------------------------
# Hero image (minimal — insert + z-order + clear header band fill)
# ---------------------------------------------------------------------------


def _insert_hero_image(prs: Any, cover: Any, image_url: str) -> None:
    """
    Insert a hero image at (0, 0) full-slide, send to the back of
    z-order, and CLEAR the header band's fill so the image shows
    through the top area. No other cover shapes are touched — the
    template's title, subtitle, logo placeholders, labels all render
    on top of the hero.
    """
    from pptx.util import Emu  # noqa: PLC0415

    img_bytes = _download_image(image_url)
    if not img_bytes:
        logger.debug("Cover preset: hero image not downloadable")
        return

    pic = cover.shapes.add_picture(
        io.BytesIO(img_bytes), Emu(0), Emu(0),
        width=prs.slide_width, height=prs.slide_height,
    )
    _reorder_to_back(cover, pic)
    logger.info(
        "Hero pic inserted at (0,0) full-bleed; slide is %.2fx%.2f inches",
        prs.slide_width / 914400, prs.slide_height / 914400,
    )

    # Clear the header band's fill so the hero shows through. Doesn't
    # delete the band — just makes it transparent. If no band is found
    # (template with different cover design) this is a no-op.
    band = _find_header_band(cover, prs)
    if band is not None:
        try:
            band.fill.background()
            logger.info("Hero: cleared header-band fill")
        except Exception as exc:
            logger.debug("Hero: could not clear header band fill: %s", exc)


def _reorder_to_back(slide: Any, shape: Any) -> None:
    """Move the given shape to the first visible position in spTree
    (just after the mandatory group-property children)."""
    sp_tree = slide.shapes._spTree
    el = shape._element
    if el.getparent() is sp_tree:
        sp_tree.remove(el)

    insert_at = 0
    for i, child in enumerate(sp_tree):
        tag = etree.QName(child).localname
        if tag in ("nvGrpSpPr", "grpSpPr"):
            insert_at = i + 1
        else:
            break
    sp_tree.insert(insert_at, el)


# ---------------------------------------------------------------------------
# Accent bar (thin stripe at the bottom of the header band)
# ---------------------------------------------------------------------------


def _draw_accent_bar(prs: Any, cover: Any, accent_hex: str) -> None:
    from pptx.dml.color import RGBColor  # noqa: PLC0415
    from pptx.util import Emu, Inches    # noqa: PLC0415

    rgb = _hex_to_rgb(accent_hex)
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    bar_h   = Inches(0.10)
    bar_top = int(slide_h * 0.33) - int(bar_h)
    bar     = cover.shapes.add_shape(1, Emu(0), Emu(bar_top), slide_w, bar_h)
    try:
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor(*rgb)
        bar.line.fill.background()
    except Exception as exc:
        logger.debug("Accent bar fill failed: %s", exc)


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
        return v.upper()
    return None


def _hex_to_rgb(hex_str: Optional[str]) -> tuple[int, int, int]:
    h = _normalise_hex(hex_str) or "4338CA"
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _resolve_brand(value: str, brand_hex: str) -> str:
    return brand_hex if value == "brand" else value


def _download_image(url: str, max_bytes: int = 5 * 1024 * 1024) -> Optional[bytes]:
    if not url:
        return None
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.content
            if len(data) > max_bytes:
                logger.warning("Hero image exceeds %d bytes — skipping", max_bytes)
                return None
            return data
    except Exception as exc:
        logger.debug("Hero image download failed (%s): %s", url, exc)
        return None
