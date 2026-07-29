import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AuthUser {
  id: number
  name: string
  email: string
  role: 'farmer' | 'admin'
  location: string | null
  preferred_language: string
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
  setSession: (accessToken: string, user: AuthUser, refreshToken?: string | null) => void
  setAccessToken: (accessToken: string, refreshToken?: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setSession: (accessToken, user, refreshToken = null) => set({ accessToken, user, refreshToken }),
      setAccessToken: (accessToken, refreshToken) =>
        set((state) => ({ accessToken, refreshToken: refreshToken !== undefined ? refreshToken : state.refreshToken })),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: 'healthecrop_auth' },
  ),
)
