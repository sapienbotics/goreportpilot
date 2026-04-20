"""
Theme Layout Spec — single source of truth (Python side).

Measured once from the 6 template PPTX files via python-pptx. The
frontend has a mirror of this same data in
`frontend/src/lib/theme-layout.ts`; any change here MUST be mirrored
there (same coordinates, same field names).

Per-theme fields:
  slide_inches                 — {width, height}
  client_name_box              — position/size of the {{client_name}} shape
  client_name_align            — v2.1: per-theme alignment ("left"|"center"|
                                 "right"). Matches designer intent from the
                                 pre-strip template paragraphs. 5/6 themes
                                 are "left", minimal_elegant is "center".
  report_period_box            — position/size of the {{report_period}} shape
                                 (the "natural" y before any subtitle shift)
  report_period_align          — v2.1: per-theme alignment, same values as
                                 client_name_align.
  subtitle_box                 — v2.1 fix (DA2 Option B-1). Where the user's
                                 cover subtitle (tagline) renders when set.
                                 Occupies the original period slot — when
                                 subtitle is present, the period is shifted
                                 down by subtitle.h + a small gap. When
                                 subtitle is absent, period renders at its
                                 report_period_box coords unchanged.
  subtitle_font                — v2.1: font spec for the tagline. Mid-tier
                                 sizing (between headline and period) so the
                                 tagline reads as secondary to headline but
                                 more prominent than the period line.
  header_band                  — the recolourable header band (None if the
                                 template's top decoration is multi-shape
                                 or side-based — see `brand_tint_strategy`)
  agency_logo_placeholder      — default position for the agency logo
  client_logo_placeholder      — default position for the client logo
  client_name_font / report_period_font
                               — template defaults; preview matches these
  brand_tint_strategy          — "header_band" | "none"
                                 If "none", brand_primary colour does NOT
                                 tint the cover (applies to charts only).
                                 Three templates use multi-colour cover
                                 decoration that would break under a single
                                 recolour.
  agency_attribution           — v2 fix (D-D Option D-1). Where to draw
                                 "Prepared by <agency_name>" at generate
                                 time. Coordinates + font measured from
                                 the pre-strip template masters so the
                                 restored text sits exactly where the
                                 designer originally placed it. Some
                                 themes place it inside the tinted band
                                 (modern_clean, gradient_modern), others
                                 in the footer. Optional — set to None
                                 to skip drawing it for a theme.

All coordinates in SLIDE INCHES (1 inch = 914400 EMU).
"""
from __future__ import annotations

from typing import Any, Optional


