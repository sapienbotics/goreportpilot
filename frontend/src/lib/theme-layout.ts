// Theme Layout Spec — single source of truth (TypeScript mirror).
//
// This mirrors backend/services/theme_layout.py. Coordinates are in
// slide INCHES (slide is 13.333 × 7.5). Any change here MUST be
// mirrored in the backend file — they are the shared contract between
// the React overlay preview and the python-pptx cover builder.
//
// Slide aspect ratio: 13.333 / 7.5 = 1.7777... (widescreen 16:9).

export type ThemeId =
  | 'modern_clean'
  | 'dark_executive'
  | 'colorful_agency'
  | 'bold_geometric'
  | 'minimal_elegant'
  | 'gradient_modern'

export const THEME_IDS: ThemeId[] = [
  'modern_clean',
  'dark_executive',
  'colorful_agency',
  'bold_geometric',
  'minimal_elegant',
  'gradient_modern',
]

export interface Box {
  x: number
  y: number
  w: number
  h: number
}

export interface FontSpec {
  name: string
  size_pt: number
  color_hex: string
  bold: boolean
}

export type Align = 'left' | 'center' | 'right'

export interface AgencyAttribution {
  box: Box
  font: FontSpec
  align: Align
}

export interface ThemeLayout {
  slide_inches: { width: number; height: number }
  client_name_box: Box
  /** v2.1: per-theme headline alignment (matches designer intent). */
  client_name_align: Align
  report_period_box: Box
  /** v2.1: per-theme period alignment. */
  report_period_align: Align
  /**
   * v2.1: where the user's subtitle (tagline) renders on the cover.
   * Occupies the original period slot — when subtitle is set, the
   * period is shifted down by subtitle.h + SUBTITLE_PERIOD_GAP. When
   * subtitle is absent, period renders at its report_period_box coords
   * unchanged.
   */
  subtitle_box: Box
  subtitle_font: FontSpec
  header_band: Box | null
  agency_logo_placeholder: Box
  client_logo_placeholder: Box
  client_name_font: FontSpec
  report_period_font: FontSpec
  /**
   * Whether the theme's cover has a recolour-safe header band.
   * - 'header_band': brand_primary_color tints the band; accent bar renders
   * - 'none': cover palette stays theme-native (colour flows to charts only)
   */
  brand_tint_strategy: 'header_band' | 'none'
  /**
   * Where "Prepared by <agency_name>" is drawn on the cover. Mirrors
   * the pre-strip templates' original attribution placement. Set to
   * null to skip. Frontend preview does not currently render this
   * overlay; the backend draws it during PPTX generation.
   */
  agency_attribution: AgencyAttribution | null
  /** Short description shown in the theme picker. */
  label: string
  tagline: string
}

