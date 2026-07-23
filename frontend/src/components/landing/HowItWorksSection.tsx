import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Radio, Cpu, Database, Server, Brain, Sprout, LayoutDashboard, ArrowRight, ArrowDown } from 'lucide-react'
import SectionHeading from './SectionHeading'

const ICONS = [Radio, Cpu, Database, Server, Brain, Sprout, LayoutDashboard]

export default function HowItWorksSection() {
  const { t } = useTranslation()

  const steps = [1, 2, 3, 4, 5, 6, 7].map((n) => ({
    title: t(`landing.howItWorks.step${n}Title`),
    text: t(`landing.howItWorks.step${n}Text`),
    Icon: ICONS[n - 1],
  }))

  return (
    <section className="bg-forest/5 py-16">
      <div className="max-w-6xl mx-auto px-4 flex flex-col gap-12">
        <SectionHeading
          eyebrow={t('landing.howItWorks.eyebrow')}
          title={t('landing.howItWorks.title')}
          subtitle={t('landing.howItWorks.subtitle')}
        />

        <div className="flex flex-col lg:flex-row items-stretch gap-3">
          {steps.map(({ title, text, Icon }, i) => (
            <div key={title} className="flex flex-1 flex-col lg:flex-row items-center gap-3">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className="card flex-1 p-5 flex flex-col items-center text-center gap-2.5 hover:shadow-lg transition-shadow duration-200"
              >
                <div className="bg-forest text-white w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm">
                  {i + 1}
                </div>
                <Icon size={26} className="text-forest" />
                <h3 className="font-bold text-forest-dark text-sm">{title}</h3>
                <p className="text-xs text-earth-dark leading-snug">{text}</p>
              </motion.div>

              {i < steps.length - 1 && (
                <>
                  <ArrowRight size={20} className="hidden lg:block text-forest/40 shrink-0" />
                  <ArrowDown size={20} className="lg:hidden text-forest/40 shrink-0 mx-auto" />
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
