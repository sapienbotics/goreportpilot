'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Menu, X } from 'lucide-react'

export default function MobileNav() {
  const [open, setOpen] = useState(false)

  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rounded-md p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
        aria-label={open ? 'Close menu' : 'Open menu'}
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-16 bg-white border-b border-slate-100 shadow-lg z-50 px-6 py-4 space-y-1">
          <a
            href="#features"
            onClick={() => setOpen(false)}
            className="block rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
          >
            Features
          </a>
          <a
            href="#pricing"
            onClick={() => setOpen(false)}
            className="block rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
          >
            Pricing
          </a>
          <Link
            href="/login"
            onClick={() => setOpen(false)}
            className="block rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
          >
            Sign In
          </Link>
          <div className="pt-2">
            <Link
              href="/signup"
              onClick={() => setOpen(false)}
              className="block rounded-lg bg-indigo-700 px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
