'use client'

// Dashboard shell — handles mobile sidebar toggle
// Wraps the sidebar, header, and main content area

import { useState } from 'react'
import { Menu } from 'lucide-react'
import { Sidebar } from './sidebar'
import { SignOutButton } from './sign-out-button'

interface DashboardShellProps {
  email: string
  children: React.ReactNode
}

export function DashboardShell({ email, children }: DashboardShellProps) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Desktop sidebar — always visible */}
      <div className="hidden md:flex md:flex-col">
        <Sidebar />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileSidebarOpen(false)}
          />
          {/* Drawer */}
          <div className="relative flex flex-col w-64 h-full bg-white shadow-xl">
            <Sidebar onClose={() => setMobileSidebarOpen(false)} />
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        {/* Header */}
        <header className="h-16 shrink-0 flex items-center justify-between px-4 md:px-6 bg-white border-b border-slate-200">
          <div className="flex items-center gap-3">
            {/* Hamburger — mobile only */}
            <button
              className="md:hidden p-2 rounded-md text-slate-500 hover:bg-slate-100 transition-colors"
              onClick={() => setMobileSidebarOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="text-sm text-slate-500 font-medium truncate max-w-[200px] sm:max-w-none">
              {email}
            </span>
          </div>
          <SignOutButton />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}
