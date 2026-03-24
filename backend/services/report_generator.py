"""
Report generation orchestrator.
Template-based PPTX generation + ReportLab PDF fallback.
Both functions are synchronous — call via asyncio.to_thread() in async endpoints.
"""
import io
import os
import logging
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, Any

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN  # type: ignore[attr-defined]

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER  # noqa: F401
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.platypus import Image as RLImage
from reportlab.platypus import PageBreak
from reportlab.lib import colors as rl_colors
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# ── Register DejaVu Sans for PDF Unicode rendering (₹ € £ ¥ etc.) ───────────
_PDF_BODY_FONT = "Helvetica"
_PDF_BOLD_FONT = "Helvetica-Bold"
try:
    import matplotlib.font_manager as _fm
    from reportlab.pdfbase import pdfmetrics as _pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as _TTFont

    _djv_regular = _fm.findfont(_fm.FontProperties(family="DejaVu Sans", style="normal", weight="regular"))
    _djv_bold    = _fm.findfont(_fm.FontProperties(family="DejaVu Sans", style="normal", weight="bold"))
    _pdfmetrics.registerFont(_TTFont("DejaVu",      _djv_regular))
    _pdfmetrics.registerFont(_TTFont("DejaVu-Bold", _djv_bold))
    _PDF_BODY_FONT = "DejaVu"
    _PDF_BOLD_FONT = "DejaVu-Bold"
    logger.info("DejaVu Sans registered for PDF — Unicode currency symbols will render correctly")
except Exception as _font_err:
    logger.warning(
        "Could not register DejaVu Sans for PDF (%s) — "
        "non-ASCII currency symbols (₹ € £) may render as black squares",
        _font_err,
    )

# ── Static file root (logos served by FastAPI StaticFiles mount at /static) ──
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

# ── Branding helpers ─────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> RGBColor:
    """Convert a #RRGGBB hex string to RGBColor. Returns default indigo on parse error."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 6:
            return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except (ValueError, AttributeError):
        pass
    return RGBColor(0x43, 0x38, 0xCA)  # default indigo


def _delete_shape(slide: Any, shape: Any) -> None:
    """Remove a shape element from a slide entirely."""
    try:
        sp = shape._element
        sp.getparent().remove(sp)
    except Exception as exc:
        logger.debug("Could not delete shape: %s", exc)


def _hex_to_rl(hex_color: str):
    """Convert a #RRGGBB hex string to a ReportLab HexColor."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 6:
            return rl_colors.HexColor(f"#{h}")
    except (ValueError, AttributeError):
        pass
    return _RL_INDIGO


def _download_image(url: str) -> io.BytesIO | None:
    """Return image bytes as BytesIO from a URL or local static path."""
    if not url:
        return None
    local_subpath: str | None = None
    if url.startswith("/static/"):
        local_subpath = url[len("/static/"):]
    else:
        import re as _re
        _m = _re.match(r"https?://localhost(?::\d+)?/static/(.*)", url)
        if _m:
            local_subpath = _m.group(1)
    if local_subpath is not None:
        file_path = os.path.join(_STATIC_DIR, local_subpath)
        try:
            with open(file_path, "rb") as _fh:
                return io.BytesIO(_fh.read())
        except Exception as exc:
            logger.warning("Could not read local logo file %s: %s", file_path, exc)
            return None
    try:
        import httpx as _httpx
        response = _httpx.get(url, timeout=10, follow_redirects=True)
        if response.status_code == 200:
            return io.BytesIO(response.content)
        logger.warning("Logo download returned status %s for URL: %s", response.status_code, url)
    except Exception as exc:
        logger.warning("Logo download failed (%s): %s", url, exc)
    return None


# ── Currency symbol lookup ───────────────────────────────────────────────────
_CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",   "EUR": "€",   "GBP": "£",   "INR": "₹",
    "AUD": "A$",  "CAD": "C$",  "JPY": "¥",   "CNY": "¥",
    "BRL": "R$",  "MXN": "Mex$","SGD": "S$",  "HKD": "HK$",
    "CHF": "CHF ","SEK": "kr",  "NOK": "kr",  "DKK": "kr",
    "ZAR": "R",   "AED": "AED ","SAR": "SAR ","MYR": "RM",
}


def _currency_symbol(data: Dict[str, Any]) -> str:
    code = data.get("meta_ads", {}).get("currency", "USD") or "USD"
    return _CURRENCY_SYMBOLS.get(code.upper(), code + " ")


def _section_enabled(enabled_sections: dict | None, key: str) -> bool:
    if enabled_sections is None:
        return True
    return bool(enabled_sections.get(key, True))


def _to_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            if isinstance(item, str):
                lines.extend(item.splitlines())
            else:
                lines.append(str(item))
        return [l for l in lines if l.strip()]
    if isinstance(value, str):
        return [l for l in value.splitlines() if l.strip()]
    return []


# ── Colour constants ────────────────────────────────────────────────────────
_INDIGO        = RGBColor(0x43, 0x38, 0xCA)
_WHITE         = RGBColor(0xFF, 0xFF, 0xFF)
_SLATE_900     = RGBColor(0x0F, 0x17, 0x2A)
_SLATE_700     = RGBColor(0x33, 0x41, 0x55)
_SLATE_500     = RGBColor(0x64, 0x74, 0x8B)
_SLATE_400     = RGBColor(0x94, 0xA3, 0xB8)
_SLATE_200     = RGBColor(0xE2, 0xE8, 0xF0)
_SLATE_100     = RGBColor(0xF1, 0xF5, 0xF9)
_EMERALD       = RGBColor(0x05, 0x96, 0x69)
_AMBER         = RGBColor(0xD9, 0x77, 0x06)
_ROSE          = RGBColor(0xE1, 0x1D, 0x48)

_RL_INDIGO     = rl_colors.HexColor("#4338CA")
_RL_SLATE_900  = rl_colors.HexColor("#0F172A")
_RL_SLATE_700  = rl_colors.HexColor("#334155")
_RL_SLATE_500  = rl_colors.HexColor("#64748B")
_RL_SLATE_400  = rl_colors.HexColor("#94A3B8")
_RL_SLATE_200  = rl_colors.HexColor("#E2E8F0")
_RL_SLATE_100  = rl_colors.HexColor("#F1F5F9")
_RL_SLATE_50   = rl_colors.HexColor("#F8FAFC")
_RL_EMERALD    = rl_colors.HexColor("#059669")
_RL_AMBER      = rl_colors.HexColor("#D97706")
_RL_ROSE       = rl_colors.HexColor("#E11D48")


