"""
Cover Page Presets — Phase 3.

Five preset visual styles that can be applied on top of any of the six
visual templates (modern_clean, dark_executive, colorful_agency,
bold_geometric, minimal_elegant, gradient_modern). Applied as in-place
modifications to the generated slide[0] so we never need to maintain
30 × (6 templates × 5 presets) separate PPTX files.

Preset keys:
  * default    — no changes (use the visual template's cover as-is)
  * minimal    — white background, thin accent line, black title
  * bold       — full-bleed brand-color background, large white title
  * corporate  — dark navy header, white title, brand accent bar
  * hero       — hero image as full-bleed background with semi-dark overlay
  * gradient   — solid brand-color header band (gradient approximation)

Each preset exposes optional headline / subtitle overrides so the agency
can personalise the title line per client without editing a PPTX file.

Design decision (per Phase 1-2 refined plan §6): we do NOT ship 5 separate
PPTX variant files. Managing them requires building them visually in
PowerPoint, and swapping slides between python-pptx presentations is
brittle (relationship refs, layout inheritance). Pure Python style
configs produce the same visible outcome with far less maintenance cost.
"""
from __future__ import annotations

import io
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Preset style configs
# ---------------------------------------------------------------------------
#
# Per-preset fields:
#   header_fill       — hex (no '#') for the top cover band. None = leave as-is.
#                       The special string "brand" resolves to branding's brand_color.
#   page_bg           — hex for the full slide background, or None.
#   headline_color    — hex for the main title text.
#   subtitle_color    — hex for the subtitle text.
#   title_font_pt     — max desired title font size in points.
#   use_hero_image    — when True AND a cover_hero_image_url is available,
#                       the image is inserted full-bleed behind all shapes.
#   overlay_fill      — only when use_hero_image is True; applied as a
#                       full-bleed rectangle over the hero image for text
#                       legibility. None skips the overlay.

PRESETS: dict[str, Optional[dict[str, Any]]] = {
    "default": None,  # no-op — preserve the visual template's native cover.

    "minimal": {
        "header_fill":    "FFFFFF",
        "page_bg":        "FFFFFF",
        "headline_color": "0F172A",
        "subtitle_color": "64748B",
        "title_font_pt":  44,
        "use_hero_image": False,
        "overlay_fill":   None,
    },

    "bold": {
        "header_fill":    "brand",    # full-bleed brand color
        "page_bg":        "brand",
        "headline_color": "FFFFFF",
        "subtitle_color": "F1F5F9",
        "title_font_pt":  56,
        "use_hero_image": False,
        "overlay_fill":   None,
    },

    "corporate": {
        "header_fill":    "1E293B",   # slate-900
        "page_bg":        "FFFFFF",
        "headline_color": "FFFFFF",
        "subtitle_color": "CBD5E1",
        "title_font_pt":  40,
        "use_hero_image": False,
        "overlay_fill":   None,
    },

    "hero": {
        "header_fill":    None,       # hero image takes over the background
        "page_bg":        None,
        "headline_color": "FFFFFF",
        "subtitle_color": "F1F5F9",
        "title_font_pt":  50,
        "use_hero_image": True,
        "overlay_fill":   "000000",   # dark overlay for text legibility
    },

    "gradient": {
        "header_fill":    "brand",    # approximates gradient with brand color
        "page_bg":        "0F172A",   # dark bottom band (visual template's body)
        "headline_color": "FFFFFF",
        "subtitle_color": "E2E8F0",
        "title_font_pt":  48,
        "use_hero_image": False,
        "overlay_fill":   None,
    },
}


PRESET_KEYS = tuple(PRESETS.keys())


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
) -> None:
    """
    Apply a cover-page preset to slide[0] of the presentation.

    Safe to call with preset='default' — no-op. All modifications are
    wrapped in try/except so a preset failure never breaks generation.
    """
    if not preset or preset == "default":
        return

    config = PRESETS.get(preset)
    if not config:
        logger.warning("Unknown cover preset '%s' — skipping", preset)
        return

    try:
        cover = prs.slides[0]
    except Exception as exc:
        logger.warning("Could not access cover slide: %s", exc)
        return

    brand_hex = _normalise_hex(brand_color) or "4338CA"

    # 1) Background + header colours.
    try:
        _apply_colours(prs, cover, config, brand_hex)
    except Exception as exc:
        logger.debug("Cover preset colour apply failed: %s", exc)

    # 2) Hero image (only for the 'hero' preset when an image is supplied).
    if config.get("use_hero_image") and hero_image_url:
        try:
            _insert_hero_image(prs, cover, hero_image_url, config)
        except Exception as exc:
            logger.debug("Cover preset hero-image apply failed: %s", exc)

    # 3) Headline / subtitle text overrides.
    if headline or subtitle:
        try:
            _apply_text_overrides(cover, headline, subtitle, config)
        except Exception as exc:
            logger.debug("Cover preset text override failed: %s", exc)


