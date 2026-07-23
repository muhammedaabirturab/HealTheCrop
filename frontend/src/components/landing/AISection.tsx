import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import {
  Beaker, Droplets, Thermometer, Wind, TestTube2, CloudRain, CalendarRange, Brain, ArrowRight,
} from 'lucide-react'
import SectionHeading from './SectionHeading'

export default function AISection() {
  const { t } = useTranslation()

  const inputs = [
    { label: t('dashboard.nitrogen'), Icon: Beaker },
    { label: t('dashboard.phosphorus'), Icon: Beaker },
    { label: t('dashboard.potassium'), Icon: Beaker },
    { label: t('dashboard.soilMoisture'), Icon: Droplets },
    { label: t('dashboard.temperature'), Icon: Thermometer },
    { label: t('dashboard.humidity'), Icon: Wind },
    { label: t('dashboard.phLevel'), Icon: TestTube2 },
    { label: t('dashboard.rainfall'), Icon: CloudRain },
    { label: t('manualInput.season'), Icon: CalendarRange },
  ]

  return (
    <section className="max-w-6xl mx-auto px-4 py-16 flex flex-col gap-12">
      <SectionHeading
        eyebrow={t('landing.ai.eyebrow')}
        title={t('landing.ai.title')}
        subtitle={t('landing.ai.description')}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] items-center gap-6">
        {/* Inputs */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.5 }}
          className="card p-6 flex flex-col gap-4"
        >
          <span className="text-xs font-bold uppercase tracking-wide text-forest">{t('landing.ai.inputsLabel')}</span>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {inputs.map(({ label, Icon }) => (
              <div key={label} className="flex items-center gap-2 bg-forest/5 rounded-xl px-3 py-2 text-xs font-semibold text-forest-dark">
                <Icon size={14} className="text-forest shrink-0" />
                <span className="truncate">{label}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Model */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="flex flex-row lg:flex-col items-center justify-center gap-2 text-forest"
        >
          <ArrowRight size={22} className="rotate-90 lg:rotate-0 text-forest/40" />
          <div className="bg-forest text-white w-20 h-20 rounded-full flex items-center justify-center shadow-lg shrink-0">
            <Brain size={34} />
          </div>
          <span className="text-xs font-bold text-center max-w-[7rem]">Random Forest</span>
          <ArrowRight size={22} className="rotate-90 lg:rotate-0 text-forest/40" />
        </motion.div>

        {/* Output */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="card p-6 flex flex-col gap-4"
        >
          <span className="text-xs font-bold uppercase tracking-wide text-forest">{t('landing.ai.outputLabel')}</span>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between bg-forest text-white rounded-xl px-4 py-3">
              <span className="text-sm font-semibold">{t('landing.ai.outputCrop')}</span>
              <span className="text-xs font-bold bg-white/20 px-2 py-0.5 rounded-full">Rice</span>
            </div>
            <div className="flex items-center justify-between bg-leaf/15 rounded-xl px-4 py-3">
              <span className="text-sm font-semibold text-forest-dark">{t('landing.ai.outputConfidence')}</span>
              <span className="text-xs font-bold text-forest-dark">96%</span>
            </div>
            <div className="flex items-center justify-between bg-cream rounded-xl px-4 py-3 border border-forest/10">
              <span className="text-sm font-semibold text-forest-dark">{t('landing.ai.outputAlternatives')}</span>
              <span className="text-xs font-bold text-earth-dark">Jute, Maize...</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
