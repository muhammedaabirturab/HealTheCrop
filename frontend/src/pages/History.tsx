import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'

interface PredictionRecord {
  id: number
  recommended_crop: string
  confidence: number
  season_used: string
  created_at: string
}

interface PestRecord {
  id: number
  model_used: string
  detections: { display_name: string; confidence: number }[]
  created_at: string
}

export default function History() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<'predictions' | 'pest'>('predictions')
  const [predictions, setPredictions] = useState<PredictionRecord[]>([])
  const [pestScans, setPestScans] = useState<PestRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([api.get('/predictions/history'), api.get('/pest/history')])
      .then(([predictionsRes, pestRes]) => {
        setPredictions(predictionsRes.data)
        setPestScans(pestRes.data)
      })
      .catch((err) => setError(getErrorMessage(err, t)))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-forest-dark">{t('nav.history')}</h1>

      <div className="flex gap-3">
        <button
          onClick={() => setTab('predictions')}
          className={`px-4 py-2 rounded-full font-semibold ${tab === 'predictions' ? 'bg-forest text-white' : 'bg-white text-forest-dark border border-forest/30'}`}
        >
          {t('cropRecommendation.title')}
        </button>
        <button
          onClick={() => setTab('pest')}
          className={`px-4 py-2 rounded-full font-semibold ${tab === 'pest' ? 'bg-forest text-white' : 'bg-white text-forest-dark border border-forest/30'}`}
        >
          {t('pestDetection.title')}
        </button>
      </div>

      {error && (
        <div className="card p-4 flex items-center gap-2 text-sm font-semibold text-red-700 bg-red-50 border border-red-200">
          <AlertTriangle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      {loading && <div className="card p-6 text-center text-earth-dark">{t('common.loading')}</div>}

      {!loading && tab === 'predictions' && (
        <div className="flex flex-col gap-3">
          {predictions.length === 0 && <p className="text-earth-dark">--</p>}
          {predictions.map((p) => (
            <div key={p.id} className="card p-4 flex items-center justify-between">
              <div>
                <p className="font-bold text-forest-dark capitalize">{p.recommended_crop}</p>
                <p className="text-xs text-gray-500">{new Date(p.created_at).toLocaleString()} · {p.season_used}</p>
              </div>
              <span className="text-sm font-bold bg-forest/10 text-forest-dark px-2 py-1 rounded-full">
                {Math.round(p.confidence * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {!loading && tab === 'pest' && (
        <div className="flex flex-col gap-3">
          {pestScans.length === 0 && <p className="text-earth-dark">--</p>}
          {pestScans.map((p) => (
            <div key={p.id} className="card p-4">
              <p className="font-bold text-forest-dark">{p.detections[0]?.display_name ?? 'Unknown'}</p>
              <p className="text-xs text-gray-500">{new Date(p.created_at).toLocaleString()} · {p.model_used}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
