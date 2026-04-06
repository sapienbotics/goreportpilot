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
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</span>
        {Icon && (
          <div className={`rounded-lg p-2 ${colorMap[color]}`}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
    </div>
  )
}
