import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Sprout, TrendingUp, Target, Leaf, Users, History } from 'lucide-react'
import SectionHeading from './SectionHeading'

const ICONS = [Sprout, TrendingUp, Target, Leaf, Users, History]

export default function AboutSection() {
  const { t } = useTranslation()

  const points = [1, 2, 3, 4, 5, 6].map((n) => ({
    title: t(`landing.about.point${n}Title`),
    text: t(`landing.about.point${n}Text`),
    Icon: ICONS[n - 1],
  }))

  return (
    <section className="max-w-6xl mx-auto px-4 py-16 flex flex-col gap-12">
      <SectionHeading
        eyebrow={t('landing.about.eyebrow')}
        title={t('landing.about.title')}
        subtitle={t('landing.about.subtitle')}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {points.map(({ title, text, Icon }, i) => (
          <motion.div
            key={title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.4, delay: i * 0.06 }}
            className="card p-6 flex flex-col gap-3 hover:shadow-lg hover:-translate-y-1 transition-all duration-200"
          >
            <div className="bg-forest/10 text-forest w-12 h-12 rounded-2xl flex items-center justify-center">
              <Icon size={22} />
            </div>
            <h3 className="font-bold text-forest-dark">{title}</h3>
            <p className="text-sm text-earth-dark">{text}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
