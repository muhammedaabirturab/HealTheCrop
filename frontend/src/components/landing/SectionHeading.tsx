import { motion } from 'framer-motion'

export default function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = 'center',
}: {
  eyebrow: string
  title: string
  subtitle?: string
  align?: 'center' | 'left'
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.5 }}
      className={`flex flex-col gap-3 ${align === 'center' ? 'items-center text-center' : 'items-start text-left'} max-w-2xl ${align === 'center' ? 'mx-auto' : ''}`}
    >
      <span className="text-xs font-bold uppercase tracking-[0.14em] text-forest bg-forest/10 px-3 py-1 rounded-full">
        {eyebrow}
      </span>
      <h2 className="text-2xl md:text-3xl font-extrabold text-forest-dark">{title}</h2>
      {subtitle && <p className="text-earth-dark text-base">{subtitle}</p>}
    </motion.div>
  )
}
