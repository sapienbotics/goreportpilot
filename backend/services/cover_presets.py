"""
Cover Page Presets — Phase 3 (rewritten for bug-fixes).

Five preset visual styles applied as IN-PLACE modifications to the
template's existing cover slide. We NEVER add new shapes on top of the
template — all colour + text changes target the template's pre-designed
shapes. Only the `hero` preset adds two net-new elements (the hero
picture + a semi-dark overlay), carefully z-ordered behind the text.

Shape identification uses placeholder TEXT content ({{client_name}},
{{report_period}}, {{report_type}}, {{agency_name}}, {{agency_email}}).
Because of this, `apply_cover_preset()` MUST run BEFORE the generator's
text-replacement pass — otherwise the tokens have already been
substituted and cannot be used as identifiers.

Presets:
  * default    — no-op; use the template's native cover.
  * minimal    — white bg, dark type, thin accent bar.
  * bold       — full-bleed brand colour with large white title.
  * corporate  — dark-navy header band, white title, brand accent.
  * hero       — full-bleed hero image with 40% dark overlay.
  * gradient   — solid brand-colour header over dark body.
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
        # Hero image replaces visible header/body — colours are only used
        # for text recolouring so titles stay readable on the image.
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


# Placeholder groups — used for identifying which existing template shape
# plays which role on the cover. Matching is substring-based so a shape
# containing any of these tokens anywhere in its text is considered a
# match. This is robust across all 6 visual templates because each
# template uses these exact tokens in its cover.
_HEADLINE_PLACEHOLDERS = ("{{client_name}}", "{{report_type}}")
_SUBTITLE_PLACEHOLDERS = ("{{report_period}}", "{{report_date}}")
_AGENCY_TEXT_PLACEHOLDERS = ("{{agency_name}}", "{{agency_email}}")


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
    Apply a cover preset to slide[0]. Must be called BEFORE the generator's
    text-replacement pass so placeholder tokens are still intact and can be
    used to identify shapes.

    Safe to call with preset='default' — that skips colour + hero logic but
    still honours headline/subtitle text overrides.
    """
    try:
        cover = prs.slides[0]
    except Exception as exc:
        logger.warning("Cover preset: no cover slide: %s", exc)
        return

    brand_hex = _normalise_hex(brand_color) or "4338CA"
    accent_hex = _normalise_hex(accent_color)

    # Always process text overrides — they work even on the 'default' preset
    # (the user may want to change the headline without changing visuals).
    _substitute_cover_text(cover, headline=headline, subtitle=subtitle)

    if not preset or preset == "default":
        # No visual changes on default — return after text substitution.
        return

    config = PRESETS.get(preset)
    if not config:
        logger.warning("Cover preset: unknown preset '%s'", preset)
        return

    # 1) Header band + page background colours (in-place, modifies existing
    #    template shapes — does NOT add new rectangles).
    try:
        _apply_header_and_bg_colours(prs, cover, config, brand_hex)
    except Exception as exc:
        logger.debug("Cover preset: colour apply failed: %s", exc)

    # 2) Hero image — only preset that adds net-new shapes. Inserted at the
    #    back of the z-order with a 40% dark overlay between it and text.
    if config.get("use_hero_image") and hero_image_url:
        try:
            _insert_hero_image(prs, cover, hero_image_url)
        except Exception as exc:
            logger.debug("Cover preset: hero-image apply failed: %s", exc)

    # 3) Recolour existing text runs (headline / subtitle / agency text)
    #    to match the preset. Colour is applied to the runs containing the
    #    placeholder tokens — when the generator's pass substitutes the
    #    tokens with real values, the colour is preserved.
    try:
        _recolour_cover_text(
            cover,
            headline_hex=config.get("headline_color"),
            subtitle_hex=config.get("subtitle_color"),
        )
    except Exception as exc:
        logger.debug("Cover preset: text recolour failed: %s", exc)

    # 4) Optional accent bar at the bottom of the header band.
    if accent_hex:
        try:
            _draw_accent_bar(prs, cover, accent_hex)
        except Exception as exc:
            logger.debug("Cover preset: accent bar failed: %s", exc)


# ---------------------------------------------------------------------------
# Step 1 — header + page background colours
# ---------------------------------------------------------------------------


