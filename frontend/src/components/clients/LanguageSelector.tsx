'use client'

import { Globe } from 'lucide-react'
import { cn } from '@/lib/utils'

export const LANGUAGES = [
  { code: 'en', name: 'English',     flag: '🇺🇸' },
  { code: 'es', name: 'Español',     flag: '🇪🇸' },
  { code: 'fr', name: 'Français',    flag: '🇫🇷' },
  { code: 'de', name: 'Deutsch',     flag: '🇩🇪' },
  { code: 'pt', name: 'Português',   flag: '🇧🇷' },
  { code: 'it', name: 'Italiano',    flag: '🇮🇹' },
  { code: 'nl', name: 'Nederlands',  flag: '🇳🇱' },
  { code: 'sv', name: 'Svenska',     flag: '🇸🇪' },
  { code: 'no', name: 'Norsk',       flag: '🇳🇴' },
  { code: 'da', name: 'Dansk',       flag: '🇩🇰' },
  { code: 'fi', name: 'Suomi',       flag: '🇫🇮' },
  { code: 'ja', name: '日本語',      flag: '🇯🇵' },
  { code: 'zh', name: '中文',        flag: '🇨🇳' },
  { code: 'hi', name: 'हिन्दी',     flag: '🇮🇳' },
  { code: 'ar', name: 'العربية',     flag: '🇸🇦' },
  { code: 'ko', name: '한국어',      flag: '🇰🇷' },
  { code: 'tr', name: 'Türkçe',     flag: '🇹🇷' },
]

interface Props {
  value: string
  onChange: (code: string) => void
  disabled?: boolean
  showLabel?: boolean   // set false when embedded in a labelled Field row
}

export default function LanguageSelector({ value, onChange, disabled, showLabel = true }: Props) {
  const selected = LANGUAGES.find((l) => l.code === value) ?? LANGUAGES[0]

  return (
    <div className="flex flex-col gap-1.5">
      {showLabel && (
        <label className="flex items-center gap-1.5 text-sm font-medium text-slate-700">
          <Globe className="h-4 w-4 text-indigo-600" />
          Report Language
        </label>
      )}

      <div className="relative">
        {/* Flag preview badge overlaid on the left of the select */}
        <span
          className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-base select-none"
          aria-hidden="true"
        >
          {selected.flag}
        </span>

        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={cn(
            'w-full appearance-none rounded-md border border-slate-300 bg-white py-2 pl-9 pr-8 text-sm text-slate-900 shadow-sm',
            'focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30',
            'transition-colors duration-150',
            disabled && 'cursor-not-allowed bg-slate-50 text-slate-400 opacity-60'
          )}
        >
          {LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.flag} {lang.name}
            </option>
          ))}
        </select>

        {/* Custom chevron */}
        <span className="pointer-events-none absolute inset-y-0 right-2.5 flex items-center text-slate-400">
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </div>

      <p className="text-xs text-slate-500">
        AI narrative and report headings will be generated in this language.
      </p>
    </div>
  )
}
