import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { UploadCloud, Bug, Leaf } from 'lucide-react'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'

interface Detection {
  name: string
  display_name: string
  type: string
  confidence: number
  description: string
  organic_treatment: string
  chemical_treatment: string
  recommended_pesticides: string[]
  prevention_tips: string[]
  expected_recovery_days: number
}

interface ScanResult {
  model_used: string
  severity: string
  detections: Detection[]
}

export default function PestScan() {
  const { t } = useTranslation()
  const [preview, setPreview] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const previewUrlRef = useRef<string | null>(null)

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    }
  }, [])

  const handleFile = (f: File) => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    const url = URL.createObjectURL(f)
    previewUrlRef.current = url
    setFile(f)
    setPreview(url)
    setResult(null)
    setError('')
  }

  const handleSubmit = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post('/pest/scan', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(data)
    } catch (err) {
      setError(getErrorMessage(err, t))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-forest-dark">{t('pestDetection.title')}</h1>
        <p className="text-earth-dark">{t('pestDetection.subtitle')}</p>
      </div>

      <label className="card p-8 flex flex-col items-center gap-3 border-2 border-dashed border-forest/40 cursor-pointer hover:border-forest">
        <UploadCloud size={40} className="text-forest" />
        <span className="font-semibold text-forest-dark">{t('common.uploadImage')}</span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </label>

      {preview && (
        <div className="flex flex-col items-center gap-4">
          <img src={preview} alt="preview" className="max-h-72 rounded-2xl shadow" />
          <button onClick={handleSubmit} disabled={loading} className="btn-primary disabled:opacity-60">
            {loading ? t('pestDetection.analyzing') : t('common.submit')}
          </button>
        </div>
      )}

      {error && <p className="text-red-600 font-semibold text-center">{error}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          <p className="text-sm font-semibold text-earth-dark text-center">
            Model: {result.model_used} · Severity: {result.severity}
          </p>
          {result.detections.map((d, i) => (
            <div key={i} className="card p-5 flex flex-col gap-3">
              <div className="flex items-center gap-3">
                {d.type === 'healthy' ? <Leaf className="text-forest" /> : <Bug className="text-orange-600" />}
                <h3 className="text-lg font-bold text-forest-dark">{d.display_name}</h3>
                <span className="ml-auto text-sm font-bold bg-forest/10 text-forest-dark px-2 py-1 rounded-full">
                  {Math.round(d.confidence * 100)}%
                </span>
              </div>
              <p className="text-sm text-earth-dark">{d.description}</p>
              {d.type !== 'healthy' && (
                <div className="grid sm:grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.organicTreatment')}</p>
                    <p className="text-earth-dark">{d.organic_treatment}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.chemicalTreatment')}</p>
                    <p className="text-earth-dark">{d.chemical_treatment}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.recommendedPesticides')}</p>
                    <p className="text-earth-dark">{d.recommended_pesticides.join(', ')}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.preventionTips')}</p>
                    <ul className="list-disc list-inside text-earth-dark">
                      {d.prevention_tips.map((tip) => <li key={tip}>{tip}</li>)}
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.recoveryTime')}</p>
                    <p className="text-earth-dark">{d.expected_recovery_days} {t('cropRecommendation.days')}</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
