import axios from 'axios'
import { useAuthStore } from '../store/authStore'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// Requests to these endpoints handle their own 401s (e.g. "wrong password" on
// login) — they must never trigger the global session-expired logout/redirect
// or the silent-refresh flow below.
const AUTH_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/refresh']

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

// A "Remember Me" login stores a refresh token; when the (short-lived) access
// token expires, this exchanges it for a fresh one exactly once per failing
// request instead of forcing a full re-login. Concurrent 401s share the same
// in-flight refresh call rather than each firing their own.
let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = useAuthStore.getState().refreshToken
  if (!refreshToken) return null

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
      .then((res) => {
        useAuthStore.getState().setAccessToken(res.data.access_token, res.data.refresh_token)
        return res.data.access_token as string
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => config?.url?.includes(path))
    const hadToken = Boolean(config?.headers?.Authorization)

    if (error.response?.status === 401 && hadToken && !isAuthEndpoint && !config._retriedAfterRefresh) {
      config._retriedAfterRefresh = true
      const newAccessToken = await refreshAccessToken()
      if (newAccessToken) {
        config.headers.Authorization = `Bearer ${newAccessToken}`
        return api(config)
      }
      useAuthStore.getState().logout()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
