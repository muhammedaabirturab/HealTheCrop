import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { Check, Globe } from 'lucide-react'
import { SUPPORTED_LANGUAGES, type LanguageCode } from '../i18n'

const CYCLE_MS = 3000
const FADE_MS = 350

// Deliberately NOT the same key react-i18next's LanguageDetector caches to
// ('healthecrop_language', set in src/i18n/index.ts). That key gets written
// on every load — including a first-ever visit — as soon as the detector
// resolves a fallback/browser language, which is *not* the same thing as the
// user having explicitly picked one. Using it here made `settled` true from
// the very first render, so the animation never played for new visitors.
// This key is written only inside selectLanguage(), i.e. only on a real click.
const EXPLICIT_CHOICE_KEY = 'healthecrop_language_explicit'

/**
 * Self-advertising language switcher for the top navigation bar.
 *
 * While no language has been explicitly chosen yet, it cycles through every
 * supported language name so first-time, possibly low-literacy users notice
 * where to change the language without needing to already recognize a
 * dropdown affordance. The moment a language is picked — this visit or a
 * previous one — the animation stops for good and the chosen language stays
 * fixed, even across reloads.
 *
 * The cross-fade is a plain CSS opacity transition driven by a `fading`
 * flag, not framer-motion's AnimatePresence exit/unmount lifecycle — that
 * approach was tried first but exit animations never completed in testing
 * (elements piled up in the DOM instead of unmounting), which froze the
 * display on the first language forever. A timed opacity toggle has no
 * unmount step to get stuck on, so it can't fail the same way.
 */
export default function LanguageSelector() {
  const { i18n } = useTranslation()
  const [cycleIndex, setCycleIndex] = useState(0)
  const [fading, setFading] = useState(false)
  const [settled, setSettled] = useState(
    () => typeof window !== 'undefined' && Boolean(window.localStorage.getItem(EXPLICIT_CHOICE_KEY)),
  )
  const [open, setOpen] = useState(false)
  const timersRef = useRef<{ tick: ReturnType<typeof setInterval> | null; fade: ReturnType<typeof setTimeout> | null }>({
    tick: null,
    fade: null,
  })
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (settled) return
    timersRef.current.tick = setInterval(() => {
      setFading(true)
      timersRef.current.fade = setTimeout(() => {
        setCycleIndex((i) => (i + 1) % SUPPORTED_LANGUAGES.length)
        setFading(false)
      }, FADE_MS)
    }, CYCLE_MS)
    return () => {
      if (timersRef.current.tick) clearInterval(timersRef.current.tick)
      if (timersRef.current.fade) clearTimeout(timersRef.current.fade)
    }
  }, [settled])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectLanguage = (code: LanguageCode) => {
    i18n.changeLanguage(code)
    window.localStorage.setItem(EXPLICIT_CHOICE_KEY, code)
    setSettled(true)
    setOpen(false)
    if (timersRef.current.tick) clearInterval(timersRef.current.tick)
    if (timersRef.current.fade) clearTimeout(timersRef.current.fade)
  }

  const displayed = settled
    ? (SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language) ?? SUPPORTED_LANGUAGES[0])
    : SUPPORTED_LANGUAGES[cycleIndex]

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label="Choose your language"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-full border border-forest/25 bg-white/70 px-3.5 py-2 text-sm font-semibold text-forest-dark shadow-sm transition-colors hover:border-forest/50 hover:bg-white"
      >
        <Globe size={16} className="text-forest shrink-0" />
        <span
          className="inline-flex min-w-[4.5rem] items-center whitespace-nowrap transition-opacity ease-in-out"
          style={{ opacity: fading ? 0 : 1, transitionDuration: `${FADE_MS}ms` }}
        >
          {displayed.label}
        </span>
        <motion.svg
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          className="shrink-0 text-forest/70"
        >
          <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </motion.svg>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-50 mt-2 w-44 overflow-hidden rounded-2xl border border-forest/10 bg-white py-1.5 shadow-xl"
          >
            {SUPPORTED_LANGUAGES.map((lang) => {
              const active = settled && i18n.language === lang.code
              return (
                <button
                  key={lang.code}
                  onClick={() => selectLanguage(lang.code)}
                  className={`flex w-full items-center justify-between px-4 py-2 text-sm font-medium transition-colors ${
                    active ? 'bg-forest/10 text-forest-dark' : 'text-earth-dark hover:bg-cream'
                  }`}
                >
                  {lang.label}
                  {active && <Check size={14} className="text-forest" />}
                </button>
              )
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
