// Centralized API client for FastAPI backend
// All API calls from the frontend must go through this client
// Never call fetch() directly in components — use this module

import axios from 'axios'
import { createBrowserClient } from '@supabase/ssr'
import type { Client, Connection, Report } from '@/types'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

// Attach the Supabase JWT to every request so FastAPI can verify the caller
api.interceptors.request.use(async (config) => {
  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

export default api

// Helper — makes an authenticated GET request and triggers a browser file download.
// Must be called from a client component (uses window/document).
export async function downloadFileWithAuth(url: string, filename: string): Promise<void> {
  const response = await api.get(url, { responseType: 'blob' })
  const blob = new Blob([response.data], {
    type: (response.headers['content-type'] as string) || 'application/octet-stream',
  })
  const blobUrl = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(blobUrl)
}

// ---------------------------------------------------------------------------
// Clients API
// ---------------------------------------------------------------------------

export interface ClientCreatePayload {
  name: string
  website_url?: string
  industry?: string
  primary_contact_email?: string
  goals_context?: string
  ai_tone?: string
  notes?: string
}

export interface ClientUpdatePayload extends Partial<ClientCreatePayload> {
  is_active?: boolean
  report_language?: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  report_config?: any  // ReportConfig — use any to avoid circular import
}

export const clientsApi = {
  list: async (): Promise<{ clients: Client[]; total: number }> => {
    const { data } = await api.get('/api/clients')
    return data
  },

  get: async (clientId: string): Promise<Client> => {
    const { data } = await api.get(`/api/clients/${clientId}`)
    return data
  },

  create: async (payload: ClientCreatePayload): Promise<Client> => {
    const { data } = await api.post('/api/clients', payload)
    return data
  },

  update: async (clientId: string, payload: ClientUpdatePayload): Promise<Client> => {
    const { data } = await api.patch(`/api/clients/${clientId}`, payload)
    return data
  },

  delete: async (clientId: string): Promise<void> => {
    await api.delete(`/api/clients/${clientId}`)
  },
}

// ---------------------------------------------------------------------------
// Reports API
// ---------------------------------------------------------------------------

export interface ReportGeneratePayload {
  client_id: string
  period_start: string // "YYYY-MM-DD"
  period_end: string   // "YYYY-MM-DD"
  template?: string    // "full" | "summary" | "brief" — defaults to "full"
  visual_template?: string // "modern_clean" | "dark_executive" | "colorful_agency"
}

// ---------------------------------------------------------------------------
// Auth API  (Google OAuth)
// ---------------------------------------------------------------------------

export interface GoogleAuthUrlResponse {
  url: string
  state: string
}

export interface Ga4Property {
  property_id: string
  display_name: string
  time_zone?: string | null
  currency_code?: string | null
}

export interface GoogleCallbackPayload {
  code: string
  state: string
}

export interface GoogleCallbackResponse {
  properties: Ga4Property[]
  token_handle: string
}

export interface GoogleAdsAccount {
  customer_id: string
  name: string
  currency_code: string
  time_zone: string
}

export interface GoogleAdsCallbackResponse {
  accounts: GoogleAdsAccount[]
  token_handle: string
  expires_in: number
}

export interface SearchConsoleSite {
  site_url: string          // backend field name: {"site_url": ..., "permission_level": ...}
  permission_level: string
}

export interface SearchConsoleCallbackResponse {
  sites: SearchConsoleSite[]
  token_handle: string
  expires_in: number
}

export interface MetaAuthUrlResponse {
  url: string
  state: string
}

export interface MetaAdAccount {
  account_id: string
  account_name: string
  currency: string
  status: number
}

export interface MetaCallbackResponse {
  ad_accounts: MetaAdAccount[]
  token_handle: string
  expires_in: number
}

export const authApi = {
  getGoogleAuthUrl: async (): Promise<GoogleAuthUrlResponse> => {
    const { data } = await api.get('/api/auth/google/url')
    return data
  },

  googleCallback: async (payload: GoogleCallbackPayload): Promise<GoogleCallbackResponse> => {
    const { data } = await api.post('/api/auth/google/callback', payload)
    return data
  },

  getMetaAuthUrl: async (): Promise<MetaAuthUrlResponse> => {
    const { data } = await api.get('/api/auth/meta/url')
    return data
  },

  metaCallback: async (code: string): Promise<MetaCallbackResponse> => {
    const { data } = await api.post('/api/auth/meta/callback', { code })
    return data
  },

  getGoogleAdsAuthUrl: async (): Promise<{ url: string }> => {
    const { data } = await api.get('/api/auth/google-ads/url')
    return data
  },

  googleAdsCallback: async (payload: GoogleCallbackPayload): Promise<GoogleAdsCallbackResponse> => {
    const { data } = await api.post('/api/auth/google-ads/callback', payload)
    return data
  },

  getSearchConsoleAuthUrl: async (): Promise<{ url: string }> => {
    const { data } = await api.get('/api/auth/search-console/url')
    return data
  },

  searchConsoleCallback: async (payload: GoogleCallbackPayload): Promise<SearchConsoleCallbackResponse> => {
    const { data } = await api.post('/api/auth/search-console/callback', payload)
    return data
  },
}

// ---------------------------------------------------------------------------
// Connections API
// ---------------------------------------------------------------------------

export interface ConnectionCreatePayload {
  client_id: string
  platform: string
  account_id: string
  account_name: string
  token_handle: string
  currency?: string  // Ad account billing currency (e.g. "INR"). Defaults to "USD" on backend.
}

export const connectionsApi = {
  create: async (payload: ConnectionCreatePayload): Promise<Connection> => {
    const { data } = await api.post('/api/connections', payload)
    return data
  },

  listByClient: async (clientId: string): Promise<{ connections: Connection[]; total: number }> => {
    const { data } = await api.get(`/api/connections/client/${clientId}`)
    return data
  },

  delete: async (connectionId: string): Promise<void> => {
    await api.delete(`/api/connections/${connectionId}`)
  },
}

export interface ReportSendPayload {
  to_emails: string[]
  subject?: string
  attachment?: 'pdf' | 'pptx' | 'both'
  sender_name?: string
  reply_to?: string
}

export interface ReportSendResult {
  success: boolean
  resend_id?: string
  to: string[]
  subject: string
}

// ---------------------------------------------------------------------------
// Settings API
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const settingsApi = {
  getProfile: async (): Promise<Record<string, unknown>> => {
    const { data } = await api.get('/api/settings/profile')
    return data
  },

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  updateProfile: async (payload: Record<string, any>): Promise<Record<string, unknown>> => {
    const { data } = await api.patch('/api/settings/profile', payload)
    return data
  },

  uploadLogo: async (file: File): Promise<{ url: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    // For FormData uploads we use fetch directly to avoid setting Content-Type manually
    const supabase = (await import('@supabase/ssr')).createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    )
    const { data: { session } } = await supabase.auth.getSession()
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/settings/upload-logo`,
      {
        method: 'POST',
        headers: session?.access_token
          ? { Authorization: `Bearer ${session.access_token}` }
          : {},
        body: formData,
      },
    )
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },
}

// ---------------------------------------------------------------------------
// Scheduled Reports API
// ---------------------------------------------------------------------------

export interface ScheduledReportPayload {
  client_id: string
  frequency: 'weekly' | 'biweekly' | 'monthly'
  day_of_week?: number
  day_of_month?: number
  time_utc?: string
  template?: string
  auto_send?: boolean
  send_to_emails?: string[]
}

export interface ScheduledReport {
  id: string
  client_id: string
  user_id: string
  frequency: string
  day_of_week?: number | null
  day_of_month?: number | null
  time_utc: string
  template: string
  auto_send: boolean
  send_to_emails: string[]
  is_active: boolean
  last_generated_at?: string | null
  next_run_at?: string | null
  created_at: string
  updated_at: string
}

export const scheduledReportsApi = {
  create: async (payload: ScheduledReportPayload): Promise<ScheduledReport> => {
    const { data } = await api.post('/api/scheduled-reports', payload)
    return data
  },

  getByClient: async (clientId: string): Promise<ScheduledReport[]> => {
    const { data } = await api.get(`/api/scheduled-reports/client/${clientId}`)
    return data
  },

  list: async (): Promise<ScheduledReport[]> => {
    const { data } = await api.get('/api/scheduled-reports')
    return data
  },

  update: async (id: string, payload: Partial<ScheduledReportPayload> & { is_active?: boolean }): Promise<ScheduledReport> => {
    const { data } = await api.patch(`/api/scheduled-reports/${id}`, payload)
    return data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/scheduled-reports/${id}`)
  },
}

