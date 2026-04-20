'use client'

// DesignTab — unified per-client design surface (Option F v1).
//
// Four sections stacked on the left + sticky overlay preview on the right:
//   A. Theme picker         (6 cards with real template thumbnails)
//   B. Brand colours        (primary + accent, hex + color pickers)
//   C. Cover text           (headline override + subtitle)
//   D. Logo placement       (agency + client, position + size)
//
// The preview uses the real template thumbnail (pre-rendered PNG served
// from the backend at /static/cover_thumbnails/{theme}.png) with CSS
// overlays for user-customisable elements: brand-colour tint on the
// header band, accent bar, headline + subtitle text at the template's
// known coordinates, and logo imagery at the user-selected positions.

import { useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  Check, Loader2, Download, Upload, Palette, Info,
} from 'lucide-react'
import type { Client, LogoPosition, LogoSize } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { clientsApi, previewCover, settingsApi, uploadClientLogo } from '@/lib/api'
import {
  THEME_IDS, THEME_LAYOUT, boxToPercentStyle, type ThemeId,
} from '@/lib/theme-layout'

// ── Constants ───────────────────────────────────────────────────────────────

const LOGO_POSITIONS: { id: LogoPosition; label: string }[] = [
  { id: 'default',       label: 'Template default' },
  { id: 'top-left',      label: 'Top-left' },
  { id: 'top-right',     label: 'Top-right' },
  { id: 'top-center',    label: 'Top-center' },
  { id: 'footer-left',   label: 'Footer-left' },
  { id: 'footer-right',  label: 'Footer-right' },
  { id: 'footer-center', label: 'Footer-center' },
  { id: 'center',        label: 'Slide centre' },
]

// Dropdown labels mirror the actual backend bounding boxes. "default" on
// the backend maps to Medium (agency 2.5"×0.8", client 3"×2"), so the
// dropdown now surfaces that truth — "default" is no longer a separate
// option that confused users into thinking it was Small.
const LOGO_SIZES: { id: LogoSize; label: string }[] = [
  { id: 'small',   label: 'Small' },
  { id: 'medium',  label: 'Medium (default)' },
  { id: 'large',   label: 'Large' },
]

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ── Component ───────────────────────────────────────────────────────────────

interface Props {
  client: Client
  onClientUpdate: (client: Client) => void
}

