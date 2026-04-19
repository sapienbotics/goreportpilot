// Shared TypeScript interfaces for ReportPilot
// These mirror the Supabase database schema
// See supabase/migrations/001_initial_schema.sql for field definitions
// See docs/reportpilot-feature-design-blueprint.md for full schema

export interface ReportConfig {
  sections: {
    cover_page: boolean
    executive_summary: boolean
    kpi_scorecard: boolean
    website_traffic: boolean
    meta_ads: boolean
    key_wins: boolean
    concerns: boolean
    next_steps: boolean
    custom_section: boolean
  }
  kpis: {
    website: string[]
    ads: string[]
  }
  template: 'full' | 'summary' | 'brief'
  custom_section_title: string
  custom_section_text: string
  custom_section_image_url?: string | null
}

export const DEFAULT_REPORT_CONFIG: ReportConfig = {
  sections: {
    cover_page: true,
    executive_summary: true,
    kpi_scorecard: true,
    website_traffic: true,
    meta_ads: true,
    key_wins: true,
    concerns: true,
    next_steps: true,
    custom_section: false,
  },
  kpis: {
    website: ['sessions', 'users', 'conversions', 'bounce_rate'],
    ads: ['spend', 'roas', 'cpc', 'conversions'],
  },
  template: 'full',
  custom_section_title: '',
  custom_section_text: '',
}

export interface Client {
  id: string
  user_id: string
  name: string
  website_url?: string | null
  industry?: string | null
  primary_contact_email?: string | null
  logo_url?: string | null
  goals_context?: string | null
  ai_tone: string
  notes?: string | null
  is_active: boolean
  report_config?: ReportConfig | null
  report_language?: string | null  // 'en' | 'es' | 'fr' | etc.
  // Cover-page customisation (Phase 3)
  cover_design_preset?: CoverPreset | null
  cover_headline?: string | null
  cover_subtitle?: string | null
  cover_hero_image_url?: string | null
  created_at: string
  updated_at: string
}

export type CoverPreset = 'default' | 'minimal' | 'bold' | 'corporate' | 'hero' | 'gradient'

export interface Connection {
  id: string
  client_id: string
  platform: string  // 'ga4' | 'meta_ads' | 'google_ads' | 'search_console' | csv_*
  account_id: string
  account_name: string
  currency: string  // Ad account billing currency, e.g. "INR", "USD"
  status: 'active' | 'expired' | 'error'
  token_expires_at?: string
  created_at: string
  updated_at: string
}

export interface Report {
  id: string
  user_id: string
  client_id: string
  client_name?: string | null
  title: string
  status: 'generating' | 'draft' | 'approved' | 'sent' | 'failed'
  period_start: string
  period_end: string
  pptx_url?: string | null
  pdf_url?: string | null
  narrative?: Record<string, string> | null
  data_summary?: Record<string, number | null> | null
  meta_currency?: string | null  // Billing currency of the connected Meta ad account
  user_edits?: Record<string, string> | null  // Manual text overrides; keys match narrative keys
  created_at: string
  updated_at: string
}

export interface DataSnapshot {
  id: string
  connection_id: string
  snapshot_date: string
  data: Record<string, unknown>
  created_at: string
}

export interface ShareLink {
  share_hash: string
  share_url: string
  expires_at: string | null
  has_password: boolean
  created_at: string
  is_active: boolean
}
