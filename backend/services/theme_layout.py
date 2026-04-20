"""
Theme Layout Spec — single source of truth (Python side).

Measured once from the 6 template PPTX files via python-pptx. The
frontend has a mirror of this same data in
`frontend/src/lib/theme-layout.ts`; any change here MUST be mirrored
there (same coordinates, same field names).

Per-theme fields:
  slide_inches                 — {width, height}
  client_name_box              — position/size of the {{client_name}} shape
  report_period_box            — position/size of the {{report_period}} shape
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

All coordinates in SLIDE INCHES (1 inch = 914400 EMU).
"""
from __future__ import annotations

from typing import Any, Optional


THEME_LAYOUT: dict[str, dict[str, Any]] = {
    "modern_clean": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 2.70, "w": 11.7, "h": 1.5},
        "report_period_box":      {"x": 0.8, "y": 4.35, "w": 11.7, "h": 0.5},
        "header_band":            {"x": 0.0, "y": 0.00, "w": 13.3, "h": 2.2},
        "agency_logo_placeholder":{"x": 10.5, "y": 0.40, "w": 2.0, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.50, "w": 2.5, "h": 1.5},
        "client_name_font":       {"name": "Calibri",       "size_pt": 40, "color_hex": "0F172A", "bold": True},
        "report_period_font":     {"name": "Calibri Light", "size_pt": 14, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "header_band",
    },

    "dark_executive": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 2.50, "w": 11.7, "h": 1.5},
        "report_period_box":      {"x": 0.8, "y": 4.15, "w":  8.0, "h": 0.45},
        # A thin accent line (4-tenths of an inch thick); still a single shape
        # so brand tint works. If the template is ever redesigned the dark
        # navy body is achieved via slide-background, not a band shape.
        "header_band":            {"x": 0.0, "y": 2.00, "w": 13.3, "h": 0.04},
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.00, "w": 2.5, "h": 1.8},
        "client_name_font":       {"name": "Calibri", "size_pt": 40, "color_hex": "F8FAFC", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 14, "color_hex": "CBD5E1", "bold": False},
        "brand_tint_strategy":    "header_band",
    },

    "colorful_agency": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 1.80, "w": 11.7, "h": 1.6},
        "report_period_box":      {"x": 0.8, "y": 3.60, "w":  8.0, "h": 0.45},
        # No single band — template uses 3 coloured strips at top + a left
        # sidebar. Brand-colour recolour would collapse the palette.
        "header_band":            None,
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 3.80, "w": 2.5, "h": 1.8},
        "client_name_font":       {"name": "Calibri", "size_pt": 40, "color_hex": "0F172A", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 14, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "none",
    },

    "bold_geometric": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 2.00, "w":  7.0, "h": 1.8},
        "report_period_box":      {"x": 0.8, "y": 3.90, "w":  6.0, "h": 0.45},
        # No single band — right-side coloured block + asymmetric layout.
        "header_band":            None,
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.00, "w": 2.5, "h": 1.8},
        "client_name_font":       {"name": "Calibri", "size_pt": 44, "color_hex": "FFFFFF", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 16, "color_hex": "C7D2FE", "bold": False},
        "brand_tint_strategy":    "none",
    },

    "minimal_elegant": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 1.5, "y": 2.40, "w": 10.3, "h": 1.4},
        "report_period_box":      {"x": 1.5, "y": 4.30, "w": 10.3, "h": 0.4},
        # Deliberately no band — minimalist layout depends on white space.
        "header_band":            None,
        "agency_logo_placeholder":{"x": 1.5, "y": 0.80, "w": 2.0, "h": 0.8},
        "client_logo_placeholder":{"x": 5.4, "y": 5.50, "w": 2.5, "h": 1.0},
        "client_name_font":       {"name": "Georgia", "size_pt": 40, "color_hex": "0F172A", "bold": False},
        "report_period_font":     {"name": "Calibri", "size_pt": 14, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "none",
    },

    "gradient_modern": {
        "slide_inches":           {"width": 13.333, "height": 7.5},
        "client_name_box":        {"x": 0.8, "y": 3.10, "w": 11.7, "h": 1.5},
        "report_period_box":      {"x": 0.8, "y": 4.70, "w":  8.0, "h": 0.45},
        # Multi-shape gradient band at top. The leftmost (index 0) spans
        # the full width; recolouring it approximates the brand-tint
        # effect acceptably.
        "header_band":            {"x": 0.0, "y": 0.00, "w": 13.3, "h": 2.6},
        "agency_logo_placeholder":{"x": 10.3, "y": 0.50, "w": 2.2, "h": 1.0},
        "client_logo_placeholder":{"x": 9.8,  "y": 4.50, "w": 2.5, "h": 1.5},
        "client_name_font":       {"name": "Calibri", "size_pt": 42, "color_hex": "0F172A", "bold": True},
        "report_period_font":     {"name": "Calibri", "size_pt": 16, "color_hex": "64748B", "bold": False},
        "brand_tint_strategy":    "header_band",
    },
}


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
