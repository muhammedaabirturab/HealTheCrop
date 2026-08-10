import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { UploadCloud, Bug, Leaf, AlertTriangle, ShieldAlert, Sprout, BookOpen } from 'lucide-react'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'

interface SourceCitation {
  title: string
  publisher: string
  url: string | null
}

interface Detection {
  name: string
  display_name: string
  type: string
  category: string
  scientific_name: string | null
  applicable_crops: string[]
  confidence: number
  description: string
  severity_level: string
  organic_treatment: string
  biological_control: string | null
  chemical_treatment: string
  recommended_pesticides: string[]
  recommended_insecticide: string | null
  recommended_fungicide: string | null
  dosage_guidance: string
  safety_precautions: string | null
  waiting_period_before_harvest: string | null
  prevention_tips: string[]
  recovery_recommendations: string
  expected_recovery_days: number
  sources: SourceCitation[]
  content_language: string
}

interface ImageQuality {
  is_acceptable: boolean
  issues: string[]
  messages: string[]
}

interface ScanResult {
  model_used: string
  severity: string
  detections: Detection[]
  image_quality: ImageQuality
  is_uncertain: boolean
  uncertainty_note: string | null
}

const ISSUE_KEY: Record<string, string> = {
  blurry: 'pestDetection.issueBlurry',
  too_dark: 'pestDetection.issueTooDark',
  overexposed: 'pestDetection.issueOverexposed',
  low_resolution: 'pestDetection.issueLowResolution',
  no_plant_detected: 'pestDetection.issueNoPlantDetected',
}

const SEVERITY_BADGE: Record<string, string> = {
  Low: 'bg-forest/10 text-forest-dark',
  Moderate: 'bg-yellow-100 text-yellow-800',
  High: 'bg-orange-100 text-orange-800',
  Critical: 'bg-red-100 text-red-700',
  None: 'bg-forest/10 text-forest-dark',
}

const SEVERITY_LEVEL_KEY: Record<string, string> = {
  Low: 'pestDetection.severityLow',
  Moderate: 'pestDetection.severityModerate',
  High: 'pestDetection.severityHigh',
  Critical: 'pestDetection.severityCritical',
  None: 'pestDetection.severityNone',
}

const OVERALL_SEVERITY_KEY: Record<string, string> = {
  healthy: 'pestDetection.overallHealthy',
  mild: 'pestDetection.overallMild',
  moderate: 'pestDetection.overallModerateLevel',
  severe: 'pestDetection.overallSevere',
  unknown: 'pestDetection.overallUnknown',
}

const MODEL_USED_KEY: Record<string, string> = {
  heuristic: 'pestDetection.modelHeuristic',
  cnn: 'pestDetection.modelCnn',
}

