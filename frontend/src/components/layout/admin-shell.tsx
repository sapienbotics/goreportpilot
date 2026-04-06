'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  BarChart3, Users, CreditCard, Link2, FileText,
  Server, Shield, Menu, X, ArrowLeft,
} from 'lucide-react'
import { SignOutButton } from './sign-out-button'

const NAV_ITEMS = [
  { label: 'Overview',       href: '/admin',               icon: BarChart3 },
  { label: 'Users',          href: '/admin/users',         icon: Users },
  { label: 'Subscriptions',  href: '/admin/subscriptions', icon: CreditCard },
  { label: 'Connections',    href: '/admin/connections',    icon: Link2 },
  { label: 'Reports',        href: '/admin/reports',       icon: FileText },
  { label: 'System',         href: '/admin/system',        icon: Server },
  { label: 'GDPR',           href: '/admin/gdpr',          icon: Shield },
]

interface AdminShellProps {
  email: string
  children: React.ReactNode
}

export function AdminShell({ email, children }: AdminShellProps) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  const isActive = (href: string) => {
    if (href === '/admin') return pathname === '/admin'
    return pathname.startsWith(href)
  }

  const sidebar = (
    <div className="flex flex-col h-full w-60 bg-slate-900 text-white">
      {/* Red accent bar */}
      <div className="h-1 bg-rose-500 shrink-0" />

      <div className="px-4 py-5">
        <p className="text-xs font-bold uppercase tracking-widest text-rose-400">Admin Dashboard</p>
        <p className="text-[11px] text-slate-400 mt-0.5 truncate">{email}</p>
      </div>

      <nav className="flex-1 px-2 space-y-0.5">
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            onClick={() => setMobileOpen(false)}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
              isActive(href)
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
            }`}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="px-2 pb-4">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Switch to User View
        </Link>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden md:flex md:flex-col shrink-0">{sidebar}</div>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <div className="relative flex flex-col w-60 h-full shadow-xl">
            {sidebar}
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute top-3 right-3 text-slate-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <header className="h-14 shrink-0 flex items-center justify-between px-4 md:px-6 bg-white border-b border-slate-200">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden p-2 rounded-md text-slate-500 hover:bg-slate-100"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="text-sm font-semibold text-rose-600">Admin</span>
          </div>
          <SignOutButton />
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}