// ---------------------------------------------------------------------------
// Client logo upload helper
// ---------------------------------------------------------------------------

export async function uploadClientLogo(clientId: string, file: File): Promise<{ url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const supabase = (await import('@supabase/ssr')).createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
  const { data: { session } } = await supabase.auth.getSession()
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/clients/${clientId}/upload-logo`,
    {
      method: 'POST',
      headers: session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {},
      body: formData,
    },
  )
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// CSV Upload API
// ---------------------------------------------------------------------------
export const csvApi = {
  upload: async (file: File, clientId: string, sourceName?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('client_id', clientId)
    if (sourceName) form.append('source_name', sourceName)
    const { data } = await api.post('/api/connections/csv-upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
  getTemplates: () => `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/connections/csv-templates`,
  getTemplateUrl: (name: string) => `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/connections/csv-templates/${name}`,
}

// ---------------------------------------------------------------------------
// Share API
// ---------------------------------------------------------------------------
export const shareApi = {
  create: async (reportId: string, payload: { password?: string; expires_days?: number }) => {
    const { data } = await api.post(`/api/reports/${reportId}/share`, payload)
    return data
  },
  list: async (reportId: string) => {
    const { data } = await api.get(`/api/reports/${reportId}/share`)
    return data
  },
  revoke: async (reportId: string, hash: string) => {
    const { data } = await api.delete(`/api/reports/${reportId}/share/${hash}`)
    return data
  },
  getAnalytics: async (reportId: string) => {
    const { data } = await api.get(`/api/reports/${reportId}/analytics`)
    return data
  },
}

// ---------------------------------------------------------------------------
// Custom Section Image Upload
// ---------------------------------------------------------------------------
export const customSectionApi = {
  uploadImage: async (clientId: string, file: File) => {
    const form = new FormData()
    form.append('image', file)
    const { data } = await api.post(`/api/clients/${clientId}/custom-section-image`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data  // Returns { url: string }
  },
}

// ---------------------------------------------------------------------------
// Dashboard API
// ---------------------------------------------------------------------------
// Note: dashboard page calls api.get('/api/dashboard/stats') directly
// to avoid circular type deps — no wrapper needed here.

// ---------------------------------------------------------------------------
// Billing API
// ---------------------------------------------------------------------------

export interface SubscriptionStatus {
  plan: string
  display_name: string
  status: string
  billing_cycle: string
  client_count: number
  client_limit: number
  current_period_start: string | null
  current_period_end: string | null
  trial_ends_at: string | null
  trial_days_remaining: number | null
  cancelled_at: string | null
  cancel_at_period_end: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  features: Record<string, any>
  can_create_client: boolean
  razorpay_subscription_id: string | null
}

export interface CreateSubscriptionResponse {
  subscription_id: string
  razorpay_key_id: string
}

export const billingApi = {
  getSubscription: async (): Promise<SubscriptionStatus> => {
    const { data } = await api.get('/api/billing/subscription')
    return data
  },

  createSubscription: async (payload: { plan: string; billing_cycle: string }): Promise<CreateSubscriptionResponse> => {
    const { data } = await api.post('/api/billing/create-subscription', payload)
    return data
  },

  verifyPayment: async (payload: {
    razorpay_payment_id: string
    razorpay_subscription_id: string
    razorpay_signature: string
  }): Promise<{ success: boolean; status: string }> => {
    const { data } = await api.post('/api/billing/verify-payment', payload)
    return data
  },

  changePlan: async (payload: { plan: string; billing_cycle: string }): Promise<CreateSubscriptionResponse> => {
    const { data } = await api.post('/api/billing/change-plan', payload)
    return data
  },

  cancel: async (): Promise<{ success: boolean; cancel_at_period_end: boolean }> => {
    const { data } = await api.post('/api/billing/cancel')
    return data
  },

  getPaymentHistory: async (): Promise<{ payments: Record<string, unknown>[] }> => {
    const { data } = await api.get('/api/billing/payment-history')
    return data
  },
}

export const reportsApi = {
  generate: async (payload: ReportGeneratePayload): Promise<Report> => {
    const { data } = await api.post('/api/reports/generate', payload)
    return data
  },

  get: async (id: string): Promise<Report> => {
    const { data } = await api.get(`/api/reports/${id}`)
    return data
  },

  listAll: async (): Promise<{ reports: Report[]; total: number }> => {
    const { data } = await api.get('/api/reports')
    return data
  },

  listByClient: async (clientId: string): Promise<{ reports: Report[]; total: number }> => {
    const { data } = await api.get(`/api/reports/client/${clientId}`)
    return data
  },

  /** Save manual text edits for one or more narrative sections. */
  update: async (id: string, userEdits: Record<string, string>): Promise<Report> => {
    const { data } = await api.patch(`/api/reports/${id}`, { user_edits: userEdits })
    return data
  },

  /** Re-run AI for a single narrative section. */
  regenerateSection: async (id: string, section: string): Promise<Report> => {
    const { data } = await api.post(`/api/reports/${id}/regenerate-section`, { section })
    return data
  },

  /** Send the report to one or more email addresses. */
  send: async (id: string, payload: ReportSendPayload): Promise<ReportSendResult> => {
    const { data } = await api.post(`/api/reports/${id}/send`, payload)
    return data
  },

  /** Create a shareable public link for this report. */
  share: async (reportId: string, payload: { password?: string; expires_days?: number }) => {
    const { data } = await api.post(`/api/reports/${reportId}/share`, payload)
    return data
  },
}
