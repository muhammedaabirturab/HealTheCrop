import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MapPin, ChevronDown, Loader2 } from 'lucide-react'
import { ALL_INDIAN_REGIONS } from '../lib/indianStates'

type Mode = 'prompt' | 'detecting' | 'detected' | 'manual' | 'unsupported'

interface Props {
  value: string
  onChange: (value: string) => void
}

/**
 * Replaces a plain free-text "Location" field with something a low-literacy
 * user can operate without typing: ask for GPS permission once, reverse-geocode
 * to an Indian state via OpenStreetMap's public Nominatim API on allow, or fall
 * back to a searchable dropdown of all 28 states + 8 union territories on deny
 * (or if geolocation isn't available/fails for any reason).
 */
export default function LocationPicker({ value, onChange }: Props) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>(() =>
    typeof navigator !== 'undefined' && 'geolocation' in navigator ? 'prompt' : 'unsupported',
  )
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (mode === 'unsupported') setMode('manual')
  }, [mode])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return ALL_INDIAN_REGIONS
    return ALL_INDIAN_REGIONS.filter((region) => region.toLowerCase().includes(q))
  }, [search])

  const handleAllow = () => {
    setMode('detecting')
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=5&addressdetails=1`,
            { headers: { Accept: 'application/json' } },
          )
          const data = await res.json()
          const detected = data?.address?.state as string | undefined
          if (detected) {
            onChange(detected)
            setMode('detected')
          } else {
            setMode('manual')
          }
        } catch {
          setMode('manual')
        }
      },
      () => setMode('manual'),
      { timeout: 10000 },
    )
  }

  const handleDeny = () => setMode('manual')

  if (mode === 'prompt') {
    return (
      <div className="flex flex-col gap-2 border border-forest/30 rounded-lg p-3 bg-forest/5">
        <p className="text-sm font-semibold text-earth-dark">{t('location.permissionPrompt')}</p>
        <div className="flex gap-2">
          <button type="button" onClick={handleAllow} className="btn-primary !py-1.5 !px-4 !text-sm">
            {t('location.allow')}
          </button>
          <button type="button" onClick={handleDeny} className="btn-secondary !py-1.5 !px-4 !text-sm">
            {t('location.deny')}
          </button>
        </div>
      </div>
    )
  }

  if (mode === 'detecting') {
    return (
      <div className="flex items-center gap-2 border border-forest/30 rounded-lg px-3 py-3 text-sm text-earth-dark">
        <Loader2 size={16} className="animate-spin" /> {t('location.detecting')}
      </div>
    )
  }

  if (mode === 'detected') {
    return (
      <div className="flex items-center justify-between border border-forest/30 rounded-lg px-3 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-forest-dark">
          <MapPin size={16} className="text-forest" />
          {t('location.autoDetected')}: {value}
        </span>
        <button type="button" onClick={() => setMode('manual')} className="text-xs font-semibold text-forest underline">
          {t('location.change')}
        </button>
      </div>
    )
  }

  // manual: searchable dropdown
  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between border border-forest/30 rounded-lg px-3 py-3 text-sm text-left"
      >
        <span className={value ? 'text-forest-dark font-semibold' : 'text-gray-400'}>
          {value || t('location.selectState')}
        </span>
        <ChevronDown size={16} className={`text-forest transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-forest/20 rounded-lg shadow-xl overflow-hidden">
          <input
            autoFocus
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('location.searchPlaceholder')}
            className="w-full px-3 py-2 text-sm border-b border-forest/10 focus:outline-none"
          />
          <div className="max-h-56 overflow-y-auto">
            {filtered.length === 0 && (
              <p className="px-3 py-2 text-sm text-gray-400">{t('location.noResults')}</p>
            )}
            {filtered.map((region) => (
              <button
                key={region}
                type="button"
                onClick={() => {
                  onChange(region)
                  setSearch('')
                  setOpen(false)
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-forest/5 ${
                  region === value ? 'bg-forest/10 font-semibold text-forest-dark' : 'text-earth-dark'
                }`}
              >
                {region}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