# ═══════════════════════════════════════════════════════════════════════════════
# ── Template-based PowerPoint report generator ─────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

from services.slide_selector import (
    select_slides, select_kpis, get_slides_to_delete,
    SLIDE_INDEX, TOTAL_TEMPLATE_SLIDES,
)
from services.text_formatter import parse_structured_text

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "templates", "pptx")

VISUAL_TEMPLATES = {
    "modern_clean":    os.path.join(_TEMPLATES_DIR, "modern_clean.pptx"),
    "dark_executive":  os.path.join(_TEMPLATES_DIR, "dark_executive.pptx"),
    "colorful_agency": os.path.join(_TEMPLATES_DIR, "colorful_agency.pptx"),
    "bold_geometric":  os.path.join(_TEMPLATES_DIR, "bold_geometric.pptx"),
    "minimal_elegant": os.path.join(_TEMPLATES_DIR, "minimal_elegant.pptx"),
    "gradient_modern": os.path.join(_TEMPLATES_DIR, "gradient_modern.pptx"),
}

# Legacy 9-slide mapping (for backwards compatibility with existing templates)
SLIDE_MAP = {
    "cover": 0,
    "executive_summary": 1,
    "kpi_scorecard": 2,
    "website_traffic": 3,
    "meta_ads": 4,
    "key_wins": 5,
    "concerns": 6,
    "next_steps": 7,
    "custom_section": 8,
}

# New 19-slide mapping from slide_selector
SLIDE_MAP_V2 = SLIDE_INDEX


def _fmt_num(val: Any) -> str:
    """Format a number with comma separators."""
    try:
        return f"{int(val):,}"
    except (ValueError, TypeError):
        return str(val) if val else "0"


def _fmt_change(val: float | None) -> str:
    """Format a percentage change value."""
    if val is None:
        return "N/A"
    return f"+{val:.1f}%" if val >= 0 else f"{val:.1f}%"


def _narrative_to_text(content: Any) -> str:
    """Convert narrative content (str or list) to plain text."""
    if isinstance(content, list):
        return "\n\n".join(str(item) for item in content if str(item).strip())
    return str(content) if content else ""


def _list_to_text(content: Any) -> str:
    """Convert list content to newline-separated text."""
    if isinstance(content, list):
        return "\n".join(str(item) for item in content if str(item).strip())
    if isinstance(content, str):
        return content
    return ""


def _build_replacements(
    data: Dict[str, Any],
    narrative: Dict[str, str],
    client_info: Dict[str, Any],
    branding: dict | None,
    custom_section: dict | None,
) -> dict[str, str]:
    """Build the {{placeholder}} → value replacement dictionary."""
    br = branding or {}
    cur_sym = _currency_symbol(data)

    # Smart KPI selection — pick the 6 best KPIs from available data
    smart_kpis = select_kpis(data, currency_symbol=cur_sym)
    kpis = [
        (k["label"], k["value"], k["change"] or "")
        for k in smart_kpis
    ]
    # Pad to 6 if fewer available
    while len(kpis) < 6:
        kpis.append(("", "", ""))

    agency_name = br.get("agency_name") or client_info.get("agency_name") or "Your Agency"
    report_date = datetime.now().strftime("%B %d, %Y")
    p_start = data.get("period_start", "")
    p_end   = data.get("period_end", "")

    replacements = {
        "{{client_name}}":           client_info.get("name", "Client"),
        "{{report_period}}":         f"{p_start} to {p_end}",
        "{{agency_name}}":           agency_name,
        "{{agency_email}}":          br.get("agency_email", ""),
        "{{report_type}}":           "Performance Report",
        "{{report_date}}":           report_date,
        "{{executive_summary}}":     _narrative_to_text(narrative.get("executive_summary", "")),
        "{{website_narrative}}":     _narrative_to_text(narrative.get("website_performance", "")),
        "{{ads_narrative}}":         _narrative_to_text(narrative.get("paid_advertising", "")),
        "{{key_wins}}":              _list_to_text(narrative.get("key_wins", "")),
        "{{concerns}}":              _list_to_text(narrative.get("concerns", "")),
        "{{next_steps}}":            _list_to_text(narrative.get("next_steps", "")),
        "{{custom_section_title}}":  (custom_section or {}).get("title", "Additional Notes"),
        "{{custom_section_text}}":   (custom_section or {}).get("text", ""),
        "{{footer_text}}":           f"{agency_name} \u2022 Confidential \u2022 {report_date}",
        "{{agency_logo}}":           "",  # Cleared — actual image embedded by _embed_logos()
        "{{client_logo}}":           "",  # Cleared — actual image embedded by _embed_logos()
    }

    # KPI placeholders
    for i, (label, value, change) in enumerate(kpis):
        replacements[f"{{{{kpi_{i}_label}}}}"]  = label
        replacements[f"{{{{kpi_{i}_value}}}}"]  = value
        replacements[f"{{{{kpi_{i}_change}}}}"] = change

    return replacements


def _replace_placeholders_in_slide(slide: Any, replacements: dict[str, str]) -> None:
    """Find and replace all {{placeholder}} text in a slide, preserving formatting."""
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for paragraph in shape.text_frame.paragraphs:
            # Combine all runs to find placeholders that may span runs
            full_text = "".join(run.text for run in paragraph.runs)
            matched = False
            for placeholder, value in replacements.items():
                if placeholder in full_text:
                    full_text = full_text.replace(placeholder, str(value))
                    matched = True
            if matched and paragraph.runs:
                # Put all text in the first run (preserving its formatting), clear others
                paragraph.runs[0].text = full_text
                for run in paragraph.runs[1:]:
                    run.text = ""


