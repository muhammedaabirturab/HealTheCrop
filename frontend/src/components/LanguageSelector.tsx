import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { SUPPORTED_LANGUAGES, type LanguageCode } from '../i18n'
import { Languages } from 'lucide-react'

const CYCLE_MS = 3000

/**
 * Prominent, self-explaining language switcher for low-literacy users.
 * Cycles through each supported language name every ~3s (fading via
 * framer-motion) until the user taps one, at which point it settles on
 * their choice and stops animating — the animation's whole purpose is to
 * point at "this is where you change the language" without relying on
 * users already knowing English UI conventions like a dropdown affordance.
 */
export default function LanguageSelector({ variant = 'hero' }: { variant?: 'hero' | 'compact' }) {
  const { i18n } = useTranslation()
  const [cycleIndex, setCycleIndex] = useState(0)
  const [settled, setSettled] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (settled) return
    intervalRef.current = setInterval(() => {
      setCycleIndex((i) => (i + 1) % SUPPORTED_LANGUAGES.length)
    }, CYCLE_MS)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [settled])

  const selectLanguage = (code: LanguageCode) => {
    i18n.changeLanguage(code)
    setSettled(true)
    if (intervalRef.current) clearInterval(intervalRef.current)
  }

  const displayed = settled
    ? SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language) ?? SUPPORTED_LANGUAGES[0]
    : SUPPORTED_LANGUAGES[cycleIndex]

  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-2">
        <Languages size={18} className="text-forest" />
        <select
          value={i18n.language}
          onChange={(e) => selectLanguage(e.target.value as LanguageCode)}
          className="bg-transparent border border-forest/40 rounded-full px-3 py-1 text-sm font-medium text-forest-dark focus:outline-none"
        >
          {SUPPORTED_LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.label}
            </option>
          ))}
        </select>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-6">
      <button
        type="button"
        onClick={() => setSettled(false)}
        className="relative h-14 flex items-center justify-center min-w-[220px]"
        aria-label="Choose your language"
      >
        <AnimatePresence mode="wait">
          <motion.span
            key={displayed.code}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4 }}
            className="text-3xl md:text-4xl font-bold text-forest-dark"
          >
            {displayed.label}
          </motion.span>
        </AnimatePresence>
      </button>

      <div className="flex flex-wrap justify-center gap-3">
        {SUPPORTED_LANGUAGES.map((lang) => (
          <button
            key={lang.code}
            onClick={() => selectLanguage(lang.code)}
            className={`px-5 py-2.5 rounded-full text-base font-semibold border-2 transition-colors ${
              settled && i18n.language === lang.code
                ? 'bg-forest text-white border-forest'
                : 'bg-white text-forest-dark border-forest/30 hover:border-forest'
            }`}
          >
            {lang.label}
          </button>
        ))}
      </div>
    </div>
  )
}
