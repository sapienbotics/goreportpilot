'use client'

// CoverPageTab — Phase 3. Lets an agency user pick one of 5 cover-page
// presets, override the headline/subtitle, and upload a hero image.
//
// Live preview: CSS mockup that matches the chosen preset's colour scheme.
// Real PPTX preview: click the "Download PPTX preview" button to fetch a
// 1-slide PPTX from /api/reports/preview-cover. Fast feedback loop without
// waiting for full report generation.

import { useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  Image as ImageIcon, Loader2, Upload, Download, Check,
} from 'lucide-react'
import type { Client, CoverPreset } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { clientsApi, previewCover, uploadCoverHero } from '@/lib/api'

interface Props {
  client: Client
  onClientUpdate: (client: Client) => void
}

interface PresetDef {
  id: CoverPreset
  label: string
  description: string
  // Swatches used only for the in-tab CSS preview mockup.
  // `brand` resolves to the agency brand color at render time.
  header: string
  body:   string
  title:  string
  subtitle: string
}

const PRESETS: PresetDef[] = [
  {
    id: 'default',
    label: 'Default',
    description: 'Use the visual template\u2019s native cover. No overrides.',
    header: '#4338CA', body: '#ffffff', title: '#ffffff', subtitle: '#C7D2FE',
  },
  {
    id: 'minimal',
    label: 'Minimal',
    description: 'Clean white background, muted accents, dark type.',
    header: '#FFFFFF', body: '#FFFFFF', title: '#0F172A', subtitle: '#64748B',
  },
  {
    id: 'bold',
    label: 'Bold',
    description: 'Full-bleed brand colour with a large white headline.',
    header: 'brand', body: 'brand', title: '#FFFFFF', subtitle: '#F1F5F9',
  },
  {
    id: 'corporate',
    label: 'Corporate',
    description: 'Deep navy header, white title, brand-coloured accent bar.',
    header: '#1E293B', body: '#FFFFFF', title: '#FFFFFF', subtitle: '#CBD5E1',
  },
  {
    id: 'hero',
    label: 'Hero image',
    description: 'Full-bleed photo background with a dark legibility overlay.',
    header: '#0F172A', body: '#0F172A', title: '#FFFFFF', subtitle: '#F1F5F9',
  },
  {
    id: 'gradient',
    label: 'Gradient',
    description: 'Brand colour band with contrasting dark body.',
    header: 'brand', body: '#0F172A', title: '#FFFFFF', subtitle: '#E2E8F0',
  },
]

function resolve(color: string, brand: string | undefined): string {
  return color === 'brand' ? (brand || '#4338CA') : color
}

