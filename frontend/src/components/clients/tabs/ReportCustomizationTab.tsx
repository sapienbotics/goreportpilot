'use client'

// ReportCustomizationTab — unified per-client branding.
//
// Covers Phase 3 (cover preset + headline/subtitle + hero image) plus the
// Phase 3 fix additions: per-client primary + accent brand colours and
// logo placement (position + size) for agency + client logos.
//
// Live preview: CSS mockup that approximates the chosen preset + colours
// + hero image.
// Pixel-perfect preview: "Download PPTX preview" hits
// /api/reports/preview-cover with the current form state and downloads a
// single-slide PPTX.

import { useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  Image as ImageIcon, Loader2, Upload, Download, Check, Palette,
} from 'lucide-react'
import type { Client, CoverPreset, LogoPosition, LogoSize } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { clientsApi, previewCover, uploadCoverHero } from '@/lib/api'

interface Props {
  client: Client
  onClientUpdate: (client: Client) => void
}

// ── Presets ─────────────────────────────────────────────────────────────────

interface PresetDef {
  id: CoverPreset
  label: string
  description: string
  header: string        // CSS colour for the mockup's header band
  body:   string
  title:  string
  subtitle: string
}

const PRESETS: PresetDef[] = [
  { id: 'default',   label: 'Default',   description: 'Native template cover. No overrides.',          header: '#4338CA', body: '#ffffff', title: '#ffffff', subtitle: '#C7D2FE' },
  { id: 'minimal',   label: 'Minimal',   description: 'White background, muted accents, dark type.',    header: '#FFFFFF', body: '#FFFFFF', title: '#0F172A', subtitle: '#64748B' },
  { id: 'bold',      label: 'Bold',      description: 'Full-bleed brand colour with a large headline.', header: 'brand',   body: 'brand',   title: '#FFFFFF', subtitle: '#F1F5F9' },
  { id: 'corporate', label: 'Corporate', description: 'Deep navy header, white title, brand accent.',   header: '#1E293B', body: '#FFFFFF', title: '#FFFFFF', subtitle: '#CBD5E1' },
  { id: 'hero',      label: 'Hero image',description: 'Full-bleed photo with dark overlay for contrast.',header: '#0F172A', body: '#0F172A', title: '#FFFFFF', subtitle: '#F1F5F9' },
  { id: 'gradient',  label: 'Gradient',  description: 'Brand colour band with contrasting dark body.',   header: 'brand',   body: '#0F172A', title: '#FFFFFF', subtitle: '#E2E8F0' },
]

const LOGO_POSITIONS: { id: LogoPosition; label: string }[] = [
  { id: 'default',       label: 'Template default' },
  { id: 'top-left',      label: 'Top-left' },
  { id: 'top-right',     label: 'Top-right' },
  { id: 'top-center',    label: 'Top-center' },
  { id: 'footer-left',   label: 'Footer-left' },
  { id: 'footer-right',  label: 'Footer-right' },
  { id: 'footer-center', label: 'Footer-center' },
  { id: 'center',        label: 'Slide center' },
]

const LOGO_SIZES: { id: LogoSize; label: string }[] = [
  { id: 'default', label: 'Default' },
  { id: 'small',   label: 'Small' },
  { id: 'medium',  label: 'Medium' },
  { id: 'large',   label: 'Large' },
]

function resolve(color: string, brand: string): string {
  return color === 'brand' ? brand : color
}

function isValidHex(v: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(v)
}

// ── Component ───────────────────────────────────────────────────────────────

