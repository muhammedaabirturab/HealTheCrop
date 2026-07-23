import { useTranslation } from 'react-i18next'
import { Leaf, GitFork, Mail } from 'lucide-react'

const TECHNOLOGIES = [
  'React', 'TypeScript', 'Vite', 'Tailwind CSS', 'FastAPI',
  'scikit-learn', 'OpenCV', 'PostgreSQL', 'MinIO', 'ESP32',
]

export default function Footer() {
  const { t } = useTranslation()
  const year = new Date().getFullYear()

  return (
    <footer className="bg-forest-dark text-white/90 mt-auto">
      <div className="max-w-6xl mx-auto px-4 py-12 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-white font-extrabold text-lg">
            <Leaf className="text-leaf" />
            {t('app.name')}
          </div>
          <p className="text-sm text-white/70">{t('landing.footer.projectText')}</p>
        </div>

        <div className="flex flex-col gap-3">
          <h4 className="text-sm font-bold uppercase tracking-wide text-leaf">{t('landing.footer.technologies')}</h4>
          <div className="flex flex-wrap gap-2">
            {TECHNOLOGIES.map((tech) => (
              <span key={tech} className="text-xs bg-white/10 rounded-full px-3 py-1">{tech}</span>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <h4 className="text-sm font-bold uppercase tracking-wide text-leaf">{t('landing.footer.team')}</h4>
          <p className="text-sm text-white/70">{t('landing.footer.project')}: HealTheCrop</p>
          <p className="text-sm text-white/70">Final-year engineering project</p>
        </div>

        <div className="flex flex-col gap-3">
          <h4 className="text-sm font-bold uppercase tracking-wide text-leaf">{t('landing.footer.links')}</h4>
          <a
            href="https://github.com/muhammedaabirturab/HealTheCrop"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 text-sm text-white/70 hover:text-white transition-colors"
          >
            <GitFork size={16} /> {t('landing.footer.github')}
          </a>
          <a
            href="mailto:contact@healthecrop.dev"
            className="flex items-center gap-2 text-sm text-white/70 hover:text-white transition-colors"
          >
            <Mail size={16} /> {t('landing.footer.contact')}
          </a>
        </div>
      </div>

      <div className="border-t border-white/10 py-5 text-center text-xs text-white/50">
        © {year} {t('app.name')}. {t('landing.footer.copyright')}
      </div>
    </footer>
  )
}