def _replace_charts(prs: Any, charts: Dict[str, str]) -> None:
    """Replace chart placeholder text boxes with actual chart PNG images.

    When a chart file exists: embeds the PNG and clears the placeholder text.
    When no chart is available: deletes the placeholder shape entirely
    (since our slide selector guarantees we only show slides with data).
    """
    chart_mapping = {
        # GA4 charts
        "{{chart_sessions}}":           charts.get("sessions"),
        "{{chart_traffic}}":            charts.get("traffic_sources"),
        "{{chart_device_breakdown}}":   charts.get("device_breakdown"),
        "{{chart_top_pages}}":          charts.get("top_pages"),
        "{{chart_new_vs_returning}}":   charts.get("new_vs_returning"),
        "{{chart_top_countries}}":      charts.get("top_countries"),
        "{{chart_bounce_rate}}":        charts.get("bounce_rate_trend"),
        "{{chart_conversion_funnel}}":  charts.get("conversion_funnel"),
        # Meta Ads charts
        "{{chart_spend}}":              charts.get("spend_conversions"),
        "{{chart_campaigns}}":          charts.get("campaigns"),
        "{{chart_demographics}}":       charts.get("audience_demographics"),
        "{{chart_placements}}":         charts.get("placements"),
        # Google Ads charts
        "{{chart_gads_spend}}":         charts.get("gads_spend_conversions"),
        "{{chart_gads_campaigns}}":     charts.get("gads_campaigns"),
        "{{chart_search_terms}}":       charts.get("search_terms_bar"),
        # Search Console charts
        "{{chart_seo_trend}}":          charts.get("seo_clicks_trend"),
        "{{chart_top_queries}}":        charts.get("top_queries"),
    }

    # Add CSV chart mappings dynamically
    for key, path in charts.items():
        if key.startswith("csv_"):
            chart_mapping[f"{{{{chart_{key}}}}}"] = path

    available = [v for v in chart_mapping.values() if v]
    logger.debug("_replace_charts: %d chart paths available: %s",
                 len(available), list(charts.keys()))

    replaced = 0
    for slide in prs.slides:
        shapes_to_process: list[tuple] = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            for placeholder, chart_path in chart_mapping.items():
                if placeholder in text:
                    shapes_to_process.append((shape, chart_path, placeholder))
                    break

        for shape, chart_path, placeholder in shapes_to_process:
            # ── Chart file exists → embed image ──────────────────────────
            if chart_path and os.path.exists(chart_path):
                slide.shapes.add_picture(
                    chart_path,
                    shape.left, shape.top,
                    shape.width, shape.height,
                )
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        run.text = ""
                replaced += 1
                logger.debug("Replaced %s with image %s", placeholder, chart_path)
                continue

            # ── No chart data → show fallback message ────────────────────
            logger.info("No chart file for %s — showing fallback text", placeholder)
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    run.text = ""
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = "No data available for this period"
            run.font.size = Pt(11)
            run.font.color.rgb = _SLATE_400
            run.font.italic = True

    logger.info("_replace_charts: %d/%d chart placeholders replaced with images",
                replaced, len(available))


def _colorize_kpi_changes(prs: Any, data: Dict[str, Any]) -> None:
    """Color KPI change values on the KPI slide (index 2).

    Finds text matching change patterns (+X.X%, -X.X%, N/A) and applies:
      - Green (#059669) for positive changes
      - Red (#E11D48) for negative changes
      - Gray (#94A3B8) for N/A
    """
    # Target KPI slide specifically (index 2) and the cover/exec slides
    # where change text won't appear, but be safe and scan all slides
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    text = run.text.strip()
                    if not text:
                        continue
                    # Positive change: "+12.3%" or "+12.3% vs prev period"
                    if text.startswith("+") and "%" in text:
                        run.font.color.rgb = _EMERALD
                        run.font.bold = True
                    # Negative change: "-5.2%" or "-5.2% vs prev period"
                    elif text.startswith("-") and "%" in text:
                        run.font.color.rgb = _ROSE
                        run.font.bold = True
                    # N/A
                    elif text == "N/A":
                        run.font.color.rgb = _SLATE_400


def _get_slides_to_delete(
    enabled_sections: dict | None,
    template: str,
    narrative: Dict[str, str],
    custom_section: dict | None,
) -> set[int]:
    """Determine which slide indices to delete based on config and content."""
    to_delete: set[int] = set()
    es = enabled_sections or {}

    section_slide_map = {
        "executive_summary": 1,
        "kpi_scorecard": 2,
        "website_traffic": 3,
        "meta_ads": 4,
        "key_wins": 5,
        "concerns": 6,
        "next_steps": 7,
        "custom_section": 8,
    }

    for section_key, slide_idx in section_slide_map.items():
        # Delete if explicitly disabled
        if section_key in es and not es[section_key]:
            to_delete.add(slide_idx)
            continue

        # Delete custom section if no content
        if section_key == "custom_section":
            cs = custom_section or {}
            if not cs.get("title") or not cs.get("text", "").strip():
                to_delete.add(slide_idx)
        # Delete narrative sections if empty
        elif section_key in ("key_wins", "concerns", "next_steps",
                             "executive_summary"):
            content = narrative.get(section_key, "")
            lines = _to_lines(content)
            if not lines:
                to_delete.add(slide_idx)

    # Template-level filtering
    if template == "summary":
        # Summary keeps: cover, exec summary, KPI, key_wins/next_steps
        to_delete.update({3, 4, 6, 8})  # website, meta_ads, concerns, custom
    elif template == "brief":
        # Brief keeps: cover, exec summary, KPI only
        to_delete.update({3, 4, 5, 6, 7, 8})

    return to_delete