def _apply_header_and_bg_colours(
    prs: Any, cover: Any, config: dict, brand_hex: str,
) -> None:
    """Recolour the header-band shape and slide background in place."""
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
        header_shape = _find_header_band(cover, prs)
        if header_shape is not None:
            try:
                header_shape.fill.solid()
                header_shape.fill.fore_color.rgb = RGBColor(*rgb)
                try:
                    header_shape.line.fill.background()
                except Exception:
                    pass
            except Exception as exc:
                logger.debug("Cover: header-band recolour failed: %s", exc)


def _find_header_band(cover: Any, prs: Any) -> Optional[Any]:
    """
    Find the header band shape: topmost non-picture shape that spans at
    least 60% of slide width and sits in the top third. Present in every
    visual template's cover. NEVER returns a text-bearing shape — those
    are title boxes, not the coloured header band.
    """
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    min_w   = int(slide_w * 0.6)
    top_cap = int(slide_h * 0.33)

    candidates = []
    for shape in cover.shapes:
        if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
            continue
        # Skip shapes with text — they're title/subtitle boxes, not a band.
        if shape.has_text_frame and (shape.text_frame.text or "").strip():
            continue
        try:
            w = int(shape.width or 0)
            t = int(shape.top or 0)
            if w >= min_w and t <= top_cap:
                candidates.append(shape)
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda s: (int(s.top or 0), -int(s.width or 0)))
    return candidates[0]


# ---------------------------------------------------------------------------
# Step 2 — hero image (z-ordered at back, 40% dark overlay above it)
# ---------------------------------------------------------------------------


def _insert_hero_image(prs: Any, cover: Any, image_url: str) -> None:
    """
    Insert a hero image full-bleed behind all existing shapes + a 40%
    dark overlay between the image and the text shapes.

    Uses robust z-order manipulation: finds the end of the group-property
    children (nvGrpSpPr, grpSpPr) and inserts the pic + overlay there, so
    they render behind every original template shape regardless of how
    many group-property nodes the template has.
    """
    from pptx.dml.color import RGBColor  # noqa: PLC0415
    from pptx.util import Emu            # noqa: PLC0415

    img_bytes = _download_image(image_url)
    if not img_bytes:
        logger.debug("Cover preset: hero image could not be downloaded")
        return

    pic = cover.shapes.add_picture(
        io.BytesIO(img_bytes), 0, 0,
        width=prs.slide_width, height=prs.slide_height,
    )

    # Overlay rectangle (black, 40% opacity) above the image but below text.
    overlay = cover.shapes.add_shape(
        1,  # MSO_SHAPE.RECTANGLE
        Emu(0), Emu(0),
        prs.slide_width, prs.slide_height,
    )
    try:
        overlay.fill.solid()
        overlay.fill.fore_color.rgb = RGBColor(0, 0, 0)
        _set_shape_fill_alpha(overlay, 40)
        overlay.line.fill.background()
    except Exception as exc:
        logger.debug("Cover: overlay fill failed: %s", exc)

    # Z-order: pic must render BEHIND everything (including overlay); overlay
    # must render above pic but BELOW the text shapes. We do this by moving
    # both newly-added elements to the very start of spTree (right after
    # group-property children), pic first, then overlay.
    _reorder_to_back(cover, pic, overlay)


def _reorder_to_back(slide: Any, pic_shape: Any, overlay_shape: Any) -> None:
    """
    Move `pic_shape` and `overlay_shape` to the start of spTree (right
    after group-property children), with pic BEFORE overlay. Net effect:
    pic is the deepest-back visible shape, overlay sits just above it,
    and all other template shapes remain on top.
    """
    sp_tree = slide.shapes._spTree
    pic_el = pic_shape._element
    ovr_el = overlay_shape._element

    # Remove both from wherever they currently sit.
    for el in (pic_el, ovr_el):
        if el.getparent() is sp_tree:
            sp_tree.remove(el)

    # Find the first index after the last group-property child.
    insert_at = 0
    for i, child in enumerate(sp_tree):
        tag = etree.QName(child).localname
        if tag in ("nvGrpSpPr", "grpSpPr"):
            insert_at = i + 1
        else:
            break

    sp_tree.insert(insert_at,     pic_el)
    sp_tree.insert(insert_at + 1, ovr_el)


