'use client'

import type { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  label: string
  value: string | number
  icon?: LucideIcon
  color?: 'indigo' | 'emerald' | 'rose' | 'amber' | 'slate'
}

const colorMap = {
  indigo:  'bg-indigo-50 text-indigo-600',
  emerald: 'bg-emerald-50 text-emerald-600',
  rose:    'bg-rose-50 text-rose-600',
  amber:   'bg-amber-50 text-amber-600',
  slate:   'bg-slate-100 text-slate-500',
}

export function StatsCard({ label, value, icon: Icon, color = 'indigo' }: StatsCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 sm:p-5 shadow-sm">
      <div className="flex items-center justify-between mb-1 sm:mb-2">
        <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wide text-slate-400 truncate mr-1">{label}</span>
        {Icon && (
          <div className={`rounded-lg p-1.5 sm:p-2 ${colorMap[color]} shrink-0`}>
            <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          </div>
        )}
      </div>
      <p className="text-lg sm:text-2xl font-bold text-slate-900 truncate">{value}</p>
    </div>
  )
}
