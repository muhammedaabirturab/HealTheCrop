import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { TrendingUp, Sprout, ShieldCheck, BarChart3, Languages, ScanEye, Wallet } from 'lucide-react'

const ICONS = [TrendingUp, Sprout, ShieldCheck, BarChart3, Languages, ScanEye, Wallet]

export default function WhyUseSection() {
  const { t } = useTranslation()

  const benefits = [1, 2, 3, 4, 5, 6, 7].map((n) => ({
    text: t(`landing.whyUse.benefit${n}`),
    Icon: ICONS[n - 1],
  }))

  return (
    <section className="bg-forest text-white py-16">
      <div className="max-w-6xl mx-auto px-4 flex flex-col gap-12">
        <div className="flex flex-col items-center text-center gap-3 max-w-2xl mx-auto">
          <span className="text-xs font-bold uppercase tracking-[0.14em] text-leaf bg-white/10 px-3 py-1 rounded-full">
            {t('landing.whyUse.eyebrow')}
          </span>
          <h2 className="text-2xl md:text-3xl font-extrabold">{t('landing.whyUse.title')}</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {benefits.map(({ text, Icon }, i) => (
            <motion.div
              key={text}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.4, delay: (i % 4) * 0.06 }}
              className="bg-white/10 rounded-2xl p-5 flex items-center gap-3 hover:bg-white/15 transition-colors duration-200"
            >
              <div className="bg-white/15 w-10 h-10 rounded-xl flex items-center justify-center shrink-0">
                <Icon size={18} />
              </div>
              <span className="font-semibold text-sm">{text}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
