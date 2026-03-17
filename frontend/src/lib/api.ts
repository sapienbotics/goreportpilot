// Centralized API client for FastAPI backend
// All API calls from the frontend must go through this client
// Never call fetch() directly in components — use this module

import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

export default api