export default function ReportCustomizationTab({ client, onClientUpdate }: Props) {
  const heroInputRef = useRef<HTMLInputElement>(null)

  const [preset,       setPreset]       = useState<CoverPreset>((client.cover_design_preset as CoverPreset) || 'default')
  const [headline,     setHeadline]     = useState(client.cover_headline ?? '')
  const [subtitle,     setSubtitle]     = useState(client.cover_subtitle ?? '')
  const [heroUrl,      setHeroUrl]      = useState(client.cover_hero_image_url ?? '')
  const [primary,      setPrimary]      = useState(client.cover_brand_primary_color ?? '')
  const [accent,       setAccent]       = useState(client.cover_brand_accent_color ?? '')
  const [agencyPos,    setAgencyPos]    = useState<LogoPosition>((client.cover_agency_logo_position as LogoPosition) || 'default')
  const [agencySz,     setAgencySz]     = useState<LogoSize>((client.cover_agency_logo_size as LogoSize) || 'default')
  const [clientPos,    setClientPos]    = useState<LogoPosition>((client.cover_client_logo_position as LogoPosition) || 'default')
  const [clientSz,     setClientSz]     = useState<LogoSize>((client.cover_client_logo_size as LogoSize) || 'default')

  const [saving,     setSaving]     = useState(false)
  const [uploading,  setUploading]  = useState(false)
  const [previewing, setPreviewing] = useState(false)

  // Effective brand colour for the CSS mockup — per-client override takes
  // precedence; otherwise fall back to a neutral swatch.
  const brandColor = isValidHex(primary) ? primary : '#4338CA'

  const activePreset = PRESETS.find((p) => p.id === preset) ?? PRESETS[0]

  const hasChanges = (
    preset     !== ((client.cover_design_preset as string) ?? 'default') ||
    headline   !== (client.cover_headline ?? '') ||
    subtitle   !== (client.cover_subtitle ?? '') ||
    heroUrl    !== (client.cover_hero_image_url ?? '') ||
    primary    !== (client.cover_brand_primary_color ?? '') ||
    accent     !== (client.cover_brand_accent_color ?? '') ||
    agencyPos  !== ((client.cover_agency_logo_position as string) ?? 'default') ||
    agencySz   !== ((client.cover_agency_logo_size as string)     ?? 'default') ||
    clientPos  !== ((client.cover_client_logo_position as string) ?? 'default') ||
    clientSz   !== ((client.cover_client_logo_size as string)     ?? 'default')
  )

  const handleSave = async () => {
    if (primary && !isValidHex(primary)) { toast.error('Primary colour must be a #RRGGBB hex value.'); return }
    if (accent  && !isValidHex(accent))  { toast.error('Accent colour must be a #RRGGBB hex value.');  return }

    setSaving(true)
    try {
      const updated = await clientsApi.update(client.id, {
        cover_design_preset:        preset,
        cover_headline:             headline || null,
        cover_subtitle:             subtitle || null,
        cover_hero_image_url:       heroUrl || null,
        cover_brand_primary_color:  primary || null,
        cover_brand_accent_color:   accent || null,
        cover_agency_logo_position: agencyPos,
        cover_agency_logo_size:     agencySz,
        cover_client_logo_position: clientPos,
        cover_client_logo_size:     clientSz,
      })
      onClientUpdate(updated)
      toast.success('Report customisation saved.')
    } catch (exc) {
      toast.error('Failed to save.')
      // eslint-disable-next-line no-console
      console.error(exc)
    } finally {
      setSaving(false)
    }
  }

  const handleHeroUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) { toast.error('Hero image must be under 2MB.'); e.target.value = ''; return }
    setUploading(true)
    try {
      const { url } = await uploadCoverHero(client.id, file)
      setHeroUrl(url)
      toast.success('Hero image uploaded.')
    } catch (exc) {
      toast.error('Upload failed.')
      // eslint-disable-next-line no-console
      console.error(exc)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDownloadPreview = async () => {
    setPreviewing(true)
    try {
      const blob = await previewCover({
        client_id:            client.id,
        preset,
        headline:             headline || null,
        subtitle:             subtitle || null,
        hero_image_url:       heroUrl || null,
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
      a.download = `${client.name.replace(/\s+/g, '_')}_report_preview.pptx`
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

  return (
    <div className="space-y-4 max-w-5xl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="text-base font-semibold text-slate-900">Report customisation</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Preset, colours, and logos are applied to every report generated for {client.name}.
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
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left column — controls */}
            <div className="space-y-5">
              {/* Preset */}
              <section>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Cover preset</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {PRESETS.map((p) => {
                    const selected = preset === p.id
                    const header = resolve(p.header, brandColor)
                    const body   = resolve(p.body,   brandColor)
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setPreset(p.id)}
                        className={`text-left rounded-lg border p-2 transition-all ${selected ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200 hover:border-slate-300'}`}
                      >
                        <div className="rounded overflow-hidden mb-2 h-12 border border-slate-100">
                          <div className="h-1/2" style={{ background: header }} />
                          <div className="h-1/2" style={{ background: body }} />
                        </div>
                        <p className="text-xs font-semibold text-slate-800">{p.label}</p>
                        <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">{p.description}</p>
                      </button>
                    )
                  })}
                </div>
              </section>

              {/* Headline + Subtitle */}
              <section>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Cover text</p>
                <div className="space-y-2">
                  <Input
                    value={headline}
                    onChange={(e) => setHeadline(e.target.value)}
                    placeholder="Headline (overrides client name on cover) — e.g. Q2 Performance Review"
                    maxLength={80}
                  />
                  <Input
                    value={subtitle}
                    onChange={(e) => setSubtitle(e.target.value)}
                    placeholder="Subtitle (overrides report period) — e.g. April 2026"
                    maxLength={120}
                  />
                </div>
              </section>

              {/* Brand colours */}
              <section>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <Palette className="h-3 w-3 text-slate-400" /> Brand colours
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <ColorField
                    label="Primary"
                    value={primary}
                    onChange={setPrimary}
                    placeholder="#4338CA"
                    hint="Header + chart palette"
                  />
                  <ColorField
                    label="Accent"
                    value={accent}
                    onChange={setAccent}
                    placeholder="#F59E0B"
                    hint="Thin bar on the cover"
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-1.5">
                  Leave blank to inherit the agency&apos;s default brand colour.
                </p>
              </section>

              {/* Logo placement */}
              <section>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Logo placement</p>
                <div className="space-y-3">
                  <LogoPlacementRow
                    label="Agency logo"
                    position={agencyPos}
                    size={agencySz}
                    onPosition={setAgencyPos}
                    onSize={setAgencySz}
                  />
                  <LogoPlacementRow
                    label="Client logo"
                    position={clientPos}
                    size={clientSz}
                    onPosition={setClientPos}
                    onSize={setClientSz}
                  />
                </div>
              </section>

              {/* Hero image */}
              <section className={`rounded-lg border p-3 ${preset === 'hero' ? '' : 'opacity-60'}`}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                      <ImageIcon className="h-3.5 w-3.5 text-slate-400" /> Hero image
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Used by the <strong>hero</strong> preset. PNG/JPEG/WEBP, max 2MB.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {heroUrl && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={heroUrl} alt="Hero preview" className="h-8 w-14 object-cover rounded border border-slate-200" />
                    )}
                    <button
                      type="button"
                      onClick={() => heroInputRef.current?.click()}
                      disabled={uploading}
                      className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                    >
                      {uploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
                      {heroUrl ? 'Replace' : 'Upload'}
                    </button>
                    {heroUrl && (
                      <button type="button" onClick={() => setHeroUrl('')} className="text-[11px] text-slate-500 hover:text-slate-700 underline">
                        Clear
                      </button>
                    )}
                    <input ref={heroInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleHeroUpload} />
                  </div>
                </div>
              </section>
            </div>

            {/* Right column — live preview mockup */}
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Preview</p>
              <div className="rounded-lg overflow-hidden border border-slate-200 shadow-sm sticky top-4">
                <div
                  className="aspect-video relative flex flex-col justify-between p-6"
                  style={{
                    background:
                      preset === 'hero' && heroUrl
                        ? `linear-gradient(rgba(0,0,0,0.40),rgba(0,0,0,0.40)), url('${heroUrl}') center/cover no-repeat`
                        : resolve(activePreset.body, brandColor),
                  }}
                >
                  {preset !== 'minimal' && preset !== 'bold' && activePreset.header !== activePreset.body && (
                    <div className="absolute top-0 left-0 right-0 h-1/3" style={{ background: resolve(activePreset.header, brandColor) }} />
                  )}
                  {/* Accent bar */}
                  {accent && isValidHex(accent) && (
                    <div className="absolute left-0 right-0 h-1" style={{ top: '33%', background: accent }} />
                  )}
                  <div className="relative">
                    <p className="text-[10px] font-semibold tracking-wider uppercase opacity-80" style={{ color: resolve(activePreset.subtitle, brandColor) }}>
                      {client.name}
                    </p>
                    <h1 className="mt-1 text-2xl sm:text-3xl font-bold leading-tight" style={{ color: resolve(activePreset.title, brandColor) }}>
                      {headline || 'Performance Report'}
                    </h1>
                    {subtitle && (
                      <p className="mt-2 text-sm opacity-90" style={{ color: resolve(activePreset.subtitle, brandColor) }}>{subtitle}</p>
                    )}
                  </div>
                  <div className="relative flex items-end justify-between text-[10px] opacity-70" style={{ color: resolve(activePreset.subtitle, brandColor) }}>
                    <span>Preview — colours only, not pixel-perfect</span>
                    <span>{activePreset.label}</span>
                  </div>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 mt-2">
                Download a PPTX preview for the real rendered cover (logos, hero image, template typography).
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
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

function LogoPlacementRow({
  label, position, size, onPosition, onSize,
}: {
  label: string
  position: LogoPosition
  size: LogoSize
  onPosition: (v: LogoPosition) => void
  onSize: (v: LogoSize) => void
}) {
  return (
    <div className="grid grid-cols-[110px_1fr_1fr] items-center gap-2">
      <span className="text-xs font-medium text-slate-700">{label}</span>
      <select
        value={position}
        onChange={(e) => onPosition(e.target.value as LogoPosition)}
        className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
      >
        {LOGO_POSITIONS.map((p) => (
          <option key={p.id} value={p.id}>{p.label}</option>
        ))}
      </select>
      <select
        value={size}
        onChange={(e) => onSize(e.target.value as LogoSize)}
        className="h-9 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
      >
        {LOGO_SIZES.map((s) => (
          <option key={s.id} value={s.id}>{s.label}</option>
        ))}
      </select>
    </div>
  )
}