export default function CoverPageTab({ client, onClientUpdate }: Props) {
  const heroInputRef = useRef<HTMLInputElement>(null)

  const [preset, setPreset] = useState<CoverPreset>(
    (client.cover_design_preset as CoverPreset) || 'default',
  )
  const [headline, setHeadline] = useState(client.cover_headline ?? '')
  const [subtitle, setSubtitle] = useState(client.cover_subtitle ?? '')
  const [heroUrl, setHeroUrl]   = useState(client.cover_hero_image_url ?? '')

  const [saving,     setSaving]     = useState(false)
  const [uploading,  setUploading]  = useState(false)
  const [previewing, setPreviewing] = useState(false)

  // Brand color from the agency profile — fetched via window.__goreportpilot_brand
  // or defaulted. The client record doesn't carry brand color, so we take the
  // preset's 'brand' sentinel and render it with a sensible fallback.
  const brandColor = '#4338CA'   // Stylistic approximation — backend uses real brand colour.

  const activePreset = PRESETS.find((p) => p.id === preset) ?? PRESETS[0]
  const hasChanges = (
    preset !== (client.cover_design_preset ?? 'default') ||
    headline !== (client.cover_headline ?? '') ||
    subtitle !== (client.cover_subtitle ?? '') ||
    heroUrl !== (client.cover_hero_image_url ?? '')
  )

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await clientsApi.update(client.id, {
        cover_design_preset: preset,
        cover_headline:      headline || null,
        cover_subtitle:      subtitle || null,
        cover_hero_image_url: heroUrl || null,
      })
      onClientUpdate(updated)
      toast.success('Cover page saved.')
    } catch (exc) {
      toast.error('Failed to save cover page settings.')
      // eslint-disable-next-line no-console
      console.error(exc)
    } finally {
      setSaving(false)
    }
  }

  const handleHeroUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Hero image must be under 2MB.')
      e.target.value = ''
      return
    }
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
        client_id:      client.id,
        preset,
        headline:       headline || null,
        subtitle:       subtitle || null,
        hero_image_url: heroUrl || null,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${client.name.replace(/\s+/g, '_')}_cover_preview.pptx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (exc) {
      toast.error('Could not generate cover preview.')
      // eslint-disable-next-line no-console
      console.error(exc)
    } finally {
      setPreviewing(false)
    }
  }

  return (
    <div className="space-y-4 max-w-4xl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="text-base font-semibold text-slate-900">Cover page</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Pick a preset, tailor the headline, and optionally add a hero image. Applied to every report for {client.name}.
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
          {/* Preset selector */}
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Preset</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-6">
            {PRESETS.map((p) => {
              const selected = preset === p.id
              const header = resolve(p.header, brandColor)
              const body = resolve(p.body, brandColor)
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPreset(p.id)}
                  className={`text-left rounded-lg border p-2 transition-all ${selected ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200 hover:border-slate-300'}`}
                >
                  {/* Mini swatch */}
                  <div className="rounded overflow-hidden mb-2 h-16 border border-slate-100">
                    <div className="h-1/2" style={{ background: header }} />
                    <div className="h-1/2" style={{ background: body }} />
                  </div>
                  <p className="text-xs font-semibold text-slate-800">{p.label}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">{p.description}</p>
                </button>
              )
            })}
          </div>

          {/* Headline / subtitle */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Headline (optional)
              </label>
              <Input
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                placeholder="e.g. Q2 Performance Review"
                maxLength={80}
                className="mt-1"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Overrides the default report title on the cover.
              </p>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Subtitle (optional)
              </label>
              <Input
                value={subtitle}
                onChange={(e) => setSubtitle(e.target.value)}
                placeholder="e.g. Prepared for Acme Corp"
                maxLength={120}
                className="mt-1"
              />
            </div>
          </div>

          {/* Hero image uploader — only meaningful for hero preset */}
          <div className={`rounded-lg border p-3 mb-6 transition-opacity ${preset === 'hero' ? '' : 'opacity-60'}`}>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <ImageIcon className="h-3.5 w-3.5 text-slate-400" />
                  Hero image
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
                  <button
                    type="button"
                    onClick={() => setHeroUrl('')}
                    className="text-[11px] text-slate-500 hover:text-slate-700 underline"
                  >
                    Clear
                  </button>
                )}
                <input
                  ref={heroInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={handleHeroUpload}
                />
              </div>
            </div>
          </div>

          {/* Live CSS mockup preview */}
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Preview</p>
          <div className="rounded-lg overflow-hidden border border-slate-200 shadow-sm">
            <div
              className="aspect-video relative flex flex-col justify-between p-6"
              style={{
                background:
                  preset === 'hero' && heroUrl
                    ? `linear-gradient(rgba(0,0,0,0.55),rgba(0,0,0,0.55)), url('${heroUrl}') center/cover no-repeat`
                    : resolve(activePreset.body, brandColor),
              }}
            >
              {/* Header band (if distinct from body) */}
              {preset !== 'minimal' && preset !== 'bold' && activePreset.header !== activePreset.body && (
                <div
                  className="absolute top-0 left-0 right-0 h-1/3"
                  style={{ background: resolve(activePreset.header, brandColor) }}
                />
              )}
              <div className="relative">
                <p
                  className="text-[10px] font-semibold tracking-wider uppercase opacity-80"
                  style={{ color: resolve(activePreset.subtitle, brandColor) }}
                >
                  {client.name}
                </p>
                <h1
                  className="mt-1 text-2xl sm:text-3xl font-bold leading-tight"
                  style={{ color: resolve(activePreset.title, brandColor) }}
                >
                  {headline || 'Performance Report'}
                </h1>
                {subtitle && (
                  <p
                    className="mt-2 text-sm opacity-90"
                    style={{ color: resolve(activePreset.subtitle, brandColor) }}
                  >
                    {subtitle}
                  </p>
                )}
              </div>
              <div className="relative flex items-end justify-between text-[10px] opacity-70"
                style={{ color: resolve(activePreset.subtitle, brandColor) }}>
                <span>Cover preview — colours only, not pixel-perfect</span>
                <span>{activePreset.label}</span>
              </div>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            The mockup above is a CSS approximation. Click <strong>Download PPTX preview</strong> to see the real rendered cover.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
