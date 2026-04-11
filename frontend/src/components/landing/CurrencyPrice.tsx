'use client'

import { useEffect, useState } from 'react'
import { detectCurrency, type Currency } from '@/lib/detect-currency'

interface Props {
  /**
   * Which plan's price to render.
   * "starter" → $19 / ₹999
   * "pro"     → $39 / ₹1,999
   */
  plan?: 'starter' | 'pro'
  /** Optional prefix text rendered before the price. */
  prefix?: string
  /** Optional suffix text rendered after the price. */
  suffix?: string
  className?: string
}

const PRICE_MAP: Record<'starter' | 'pro', { usd: string; inr: string }> = {
  starter: { usd: '$19',  inr: '\u20B9999' },
  pro:     { usd: '$39',  inr: '\u20B91,999' },
}

/**
 * Small client component that renders a localized monthly price. The first
 * render (server + initial client) uses USD so there's no layout shift if
 * the visitor is not in India. We then swap to INR in a useEffect once
 * the browser locale is readable.
 *
 * Use for the hero reassurance line, feature-card flat-pricing copy, and
 * any other price mention outside the PricingToggle component.
 */
export default function CurrencyPrice({
  plan = 'starter',
  prefix = '',
  suffix = '',
  className = '',
}: Props) {
  const [currency, setCurrency] = useState<Currency>('USD')

  useEffect(() => {
    setCurrency(detectCurrency())
  }, [])

  const { usd, inr } = PRICE_MAP[plan]
  const price = currency === 'INR' ? inr : usd
  return <span className={className}>{prefix}{price}{suffix}</span>
}
