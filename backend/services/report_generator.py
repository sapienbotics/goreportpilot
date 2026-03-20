"""
Report generation orchestrator.
Combines python-pptx (PowerPoint) and ReportLab (PDF) with chart images.
Both functions are synchronous — call via asyncio.to_thread() in async endpoints.
"""
import io
import os
import logging
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
from reportlab.lib import colors as rl_colors

logger = logging.getLogger(__name__)


def _to_lines(value: Any) -> list[str]:
    """
    Normalise a narrative value to a flat list of non-empty lines.
    GPT-4o may return strings OR lists depending on the field; handle both.
    """
    if isinstance(value, list):
        # Each element may itself be a multi-line string — flatten
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


# ── PPTX brand colours ──────────────────────────────────────────────────────
_INDIGO        = RGBColor(0x43, 0x38, 0xCA)
_INDIGO_LIGHT  = RGBColor(0xC7, 0xD2, 0xFE)
_INDIGO_BG     = RGBColor(0xEE, 0xF2, 0xFF)
_WHITE         = RGBColor(0xFF, 0xFF, 0xFF)
_SLATE_900     = RGBColor(0x0F, 0x17, 0x2A)
_SLATE_700     = RGBColor(0x33, 0x41, 0x55)
_SLATE_400     = RGBColor(0x94, 0xA3, 0xB8)
_EMERALD       = RGBColor(0x05, 0x96, 0x69)
_ROSE          = RGBColor(0xE1, 0x1D, 0x48)

# ── ReportLab brand colours ─────────────────────────────────────────────────
_RL_INDIGO     = rl_colors.HexColor("#4338CA")
_RL_SLATE_900  = rl_colors.HexColor("#0F172A")
_RL_SLATE_700  = rl_colors.HexColor("#334155")
_RL_SLATE_400  = rl_colors.HexColor("#94A3B8")
_RL_EMERALD    = rl_colors.HexColor("#059669")
_RL_ROSE       = rl_colors.HexColor("#E11D48")
_RL_INDIGO_BG  = rl_colors.HexColor("#EEF2FF")
_RL_EMERALD_BG = rl_colors.HexColor("#F0FDF4")


# ── PPTX helpers ────────────────────────────────────────────────────────────

def _add_slide_header(slide: Any, title: str, slide_width: float) -> None:
    """Indigo header bar + white title text."""
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(slide_width), Inches(0.85))
    bar.fill.solid()
    bar.fill.fore_color.rgb = _INDIGO
    bar.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.4), Inches(0.08), Inches(slide_width - 0.8), Inches(0.7))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = _WHITE


def _add_footer(slide: Any, w: float, h: float) -> None:
    """Small gray footer: 'Prepared by ReportPilot'."""
    tb = slide.shapes.add_textbox(Inches(0.3), Inches(h - 0.28), Inches(w - 0.6), Inches(0.22))
    p = tb.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "Prepared by ReportPilot"
    run.font.size = Pt(8)
    run.font.italic = True
    run.font.color.rgb = _SLATE_400


def _text_box(
    slide: Any,
    text: str,
    left: float, top: float, width: float, height: float,
    font_size: int = 11,
    bold: bool = False,
    color: RGBColor | None = None,
    align: Any = PP_ALIGN.LEFT,
) -> None:
    color = color or _SLATE_700
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color


def _multiline_text_box(
    slide: Any,
    text: Any,   # str OR list — normalised via _to_lines
    left: float, top: float, width: float, height: float,
    font_size: int = 12,
    color: RGBColor | None = None,
    line_spacing_pt: int = 8,
) -> None:
    """Render multi-paragraph text, splitting on newlines. Accepts str or list."""
    color = color or _SLATE_700
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True

    paragraphs = _to_lines(text)
    for i, para in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(line_spacing_pt if i > 0 else 0)
        run = p.add_run()
        run.text = para.strip()
        run.font.size = Pt(font_size)
        run.font.color.rgb = color


def _format_change(change: float) -> tuple[str, RGBColor]:
    if change > 0:
        return f"+{change:.1f}%", _EMERALD
    if change < 0:
        return f"{change:.1f}%", _ROSE
    return "0.0%", _SLATE_400


# ── PowerPoint report ───────────────────────────────────────────────────────

