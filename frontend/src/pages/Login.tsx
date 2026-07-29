import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { isAxiosError } from 'axios'
import { api } from '../lib/api'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { email, password, remember_me: rememberMe })
      setSession(data.access_token, data.user, data.refresh_token)
      navigate(data.user.role === 'admin' ? '/admin' : '/dashboard')
    } catch (err) {
      if (isAxiosError(err) && !err.response) {
        setError(t('errors.network'))
      } else {
        setError(t('auth.invalidCredentials'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-10">
      <form onSubmit={handleSubmit} autoComplete="off" className="card w-full max-w-md p-8 flex flex-col gap-4">
        <h1 className="text-2xl font-bold text-forest-dark text-center">{t('auth.welcomeBack')}</h1>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.email')}
          <input
            type="email"
            required
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-forest/30 rounded-lg px-4 py-3 text-base focus:outline-none focus:border-forest"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.password')}
          <input
            type="password"
            required
            autoComplete="off"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border border-forest/30 rounded-lg px-4 py-3 text-base focus:outline-none focus:border-forest"
          />
        </label>

        <label className="flex items-center gap-2 text-sm font-semibold text-earth-dark select-none">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="h-4 w-4 rounded border-forest/30 text-forest focus:ring-forest"
          />
          {t('auth.rememberMe')}
        </label>

        {error && <p className="text-red-600 text-sm font-semibold">{error}</p>}

        <button type="submit" disabled={loading} className="btn-primary mt-2 disabled:opacity-60">
          {loading ? t('common.loading') : t('auth.loginButton')}
        </button>

        <p className="text-center text-sm text-earth-dark">
          {t('auth.createAccount')}{' '}
          <Link to="/register" className="text-forest font-semibold underline">
            {t('nav.register')}
          </Link>
        </p>
      </form>
    </div>
  )
}