export default function DesignTab({ client, onClientUpdate }: Props) {
  const clientLogoInputRef = useRef<HTMLInputElement>(null)

  // Fetch agency profile for logo + brand_color (used in preview overlay).
  const [agencyLogoUrl, setAgencyLogoUrl] = useState<string | null>(null)
  const [brandDefault,  setBrandDefault]  = useState<string | null>(null)
  useEffect(() => {
    settingsApi.getProfile()
      .then((p) => {
        const logo = typeof p.agency_logo_url === 'string' ? p.agency_logo_url : null
        const bc   = typeof p.brand_color === 'string' ? p.brand_color : null
        setAgencyLogoUrl(logo)
        setBrandDefault(bc)
      })
      .catch(() => { /* non-fatal */ })
  }, [])

  const [theme,       setTheme]      = useState<ThemeId>(
    (client.theme as ThemeId) || 'modern_clean',
  )
  const [headline,    setHeadline]   = useState(client.cover_headline ?? '')
  const [subtitle,    setSubtitle]   = useState(client.cover_subtitle ?? '')
  const [primary,     setPrimary]    = useState(client.cover_brand_primary_color ?? '')
  const [accent,      setAccent]     = useState(client.cover_brand_accent_color ?? '')
  const [agencyPos,   setAgencyPos]  = useState<LogoPosition>(
    (client.cover_agency_logo_position as LogoPosition) || 'default',
  )
  // Normalise legacy 'default' size → 'medium' so the dropdown renders the
  // true size. Backend still accepts 'default' (treated as medium).
  const [agencySz,    setAgencySz]   = useState<LogoSize>(
    normaliseLogoSize(client.cover_agency_logo_size),
  )
  const [clientPos,   setClientPos]  = useState<LogoPosition>(
    (client.cover_client_logo_position as LogoPosition) || 'default',
  )
  const [clientSz,    setClientSz]   = useState<LogoSize>(
    normaliseLogoSize(client.cover_client_logo_size),
  )
  const [clientLogo,  setClientLogo] = useState<string>(client.logo_url ?? '')
  const [logoUploading, setLogoUploading] = useState(false)

  const [saving,     setSaving]     = useState(false)
  const [previewing, setPreviewing] = useState(false)

  const layout = THEME_LAYOUT[theme]

  const bandTintSupported = layout.brand_tint_strategy === 'header_band'

  const hasChanges = (
    theme      !== ((client.theme as string) ?? 'modern_clean') ||
    headline   !== (client.cover_headline ?? '') ||
    subtitle   !== (client.cover_subtitle ?? '') ||
    primary    !== (client.cover_brand_primary_color ?? '') ||
    accent     !== (client.cover_brand_accent_color ?? '') ||
    agencyPos  !== ((client.cover_agency_logo_position as string) ?? 'default') ||
    agencySz   !== normaliseLogoSize(client.cover_agency_logo_size) ||
    clientPos  !== ((client.cover_client_logo_position as string) ?? 'default') ||
    clientSz   !== normaliseLogoSize(client.cover_client_logo_size)
  )

  // ── Save ──────────────────────────────────────────────────────────────────

  const handleSave = async () => {
    if (primary && !isValidHex(primary)) { toast.error('Primary colour must be #RRGGBB.'); return }
    if (accent  && !isValidHex(accent))  { toast.error('Accent colour must be #RRGGBB.');  return }
    setSaving(true)
    try {
      const updated = await clientsApi.update(client.id, {
        theme,
        cover_headline:             headline || null,
        cover_subtitle:             subtitle || null,
        cover_brand_primary_color:  primary || null,
        cover_brand_accent_color:   accent || null,
        cover_agency_logo_position: agencyPos,
        cover_agency_logo_size:     agencySz,
        cover_client_logo_position: clientPos,
        cover_client_logo_size:     clientSz,
      })
      onClientUpdate(updated)
      toast.success('Design saved. Every new report for this client uses this design.')
    } catch (exc) {
      toast.error('Failed to save design.')
      // eslint-disable-next-line no-console
      console.error(exc)
    } finally {
      setSaving(false)
    }
  }

  // ── Download PPTX preview ─────────────────────────────────────────────────

  const handleDownloadPreview = async () => {
    setPreviewing(true)
    try {
      const blob = await previewCover({
        client_id:            client.id,
        theme,
        headline:             headline || null,
        subtitle:             subtitle || null,
        primary_color:        primary || null,
        accent_color:         accent || null,
        agency_logo_position: agencyPos,
        agency_logo_size:     agencySz,
        client_logo_position: clientPos,
        client_logo_size:     clientSz,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${client.name.replace(/\s+/g, '_')}_cover_preview.pptx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (exc) {
      toast.error('Could not generate preview.')
      // eslint-disable-next-line no-console
      console.error(exc)
    } finally {
      setPreviewing(false)
    }
  }

  // ── Client logo upload (reused from existing flow) ────────────────────────

  const handleClientLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) { toast.error('Logo must be under 2MB.'); e.target.value = ''; return }
    setLogoUploading(true)
    try {
      const { url } = await uploadClientLogo(client.id, file)
      setClientLogo(url)
      onClientUpdate({ ...client, logo_url: url })
      toast.success('Client logo uploaded.')
    } catch (exc) {
      toast.error('Upload failed.')
      // eslint-disable-next-line no-console
      console.error(exc)
    } finally {
      setLogoUploading(false)
      e.target.value = ''
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_minmax(0,560px)] gap-6">
      {/* ── Left: controls ──────────────────────────────────────────────── */}
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900">Design</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Theme + colours + text + logos. Applied to every report generated for {client.name}.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleDownloadPreview}
                  disabled={previewing}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                >
                  {previewing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                  Download PPTX preview
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving || !hasChanges}
                  className="inline-flex items-center gap-1.5 rounded-md bg-indigo-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-800 disabled:opacity-60"
                >
                  {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                  Save
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">

            {/* Section A — Theme picker */}
            <section>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Theme</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {THEME_IDS.map((id) => {
                  const info = THEME_LAYOUT[id]
                  const selected = theme === id
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setTheme(id)}
                      className={`text-left rounded-lg border p-2 transition-all ${selected ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200 hover:border-slate-300'}`}
                    >
                      <div className="rounded overflow-hidden mb-2 aspect-video bg-slate-100 border border-slate-100">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`${API_URL}/static/cover_thumbnails/${id}.png`}
                          alt={info.label}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <p className="text-xs font-semibold text-slate-800">{info.label}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">{info.tagline}</p>
                    </button>
                  )
                })}
              </div>
              <p className="text-[11px] text-slate-400 mt-2">
                The theme governs the whole deck — cover and all content slides share a design language.
              </p>
            </section>

            {/* Section B — Brand colours */}
            <section>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Palette className="h-3 w-3 text-slate-400" /> Brand colours
              </p>
              <div className="grid grid-cols-2 gap-3">
                <ColorField
                  label="Primary"
                  value={primary}
                  onChange={setPrimary}
                  placeholder={brandDefault || '#4338CA'}
                  hint="Cover header (if theme supports) + chart palette"
                />
                <ColorField
                  label="Accent"
                  value={accent}
                  onChange={setAccent}
                  placeholder="#F59E0B"
                  hint="Thin bar under the header"
                />
              </div>
              <div className="mt-2 flex items-start gap-1.5 text-[11px] text-slate-400">
                <Info className="h-3 w-3 shrink-0 mt-0.5" />
                <p>
                  Brand colour applies to the cover header {bandTintSupported ? '' : '(not supported by this theme — colour flows to charts only)'} and chart palette. Slide backgrounds and decorative elements follow the chosen theme.
                </p>
              </div>
            </section>

            {/* Section C — Cover text */}
            <section>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Cover text</p>
              <div className="space-y-2">
                <div>
                  <label className="text-[11px] font-medium text-slate-600">Headline</label>
                  <Input
                    value={headline}
                    onChange={(e) => setHeadline(e.target.value)}
                    placeholder={`Leave blank to show client name: ${client.name}`}
                    maxLength={80}
                    className="mt-1"
                  />
                  <p className="text-[10px] text-slate-400 mt-0.5">Replaces the default title on the cover.</p>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-600">Subtitle</label>
                  <Input
                    value={subtitle}
                    onChange={(e) => setSubtitle(e.target.value)}
                    placeholder="Leave blank to show just the report period"
                    maxLength={120}
                    className="mt-1"
                  />
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Appended after the period — e.g. <span className="font-mono">April 2026 — {subtitle || 'Executive Brief'}</span>
                  </p>
                </div>
              </div>
            </section>

            {/* Section D — Logo placement */}
            <section>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Logo placement</p>
              <div className="space-y-3">
                <LogoRow
                  label="Agency logo"
                  position={agencyPos}
                  size={agencySz}
                  onPosition={setAgencyPos}
                  onSize={setAgencySz}
                  imageUrl={agencyLogoUrl ?? null}
                  emptyHint="Upload an agency logo in Settings → Branding."
                />
                <LogoRow
                  label="Client logo"
                  position={clientPos}
                  size={clientSz}
                  onPosition={setClientPos}
                  onSize={setClientSz}
                  imageUrl={clientLogo}
                  emptyHint="Upload a client logo (below) to enable placement."
                  onUploadClick={() => clientLogoInputRef.current?.click()}
                  uploading={logoUploading}
                />
              </div>
              <input
                ref={clientLogoInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                className="hidden"
                onChange={handleClientLogoUpload}
              />
            </section>
          </CardContent>
        </Card>
      </div>

      {/* ── Right: preview ──────────────────────────────────────────────── */}
      <div>
        <div className="sticky top-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Preview</p>
          <OverlayPreview
            theme={theme}
            headline={headline || client.name}
            periodLine={buildPeriodLine(subtitle)}
            primary={isValidHex(primary) ? primary : null}
            accent={isValidHex(accent) ? accent : null}
            agencyLogoUrl={agencyLogoUrl ?? null}
            agencyPos={agencyPos}
            agencySz={agencySz}
            clientLogoUrl={clientLogo || null}
            clientPos={clientPos}
            clientSz={clientSz}
          />
          <p className="text-[11px] text-slate-400 mt-2">
            Preview approximates the rendered cover. Click <strong>Download PPTX preview</strong> for the exact file.
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Overlay preview ─────────────────────────────────────────────────────────

interface OverlayPreviewProps {
  theme: ThemeId
  headline: string
  periodLine: string
  primary: string | null
  accent: string | null
  agencyLogoUrl: string | null
  agencyPos: LogoPosition
  agencySz: LogoSize
  clientLogoUrl: string | null
  clientPos: LogoPosition
  clientSz: LogoSize
}

function OverlayPreview({
  theme, headline, periodLine, primary, accent,
  agencyLogoUrl, agencyPos, agencySz, clientLogoUrl, clientPos, clientSz,
}: OverlayPreviewProps) {
  const layout = THEME_LAYOUT[theme]

  const nameStyle = useMemo(() => {
    const box = boxToPercentStyle(layout.client_name_box)
    // Text overlays are the sole source of cover text since the
    // chrome-only thumbnails carry no placeholder runs. Center-aligned
    // to match backend cover_customization.py (PP_ALIGN.CENTER).
    return {
      ...box,
      color: `#${layout.client_name_font.color_hex}`,
      fontWeight: layout.client_name_font.bold ? 700 : 400,
      fontFamily: layout.client_name_font.name === 'Georgia' ? 'Georgia, serif' : 'Inter, Arial, sans-serif',
      fontSize: `clamp(14px, ${layout.client_name_font.size_pt / 4}%, 44px)`,
      lineHeight: 1.1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center' as const,
      overflow: 'hidden',
      whiteSpace: 'nowrap' as const,
      textOverflow: 'ellipsis',
      zIndex: 3,
    }
  }, [layout])

  const periodStyle = useMemo(() => {
    const box = boxToPercentStyle(layout.report_period_box)
    return {
      ...box,
      color: `#${layout.report_period_font.color_hex}`,
      fontWeight: layout.report_period_font.bold ? 700 : 400,
      fontFamily: 'Inter, Arial, sans-serif',
      fontSize: `clamp(10px, ${layout.report_period_font.size_pt / 4}%, 18px)`,
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'center',
      textAlign: 'center' as const,
      zIndex: 3,
    }
  }, [layout])

  // B-fix: solid overlay (no blend mode) so the user's exact hex renders
  // in the preview. Previously `mixBlendMode: multiply` + `opacity: 0.85`
  // on dark template bands produced a muddy colour that didn't match the
  // user's intent. Trade-off: solid hides any decorative shading under
  // the band — acceptable because the chrome-only thumbnails now leave
  // the band region clean anyway.
  const bandStyle = useMemo(() => {
    if (!layout.header_band || !primary || layout.brand_tint_strategy !== 'header_band') return null
    return {
      ...boxToPercentStyle(layout.header_band),
      background: primary,
      zIndex: 1,
    }
  }, [layout, primary])

  // B-fix: accent bar bumped to 0.10" (was 0.08"), pinned above band via
  // z-index so it stays visible. Matches backend cover_customization.py:
  // _draw_accent_bar uses bar_h_emu = Inches(0.10).
  const accentStyle = useMemo(() => {
    if (!layout.header_band || !accent || layout.brand_tint_strategy !== 'header_band') return null
    return {
      ...boxToPercentStyle({
        x: layout.header_band.x,
        y: layout.header_band.y + layout.header_band.h - 0.10,
        w: layout.header_band.w,
        h: 0.10,
      }),
      background: accent,
      zIndex: 2,
    }
  }, [layout, accent])

  return (
    <div
      className="relative w-full rounded-lg overflow-hidden border border-slate-200 shadow-sm bg-slate-100"
      style={{ aspectRatio: '13.333 / 7.5' }}
    >
      {/* Base: template thumbnail */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`${API_URL}/static/cover_thumbnails/${theme}.png`}
        alt=""
        className="absolute inset-0 w-full h-full object-cover"
      />

      {/* Brand tint over header band (if theme supports) */}
      {bandStyle && <div className="absolute" style={bandStyle} />}

      {/* Accent bar */}
      {accentStyle && <div className="absolute" style={accentStyle} />}

      {/* Headline overlay — drawn over (and partially occluding) the
          template's own {{client_name}} text. Colour from theme layout. */}
      <div className="absolute px-1" style={nameStyle}>
        <span className="block truncate w-full">{headline}</span>
      </div>

      {/* Period / subtitle overlay */}
      <div className="absolute px-1" style={periodStyle}>
        <span className="block truncate w-full">{periodLine}</span>
      </div>

      {/* Agency logo overlay */}
      {agencyLogoUrl && (
        <PreviewLogo
          url={agencyLogoUrl}
          position={agencyPos}
          size={agencySz}
          defaultBox={layout.agency_logo_placeholder}
          kind="agency"
        />
      )}

      {/* Client logo overlay */}
      {clientLogoUrl && (
        <PreviewLogo
          url={clientLogoUrl}
          position={clientPos}
          size={clientSz}
          defaultBox={layout.client_logo_placeholder}
          kind="client"
        />
      )}

    </div>
  )
}

function PreviewLogo({
  url, position, size, defaultBox, kind,
}: {
  url: string
  position: LogoPosition
  size: LogoSize
  defaultBox: { x: number; y: number; w: number; h: number }
  kind: 'agency' | 'client'
}) {
  const { w: slideW, h: slideH } = { w: 13.333, h: 7.5 }

  // Resolve box dimensions based on size setting.
  const sizeBox = resolveSizeBox(size, kind)
  const box = position === 'default'
    ? defaultBox
    : {
        ...positionToXY(position, slideW, slideH, sizeBox.w, sizeBox.h),
        w: sizeBox.w,
        h: sizeBox.h,
      }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt=""
      style={{ ...boxToPercentStyle(box), objectFit: 'contain', zIndex: 4 }}
      className="absolute"
    />
  )
}

// Mirrors backend _logo_max_box semantics (inches) roughly.
function resolveSizeBox(size: LogoSize, kind: 'agency' | 'client') {
  if (kind === 'agency') {
    if (size === 'small')  return { w: 1.5, h: 0.5 }
    if (size === 'large')  return { w: 3.5, h: 1.2 }
    return { w: 2.5, h: 0.8 }  // medium / default
  }
  if (size === 'small')    return { w: 1.5, h: 1.0 }
  if (size === 'large')    return { w: 4.5, h: 3.0 }
  return { w: 3.0, h: 2.0 }    // medium / default
}

// Mirrors backend _logo_corner_xy.
function positionToXY(
  pos: LogoPosition, slideW: number, slideH: number, logoW: number, logoH: number,
): { x: number; y: number } {
  const m = 0.3
  switch (pos) {
    case 'top-left':      return { x: m, y: m }
    case 'top-right':     return { x: slideW - logoW - m, y: m }
    case 'top-center':    return { x: (slideW - logoW) / 2, y: m }
    case 'footer-left':   return { x: m, y: slideH - logoH - m }
    case 'footer-right':  return { x: slideW - logoW - m, y: slideH - logoH - m }
    case 'footer-center': return { x: (slideW - logoW) / 2, y: slideH - logoH - m }
    case 'center':        return { x: (slideW - logoW) / 2, y: (slideH - logoH) / 2 }
    default:              return { x: slideW - logoW - m, y: m }
  }
}

// ── Sub-components ──────────────────────────────────────────────────────────

function ColorField({
  label, value, onChange, placeholder, hint,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
  hint?: string
}) {
  const valid = !value || /^#[0-9a-fA-F]{6}$/.test(value)
  return (
    <div>
      <label className="text-[11px] font-medium text-slate-600">{label}</label>
      <div className="mt-1 flex items-center gap-2">
        <input
          type="color"
          value={valid && value ? value : '#4338CA'}
          onChange={(e) => onChange(e.target.value)}
          className="h-9 w-12 rounded border border-slate-200 bg-white cursor-pointer"
        />
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`flex-1 h-9 font-mono text-xs ${!valid ? 'border-rose-300' : ''}`}
          maxLength={7}
        />
        {value && (
          <button type="button" onClick={() => onChange('')} className="text-[11px] text-slate-500 hover:text-slate-700 underline">
            Clear
          </button>
        )}
      </div>
      {hint && <p className="text-[10px] text-slate-400 mt-0.5">{hint}</p>}
    </div>
  )
}