def _embed_logos(prs: Any, branding: dict | None) -> None:
    """Embed agency and client logos on the cover slide.

    When an image URL is provided: download and embed it at the placeholder position.
    When no image is provided: DELETE the placeholder shape so no empty box appears.
    """
    cover = prs.slides[0]

    # Locate placeholder shapes by their text content
    agency_logo_shape = None
    client_logo_shape = None
    for shape in list(cover.shapes):
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text.strip()
        if "agency_logo" in text.lower():
            agency_logo_shape = shape
        elif "client_logo" in text.lower():
            client_logo_shape = shape

    br = branding or {}

    # ── Agency logo ───────────────────────────────────────────────────────────
    agency_img = _download_image(br.get("agency_logo_url", ""))
    if agency_img and agency_logo_shape:
        try:
            agency_img.seek(0)
            cover.shapes.add_picture(
                agency_img,
                agency_logo_shape.left, agency_logo_shape.top,
                height=agency_logo_shape.height,
            )
            _delete_shape(cover, agency_logo_shape)   # remove placeholder text box
        except Exception as e:
            logger.debug("Could not embed agency logo: %s", e)
    elif agency_img:
        # No placeholder found — fall back to top-right corner
        try:
            agency_img.seek(0)
            sw = prs.slide_width
            cover.shapes.add_picture(agency_img, sw - Inches(2.2), Inches(0.3), height=Inches(0.8))
        except Exception as e:
            logger.debug("Could not embed agency logo (fallback): %s", e)
    else:
        # No logo provided — delete the empty placeholder so it doesn't clutter the slide
        if agency_logo_shape:
            _delete_shape(cover, agency_logo_shape)

    # ── Client logo ───────────────────────────────────────────────────────────
    client_img = _download_image(br.get("client_logo_url", ""))
    if client_img and client_logo_shape:
        try:
            client_img.seek(0)
            cover.shapes.add_picture(
                client_img,
                client_logo_shape.left, client_logo_shape.top,
                height=client_logo_shape.height,
            )
            _delete_shape(cover, client_logo_shape)   # remove placeholder text box
        except Exception as e:
            logger.debug("Could not embed client logo: %s", e)
    elif client_img:
        try:
            client_img.seek(0)
            sw = prs.slide_width
            cover.shapes.add_picture(
                client_img,
                (sw - Inches(2.0)) // 2, Inches(5.5),
                height=Inches(1.5),
            )
        except Exception as e:
            logger.debug("Could not embed client logo (fallback): %s", e)
    else:
        if client_logo_shape:
            _delete_shape(cover, client_logo_shape)


def _embed_custom_section_image(prs: Any, custom_section: dict | None, slide_index: int) -> None:
    """
    Embed an uploaded image on the custom section slide.
    Adjusts text area width if image is present.
    """
    if not custom_section:
        return
    image_url = custom_section.get("image_url", "")
    if not image_url:
        return

    # Get the custom section slide
    if slide_index >= len(prs.slides):
        return
    slide = prs.slides[slide_index]

    img_data = _download_image(image_url)
    if not img_data:
        return

    try:
        img_data.seek(0)
        # Place image on right side (35% of slide width)
        slide_w = prs.slide_width
        slide_h = prs.slide_height
        img_w = int(slide_w * 0.35)
        img_x = slide_w - img_w - Inches(0.3)
        img_y = Inches(1.5)
        img_h = int(slide_h * 0.55)
        slide.shapes.add_picture(img_data, img_x, img_y, width=img_w, height=img_h)

        # Narrow the text area on this slide to avoid overlap
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text
                if "custom_section_text" in text or (shape.left < Inches(1) and shape.top > Inches(1.2)):
                    # Limit width to 60% of slide
                    shape.width = int(slide_w * 0.60)
                    break
        logger.info("Custom section image embedded successfully")
    except Exception as e:
        logger.warning("Could not embed custom section image: %s", e)


def _populate_text_frame_formatted(
    text_frame: Any,
    content: str,
    font_size: Any = None,
    font_color: Any = None,
    bold: bool = False,
) -> None:
    """
    Replace a text frame's content with properly-formatted multi-paragraph text.
    Splits content on double newlines into separate paragraphs.
    Preserves font name and size from the template's first run where possible.
    """
    import re as _re

    if not content or not content.strip():
        text_frame.clear()
        return

    # Capture template formatting from first paragraph / first run
    template_name: str | None = None
    template_size: Any = font_size
    template_color: Any = font_color
    template_bold: bool = bold
    try:
        first_para = text_frame.paragraphs[0]
        if first_para.runs:
            r0 = first_para.runs[0]
            if r0.font.name:
                template_name = r0.font.name
            if r0.font.size:
                template_size = r0.font.size
            if r0.font.color and r0.font.color.type is not None:
                try:
                    template_color = r0.font.color.rgb
                except Exception:
                    pass
            if r0.font.bold is not None:
                template_bold = r0.font.bold
    except Exception:
        pass

    text_frame.clear()

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [content.strip()]

    for i, para_text in enumerate(paragraphs):
        p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
        p.space_after  = Pt(6)
        p.space_before = Pt(0)

        run = p.add_run()
        run.text = para_text
        if template_name:
            run.font.name = template_name
        if template_size:
            run.font.size = template_size
        if template_color:
            run.font.color.rgb = template_color
        run.font.bold = template_bold


def _populate_bullet_list(
    text_frame: Any,
    content: str,
    prefix: str = "•",
    font_size: Any = None,
    font_color: Any = None,
    prefix_color: Any = None,
) -> None:
    """
    Replace a text frame's content with a formatted bullet list.
    Splits content on single newlines into individual items.
    Strips any existing prefix chars (✓ ⚠ • numbered) before re-adding prefix.
    """
    import re as _re

    if not content or not content.strip():
        text_frame.clear()
        return

    # Capture template formatting
    template_name: str | None = None
    template_size: Any = font_size
    template_color: Any = font_color
    try:
        first_para = text_frame.paragraphs[0]
        if first_para.runs:
            r0 = first_para.runs[0]
            if r0.font.name:
                template_name = r0.font.name
            if r0.font.size:
                template_size = r0.font.size
            if r0.font.color and r0.font.color.type is not None:
                try:
                    template_color = r0.font.color.rgb
                except Exception:
                    pass
    except Exception:
        pass

    text_frame.clear()

    items = [item.strip() for item in content.split("\n") if item.strip()]

    for i, item_text in enumerate(items):
        p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
        p.space_after  = Pt(8)
        p.space_before = Pt(2)

        # Strip any existing prefix that AI or previous code may have added
        clean = item_text
        for strip_pfx in ("✓ ", "⚠ ", "• ", "→ ", "- "):
            if clean.startswith(strip_pfx):
                clean = clean[len(strip_pfx):]
                break
        # Strip numbered prefixes like "1. " or "2) "
        clean = _re.sub(r"^\d+[.)]\s*", "", clean)

        # Prefix run (bold, coloured)
        if prefix:
            pr = p.add_run()
            pr.text = f"{prefix}  "
            if template_name:
                pr.font.name = template_name
            if template_size:
                pr.font.size = template_size
            pr.font.bold = True
            if prefix_color:
                pr.font.color.rgb = prefix_color

        # Content run
        cr = p.add_run()
        cr.text = clean
        if template_name:
            cr.font.name = template_name
        if template_size:
            cr.font.size = template_size
        if template_color:
            cr.font.color.rgb = template_color


