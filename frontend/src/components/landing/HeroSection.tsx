import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

export default function HeroSection() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)

  return (
    <section className="relative overflow-hidden">
      {/* Subtle decorative background blobs — pure CSS, no image assets required */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-24 -left-20 h-72 w-72 rounded-full bg-leaf/25 blur-3xl" />
        <div className="absolute top-10 right-0 h-96 w-96 rounded-full bg-forest/15 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-64 w-64 rounded-full bg-earth/10 blur-3xl" />
      </div>

      <div className="max-w-5xl mx-auto px-4 pt-16 pb-20 flex flex-col items-center text-center gap-6">
        <motion.span
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-forest bg-forest/10 px-4 py-1.5 rounded-full"
        >
          <Sparkles size={14} />
          {t('landing.hero.eyebrow')}
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-5xl md:text-7xl font-extrabold text-forest-dark tracking-tight"
        >
          {t('landing.hero.title')}
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
          className="text-xl md:text-2xl font-semibold text-earth-dark"
        >
          {t('landing.hero.subtitle')}
        </motion.p>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.26 }}
          className="max-w-2xl text-base md:text-lg text-earth-dark/90"
        >
          {t('landing.hero.description')}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.34 }}
          className="flex flex-col sm:flex-row gap-4 mt-2"
        >
          {user ? (
            <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2">
              {t('landing.hero.goToDashboard')} <ArrowRight size={18} />
            </Link>
          ) : (
            <>
              <Link to="/register" className="btn-primary inline-flex items-center gap-2">
                {t('landing.hero.ctaPrimary')} <ArrowRight size={18} />
              </Link>
              <Link to="/login" className="btn-secondary">
                {t('landing.hero.ctaSecondary')}
              </Link>
            </>
          )}
        </motion.div>
      </div>
    </section>
  )
}