export const THEME_LAYOUT: Record<ThemeId, ThemeLayout> = {
  modern_clean: {
    slide_inches:            { width: 13.333, height: 7.5 },
    client_name_box:         { x: 0.8,  y: 2.70, w: 11.7, h: 1.5 },
    client_name_align:       'left',
    report_period_box:       { x: 0.8,  y: 4.35, w: 11.7, h: 0.5 },
    report_period_align:     'left',
    subtitle_box:            { x: 0.8,  y: 4.35, w: 11.7, h: 0.4 },
    subtitle_font:           { name: 'Calibri', size_pt: 18, color_hex: '64748B', bold: false },
    header_band:             { x: 0.0,  y: 0.00, w: 13.3, h: 2.2 },
    agency_logo_placeholder: { x: 10.5, y: 0.40, w: 2.0,  h: 1.0 },
    client_logo_placeholder: { x: 9.8,  y: 4.50, w: 2.5,  h: 1.5 },
    client_name_font:        { name: 'Calibri',       size_pt: 40, color_hex: '0F172A', bold: true },
    report_period_font:      { name: 'Calibri Light', size_pt: 14, color_hex: '64748B', bold: false },
    brand_tint_strategy:     'header_band',
    agency_attribution: {
      box:   { x: 0.8, y: 1.15, w: 6.0, h: 0.35 },
      font:  { name: 'Calibri Light', size_pt: 11, color_hex: 'C7D2FE', bold: false },
      align: 'left',
    },
    label:                   'Modern Clean',
    tagline:                 'Light, minimalist; indigo accent',
  },
  dark_executive: {
    slide_inches:            { width: 13.333, height: 7.5 },
    client_name_box:         { x: 0.8,  y: 2.50, w: 11.7, h: 1.5 },
    client_name_align:       'left',
    report_period_box:       { x: 0.8,  y: 4.15, w:  8.0, h: 0.45 },
    report_period_align:     'left',
    subtitle_box:            { x: 0.8,  y: 4.15, w:  8.0, h: 0.4 },
    subtitle_font:           { name: 'Calibri', size_pt: 18, color_hex: 'CBD5E1', bold: false },
    header_band:             { x: 0.0,  y: 2.00, w: 13.3, h: 0.04 },
    agency_logo_placeholder: { x: 10.3, y: 0.50, w: 2.2,  h: 1.0 },
    client_logo_placeholder: { x: 9.8,  y: 4.00, w: 2.5,  h: 1.8 },
    client_name_font:        { name: 'Calibri', size_pt: 40, color_hex: 'F8FAFC', bold: true },
    report_period_font:      { name: 'Calibri', size_pt: 14, color_hex: 'CBD5E1', bold: false },
    brand_tint_strategy:     'header_band',
    agency_attribution: {
      box:   { x: 0.8, y: 6.70, w: 8.0, h: 0.35 },
      font:  { name: 'Calibri', size_pt: 11, color_hex: '475569', bold: false },
      align: 'left',
    },
    label:                   'Dark Executive',
    tagline:                 'Dark navy; corporate; serif accents',
  },
  colorful_agency: {
    slide_inches:            { width: 13.333, height: 7.5 },
    client_name_box:         { x: 0.8,  y: 1.80, w: 11.7, h: 1.6 },
    client_name_align:       'left',
    report_period_box:       { x: 0.8,  y: 3.60, w:  8.0, h: 0.45 },
    report_period_align:     'left',
    subtitle_box:            { x: 0.8,  y: 3.60, w:  8.0, h: 0.4 },
    subtitle_font:           { name: 'Calibri', size_pt: 18, color_hex: '64748B', bold: false },
    header_band:             null,
    agency_logo_placeholder: { x: 10.3, y: 0.50, w: 2.2,  h: 1.0 },
    client_logo_placeholder: { x: 9.8,  y: 3.80, w: 2.5,  h: 1.8 },
    client_name_font:        { name: 'Calibri', size_pt: 40, color_hex: '0F172A', bold: true },
    report_period_font:      { name: 'Calibri', size_pt: 14, color_hex: '64748B', bold: false },
    brand_tint_strategy:     'none',
    agency_attribution: {
      box:   { x: 0.8, y: 6.80, w: 8.0, h: 0.35 },
      font:  { name: 'Calibri', size_pt: 11, color_hex: '94A3B8', bold: false },
      align: 'left',
    },
    label:                   'Colorful Agency',
    tagline:                 'Multi-colour, agency-forward',
  },
  bold_geometric: {
    slide_inches:            { width: 13.333, height: 7.5 },
    client_name_box:         { x: 0.8,  y: 2.00, w:  7.0, h: 1.8 },
    client_name_align:       'left',
    report_period_box:       { x: 0.8,  y: 3.90, w:  6.0, h: 0.45 },
    report_period_align:     'left',
    subtitle_box:            { x: 0.8,  y: 3.90, w:  6.0, h: 0.4 },
    subtitle_font:           { name: 'Calibri', size_pt: 20, color_hex: 'C7D2FE', bold: false },
    header_band:             null,
    agency_logo_placeholder: { x: 10.3, y: 0.50, w: 2.2,  h: 1.0 },
    client_logo_placeholder: { x: 9.8,  y: 4.00, w: 2.5,  h: 1.8 },
    client_name_font:        { name: 'Calibri', size_pt: 44, color_hex: 'FFFFFF', bold: true },
    report_period_font:      { name: 'Calibri', size_pt: 16, color_hex: 'C7D2FE', bold: false },
    brand_tint_strategy:     'none',
    agency_attribution: {
      box:   { x: 0.8, y: 6.80, w: 8.0, h: 0.35 },
      font:  { name: 'Calibri', size_pt: 11, color_hex: 'A5B4FC', bold: false },
      align: 'left',
    },
    label:                   'Bold Geometric',
    tagline:                 'High-contrast, geometric, modern',
  },
  minimal_elegant: {
    slide_inches:            { width: 13.333, height: 7.5 },
    client_name_box:         { x: 1.5,  y: 2.40, w: 10.3, h: 1.4 },
    client_name_align:       'center',
    report_period_box:       { x: 1.5,  y: 4.30, w: 10.3, h: 0.4 },
    report_period_align:     'center',
    subtitle_box:            { x: 1.5,  y: 4.30, w: 10.3, h: 0.4 },
    subtitle_font:           { name: 'Georgia', size_pt: 16, color_hex: '64748B', bold: false },
    header_band:             null,
    agency_logo_placeholder: { x: 1.5,  y: 0.80, w: 2.0,  h: 0.8 },
    client_logo_placeholder: { x: 5.4,  y: 5.50, w: 2.5,  h: 1.0 },
    client_name_font:        { name: 'Georgia', size_pt: 40, color_hex: '0F172A', bold: false },
    report_period_font:      { name: 'Calibri', size_pt: 14, color_hex: '64748B', bold: false },
    brand_tint_strategy:     'none',
    agency_attribution: {
      box:   { x: 1.5, y: 6.90, w: 10.3, h: 0.3 },
      font:  { name: 'Calibri', size_pt: 9, color_hex: '94A3B8', bold: false },
      align: 'center',
    },
    label:                   'Minimal Elegant',
    tagline:                 'Off-white; serif; editorial',
  },
  gradient_modern: {
    slide_inches:            { width: 13.333, height: 7.5 },
    client_name_box:         { x: 0.8,  y: 3.10, w: 11.7, h: 1.5 },
    client_name_align:       'left',
    report_period_box:       { x: 0.8,  y: 4.70, w:  8.0, h: 0.45 },
    report_period_align:     'left',
    subtitle_box:            { x: 0.8,  y: 4.70, w:  8.0, h: 0.4 },
    subtitle_font:           { name: 'Calibri', size_pt: 20, color_hex: '64748B', bold: false },
    header_band:             { x: 0.0,  y: 0.00, w: 13.3, h: 2.6 },
    agency_logo_placeholder: { x: 10.3, y: 0.50, w: 2.2,  h: 1.0 },
    client_logo_placeholder: { x: 9.8,  y: 4.50, w: 2.5,  h: 1.5 },
    client_name_font:        { name: 'Calibri', size_pt: 42, color_hex: '0F172A', bold: true },
    report_period_font:      { name: 'Calibri', size_pt: 16, color_hex: '64748B', bold: false },
    brand_tint_strategy:     'header_band',
    agency_attribution: {
      box:   { x: 0.8, y: 1.20, w: 6.0, h: 0.35 },
      font:  { name: 'Calibri', size_pt: 11, color_hex: 'FECDD3', bold: false },
      align: 'left',
    },
    label:                   'Gradient Modern',
    tagline:                 'Gradient accents, dark body',
  },
}

/**
 * v2.1: vertical gap (inches) between the subtitle and the period line
 * when the subtitle is set. Must match backend theme_layout.SUBTITLE_PERIOD_GAP.
 */
export const SUBTITLE_PERIOD_GAP = 0.10

// Helper: convert a slide-inch Box to CSS percent-based positioning props
// for overlaying on a thumbnail that preserves the 13.333:7.5 aspect ratio.
export function boxToPercentStyle(box: Box, slideW = 13.333, slideH = 7.5) {
  return {
    left:   `${(box.x / slideW) * 100}%`,
    top:    `${(box.y / slideH) * 100}%`,
    width:  `${(box.w / slideW) * 100}%`,
    height: `${(box.h / slideH) * 100}%`,
  }
}
