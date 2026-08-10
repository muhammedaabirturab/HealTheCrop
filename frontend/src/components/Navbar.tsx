import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Leaf, LogOut } from 'lucide-react'
import LanguageSelector from './LanguageSelector'
import { useAuthStore } from '../store/authStore'

export default function Navbar() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  return (
    <header className="sticky top-0 z-40 bg-cream/95 backdrop-blur border-b border-forest/10">
      <nav className="max-w-6xl mx-auto flex items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-forest-dark font-extrabold text-xl">
          <Leaf className="text-forest" />
          {t('app.name')}
        </Link>

        {user && (
          <div className="hidden md:flex items-center gap-6 text-sm font-semibold text-forest-dark">
            {isAdmin ? (
              <Link to="/admin" className="hover:text-forest">{t('admin.title')}</Link>
            ) : (
              <>
                <Link to="/dashboard" className="hover:text-forest">{t('nav.dashboard')}</Link>
                <Link to="/manual-input" className="hover:text-forest">{t('nav.manualInput')}</Link>
                <Link to="/live-sensor" className="hover:text-forest">{t('nav.liveSensor')}</Link>
                <Link to="/pest-scan" className="hover:text-forest">{t('nav.scanCrop')}</Link>
              </>
            )}
          </div>
        )}

        <div className="flex items-center gap-4">
          <LanguageSelector />
          {user ? (
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="flex items-center gap-1 text-sm font-semibold text-earth-dark hover:text-red-700"
            >
              <LogOut size={16} /> {t('nav.logout')}
            </button>
          ) : (
            <Link to="/login" className="btn-primary !py-2 !px-5 !text-sm">
              {t('nav.login')}
            </Link>
          )}
        </div>
      </nav>
    </header>
  )
}
