import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'
import CropCard, { type CropCardData } from '../components/CropCard'

interface FormState {
  nitrogen: string
  phosphorus: string
  potassium: string
  temperature: string
  humidity: string
  ph: string
  rainfall: string
  season: string
  location: string
}

const DEFAULT_FORM: FormState = {
  nitrogen: '80', phosphorus: '45', potassium: '40', temperature: '26',
  humidity: '70', ph: '6.5', rainfall: '150', season: '', location: '',
}

interface PredictionResult {
  recommended_crop: string
  confidence: number
  alternatives: { crop: string; confidence: number; crop_details: Record<string, unknown> }[]
  crop_details: Record<string, unknown>
  feature_importance: Record<string, number>
  season_used: string
}

export default function ManualInput() {
  const { t } = useTranslation()
  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const update = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const numericFields = {
      nitrogen: Number(form.nitrogen),
      phosphorus: Number(form.phosphorus),
      potassium: Number(form.potassium),
      temperature: Number(form.temperature),
      humidity: Number(form.humidity),
      ph: Number(form.ph),
      rainfall: Number(form.rainfall),
    }
    if (Object.values(numericFields).some((v) => Number.isNaN(v))) {
      setError(t('errors.validation'))
      return
    }

    setLoading(true)
    setResult(null)
    try {
      const { data } = await api.post('/predictions/manual', {
        ...numericFields,
        season: form.season || undefined,
        location: form.location || undefined,
      })
      setResult(data)
    } catch (err) {
      setError(getErrorMessage(err, t))
    } finally {
      setLoading(false)
    }
  }

  const fields: { key: keyof FormState; label: string; step?: string }[] = [
    { key: 'nitrogen', label: t('dashboard.nitrogen') },
    { key: 'phosphorus', label: t('dashboard.phosphorus') },
    { key: 'potassium', label: t('dashboard.potassium') },
    { key: 'temperature', label: t('dashboard.temperature') },
    { key: 'humidity', label: t('dashboard.humidity') },
    { key: 'ph', label: t('dashboard.phLevel'), step: '0.1' },
    { key: 'rainfall', label: `${t('dashboard.rainfall')} (mm)` },
  ]

  const buildCard = (crop: string, confidence: number, details: Record<string, unknown>, highlight: boolean): CropCardData => {
    return {
      crop,
      confidence,
      highlight,
      display_name: (details.display_name as string) || crop,
      image: (details.image as string) || 'placeholder.jpg',
      season: (details.season as string[]) || [result?.season_used ?? ''],
      water_requirement: (details.water_requirement as string) || 'Medium',
      harvest_duration_days: (details.harvest_duration_days as number) || 100,
      soil_suitability: (details.soil_suitability as string[]) || ['Loamy'],
      expected_yield: (details.expected_yield as string) || 'N/A',
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-forest-dark">{t('manualInput.title')}</h1>
        <p className="text-earth-dark">{t('manualInput.subtitle')}</p>
      </div>

      <form onSubmit={handleSubmit} className="card p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        {fields.map((f) => (
          <label key={f.key} className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
            {f.label}
            <input
              type="number"
              step={f.step || '1'}
              required
              value={form[f.key]}
              onChange={update(f.key)}
              className="border border-forest/30 rounded-lg px-3 py-2 focus:outline-none focus:border-forest"
            />
          </label>
        ))}

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('manualInput.season')}
          <select value={form.season} onChange={update('season')} className="border border-forest/30 rounded-lg px-3 py-2 focus:outline-none focus:border-forest">
            <option value="">Auto-detect</option>
            <option value="Kharif">Kharif</option>
            <option value="Rabi">Rabi</option>
            <option value="Zaid">Zaid</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.location')}
          <input value={form.location} onChange={update('location')} placeholder="Karnataka" className="border border-forest/30 rounded-lg px-3 py-2 focus:outline-none focus:border-forest" />
        </label>

        <div className="col-span-full flex justify-end">
          <button type="submit" disabled={loading} className="btn-primary disabled:opacity-60">
            {loading ? t('common.loading') : t('manualInput.getRecommendation')}
          </button>
        </div>
      </form>

      {error && <p className="text-red-600 font-semibold">{error}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          <h2 className="text-xl font-bold text-forest-dark">{t('cropRecommendation.title')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <CropCard data={buildCard(result.recommended_crop, result.confidence, result.crop_details, true)} />
            {result.alternatives
              .filter((a) => a.crop !== result.recommended_crop)
              .map((alt) => (
                <CropCard key={alt.crop} data={buildCard(alt.crop, alt.confidence, alt.crop_details, false)} />
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