THEME_LAYOUT: dict[str, dict[str, Any]] = {
    "modern_clean": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 2.70, "w": 11.7, "h": 1.5},
        "client_name_align":      "left",
        "report_period_box":      {"x": 0.8, "y": 4.35, "w": 11.7, "h": 0.5},
        "report_period_align":    "left",
        "subtitle_box":           {"x": 0.8, "y": 4.35, "w": 11.7, "h": 0.4},
        "subtitle_font":          {"name": "Calibri", "size_pt": 18, "color_hex": "64748B", "bold": False},
        "header_band":            {"x": 0.0, "y": 0.00, "w": 13.3, "h": 2.2},
        "agency_logo_placeholder":{"x": 10.5, "y": 0.40, "w": 2.0, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.50, "w": 2.5, "h": 1.5},
        "client_name_font":       {"name": "Calibri",       "size_pt": 40, "color_hex": "0F172A", "bold": True},
        "report_period_font":     {"name": "Calibri Light", "size_pt": 14, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "header_band",
        # Attribution sits INSIDE the tinted band. Original designer hue
        # C7D2FE (indigo-200) reads as "light text on brand tint".
        "agency_attribution":     {
            "box":   {"x": 0.8, "y": 1.15, "w": 6.0, "h": 0.35},
            "font":  {"name": "Calibri Light", "size_pt": 11, "color_hex": "C7D2FE", "bold": False},
            "align": "left",
        },
    },

    "dark_executive": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 2.50, "w": 11.7, "h": 1.5},
        "client_name_align":      "left",
        "report_period_box":      {"x": 0.8, "y": 4.15, "w":  8.0, "h": 0.45},
        "report_period_align":    "left",
        "subtitle_box":           {"x": 0.8, "y": 4.15, "w":  8.0, "h": 0.4},
        "subtitle_font":          {"name": "Calibri", "size_pt": 18, "color_hex": "CBD5E1", "bold": False},
        # A thin accent line (4-tenths of an inch thick); still a single shape
        # so brand tint works. If the template is ever redesigned the dark
        # navy body is achieved via slide-background, not a band shape.
        "header_band":            {"x": 0.0, "y": 2.00, "w": 13.3, "h": 0.04},
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.00, "w": 2.5, "h": 1.8},
        "client_name_font":       {"name": "Calibri", "size_pt": 40, "color_hex": "F8FAFC", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 14, "color_hex": "CBD5E1", "bold": False},
        "brand_tint_strategy":    "header_band",
        # Attribution in the footer on dark-navy body — slate-700 reads as
        # subdued muted text per designer intent.
        "agency_attribution":     {
            "box":   {"x": 0.8, "y": 6.70, "w": 8.0, "h": 0.35},
            "font":  {"name": "Calibri", "size_pt": 11, "color_hex": "475569", "bold": False},
            "align": "left",
        },
    },

    "colorful_agency": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 1.80, "w": 11.7, "h": 1.6},
        "client_name_align":      "left",
        "report_period_box":      {"x": 0.8, "y": 3.60, "w":  8.0, "h": 0.45},
        "report_period_align":    "left",
        "subtitle_box":           {"x": 0.8, "y": 3.60, "w":  8.0, "h": 0.4},
        "subtitle_font":          {"name": "Calibri", "size_pt": 18, "color_hex": "64748B", "bold": False},
        # No single band — template uses 3 coloured strips at top + a left
        # sidebar. Brand-colour recolour would collapse the palette.
        "header_band":            None,
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 3.80, "w": 2.5, "h": 1.8},
        "client_name_font":       {"name": "Calibri", "size_pt": 40, "color_hex": "0F172A", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 14, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "none",
        "agency_attribution":     {
            "box":   {"x": 0.8, "y": 6.80, "w": 8.0, "h": 0.35},
            "font":  {"name": "Calibri", "size_pt": 11, "color_hex": "94A3B8", "bold": False},
            "align": "left",
        },
    },

    "bold_geometric": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 2.00, "w":  7.0, "h": 1.8},
        "client_name_align":      "left",
        "report_period_box":      {"x": 0.8, "y": 3.90, "w":  6.0, "h": 0.45},
        "report_period_align":    "left",
        "subtitle_box":           {"x": 0.8, "y": 3.90, "w":  6.0, "h": 0.4},
        "subtitle_font":          {"name": "Calibri", "size_pt": 20, "color_hex": "C7D2FE", "bold": False},
        # No single band — right-side coloured block + asymmetric layout.
        "header_band":            None,
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.00, "w": 2.5, "h": 1.8},
        "client_name_font":       {"name": "Calibri", "size_pt": 44, "color_hex": "FFFFFF", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 16, "color_hex": "C7D2FE", "bold": False},
        "brand_tint_strategy":    "none",
        # Attribution in footer on the left (white) side — indigo-300 accent.
        "agency_attribution":     {
            "box":   {"x": 0.8, "y": 6.80, "w": 8.0, "h": 0.35},
            "font":  {"name": "Calibri", "size_pt": 11, "color_hex": "A5B4FC", "bold": False},
            "align": "left",
        },
    },

    "minimal_elegant": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 1.5, "y": 2.40, "w": 10.3, "h": 1.4},
        "client_name_align":      "center",
        "report_period_box":      {"x": 1.5, "y": 4.30, "w": 10.3, "h": 0.4},
        "report_period_align":    "center",
        # Serif subtitle continues the editorial voice of the headline.
        "subtitle_box":           {"x": 1.5, "y": 4.30, "w": 10.3, "h": 0.4},
        "subtitle_font":          {"name": "Georgia", "size_pt": 16, "color_hex": "64748B", "bold": False},
        # Deliberately no band — minimalist layout depends on white space.
        "header_band":            None,
        "agency_logo_placeholder":{"x": 1.5, "y": 0.80, "w": 2.0, "h": 0.8},
        "client_logo_placeholder":{"x": 5.4, "y": 5.50, "w": 2.5, "h": 1.0},
        "client_name_font":       {"name": "Georgia", "size_pt": 40, "color_hex": "0F172A", "bold": False},
        "report_period_font":     {"name": "Calibri", "size_pt": 14, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "none",
        # Center-aligned footer attribution — editorial style.
        "agency_attribution":     {
            "box":   {"x": 1.5, "y": 6.90, "w": 10.3, "h": 0.3},
            "font":  {"name": "Calibri", "size_pt": 9, "color_hex": "94A3B8", "bold": False},
            "align": "center",
        },
    },

    "gradient_modern": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 3.10, "w": 11.7, "h": 1.5},
        "client_name_align":      "left",
        "report_period_box":      {"x": 0.8, "y": 4.70, "w":  8.0, "h": 0.45},
        "report_period_align":    "left",
        "subtitle_box":           {"x": 0.8, "y": 4.70, "w":  8.0, "h": 0.4},
        "subtitle_font":          {"name": "Calibri", "size_pt": 20, "color_hex": "64748B", "bold": False},
        # Multi-shape gradient band at top. The leftmost (index 0) spans
        # the full width; recolouring it approximates the brand-tint
        # effect acceptably.
        "header_band":            {"x": 0.0, "y": 0.00, "w": 13.3, "h": 2.6},
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.50, "w": 2.5, "h": 1.5},
        "client_name_font":       {"name": "Calibri", "size_pt": 42, "color_hex": "0F172A", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 16, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "header_band",
        # Attribution inside the gradient band — rose-200 reads as warm
        # light text on coloured background.
        "agency_attribution":     {
            "box":   {"x": 0.8, "y": 1.20, "w": 6.0, "h": 0.35},
            "font":  {"name": "Calibri", "size_pt": 11, "color_hex": "FECDD3", "bold": False},
            "align": "left",
        },
    },
}


# v2.1: exposed constant for the period-shift-on-subtitle amount. Kept as
# a module-level value so both backend render + frontend overlay can use
# the exact same offset.
SUBTITLE_PERIOD_GAP = 0.10


VALID_THEMES = tuple(THEME_LAYOUT.keys())


def get(theme: str) -> dict[str, Any]:
    """Return the layout spec for a theme, falling back to modern_clean."""
    return THEME_LAYOUT.get(theme) or THEME_LAYOUT["modern_clean"]


def supports_brand_tint(theme: str) -> bool:
    """True when the theme's cover has a recolourable header band."""
    return get(theme).get("brand_tint_strategy") == "header_band"


def header_band_box(theme: str) -> Optional[dict[str, float]]:
    """Return the header-band coord box for themes that support it."""
    return get(theme).get("header_band")
