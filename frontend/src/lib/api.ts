// Centralized API client for FastAPI backend
// All API calls from the frontend must go through this client
// Never call fetch() directly in components — use this module

import axios from 'axios'
import { createBrowserClient } from '@supabase/ssr'
import type { Client } from '@/types'

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
}

import type { Report } from '@/types'

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
}
