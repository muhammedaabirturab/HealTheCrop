import axios from 'axios'
import { useAuthStore } from '../store/authStore'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// Requests to these endpoints handle their own 401s (e.g. "wrong password" on
// login) — they must never trigger the global session-expired logout/redirect.
const AUTH_ENDPOINTS = ['/auth/login', '/auth/register']

export const api = axios.create({
  baseURL: API_BASE_URL,
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => error.config?.url?.includes(path))
    const hadToken = Boolean(error.config?.headers?.Authorization)

    if (error.response?.status === 401 && hadToken && !isAuthEndpoint) {
      useAuthStore.getState().logout()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
