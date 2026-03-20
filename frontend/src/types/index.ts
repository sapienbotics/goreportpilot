// Shared TypeScript interfaces for ReportPilot
// These mirror the Supabase database schema
// See supabase/migrations/001_initial_schema.sql for field definitions
// See docs/reportpilot-feature-design-blueprint.md for full schema

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
  created_at: string
  updated_at: string
}

export interface Connection {
  id: string
  client_id: string
  platform: 'ga4' | 'meta_ads' | 'google_ads' | 'search_console' | 'linkedin_ads'
  account_id: string
  account_name: string
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