def generate_pptx_report(
    data: Dict[str, Any],
    narrative: Dict[str, str],
    charts: Dict[str, str],
    client_info: Dict[str, Any],
) -> bytes:
    """
    Generate a branded PowerPoint report (8 slides).
    Returns raw bytes suitable for writing to disk or streaming as a download.
    """
    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)
    W, H = 13.33, 7.5

    blank = prs.slide_layouts[6]  # Blank layout

    ga4    = data.get("ga4", {}).get("summary", {})
    meta   = data.get("meta_ads", {}).get("summary", {})
    p_start = data.get("period_start", "")
    p_end   = data.get("period_end", "")
    client_name  = client_info.get("name", "Client")
    agency_name  = client_info.get("agency_name", "Your Agency")
    report_date  = datetime.now().strftime("%B %d, %Y")

    # ── Slide 1 — Cover ──────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank)

    # Full indigo background
    bg = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(W), Inches(H))
    bg.fill.solid(); bg.fill.fore_color.rgb = _INDIGO; bg.line.fill.background()

    # Thin white accent bar
    acc = slide.shapes.add_shape(1, Inches(1.0), Inches(3.35), Inches(2.5), Inches(0.07))
    acc.fill.solid(); acc.fill.fore_color.rgb = _WHITE; acc.line.fill.background()

    _text_box(slide, client_name, 1.0, 1.5, 11.33, 1.5, font_size=44, bold=True, color=_WHITE)
    _text_box(slide, "Monthly Performance Report", 1.0, 3.5, 11.33, 0.6, font_size=22, color=_INDIGO_LIGHT)
    _text_box(slide, f"{p_start}  →  {p_end}", 1.0, 4.25, 11.33, 0.5, font_size=14, color=_INDIGO_LIGHT)
    _text_box(
        slide,
        f"Prepared by {agency_name}  •  Powered by ReportPilot  •  {report_date}",
        1.0, 6.3, 11.33, 0.5, font_size=10, color=_INDIGO_LIGHT,
    )

    # ── Slide 2 — Executive Summary ─────────────────────────────────────────
    slide = prs.slides.add_slide(blank)
    _add_slide_header(slide, "Executive Summary", W)
    _multiline_text_box(
        slide, narrative.get("executive_summary", "Executive summary not available."),
        0.5, 1.0, W - 1.0, H - 1.8, font_size=13,
    )
    _add_footer(slide, W, H)

    # ── Slide 3 — KPI Scorecard ──────────────────────────────────────────────
    slide = prs.slides.add_slide(blank)
    _add_slide_header(slide, "Key Performance Indicators", W)

    roas       = meta.get("roas", 0)
    prev_roas  = meta.get("prev_roas", 0)
    roas_chg   = round((roas - prev_roas) / max(prev_roas, 0.01) * 100, 1) if prev_roas else 0.0
    cpa        = meta.get("cost_per_conversion", 0)
    prev_cpa   = meta.get("prev_cost_per_conversion", 0)
    cpa_chg    = round((cpa - prev_cpa) / max(prev_cpa, 0.01) * 100, 1) if prev_cpa else 0.0

    kpis = [
        ("Sessions",    f"{ga4.get('sessions', 0):,}",            ga4.get("sessions_change", 0)),
        ("Users",       f"{ga4.get('users', 0):,}",               ga4.get("users_change", 0)),
        ("Conversions", f"{ga4.get('conversions', 0):,}",         ga4.get("conversions_change", 0)),
        ("Ad Spend",    f"${meta.get('spend', 0):,.0f}",          meta.get("spend_change", 0)),
        ("ROAS",        f"{roas:.1f}x",                           roas_chg),
        ("Cost / Conv", f"${cpa:.2f}",                            -cpa_chg),  # lower is better
    ]

    col_x = [0.35, 4.55, 8.75]
    row_y = [1.1, 4.0]
    box_w, box_h = 4.0, 2.75

    for idx, (label, value, change) in enumerate(kpis):
        col, row = idx % 3, idx // 3
        x, y = col_x[col], row_y[row]

        # KPI card background
        card = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(box_w), Inches(box_h))
        card.fill.solid(); card.fill.fore_color.rgb = _INDIGO_BG
        card.line.color.rgb = _INDIGO_LIGHT; card.line.width = Pt(1)

        _text_box(slide, label.upper(), x + 0.2, y + 0.2, box_w - 0.4, 0.35,
                  font_size=8, bold=True, color=_SLATE_400)
        _text_box(slide, value, x + 0.2, y + 0.6, box_w - 0.4, 0.9,
                  font_size=26, bold=True, color=_SLATE_900)

        change_str, change_color = _format_change(float(change))
        _text_box(slide, f"{change_str} vs prev period", x + 0.2, y + 1.65, box_w - 0.4, 0.4,
                  font_size=10, bold=True, color=change_color)

    _add_footer(slide, W, H)

    # ── Slide 4 — Website Performance ───────────────────────────────────────
    slide = prs.slides.add_slide(blank)
    _add_slide_header(slide, "Website Performance", W)

    s_chart = charts.get("sessions")
    t_chart = charts.get("traffic_sources")
    if s_chart and os.path.exists(s_chart):
        slide.shapes.add_picture(s_chart, Inches(0.35), Inches(1.0), Inches(6.2), Inches(3.1))
    if t_chart and os.path.exists(t_chart):
        slide.shapes.add_picture(t_chart, Inches(6.85), Inches(1.0), Inches(6.1), Inches(3.1))

    _multiline_text_box(
        slide, narrative.get("website_performance", "Website data available."),
        0.35, 4.25, W - 0.7, 2.8, font_size=11,
    )
    _add_footer(slide, W, H)

    # ── Slide 5 — Meta Ads Performance ──────────────────────────────────────
    slide = prs.slides.add_slide(blank)
    _add_slide_header(slide, "Paid Advertising — Meta Ads", W)

    sc_chart = charts.get("spend_conversions")
    cp_chart  = charts.get("campaigns")
    if sc_chart and os.path.exists(sc_chart):
        slide.shapes.add_picture(sc_chart, Inches(0.35), Inches(1.0), Inches(6.2), Inches(3.1))
    if cp_chart and os.path.exists(cp_chart):
        slide.shapes.add_picture(cp_chart, Inches(6.85), Inches(1.0), Inches(6.1), Inches(3.1))

    _multiline_text_box(
        slide, narrative.get("paid_advertising", "Paid ads data available."),
        0.35, 4.25, W - 0.7, 2.8, font_size=11,
    )
    _add_footer(slide, W, H)

    # ── Slide 6 — Key Wins ──────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank)
    _add_slide_header(slide, "Key Wins This Month", W)
    _multiline_text_box(
        slide, narrative.get("key_wins", "✓ Data collected successfully"),
        0.5, 1.0, W - 1.0, H - 2.0, font_size=14, line_spacing_pt=10,
    )
    _add_footer(slide, W, H)

    # ── Slide 7 — Concerns & Recommendations ────────────────────────────────
    slide = prs.slides.add_slide(blank)
    _add_slide_header(slide, "Concerns & Recommendations", W)
    _multiline_text_box(
        slide, narrative.get("concerns", "⚠ No major concerns identified."),
        0.5, 1.0, W - 1.0, H - 2.0, font_size=14, line_spacing_pt=10,
    )
    _add_footer(slide, W, H)

    # ── Slide 8 — Next Steps ─────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank)
    _add_slide_header(slide, "Next Steps", W)
    _multiline_text_box(
        slide, narrative.get("next_steps", "1. Review report and share with client"),
        0.5, 1.0, W - 1.0, H - 2.0, font_size=14, line_spacing_pt=10,
    )
    _add_footer(slide, W, H)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    logger.info("PPTX report generated for %s", client_info.get("name"))
    return buf.read()


