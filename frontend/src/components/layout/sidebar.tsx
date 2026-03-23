'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Users, FileText, Link2, Settings, CreditCard, X } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/clients', label: 'Clients', icon: Users },
  { href: '/dashboard/reports', label: 'Reports', icon: FileText },
  { href: '/dashboard/integrations', label: 'Integrations', icon: Link2 },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
  { href: '/dashboard/billing', label: 'Billing', icon: CreditCard },
]

interface SidebarProps {
  onClose?: () => void
}

export function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col h-full">
      {/* Logo area */}
      <div className="flex items-center justify-between h-16 px-6 border-b border-slate-200">
        <span
          className="text-xl font-bold text-indigo-700"
          style={{ fontFamily: 'var(--font-plus-jakarta-sans)' }}
        >
          ReportPilot
        </span>
        {/* Close button — only shown on mobile overlay */}
        {onClose && (
          <button onClick={onClose} className="md:hidden p-1 rounded text-slate-400 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === '/dashboard'
              ? pathname === '/dashboard'
              : pathname.startsWith(href)

          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer links */}
      <div className="px-6 py-4 border-t border-slate-100">
        <div className="flex gap-3 text-xs text-slate-400">
          <Link href="/privacy" className="hover:text-slate-600">Privacy</Link>
          <Link href="/terms" className="hover:text-slate-600">Terms</Link>
        </div>
      </div>
    </aside>
  )
}