# Keys that get formatted population instead of plain text replacement.
# These are popped from replacements before the generic pass so the
# generic _replace_placeholders_in_slide() doesn't flatten them first.
_NARRATIVE_KEYS = {
    "{{executive_summary}}",
    "{{website_narrative}}",
    "{{ads_narrative}}",
}
_LIST_KEYS = {
    "{{key_wins}}",
    "{{concerns}}",
    "{{next_steps}}",
}
_FORMATTED_KEYS = _NARRATIVE_KEYS | _LIST_KEYS


def generate_pptx_report(
    data: Dict[str, Any],
    narrative: Dict[str, str],
    charts: Dict[str, str],
    client_info: Dict[str, Any],
    enabled_sections: dict | None = None,
    template: str = "full",
    custom_section: dict | None = None,
    branding: dict | None = None,
    visual_template: str = "modern_clean",
) -> bytes:
    """
    Generate a report by populating a pre-designed PPTX template.

    Uses adaptive slide selection: only includes slides with actual data.
    Never shows empty slides or N/A KPIs.

    Args:
        data:             Combined data dict (ga4, meta_ads, google_ads, search_console, csv_sources).
        narrative:        AI-generated narrative sections dict.
        charts:           {chart_name: file_path} for PNG chart images.
        client_info:      Dict with "name", "agency_name".
        enabled_sections: Per-client section toggles (all True by default).
        template:         "full" | "summary" | "brief" — detail level.
        custom_section:   {"title": str, "text": str} for the optional custom section.
        branding:         Agency branding dict.
        visual_template:  "modern_clean" | "dark_executive" | "colorful_agency" | etc.

    Returns raw bytes suitable for writing to disk or streaming as a download.
    """
    # Load the visual template
    template_path = VISUAL_TEMPLATES.get(visual_template, VISUAL_TEMPLATES["modern_clean"])
    if not os.path.exists(template_path):
        logger.warning("Visual template %s not found, falling back to modern_clean", visual_template)
        template_path = VISUAL_TEMPLATES["modern_clean"]

    prs = Presentation(template_path)
    num_slides = len(prs.slides)

    # Determine whether this is a legacy 9-slide template or new 19-slide template
    use_legacy = num_slides <= 10
    logger.info("Template %s has %d slides — using %s slide mapping",
                visual_template, num_slides, "legacy" if use_legacy else "v2")

    # Build the full replacement map, then split out the keys that get
    # rich formatting (paragraphs / bullet lists) so the generic pass
    # doesn't flatten them to a single unstyled run first.
    replacements = _build_replacements(data, narrative, client_info, branding, custom_section)
    formatted_content: dict[str, str] = {}
    for key in _FORMATTED_KEYS:
        if key in replacements:
            formatted_content[key] = replacements.pop(key)

    # Also add new narrative keys for expanded sections
    extra_narratives = {
        "{{google_ads_narrative}}": _narrative_to_text(narrative.get("google_ads_performance", "")),
        "{{seo_narrative}}": _narrative_to_text(narrative.get("seo_performance", "")),
    }
    for k, v in extra_narratives.items():
        if v:
            formatted_content[k] = v
        else:
            replacements[k] = ""  # Clear unused placeholders

    # ── Generic pass: single-value placeholders (names, KPIs, dates, logos) ─
    for slide in prs.slides:
        _replace_placeholders_in_slide(slide, replacements)

    # ── Formatted pass: narrative paragraphs ──────────────────────────────────
    if use_legacy:
        # Legacy 9-slide mapping
        _NARRATIVE_SLIDES = {
            1: "{{executive_summary}}",
            3: "{{website_narrative}}",
            4: "{{ads_narrative}}",
        }
        _LIST_SLIDES = {
            5: ("{{key_wins}}",    "\u2713", RGBColor(0x05, 0x96, 0x69)),
            6: ("{{concerns}}",   "\u26A0", RGBColor(0xD9, 0x77, 0x06)),
            7: ("{{next_steps}}", "\u2192", _hex_to_rgb((branding or {}).get("brand_color") or "#4338CA")),
        }
    else:
        # New 19-slide mapping
        _NARRATIVE_SLIDES = {
            SLIDE_INDEX["executive_summary"]:   "{{executive_summary}}",
            SLIDE_INDEX["website_traffic"]:     "{{website_narrative}}",
            SLIDE_INDEX["meta_ads_overview"]:   "{{ads_narrative}}",
            SLIDE_INDEX["google_ads_overview"]: "{{google_ads_narrative}}",
            SLIDE_INDEX["seo_overview"]:        "{{seo_narrative}}",
            SLIDE_INDEX.get("website_engagement", 4):   "{{website_narrative}}",
            SLIDE_INDEX.get("website_audience", 5):     "{{website_narrative}}",
            SLIDE_INDEX.get("bounce_rate_analysis", 6): "{{website_narrative}}",
            SLIDE_INDEX.get("meta_ads_audience", 8):    "{{ads_narrative}}",
            SLIDE_INDEX.get("meta_ads_creative", 9):    "{{ads_narrative}}",
            SLIDE_INDEX.get("google_ads_keywords", 11): "{{google_ads_narrative}}",
            SLIDE_INDEX.get("conversion_funnel", 14):   "{{website_narrative}}",
        }
        _LIST_SLIDES = {
            SLIDE_INDEX["key_wins"]:   ("{{key_wins}}",    "\u2713", RGBColor(0x05, 0x96, 0x69)),
            SLIDE_INDEX["concerns"]:   ("{{concerns}}",   "\u26A0", RGBColor(0xD9, 0x77, 0x06)),
            SLIDE_INDEX["next_steps"]: ("{{next_steps}}", "\u2192", _hex_to_rgb((branding or {}).get("brand_color") or "#4338CA")),
        }

    for slide_idx, placeholder_key in _NARRATIVE_SLIDES.items():
        if slide_idx >= len(prs.slides):
            continue
        content = formatted_content.get(placeholder_key, "")
        if not content:
            continue
        slide = prs.slides[slide_idx]
        for shape in slide.shapes:
            if shape.has_text_frame and placeholder_key in shape.text_frame.text:
                _populate_text_frame_formatted(shape.text_frame, content)
                break

    for slide_idx, (placeholder_key, prefix, prefix_color) in _LIST_SLIDES.items():
        if slide_idx >= len(prs.slides):
            continue
        content = formatted_content.get(placeholder_key, "")
        if not content:
            continue
        slide = prs.slides[slide_idx]
        for shape in slide.shapes:
            if shape.has_text_frame and placeholder_key in shape.text_frame.text:
                _populate_bullet_list(shape.text_frame, content,
                                      prefix=prefix, prefix_color=prefix_color)
                break

    # ── Custom section rich formatting ─────────────────────────────────────────
    cs = custom_section or {}
    cs_text = cs.get("text", "")
    if cs_text:
        cs_slide_idx = SLIDE_INDEX.get("custom_section", 18) if not use_legacy else 8
        if cs_slide_idx < len(prs.slides):
            cs_slide = prs.slides[cs_slide_idx]
            for shape in cs_slide.shapes:
                if shape.has_text_frame and "{{custom_section_text}}" in shape.text_frame.text:
                    # Apply rich formatting using text_formatter
                    from services.text_formatter import parse_structured_text as _parse
                    blocks = _parse(cs_text)
                    tf = shape.text_frame
                    tf.clear()
                    brand_color = _hex_to_rgb((branding or {}).get("brand_color") or "#4338CA")
                    for block in blocks:
                        p = tf.add_paragraph()
                        p.space_after = Pt(4)
                        if block["type"] == "header":
                            run = p.add_run()
                            run.text = block["text"]
                            run.font.bold = True
                            run.font.size = Pt(14)
                            run.font.color.rgb = brand_color
                        elif block["type"] == "bullet":
                            pr = p.add_run()
                            pr.text = "•  "
                            pr.font.bold = True
                            pr.font.color.rgb = brand_color
                            cr = p.add_run()
                            cr.text = block["text"]
                            cr.font.size = Pt(11)
                        elif block["type"] == "numbered":
                            pr = p.add_run()
                            pr.text = f"{block['number']}.  "
                            pr.font.bold = True
                            pr.font.color.rgb = brand_color
                            cr = p.add_run()
                            cr.text = block["text"]
                            cr.font.size = Pt(11)
                        else:
                            run = p.add_run()
                            run.text = block["text"]
                            run.font.size = Pt(11)
                    break

    # ── Charts ────────────────────────────────────────────────────────────────
    _replace_charts(prs, charts)

    # ── KPI colour coding ─────────────────────────────────────────────────────
    _colorize_kpi_changes(prs, data)

    # ── Logos ─────────────────────────────────────────────────────────────────
    _embed_logos(prs, branding)

    # ── Custom section image ─────────────────────────────────────────────────
    if not use_legacy:
        custom_slide_idx = SLIDE_INDEX.get("custom_section", 18)
        _embed_custom_section_image(prs, custom_section, custom_slide_idx)
    else:
        _embed_custom_section_image(prs, custom_section, 8)  # legacy index

    # ── Smart slide deletion ──────────────────────────────────────────────────
    if use_legacy:
        # Legacy behavior for existing 9-slide templates
        slides_to_delete = _get_slides_to_delete(enabled_sections, template, narrative, custom_section)
    else:
        # New adaptive selection for 19-slide templates
        selected = select_slides(data, template, custom_section, narrative)
        slides_to_delete = get_slides_to_delete(
            selected, len(data.get("csv_sources", []))
        )

    # Delete in reverse order to preserve indices
    for idx in sorted(slides_to_delete, reverse=True):
        if idx < len(prs.slides):
            try:
                rId = prs.slides._sldIdLst[idx].rId
                prs.part.drop_rel(rId)
                del prs.slides._sldIdLst[idx]
            except Exception as e:
                logger.warning("Could not delete slide %d: %s", idx, e)

    # Save to bytes
    output = io.BytesIO()
    prs.save(output)
    logger.info("PPTX report generated for %s (detail=%s, visual=%s, slides=%d)",
                client_info.get("name"), template, visual_template, len(prs.slides))
    return output.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# ── PDF report — PPTX→PDF via LibreOffice with ReportLab fallback ──────────
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdf_report(
    data: Dict[str, Any],
    narrative: Dict[str, str],
    charts: Dict[str, str],
    client_info: Dict[str, Any],
    enabled_sections: dict | None = None,
    template: str = "full",
    custom_section: dict | None = None,
    branding: dict | None = None,
    visual_template: str = "modern_clean",
) -> bytes:
    """
    Generate PDF by first creating PPTX then converting via LibreOffice.
    Falls back to the ReportLab-based PDF generator if LibreOffice is unavailable.
    """
    # First generate the PPTX
    pptx_bytes = generate_pptx_report(
        data, narrative, charts, client_info,
        enabled_sections, template, custom_section, branding, visual_template,
    )

    # Try LibreOffice conversion
    with tempfile.TemporaryDirectory() as tmpdir:
        pptx_path = os.path.join(tmpdir, "report.pptx")
        with open(pptx_path, "wb") as f:
            f.write(pptx_bytes)

        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmpdir, pptx_path],
                timeout=60, check=True, capture_output=True,
            )
            pdf_path = os.path.join(tmpdir, "report.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    logger.info("PDF generated via LibreOffice for %s", client_info.get("name"))
                    return f.read()
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.info("LibreOffice not available (%s), falling back to ReportLab PDF", e)

    # Fallback: ReportLab-based PDF
    return _generate_pdf_reportlab(
        data, narrative, charts, client_info,
        enabled_sections, template, custom_section, branding,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ── ReportLab PDF fallback ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_pdf_reportlab(
    data: Dict[str, Any],
    narrative: Dict[str, str],
    charts: Dict[str, str],
    client_info: Dict[str, Any],
    enabled_sections: dict | None = None,
    template: str = "full",
    custom_section: dict | None = None,
    branding: dict | None = None,
) -> bytes:
    """
    Generate a clean PDF report using ReportLab (used when LibreOffice is unavailable).
    """
    _br         = branding or {}
    agency_name = _br.get("agency_name") or client_info.get("agency_name") or "Your Agency"
    _brand_rl   = _hex_to_rl(_br.get("brand_color") or "#4338CA")

    agency_logo_img = _download_image(_br.get("agency_logo_url", ""))
    client_logo_img = _download_image(_br.get("client_logo_url", ""))

    ga4         = data.get("ga4", {}).get("summary", {})
    meta        = data.get("meta_ads", {}).get("summary", {})
    p_start     = data.get("period_start", "")
    p_end       = data.get("period_end", "")
    client_name = client_info.get("name", "Client")
    report_date = datetime.now().strftime("%B %d, %Y")
    cur_sym     = _currency_symbol(data)
    _page_w, _page_h = A4
    _lm = 0.75 * inch

    # ── Canvas callbacks ──────────────────────────────────────────────────────
    def _draw_cover_canvas(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        band_h = 1.6 * inch
        canvas.setFillColor(_brand_rl)
        canvas.rect(0, _page_h - band_h, _page_w, band_h, fill=1, stroke=0)
        canvas.setFillColor(rl_colors.white)
        canvas.setFont(_PDF_BOLD_FONT, 12)
        canvas.drawString(_lm, _page_h - 0.9 * inch, agency_name.upper())
        canvas.setFont(_PDF_BODY_FONT, 9)
        canvas.drawString(_lm, _page_h - 1.18 * inch, "CLIENT PERFORMANCE REPORT")
        if agency_logo_img:
            try:
                agency_logo_img.seek(0)
                canvas.drawImage(
                    ImageReader(agency_logo_img),
                    _page_w - 2.3 * inch, _page_h - 1.42 * inch,
                    width=1.6 * inch, height=0.8 * inch,
                    preserveAspectRatio=True, mask="auto",
                )
            except Exception:
                pass
        _draw_pdf_footer(canvas, doc)
        canvas.restoreState()

    def _draw_content_canvas(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        y_line = _page_h - 0.55 * inch
        canvas.setStrokeColor(_brand_rl)
        canvas.setLineWidth(1.5)
        canvas.line(_lm, y_line, _page_w - _lm, y_line)
        canvas.setFont(_PDF_BODY_FONT, 8)
        canvas.setFillColor(_RL_SLATE_500)
        canvas.drawString(_lm, _page_h - 0.42 * inch, agency_name)
        canvas.drawRightString(_page_w - _lm, _page_h - 0.42 * inch, f"Page {doc.page}")
        _draw_pdf_footer(canvas, doc)
        canvas.restoreState()

    def _draw_pdf_footer(canvas: Any, doc: Any) -> None:
        canvas.setStrokeColor(_RL_SLATE_200)
        canvas.setLineWidth(0.5)
        canvas.line(_lm, 0.52 * inch, _page_w - _lm, 0.52 * inch)
        canvas.setFont(_PDF_BODY_FONT, 8)
        canvas.setFillColor(_RL_SLATE_400)
        canvas.drawString(_lm, 0.34 * inch,
                          f"Prepared by {agency_name}  \u2022  Confidential  \u2022  {report_date}")
        canvas.drawRightString(_page_w - _lm, 0.34 * inch, f"Page {doc.page}")

    # ── Doc setup ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=_lm, leftMargin=_lm,
        topMargin=1.75 * inch, bottomMargin=0.75 * inch,
    )
    ss = getSampleStyleSheet()

    h1 = ParagraphStyle("RPH1", parent=ss["Heading1"],
                        fontSize=18, textColor=_brand_rl, spaceBefore=18, spaceAfter=4,
                        leading=22, fontName=_PDF_BOLD_FONT)
    body = ParagraphStyle("RPBody", parent=ss["Normal"],
                          fontSize=11, textColor=_RL_SLATE_700, spaceBefore=4, spaceAfter=4,
                          leading=18, fontName=_PDF_BODY_FONT)
    label_s = ParagraphStyle("RPLabel", parent=ss["Normal"],
                              fontSize=9, textColor=_RL_SLATE_400, spaceAfter=2, leading=11,
                              fontName=_PDF_BOLD_FONT)
    value_s = ParagraphStyle("RPValue", parent=ss["Normal"],
                              fontSize=20, textColor=_RL_SLATE_900, spaceAfter=2, leading=24,
                              fontName=_PDF_BOLD_FONT)
    chg_pos = ParagraphStyle("RPChgPos", parent=ss["Normal"],
                              fontSize=10, textColor=_RL_EMERALD, leading=13, fontName=_PDF_BOLD_FONT)
    chg_neg = ParagraphStyle("RPChgNeg", parent=ss["Normal"],
                              fontSize=10, textColor=_RL_ROSE,    leading=13, fontName=_PDF_BOLD_FONT)
    chg_na  = ParagraphStyle("RPChgNa",  parent=ss["Normal"],
                              fontSize=10, textColor=_RL_SLATE_400, leading=13, fontName=_PDF_BODY_FONT)

    def _chg_style(val: float | None) -> ParagraphStyle:
        if val is None: return chg_na
        return chg_pos if val >= 0 else chg_neg

    def _section_heading(title: str) -> None:
        story.append(Paragraph(title, h1))
        story.append(HRFlowable(width="100%", thickness=1.0, color=_brand_rl, spaceAfter=8))

    # KPI data
    s_chg    = ga4.get("sessions_change")
    u_chg    = ga4.get("users_change")
    c_chg    = ga4.get("conversions_change")
    sp_chg   = meta.get("spend_change")
    roas     = meta.get("roas") or 0.0
    proas    = meta.get("prev_roas") or 0.0
    roas_chg = round((roas - proas) / max(proas, 0.01) * 100, 1) if proas else None
    cpa      = meta.get("cost_per_conversion") or 0.0
    pcpa     = meta.get("prev_cost_per_conversion") or 0.0
    cpa_chg  = round((cpa - pcpa) / max(pcpa, 0.01) * 100, 1) if pcpa else None

    template_label = {"summary": "Summary Report", "brief": "Executive Brief"}.get(template, "Full Performance Report")

    # ── Story ──────────────────────────────────────────────────────────────────
    story: list[Any] = []

    # Cover page
    story.append(Paragraph(
        client_name,
        ParagraphStyle("RPClientName", parent=ss["Normal"],
                       fontSize=30, textColor=_RL_SLATE_900, fontName=_PDF_BOLD_FONT,
                       leading=36, spaceBefore=6, spaceAfter=10),
    ))
    if client_logo_img:
        try:
            client_logo_img.seek(0)
            _clogo = RLImage(client_logo_img, width=1.4 * inch, height=1.4 * inch)
            _clogo.hAlign = "LEFT"
            story.append(_clogo)
            story.append(Spacer(1, 0.1 * inch))
        except Exception:
            pass
    story.append(Paragraph(
        f"{template_label}  \u2022  {p_start} to {p_end}",
        ParagraphStyle("RPSub", parent=ss["Normal"], fontSize=13,
                       textColor=_RL_SLATE_500, fontName=_PDF_BODY_FONT, leading=17, spaceAfter=6),
    ))
    story.append(Paragraph(
        f"Prepared by {agency_name}  \u2022  Powered by ReportPilot  \u2022  {report_date}",
        ParagraphStyle("RPPrep", parent=ss["Normal"], fontSize=10,
                       textColor=_RL_SLATE_400, fontName=_PDF_BODY_FONT, leading=14, spaceAfter=16),
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_brand_rl, spaceAfter=0))
    story.append(PageBreak())

    # Executive Summary
    if _section_enabled(enabled_sections, "executive_summary"):
        _exec = _to_lines(narrative.get("executive_summary", ""))
        if _exec:
            _section_heading("Executive Summary")
            for line in _exec:
                story.append(Paragraph(line, body))
            story.append(Spacer(1, 0.15 * inch))

    # KPI Scorecard
    if _section_enabled(enabled_sections, "kpi_scorecard"):
        _section_heading("Key Performance Indicators")
        col_w = (_page_w - 2 * _lm) / 3
        _neg_cpa = -cpa_chg if cpa_chg is not None else None

        def _kpi_cell(lbl, val, chg):
            return [Paragraph(lbl, label_s), Paragraph(val, value_s),
                    Paragraph(_fmt_change(chg), _chg_style(chg))]

        kpi_data = [
            [_kpi_cell("SESSIONS", f"{ga4.get('sessions',0):,}", s_chg),
             _kpi_cell("USERS", f"{ga4.get('users',0):,}", u_chg),
             _kpi_cell("CONVERSIONS", f"{ga4.get('conversions',0):,}", c_chg)],
            [_kpi_cell("AD SPEND", f"{cur_sym}{meta.get('spend',0):,.0f}", sp_chg),
             _kpi_cell("ROAS", f"{roas:.1f}x", roas_chg),
             _kpi_cell("COST / CONV.", f"{cur_sym}{cpa:.2f}", _neg_cpa)],
        ]
        kpi_table = Table(kpi_data, colWidths=[col_w] * 3, rowHeights=[1.05 * inch] * 2)
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (2, 0), _RL_SLATE_100),
            ("BACKGROUND", (0, 1), (2, 1), _RL_SLATE_50),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 1.5, rl_colors.white),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 0.2 * inch))

    # Website Performance
    if _section_enabled(enabled_sections, "website_traffic"):
        s_chart = charts.get("sessions")
        t_chart = charts.get("traffic_sources")
        _web = _to_lines(narrative.get("website_performance", ""))
        if (s_chart and os.path.exists(s_chart)) or (t_chart and os.path.exists(t_chart)) or _web:
            _section_heading("Website Performance")
            for c in [s_chart, t_chart]:
                if c and os.path.exists(c):
                    img = RLImage(c, width=6.5 * inch, height=2.9 * inch)
                    img.hAlign = "CENTER"
                    story.append(img)
                    story.append(Spacer(1, 0.1 * inch))
            for line in _web:
                story.append(Paragraph(line, body))
            story.append(Spacer(1, 0.15 * inch))

    # Paid Advertising
    if _section_enabled(enabled_sections, "meta_ads"):
        sc = charts.get("spend_conversions")
        cp = charts.get("campaigns")
        _ads = _to_lines(narrative.get("paid_advertising", ""))
        if (sc and os.path.exists(sc)) or (cp and os.path.exists(cp)) or _ads:
            _section_heading("Paid Advertising \u2014 Meta Ads")
            for c in [sc, cp]:
                if c and os.path.exists(c):
                    img = RLImage(c, width=6.5 * inch, height=2.9 * inch)
                    img.hAlign = "CENTER"
                    story.append(img)
                    story.append(Spacer(1, 0.1 * inch))
            for line in _ads:
                story.append(Paragraph(line, body))
            story.append(Spacer(1, 0.15 * inch))

    # Key Wins
    if _section_enabled(enabled_sections, "key_wins"):
        _wins = _to_lines(narrative.get("key_wins", ""))
        if _wins:
            _section_heading("Key Wins")
            win_s = ParagraphStyle("RPWin", parent=body, leftIndent=16, firstLineIndent=-16, spaceAfter=6)
            for line in _wins:
                clean = line.lstrip("\u2022\u2713\u2714\u26A0-\u2013\u2014 ").strip()
                if clean:
                    story.append(Paragraph(f'<font color="#059669"><b>\u2713</b></font>\u2002{clean}', win_s))
            story.append(Spacer(1, 0.15 * inch))

    # Concerns
    if _section_enabled(enabled_sections, "concerns"):
        _concerns = _to_lines(narrative.get("concerns", ""))
        if _concerns:
            _section_heading("Concerns & Recommendations")
            con_s = ParagraphStyle("RPCon", parent=body, leftIndent=16, firstLineIndent=-16, spaceAfter=6)
            for line in _concerns:
                clean = line.lstrip("\u2022\u2713\u2714\u26A0-\u2013\u2014 ").strip()
                if clean:
                    story.append(Paragraph(f'<font color="#D97706"><b>\u26A0</b></font>\u2002{clean}', con_s))
            story.append(Spacer(1, 0.15 * inch))

    # Next Steps
    if _section_enabled(enabled_sections, "next_steps"):
        _steps = _to_lines(narrative.get("next_steps", ""))
        if _steps:
            _section_heading("Next Steps")
            step_s = ParagraphStyle("RPStep", parent=body, leftIndent=20, firstLineIndent=-20, spaceAfter=8)
            bc = _br.get("brand_color", "#4338CA")
            for i, line in enumerate(_steps, 1):
                clean = line.lstrip("0123456789.)- ").strip()
                if clean:
                    story.append(Paragraph(f'<font color="{bc}"><b>{i}.</b></font>\u2002{clean}', step_s))
            story.append(Spacer(1, 0.1 * inch))

    # Custom Section
    if (_section_enabled(enabled_sections, "custom_section")
            and custom_section and custom_section.get("title") and custom_section.get("text")):
        _cl = _to_lines(custom_section["text"])
        if _cl:
            _section_heading(custom_section["title"])
            for line in _cl:
                story.append(Paragraph(line, body))

    # Build
    doc.build(story, onFirstPage=_draw_cover_canvas, onLaterPages=_draw_content_canvas)
    buf.seek(0)
    logger.info("PDF report (ReportLab) generated for %s", client_info.get("name"))
    return buf.read()