# ── PDF report ──────────────────────────────────────────────────────────────

def generate_pdf_report(
    data: Dict[str, Any],
    narrative: Dict[str, str],
    charts: Dict[str, str],
    client_info: Dict[str, Any],
) -> bytes:
    """
    Generate a clean, professional PDF report using ReportLab.
    Returns raw bytes suitable for writing to disk or streaming as a download.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1.0 * inch,
        bottomMargin=0.75 * inch,
    )

    ss = getSampleStyleSheet()

    # ── Custom paragraph styles ──────────────────────────────────────────────
    h1 = ParagraphStyle("RPH1", parent=ss["Heading1"],
                        fontSize=16, textColor=_RL_INDIGO, spaceBefore=14, spaceAfter=6, leading=20)
    body = ParagraphStyle("RPBody", parent=ss["Normal"],
                          fontSize=10, textColor=_RL_SLATE_700, spaceBefore=3, spaceAfter=3, leading=14)
    label_s = ParagraphStyle("RPLabel", parent=ss["Normal"],
                              fontSize=8, textColor=_RL_SLATE_400, spaceAfter=1, leading=10,
                              fontName="Helvetica-Bold")
    value_s = ParagraphStyle("RPValue", parent=ss["Normal"],
                              fontSize=18, textColor=_RL_SLATE_900, spaceAfter=2, leading=22,
                              fontName="Helvetica-Bold")
    chg_pos = ParagraphStyle("RPChgPos", parent=ss["Normal"],
                              fontSize=9, textColor=_RL_EMERALD, leading=12, fontName="Helvetica-Bold")
    chg_neg = ParagraphStyle("RPChgNeg", parent=ss["Normal"],
                              fontSize=9, textColor=_RL_ROSE,    leading=12, fontName="Helvetica-Bold")
    small   = ParagraphStyle("RPSmall", parent=ss["Normal"],
                              fontSize=8, textColor=_RL_SLATE_400, leading=10, alignment=TA_CENTER)

    ga4    = data.get("ga4", {}).get("summary", {})
    meta   = data.get("meta_ads", {}).get("summary", {})
    p_start     = data.get("period_start", "")
    p_end       = data.get("period_end", "")
    client_name = client_info.get("name", "Client")
    agency_name = client_info.get("agency_name", "Your Agency")
    report_date = datetime.now().strftime("%B %d, %Y")

    story = []

    # ── Cover header ─────────────────────────────────────────────────────────
    cover_style = ParagraphStyle(
        "RPCover", parent=ss["Normal"], fontSize=26, textColor=rl_colors.white,
        fontName="Helvetica-Bold", leading=32,
    )
    cover_bg_style = ParagraphStyle(
        "RPCoverBg", parent=ss["Normal"], fontSize=26, textColor=rl_colors.white,
        fontName="Helvetica-Bold", leading=32, backColor=_RL_INDIGO,
        leftIndent=-0.75 * 72, rightIndent=-0.75 * 72,
        borderPadding=(10, 10 + int(0.75 * 72), 10, 10 + int(0.75 * 72)),
    )
    story.append(Paragraph(client_name, cover_bg_style))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        f"Monthly Performance Report  •  {p_start} to {p_end}",
        ParagraphStyle("RPSub", parent=ss["Normal"], fontSize=11,
                       textColor=_RL_SLATE_400, spaceAfter=2),
    ))
    story.append(Paragraph(
        f"Prepared by {agency_name}  •  Powered by ReportPilot  •  {report_date}",
        ParagraphStyle("RPPrep", parent=ss["Normal"], fontSize=9,
                       textColor=_RL_SLATE_400, spaceAfter=6),
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_RL_INDIGO, spaceAfter=10))

    # ── Executive Summary ────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", h1))
    for line in _to_lines(narrative.get("executive_summary", "")):
        story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.1 * inch))

    # ── KPI table ────────────────────────────────────────────────────────────
    story.append(Paragraph("Key Performance Indicators", h1))

    def _chg(val: float) -> ParagraphStyle:
        return chg_pos if val >= 0 else chg_neg

    def _chg_str(val: float) -> str:
        return f"+{val:.1f}%" if val >= 0 else f"{val:.1f}%"

    s_chg = ga4.get("sessions_change", 0)
    u_chg = ga4.get("users_change", 0)
    c_chg = ga4.get("conversions_change", 0)
    sp_chg = meta.get("spend_change", 0)
    roas   = meta.get("roas", 0)
    proas  = meta.get("prev_roas", 0)
    roas_chg = round((roas - proas) / max(proas, 0.01) * 100, 1) if proas else 0.0
    cpa    = meta.get("cost_per_conversion", 0)
    pcpa   = meta.get("prev_cost_per_conversion", 0)
    cpa_chg = round((cpa - pcpa) / max(pcpa, 0.01) * 100, 1) if pcpa else 0.0

    kpi_rows = [
        # Row 0 — labels
        [Paragraph("SESSIONS", label_s),    Paragraph("USERS", label_s),       Paragraph("CONVERSIONS", label_s)],
        # Row 1 — values
        [Paragraph(f"{ga4.get('sessions', 0):,}", value_s),
         Paragraph(f"{ga4.get('users', 0):,}", value_s),
         Paragraph(f"{ga4.get('conversions', 0):,}", value_s)],
        # Row 2 — changes
        [Paragraph(_chg_str(s_chg), _chg(s_chg)),
         Paragraph(_chg_str(u_chg), _chg(u_chg)),
         Paragraph(_chg_str(c_chg), _chg(c_chg))],
        # Row 3 — labels
        [Paragraph("AD SPEND", label_s),    Paragraph("ROAS", label_s),         Paragraph("COST / CONV.", label_s)],
        # Row 4 — values
        [Paragraph(f"${meta.get('spend', 0):,.0f}", value_s),
         Paragraph(f"{roas:.1f}x", value_s),
         Paragraph(f"${cpa:.2f}", value_s)],
        # Row 5 — changes
        [Paragraph(_chg_str(sp_chg), _chg(sp_chg)),
         Paragraph(_chg_str(roas_chg), _chg(roas_chg)),
         Paragraph(_chg_str(-cpa_chg), _chg(-cpa_chg))],   # lower CPA = good
    ]

    col_w = (A4[0] - 1.5 * inch) / 3
    kpi_table = Table(kpi_rows, colWidths=[col_w] * 3)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (2, 2), _RL_INDIGO_BG),
        ("BACKGROUND",    (0, 3), (2, 5), _RL_EMERALD_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",     (0, 2), (2, 2), 3, rl_colors.white),
        ("LINEABOVE",     (0, 3), (2, 3), 3, rl_colors.white),
        ("GRID",          (0, 0), (-1, -1), 0.5, rl_colors.white),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.15 * inch))

    # ── Website Performance ──────────────────────────────────────────────────
    story.append(Paragraph("Website Performance", h1))
    s_chart = charts.get("sessions")
    t_chart = charts.get("traffic_sources")
    if s_chart and os.path.exists(s_chart):
        story.append(RLImage(s_chart, width=6.5 * inch, height=2.8 * inch))
        story.append(Spacer(1, 0.05 * inch))
    if t_chart and os.path.exists(t_chart):
        story.append(RLImage(t_chart, width=6.5 * inch, height=2.8 * inch))
        story.append(Spacer(1, 0.05 * inch))
    for line in _to_lines(narrative.get("website_performance", "")):
        story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.1 * inch))

    # ── Paid Advertising ─────────────────────────────────────────────────────
    story.append(Paragraph("Paid Advertising — Meta Ads", h1))
    sc_chart = charts.get("spend_conversions")
    cp_chart  = charts.get("campaigns")
    if sc_chart and os.path.exists(sc_chart):
        story.append(RLImage(sc_chart, width=6.5 * inch, height=2.8 * inch))
        story.append(Spacer(1, 0.05 * inch))
    if cp_chart and os.path.exists(cp_chart):
        story.append(RLImage(cp_chart, width=6.5 * inch, height=2.8 * inch))
        story.append(Spacer(1, 0.05 * inch))
    for line in _to_lines(narrative.get("paid_advertising", "")):
        story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.1 * inch))

    # ── Key Wins ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Key Wins", h1))
    for line in _to_lines(narrative.get("key_wins", "")):
        story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.1 * inch))

    # ── Concerns & Recommendations ───────────────────────────────────────────
    story.append(Paragraph("Concerns & Recommendations", h1))
    for line in _to_lines(narrative.get("concerns", "")):
        story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.1 * inch))

    # ── Next Steps ────────────────────────────────────────────────────────────
    story.append(Paragraph("Next Steps", h1))
    for line in _to_lines(narrative.get("next_steps", "")):
        story.append(Paragraph(line, body))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_RL_SLATE_400))
    story.append(Paragraph(
        f"Generated by ReportPilot  •  {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        small,
    ))

    doc.build(story)
    buf.seek(0)
    logger.info("PDF report generated for %s", client_info.get("name"))
    return buf.read()