export default function PestScan() {
  const { t, i18n } = useTranslation()
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
        params: { lang: i18n.language },
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

      {result && !result.image_quality.is_acceptable && (
        <div className="card p-6 flex flex-col items-center gap-3 border-2 border-red-200 bg-red-50 text-center">
          <ShieldAlert className="text-red-600" size={32} />
          <h3 className="text-lg font-bold text-red-700">{t('pestDetection.imageQualityTitle')}</h3>
          <ul className="text-sm text-red-700 flex flex-col gap-1">
            {result.image_quality.issues.map((issue) => (
              <li key={issue}>{t(ISSUE_KEY[issue] || issue)}</li>
            ))}
          </ul>
          <label className="btn-primary cursor-pointer">
            {t('pestDetection.retakePhoto')}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
          </label>
        </div>
      )}

      {result && result.image_quality.is_acceptable && (
        <div className="flex flex-col gap-4">
          <p className="text-sm font-semibold text-earth-dark text-center">
            {t('pestDetection.modelUsed')}: {t(MODEL_USED_KEY[result.model_used] || result.model_used)} · {t('pestDetection.overallSeverity')}: {t(OVERALL_SEVERITY_KEY[result.severity] || result.severity)}
          </p>
          {result.is_uncertain && (
            <div className="card p-4 flex items-start gap-3 border-2 border-yellow-200 bg-yellow-50">
              <ShieldAlert className="text-yellow-700 shrink-0" size={20} />
              <p className="text-sm text-yellow-800 font-medium">{t('pestDetection.uncertainDiagnosis')}</p>
            </div>
          )}
          {result.detections.map((d, i) => (
            <div key={i} className="card p-5 flex flex-col gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                {d.type === 'healthy' ? <Leaf className="text-forest" /> : <Bug className="text-orange-600" />}
                <h3 className="text-lg font-bold text-forest-dark">{d.display_name}</h3>
                <span
                  className="text-sm font-bold bg-forest/10 text-forest-dark px-2 py-1 rounded-full"
                  title={t('pestDetection.detectionConfidence')}
                >
                  {t('pestDetection.detectionConfidence')}: {Math.round(d.confidence * 100)}%
                </span>
                {d.type !== 'healthy' && (
                  <span className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-full ${SEVERITY_BADGE[d.severity_level] || SEVERITY_BADGE.Moderate}`}>
                    <AlertTriangle size={12} /> {t('pestDetection.severityLevel')}: {t(SEVERITY_LEVEL_KEY[d.severity_level] || d.severity_level)}
                  </span>
                )}
              </div>
              {d.scientific_name && (
                <p className="text-xs italic text-earth-dark/70 -mt-2">
                  {t('pestDetection.scientificName')}: {d.scientific_name}
                </p>
              )}
              {d.content_language !== i18n.language && (
                <p className="text-xs font-semibold text-orange-700 bg-orange-50 border border-orange-100 rounded-md px-2 py-1 -mt-1 w-fit">
                  {t('pestDetection.contentUnavailableInLanguage')}
                </p>
              )}
              <p className="text-sm text-earth-dark">{d.description}</p>
              {d.type !== 'healthy' && (
                <div className="grid sm:grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.organicTreatment')}</p>
                    <p className="text-earth-dark">{d.organic_treatment}</p>
                  </div>
                  {d.biological_control && (
                    <div>
                      <p className="font-semibold text-forest-dark">{t('pestDetection.biologicalControl')}</p>
                      <p className="text-earth-dark">{d.biological_control}</p>
                    </div>
                  )}
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.chemicalTreatment')}</p>
                    <p className="text-earth-dark">{d.chemical_treatment}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.recommendedPesticides')}</p>
                    <p className="text-earth-dark">{d.recommended_pesticides.join(', ') || '—'}</p>
                  </div>
                  {d.recommended_insecticide && (
                    <div>
                      <p className="font-semibold text-forest-dark">{t('pestDetection.recommendedInsecticide')}</p>
                      <p className="text-earth-dark">{d.recommended_insecticide}</p>
                    </div>
                  )}
                  {d.recommended_fungicide && (
                    <div>
                      <p className="font-semibold text-forest-dark">{t('pestDetection.recommendedFungicide')}</p>
                      <p className="text-earth-dark">{d.recommended_fungicide}</p>
                    </div>
                  )}
                  <div className="sm:col-span-2">
                    <p className="font-semibold text-forest-dark">{t('pestDetection.dosageGuidance')}</p>
                    <p className="text-earth-dark">{d.dosage_guidance}</p>
                  </div>
                  {d.safety_precautions && (
                    <div className="sm:col-span-2 flex gap-2 bg-red-50 border border-red-100 rounded-lg p-3">
                      <ShieldAlert className="text-red-500 shrink-0" size={16} />
                      <div>
                        <p className="font-semibold text-red-700">{t('pestDetection.safetyPrecautions')}</p>
                        <p className="text-red-700/90">{d.safety_precautions}</p>
                      </div>
                    </div>
                  )}
                  {d.waiting_period_before_harvest && (
                    <div>
                      <p className="font-semibold text-forest-dark flex items-center gap-1">
                        <Sprout size={14} /> {t('pestDetection.waitingPeriod')}
                      </p>
                      <p className="text-earth-dark">{d.waiting_period_before_harvest}</p>
                    </div>
                  )}
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.preventionTips')}</p>
                    <ul className="list-disc list-inside text-earth-dark">
                      {d.prevention_tips.map((tip) => <li key={tip}>{tip}</li>)}
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold text-forest-dark">{t('pestDetection.recoveryTime')}</p>
                    <p className="text-earth-dark">{d.expected_recovery_days} {t('cropRecommendation.days')}</p>
                    {d.recovery_recommendations && (
                      <p className="text-earth-dark mt-1">{d.recovery_recommendations}</p>
                    )}
                  </div>
                  {d.sources.length > 0 && (
                    <div className="sm:col-span-2 pt-2 border-t border-forest/10">
                      <p className="font-semibold text-forest-dark flex items-center gap-1">
                        <BookOpen size={14} /> {t('pestDetection.sources')}
                      </p>
                      <ul className="text-xs text-earth-dark/80 flex flex-col gap-0.5 mt-1">
                        {d.sources.map((src, si) => (
                          <li key={si}>
                            {src.url ? (
                              <a href={src.url} target="_blank" rel="noopener noreferrer" className="underline hover:text-forest-dark">
                                {src.title}
                              </a>
                            ) : src.title} — {src.publisher}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
