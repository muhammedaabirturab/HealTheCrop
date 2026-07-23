import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'
import { useAuthStore } from '../store/authStore'

export default function Register() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)

  const [form, setForm] = useState({ name: '', email: '', password: '', location: '', phone: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/register', { ...form, preferred_language: i18n.language })
      const { data } = await api.post('/auth/login', { email: form.email, password: form.password })
      const me = await api.get('/auth/me', { headers: { Authorization: `Bearer ${data.access_token}` } })
      setSession(data.access_token, me.data)
      navigate('/dashboard')
    } catch (err) {
      setError(getErrorMessage(err, t))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-10">
      <form onSubmit={handleSubmit} className="card w-full max-w-md p-8 flex flex-col gap-4">
        <h1 className="text-2xl font-bold text-forest-dark text-center">{t('auth.createAccount')}</h1>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.name')}
          <input required value={form.name} onChange={update('name')} className="border border-forest/30 rounded-lg px-4 py-3 focus:outline-none focus:border-forest" />
        </label>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.email')}
          <input type="email" required value={form.email} onChange={update('email')} className="border border-forest/30 rounded-lg px-4 py-3 focus:outline-none focus:border-forest" />
        </label>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.password')}
          <input type="password" required minLength={6} value={form.password} onChange={update('password')} className="border border-forest/30 rounded-lg px-4 py-3 focus:outline-none focus:border-forest" />
        </label>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.location')}
          <input value={form.location} onChange={update('location')} placeholder="Karnataka" className="border border-forest/30 rounded-lg px-4 py-3 focus:outline-none focus:border-forest" />
        </label>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.phone')}
          <input value={form.phone} onChange={update('phone')} className="border border-forest/30 rounded-lg px-4 py-3 focus:outline-none focus:border-forest" />
        </label>

        {error && <p className="text-red-600 text-sm font-semibold">{error}</p>}

        <button type="submit" disabled={loading} className="btn-primary mt-2 disabled:opacity-60">
          {loading ? t('common.loading') : t('auth.registerButton')}
        </button>

        <p className="text-center text-sm text-earth-dark">
          <Link to="/login" className="text-forest font-semibold underline">
            {t('auth.welcomeBack')}
          </Link>
        </p>
      </form>
    </div>
  )
}