function LogoRow({
  label, position, size, onPosition, onSize, imageUrl, emptyHint, onUploadClick, uploading,
}: {
  label: string
  position: LogoPosition
  size: LogoSize
  onPosition: (v: LogoPosition) => void
  onSize: (v: LogoSize) => void
  imageUrl: string | null
  emptyHint: string
  onUploadClick?: () => void
  uploading?: boolean
}) {
  const disabled = !imageUrl
  return (
    <div className="rounded-lg border border-slate-100 p-2.5">
      <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          {imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={imageUrl} alt={label} className="h-8 w-14 object-contain rounded bg-slate-50 border border-slate-200" />
          ) : (
            <div className="h-8 w-14 rounded bg-slate-50 border border-dashed border-slate-300" />
          )}
          <span className="text-xs font-medium text-slate-700">{label}</span>
        </div>
        {onUploadClick && (
          <button
            type="button"
            onClick={onUploadClick}
            disabled={uploading}
            className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {uploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
            {imageUrl ? 'Replace' : 'Upload'}
          </button>
        )}
      </div>
      {disabled ? (
        <p className="text-[11px] text-slate-400">{emptyHint}</p>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <select
            value={position}
            onChange={(e) => onPosition(e.target.value as LogoPosition)}
            className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
          >
            {LOGO_POSITIONS.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
          <select
            value={size}
            onChange={(e) => onSize(e.target.value as LogoSize)}
            className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
          >
            {LOGO_SIZES.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function isValidHex(v: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(v)
}

function buildPeriodLine(subtitle: string): string {
  const now = new Date()
  const period = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  if (subtitle) return `${period} — ${subtitle}`
  return period
}

// Collapse the legacy 'default' value (which resolved to Medium on the
// backend) to its honest name so users see what they're actually getting.
function normaliseLogoSize(value: LogoSize | string | null | undefined): LogoSize {
  if (value === 'small' || value === 'medium' || value === 'large') return value
  return 'medium'
}
