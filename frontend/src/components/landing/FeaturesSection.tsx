import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import {
  Droplets, Sparkles, Gauge, FlaskConical, Bug,
  LineChart, Languages, SlidersHorizontal, CloudCog, LayoutDashboard,
} from 'lucide-react'
import SectionHeading from './SectionHeading'

const FEATURES = [
  { key: 'soilMonitoring', Icon: Droplets },
  { key: 'aiRecommendation', Icon: Sparkles },
  { key: 'fertilityAnalysis', Icon: Gauge },
  { key: 'fertilityImprovement', Icon: FlaskConical },
  { key: 'pestDetection', Icon: Bug },
  { key: 'analytics', Icon: LineChart },
  { key: 'multilingual', Icon: Languages },
  { key: 'manualMode', Icon: SlidersHorizontal },
  { key: 'storage', Icon: CloudCog },
  { key: 'smartDashboard', Icon: LayoutDashboard },
]

export default function FeaturesSection() {
  const { t } = useTranslation()

  return (
    <section className="max-w-6xl mx-auto px-4 py-16 flex flex-col gap-12">
      <SectionHeading eyebrow={t('landing.features.eyebrow')} title={t('landing.features.title')} />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {FEATURES.map(({ key, Icon }, i) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.4, delay: (i % 4) * 0.06 }}
            className="card p-5 flex flex-col gap-3 hover:shadow-lg hover:-translate-y-1 transition-all duration-200"
          >
            <div className="bg-leaf/15 text-forest-dark w-11 h-11 rounded-xl flex items-center justify-center">
              <Icon size={20} />
            </div>
            <h3 className="font-bold text-forest-dark text-sm">{t(`landing.features.${key}Title`)}</h3>
            <p className="text-xs text-earth-dark leading-relaxed">{t(`landing.features.${key}Text`)}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
