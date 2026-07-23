import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Sprout, ScanEye, LineChart, Sparkles } from 'lucide-react'
import LanguageSelector from '../components/LanguageSelector'

export default function Landing() {
  const { t } = useTranslation()

  const features = [
    { icon: LineChart, title: t('dashboard.title'), desc: t('dashboard.liveSensorValues') },
    { icon: Sprout, title: t('cropRecommendation.title'), desc: t('manualInput.subtitle') },
    { icon: ScanEye, title: t('pestDetection.title'), desc: t('pestDetection.subtitle') },
  ]

  return (
    <div className="flex-1 flex flex-col items-center px-4">
      <section className="max-w-3xl w-full text-center pt-12 pb-10 flex flex-col items-center gap-8">
        <LanguageSelector variant="hero" />

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <h1 className="text-4xl md:text-6xl font-extrabold text-forest-dark flex items-center justify-center gap-3">
            <Sparkles className="text-leaf" size={40} />
            {t('app.name')}
          </h1>
          <p className="text-lg md:text-xl text-earth-dark mt-3">{t('app.tagline')}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="flex flex-col sm:flex-row gap-4"
        >
          <Link to="/register" className="btn-primary">{t('auth.createAccount')}</Link>
          <Link to="/login" className="btn-secondary">{t('auth.loginButton')}</Link>
        </motion.div>
      </section>

      <section className="max-w-5xl w-full grid grid-cols-1 md:grid-cols-3 gap-6 pb-16">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * i }}
            className="card p-6 flex flex-col items-center text-center gap-3"
          >
            <div className="bg-forest/10 text-forest p-4 rounded-full">
              <f.icon size={32} />
            </div>
            <h2 className="text-lg font-bold text-forest-dark">{f.title}</h2>
            <p className="text-sm text-earth-dark">{f.desc}</p>
          </motion.div>
        ))}
      </section>
    </div>
  )
}
