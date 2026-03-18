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

// ---------------------------------------------------------------------------
// Clients API
// ---------------------------------------------------------------------------

export interface ClientCreatePayload {
  name: string
  website?: string
  industry?: string
  contact_name?: string
  contact_email?: string
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
