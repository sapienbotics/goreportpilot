'use client'
import { useRef } from 'react'
import Link from 'next/link'
import {
  FileText, Sparkles, Calendar, ChevronRight, Settings2,
  Check, Loader2, Image as ImageIcon,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import RichTextEditor from '@/components/clients/RichTextEditor'
import type { Report, ReportConfig } from '@/types'

type TemplateValue = 'full' | 'summary' | 'brief'
type VisualValue = 'modern_clean' | 'dark_executive' | 'colorful_agency' | 'bold_geometric' | 'minimal_elegant' | 'gradient_modern'

interface Props {
  clientId: string
  reports: Report[]
  reportsLoading: boolean
  periodStart: string
  periodEnd: string
  setPeriodStart: (v: string) => void
  setPeriodEnd: (v: string) => void
  selectedTemplate: TemplateValue
  setSelectedTemplate: (v: TemplateValue) => void
  visualTemplate: VisualValue
  setVisualTemplate: (v: VisualValue) => void
  generating: boolean
  genError: string | null
  reportConfig: ReportConfig
  setReportConfig: React.Dispatch<React.SetStateAction<ReportConfig>>
  savingConfig: boolean
  configSaved: boolean
  customImgInputRef: React.RefObject<HTMLInputElement>
  customImgUploading: boolean
  handleGenerate: () => void
  handleSaveConfig: () => void
  handleCustomSectionImageUpload: (e: React.ChangeEvent<HTMLInputElement>) => void
}

export default function ReportsTab({
  clientId, reports, reportsLoading,
  periodStart, periodEnd, setPeriodStart, setPeriodEnd,
  selectedTemplate, setSelectedTemplate,
  visualTemplate, setVisualTemplate,
  generating, genError,
  reportConfig, setReportConfig,
  savingConfig, configSaved,
  customImgInputRef, customImgUploading,
  handleGenerate, handleSaveConfig, handleCustomSectionImageUpload,
}: Props) {
  return (
    <div className="space-y-6">
      {/* Generate Report */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600" />
            Generate Report
          </CardTitle>
        </CardHeader>
        <CardContent>
          {generating ? (
            <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
              <div className="h-10 w-10 rounded-full border-4 border-indigo-200 border-t-indigo-700 animate-spin" />
              <p className="font-semibold text-slate-700">Generating report…</p>
              <p className="text-sm text-slate-400 max-w-xs">AI is pulling data and writing your narrative insights. This takes 15–30 seconds.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Detail level */}
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-2">Detail level</label>
                <div className="flex flex-wrap gap-2">
                  {([
                    { value: 'full' as const, label: 'Full Report', desc: '8 slides · complete analysis' },
                    { value: 'summary' as const, label: 'Summary', desc: '4 slides · KPIs + highlights' },
                    { value: 'brief' as const, label: 'One-Page Brief', desc: '2 slides · numbers + summary' },
                  ]).map(opt => (
                    <button key={opt.value} onClick={() => setSelectedTemplate(opt.value)}
                      className={`flex flex-col items-start px-4 py-2.5 rounded-lg border text-left transition-colors ${selectedTemplate === opt.value ? 'bg-indigo-700 border-indigo-700 text-white' : 'bg-white border-slate-200 text-slate-700 hover:border-indigo-300 hover:bg-indigo-50'}`}>
                      <span className="text-sm font-semibold">{opt.label}</span>
                      <span className={`text-xs mt-0.5 ${selectedTemplate === opt.value ? 'text-indigo-200' : 'text-slate-400'}`}>{opt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Visual style */}
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Visual Style</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {([
                    { value: 'modern_clean' as const, label: 'Modern Clean', desc: 'Light & professional', colors: ['#4338CA', '#FAFAFA', '#FFFFFF'] },
                    { value: 'dark_executive' as const, label: 'Dark Executive', desc: 'Premium dark theme', colors: ['#06B6D4', '#0F172A', '#1E293B'] },
                    { value: 'colorful_agency' as const, label: 'Colorful Agency', desc: 'Vibrant & creative', colors: ['#F97316', '#8B5CF6', '#14B8A6'] },
                    { value: 'bold_geometric' as const, label: 'Bold Geometric', desc: 'Strong shapes & impact', colors: ['#4338CA', '#3730A3', '#FFFFFF'] },
                    { value: 'minimal_elegant' as const, label: 'Minimal Elegant', desc: 'Ultra-clean whitespace', colors: ['#0F172A', '#FFFFFF', '#E2E8F0'] },
                    { value: 'gradient_modern' as const, label: 'Gradient Modern', desc: 'Warm startup aesthetic', colors: ['#F97316', '#F43F5E', '#8B5CF6'] },
                  ]).map(opt => (
                    <button key={opt.value} onClick={() => setVisualTemplate(opt.value)}
                      className={`flex flex-col items-start px-3 py-2.5 rounded-lg border text-left transition-colors ${visualTemplate === opt.value ? 'bg-indigo-700 border-indigo-700 text-white' : 'bg-white border-slate-200 text-slate-700 hover:border-indigo-300 hover:bg-indigo-50'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <div className="flex -space-x-0.5">
                          {opt.colors.map((c, i) => <div key={i} className="w-3 h-3 rounded-full border border-white/50" style={{ backgroundColor: c }} />)}
                        </div>
                        <span className="text-sm font-semibold">{opt.label}</span>
                      </div>
                      <span className={`text-xs ${visualTemplate === opt.value ? 'text-indigo-200' : 'text-slate-400'}`}>{opt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Date range */}
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-[160px]">
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">Period start</label>
                  <Input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} />
                </div>
                <div className="flex-1 min-w-[160px]">
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">Period end</label>
                  <Input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} />
                </div>
              </div>

              {genError && <p className="text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{genError}</p>}

              <button onClick={handleGenerate} disabled={!periodStart || !periodEnd}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-50">
                <Sparkles className="h-4 w-4" />
                Generate Report with AI
              </button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Report Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-slate-400" />
            Report Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Default detail level for scheduled reports</label>
            <select value={reportConfig.template}
              onChange={e => setReportConfig(c => ({ ...c, template: e.target.value as ReportConfig['template'] }))}
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="full">Full Report — 8 slides, complete analysis</option>
              <option value="summary">Summary — 4 slides, KPIs + highlights</option>
              <option value="brief">One-Page Brief — 2 slides, numbers + summary</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Sections</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {(Object.keys(reportConfig.sections) as Array<keyof ReportConfig['sections']>).map(key => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={reportConfig.sections[key]}
                    onChange={e => setReportConfig(c => ({ ...c, sections: { ...c.sections, [key]: e.target.checked } }))}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                  <span className="text-sm text-slate-700 capitalize">{key.replace(/_/g, ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          {reportConfig.sections.custom_section && (
            <div className="space-y-3 rounded-lg border border-indigo-100 bg-indigo-50 p-4">
              <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">Custom Section</p>
              <Input value={reportConfig.custom_section_title}
                onChange={e => setReportConfig(c => ({ ...c, custom_section_title: e.target.value }))}
                placeholder="Section title…" />
              <RichTextEditor value={reportConfig.custom_section_text}
                onChange={val => setReportConfig(c => ({ ...c, custom_section_text: val }))}
                placeholder="Write your custom commentary — use **bold**, ## headings, - bullets, 1. numbered lists…"
                rows={6} />
              <div className="flex items-center gap-3">
                {reportConfig.custom_section_image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={reportConfig.custom_section_image_url} alt="Custom section" className="h-16 w-24 object-cover rounded-md border border-indigo-200" />
                )}
                <div>
                  <button type="button" onClick={() => customImgInputRef.current?.click()} disabled={customImgUploading}
                    className="inline-flex items-center gap-1.5 rounded-md border border-indigo-200 bg-white px-3 py-1.5 text-xs text-indigo-700 hover:bg-indigo-50 transition-colors disabled:opacity-60">
                    {customImgUploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <ImageIcon className="h-3 w-3" />}
                    {customImgUploading ? 'Uploading…' : reportConfig.custom_section_image_url ? 'Replace image' : 'Add image'}
                  </button>
                  {reportConfig.custom_section_image_url && (
                    <button type="button" onClick={() => setReportConfig(c => ({ ...c, custom_section_image_url: undefined }))}
                      className="ml-2 text-xs text-rose-500 hover:text-rose-700">Remove</button>
                  )}
                  <p className="mt-1 text-[11px] text-slate-400">PNG / JPEG / WebP · max 5 MB · shown on slide right</p>
                </div>
                <input ref={customImgInputRef} type="file" accept="image/png,image/jpeg,image/webp"
                  onChange={handleCustomSectionImageUpload} className="hidden" />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button onClick={handleSaveConfig} disabled={savingConfig}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60">
              {savingConfig ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              {savingConfig ? 'Saving…' : 'Save Configuration'}
            </button>
            {configSaved && <span className="text-sm text-emerald-600 font-medium">✓ Saved</span>}
          </div>
        </CardContent>
      </Card>

      {/* Report History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <FileText className="h-4 w-4 text-slate-400" />
            Report History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {reportsLoading ? (
            <div className="space-y-2">
              {[1,2].map(i => <div key={i} className="h-12 rounded-lg bg-slate-100 animate-pulse" />)}
            </div>
          ) : reports.length === 0 ? (
            <p className="text-sm text-slate-400 py-2">No reports generated yet. Use the form above to generate your first report.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {reports.map(report => (
                <li key={report.id}>
                  <Link href={`/dashboard/reports/${report.id}`} className="flex items-center justify-between py-3 hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors group">
                    <div className="flex items-start gap-3">
                      <FileText className="h-4 w-4 text-indigo-400 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-slate-800 group-hover:text-indigo-700 transition-colors">{report.title}</p>
                        <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                          <Calendar className="h-3 w-3" />
                          {report.period_start} → {report.period_end}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${report.status === 'draft' || report.status === 'approved' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                        {report.status}
                      </span>
                      <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-500 transition-colors" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