# ---------------------------------------------------------------------------
# Step 1 — colours
# ---------------------------------------------------------------------------


def _apply_colours(prs: Any, cover: Any, config: dict, brand_hex: str) -> None:
    """
    Re-colour the cover's header-band shape and (optionally) the slide
    background. We identify the header band as the topmost full-width
    rectangular shape in the slide layout — this matches every visual
    template's cover pattern where the first shape at top is the coloured
    header.
    """
    from pptx.dml.color import RGBColor  # noqa: PLC0415

    header_fill = config.get("header_fill")
    page_bg     = config.get("page_bg")

    # Page background — set the entire slide's background fill when specified.
    if page_bg:
        rgb = _hex_to_rgb(_resolve_brand(page_bg, brand_hex))
        try:
            bg = cover.background
            bg.fill.solid()
            bg.fill.fore_color.rgb = RGBColor(*rgb)
        except Exception as exc:
            logger.debug("Cover: slide background fill failed: %s", exc)

    # Header band — recolour the first large rectangle we can find near the top.
    if header_fill:
        rgb = _hex_to_rgb(_resolve_brand(header_fill, brand_hex))
        header_shape = _find_header_band(cover, prs)
        if header_shape is not None:
            try:
                header_shape.fill.solid()
                header_shape.fill.fore_color.rgb = RGBColor(*rgb)
                # Remove any outline that fought with the new fill.
                try:
                    header_shape.line.fill.background()
                except Exception:
                    pass
            except Exception as exc:
                logger.debug("Cover: header-band recolour failed: %s", exc)


def _find_header_band(cover: Any, prs: Any) -> Optional[Any]:
    """
    Heuristic: find the topmost shape that spans at least 60% of slide
    width and sits in the top third. This is the header band across all
    six visual templates.
    """
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    min_w   = int(slide_w * 0.6)
    top_cap = int(slide_h * 0.33)

    candidates = []
    for shape in cover.shapes:
        # Skip picture shapes — we don't want to nuke the hero image.
        if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
            continue
        try:
            if shape.width and shape.width >= min_w and shape.top is not None and shape.top <= top_cap:
                candidates.append(shape)
        except Exception:
            continue
    if not candidates:
        return None
    # Pick the topmost (smallest `top`). Ties broken by largest width.
    candidates.sort(key=lambda s: (int(s.top or 0), -int(s.width or 0)))
    return candidates[0]


# ---------------------------------------------------------------------------
# Step 2 — hero image
# ---------------------------------------------------------------------------


def _insert_hero_image(prs: Any, cover: Any, image_url: str, config: dict) -> None:
    """
    Insert a full-bleed hero image behind all other shapes on the cover,
    optionally overlaid with a semi-dark rectangle for text legibility.
    """
    img_bytes = _download_image(image_url)
    if not img_bytes:
        return

    pic = cover.shapes.add_picture(
        io.BytesIO(img_bytes),
        0, 0,
        width=prs.slide_width,
        height=prs.slide_height,
    )
    # Send picture to the back of z-order.
    _send_to_back(cover, pic)

    # Optional dark overlay for text contrast.
    overlay_hex = config.get("overlay_fill")
    if overlay_hex:
        from pptx.dml.color import RGBColor  # noqa: PLC0415
        from pptx.util import Emu           # noqa: PLC0415

        rect = cover.shapes.add_shape(
            1,  # MSO_SHAPE.RECTANGLE
            Emu(0), Emu(0),
            prs.slide_width, prs.slide_height,
        )
        try:
            rect.fill.solid()
            rect.fill.fore_color.rgb = RGBColor(*_hex_to_rgb(overlay_hex))
            # ~55% opacity via alpha override on the solidFill's <a:srgbClr>.
            _set_shape_fill_alpha(rect, 55)
            rect.line.fill.background()
        except Exception as exc:
            logger.debug("Cover: overlay fill failed: %s", exc)
        # Put the overlay between hero image and text. Hero is at the back;
        # overlay sits above it but below text shapes already in the deck.
        _move_shape_after(cover, rect, pic)


# ---------------------------------------------------------------------------
# Step 3 — text overrides
# ---------------------------------------------------------------------------