def _set_shape_fill_alpha(shape: Any, alpha_percent: int) -> None:
    """
    Apply alpha (0-100) to a solid-fill shape. python-pptx doesn't expose
    this on FillFormat; we patch the <a:srgbClr> XML directly.
    """
    spPr = shape.fill._xPr
    nsmap = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    srgb = spPr.find(".//a:solidFill/a:srgbClr", nsmap)
    if srgb is None:
        return
    for child in srgb.findall("a:alpha", nsmap):
        srgb.remove(child)
    alpha = etree.SubElement(
        srgb,
        "{http://schemas.openxmlformats.org/drawingml/2006/main}alpha",
    )
    alpha.set("val", str(max(0, min(100, alpha_percent)) * 1000))


# ---------------------------------------------------------------------------
# Step 3 — text overrides (run BEFORE generator's replacement pass)
# ---------------------------------------------------------------------------


def _substitute_cover_text(
    cover: Any,
    *,
    headline: Optional[str],
    subtitle: Optional[str],
) -> None:
    """
    Replace {{client_name}} with `headline` and {{report_period}} with
    `subtitle` on the cover slide only. Token-level replacement preserves
    the run's formatting (font, size, alignment). Subsequent generator
    passes will see NO {{client_name}} token on slide 0, so the cover
    shows the override; on other slides the token survives and gets
    substituted normally with the real client name.

    If headline/subtitle are None, tokens are left intact for the normal
    substitution to handle.
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
                    for token in _HEADLINE_PLACEHOLDERS:
                        if token in txt:
                            run.text = txt.replace(token, headline)
                            txt = run.text or ""
                if subtitle:
                    for token in _SUBTITLE_PLACEHOLDERS:
                        if token in txt:
                            run.text = txt.replace(token, subtitle)
                            txt = run.text or ""


def _recolour_cover_text(
    cover: Any,
    *,
    headline_hex: Optional[str],
    subtitle_hex: Optional[str],
) -> None:
    """
    Walk the cover's text frames and recolour runs containing the known
    placeholder tokens. Runs are recoloured IN PLACE — no new shapes, no
    text rewriting. Because colouring is applied before the generator's
    text-substitution pass, the colour survives when the token is
    replaced with the real value.

    Heuristic:
      • runs containing {{client_name}} / {{report_type}} → headline colour
      • runs containing {{report_period}} / {{report_date}} / {{agency_name}}
        / {{agency_email}} → subtitle colour
      • runs that have ALREADY been substituted (custom headline present)
        are matched by the override text instead, so the colour still
        applies.
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
        # Determine which colour applies based on the tokens present.
        target_rgb = None
        if head_rgb and any(t in frame_text for t in _HEADLINE_PLACEHOLDERS):
            target_rgb = head_rgb
        elif sub_rgb and (
            any(t in frame_text for t in _SUBTITLE_PLACEHOLDERS) or
            any(t in frame_text for t in _AGENCY_TEXT_PLACEHOLDERS)
        ):
            target_rgb = sub_rgb
        elif head_rgb:
            # Fallback: any remaining cover text gets the headline colour so
            # titles/subheadings stay readable against the new background.
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
# Step 4 — accent bar (optional)
# ---------------------------------------------------------------------------


def _draw_accent_bar(prs: Any, cover: Any, accent_hex: str) -> None:
    """
    Draw a thin horizontal accent bar at ~33% of slide height (bottom of
    the header band). Exists only when the user picked an accent colour;
    kept intentionally minimal so it doesn't collide with the template's
    native geometry.
    """
    from pptx.dml.color import RGBColor  # noqa: PLC0415
    from pptx.util import Emu            # noqa: PLC0415

    rgb = _hex_to_rgb(accent_hex)
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    bar_h   = Emu(54_000)   # ~0.06"
    bar_top = int(slide_h * 0.33) - int(bar_h)
    bar     = cover.shapes.add_shape(1, Emu(0), Emu(bar_top), slide_w, bar_h)
    try:
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor(*rgb)
        bar.line.fill.background()
    except Exception as exc:
        logger.debug("Cover: accent bar fill failed: %s", exc)


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
