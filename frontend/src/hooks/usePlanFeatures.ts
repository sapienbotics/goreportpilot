import { useEffect, useState } from 'react'
import { billingApi } from '@/lib/api'

export interface PlanFeatures {
  plan: string
  pptx_export: boolean
  pdf_export: boolean
  white_label: boolean
  scheduling: boolean
  ai_tones: string[]
  visual_templates: string[]
  powered_by_badge: boolean
}

const DEFAULT_FEATURES: PlanFeatures = {
  plan: 'trial',
  pptx_export: true,
  pdf_export: true,
  white_label: true,
  scheduling: true,
  ai_tones: ['professional', 'conversational', 'executive', 'data_heavy'],
  visual_templates: ['modern_clean', 'dark_executive', 'colorful_agency'],
  powered_by_badge: true,
}

/**
 * Fetch the current user's plan features.
 * Returns generous defaults (trial-level) while loading to avoid flash of locked state.
 */
export function usePlanFeatures(): { features: PlanFeatures; status: string; loading: boolean } {
  const [features, setFeatures] = useState<PlanFeatures>(DEFAULT_FEATURES)
  const [status, setStatus] = useState<string>('trialing')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    billingApi
      .getSubscription()
      .then((sub) => {
        setStatus(sub.status)
        const f = (sub.features ?? {}) as Record<string, unknown>
        setFeatures({
          plan: sub.plan,
          pptx_export: f.pptx_export === true,
          pdf_export: f.pdf_export !== false,
          white_label: f.white_label === true,
          scheduling: f.scheduling === true,
          ai_tones: Array.isArray(f.ai_tones) ? (f.ai_tones as string[]) : ['professional'],
          visual_templates: Array.isArray(f.visual_templates) ? (f.visual_templates as string[]) : ['modern_clean'],
          powered_by_badge: f.powered_by_badge !== false,
        })
      })
      .catch(() => {
        // On error, keep trial-level defaults — don't lock out users
      })
      .finally(() => setLoading(false))
  }, [])

  return { features, status, loading }
}