_PLACEHOLDER_PATTERNS = [
    "{{report_title}}",
    "{{client_name}}",
    "performance report",
    "monthly performance",
]


def _apply_text_overrides(
    cover: Any,
    headline: Optional[str],
    subtitle: Optional[str],
    config: dict,
) -> None:
    """
    Replace the text on the cover's title + subtitle shapes.

    Heuristic for finding the title shape: largest text-bearing shape on
    the slide (by area) whose runs include a sizeable font. Subtitle is
    the next-largest text shape. Colour + optional font-size limits come
    from the preset config.
    """
    from pptx.dml.color import RGBColor  # noqa: PLC0415
    from pptx.util import Pt             # noqa: PLC0415

    text_shapes: list[tuple[int, Any]] = []
    for shape in cover.shapes:
        if not shape.has_text_frame:
            continue
        # Skip logo placeholder shapes — _embed_logos already handles these.
        txt = (shape.text_frame.text or "").strip().lower()
        if "agency_logo" in txt or "client_logo" in txt:
            continue
        try:
            area = int(shape.width or 0) * int(shape.height or 0)
        except Exception:
            area = 0
        text_shapes.append((area, shape))

    # Sort largest → smallest.
    text_shapes.sort(key=lambda t: -t[0])

    headline_color = _hex_to_rgb(config.get("headline_color") or "FFFFFF")
    subtitle_color = _hex_to_rgb(config.get("subtitle_color") or "E2E8F0")
    title_pt       = config.get("title_font_pt")

    if headline and text_shapes:
        _, shape = text_shapes[0]
        _set_text(shape, headline, color_rgb=headline_color,
                  font_pt=title_pt)
    if subtitle and len(text_shapes) >= 2:
        _, shape = text_shapes[1]
        _set_text(shape, subtitle, color_rgb=subtitle_color, font_pt=None)


def _set_text(shape: Any, text: str, *, color_rgb: tuple[int, int, int],
              font_pt: Optional[int]) -> None:
    from pptx.dml.color import RGBColor  # noqa: PLC0415
    from pptx.util import Pt             # noqa: PLC0415

    tf = shape.text_frame
    # Clear everything after paragraph 0 (we overwrite p0).
    while len(tf.paragraphs) > 1:
        p = tf.paragraphs[-1]._p
        p.getparent().remove(p)
    p0 = tf.paragraphs[0]
    # Remove existing runs so we can cleanly set our text.
    for r in list(p0.runs):
        r._r.getparent().remove(r._r)
    run = p0.add_run()
    run.text = text
    run.font.color.rgb = RGBColor(*color_rgb)
    if font_pt:
        run.font.size = Pt(font_pt)


# ---------------------------------------------------------------------------
# python-pptx z-order + alpha helpers
# ---------------------------------------------------------------------------


def _send_to_back(slide: Any, shape: Any) -> None:
    """Move a shape to the first position in the slide's spTree."""
    sp_tree = slide.shapes._spTree
    el = shape._element
    sp_tree.remove(el)
    # Insert after the mandatory <p:nvGrpSpPr> + <p:grpSpPr> children.
    sp_tree.insert(2, el)


def _move_shape_after(slide: Any, shape: Any, anchor: Any) -> None:
    """Move `shape` to sit immediately after `anchor` in the z-order."""
    sp_tree = slide.shapes._spTree
    sp_tree.remove(shape._element)
    # Insert after anchor element.
    idx = list(sp_tree).index(anchor._element)
    sp_tree.insert(idx + 1, shape._element)


def _set_shape_fill_alpha(shape: Any, alpha_percent: int) -> None:
    """
    Apply alpha to a solid-fill shape. python-pptx doesn't expose this
    directly — patch the underlying XML.
    """
    from lxml import etree  # noqa: PLC0415

    spPr = shape.fill._xPr
    nsmap = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    srgb_clr = spPr.find(".//a:solidFill/a:srgbClr", nsmap)
    if srgb_clr is None:
        return
    # Remove any existing alpha child.
    for child in srgb_clr.findall("a:alpha", nsmap):
        srgb_clr.remove(child)
    alpha = etree.SubElement(
        srgb_clr,
        "{http://schemas.openxmlformats.org/drawingml/2006/main}alpha",
    )
    # PowerPoint alpha is expressed in 1/100000ths.
    alpha.set("val", str(max(0, min(100, alpha_percent)) * 1000))


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


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = _normalise_hex(hex_str) or "4338CA"
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _resolve_brand(value: str, brand_hex: str) -> str:
    """Translate the special sentinel 'brand' to the actual brand hex."""
    if value == "brand":
        return brand_hex
    return value


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
