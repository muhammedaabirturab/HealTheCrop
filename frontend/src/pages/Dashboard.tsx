import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { AlertTriangle, Usb, Plug, PlugZap, Loader2 } from 'lucide-react'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'
import type { RecommendationExplanation } from '../lib/explanation'
import { useESP32Store } from '../store/esp32Store'
import { isWebSerialSupported } from '../lib/esp32Serial'
import SoilIndicator, { type SoilStatus } from '../components/SoilIndicator'
import CropCard, { type CropCardData } from '../components/CropCard'
import LocationPicker from '../components/LocationPicker'

// How often the dashboard re-polls the selected device's reading history for
// the trends chart. The *current* readings row below is driven live by the
// USB connection itself, not by polling.
const POLL_INTERVAL_MS = 4000

interface Device {
  id: number
  device_uid: string
  name: string
  location: string | null
  status: string
  last_seen: string | null
}

interface SensorReading {
  id: number
  nitrogen: number | null
  phosphorus: number | null
  potassium: number | null
  moisture: number | null
  temperature: number | null
  humidity: number | null
  ph: number | null
  rainfall: number | null
  recorded_at: string
}

interface SoilHealthIndicator {
  value: number | null
  status: SoilStatus
  ideal_range: [number, number]
}

interface ModelInfo {
  accuracy: number | null
  cv_mean_accuracy: number | null
  n_classes: number
}

interface PredictionResult {
  recommended_crop: string
  confidence: number
  alternatives: { crop: string; confidence: number; suitability_tier: string; crop_details: Record<string, unknown> }[]
  crop_details: Record<string, unknown>
  feature_importance: Record<string, number>
  season_used: string
  explanation: RecommendationExplanation
}

export default function Dashboard() {
  const { t } = useTranslation()
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [history, setHistory] = useState<SensorReading[]>([])
  const [indicators, setIndicators] = useState<Record<string, SoilHealthIndicator>>({})
  const [fertilityScore, setFertilityScore] = useState<number | null>(null)
  const [storageStatus, setStorageStatus] = useState<string>('--')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const { status: esp32Status, reading: esp32Reading, lastUpdated: esp32LastUpdated, errorReason, connect, disconnect } = useESP32Store()
  const liveConnected = esp32Status === 'connected' && esp32Reading !== null

  const [season, setSeason] = useState('')
  const [location, setLocation] = useState('')
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [predicting, setPredicting] = useState(false)
  const [predictError, setPredictError] = useState('')
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null)

  useEffect(() => {
    api.get('/predictions/model-info').then((res) => setModelInfo(res.data)).catch(() => setModelInfo(null))
  }, [])

  useEffect(() => {
    setLoading(true)
    api.get('/sensors/devices')
      .then((res) => {
        setDevices(res.data)
        if (res.data.length > 0) setSelectedDevice(res.data[0].device_uid)
      })
      .catch((err) => setError(getErrorMessage(err, t)))
      .finally(() => setLoading(false))

    api.get(import.meta.env.VITE_API_BASE_URL?.replace('/api/v1', '') + '/health' || 'http://localhost:8000/health')
      .then((res) => setStorageStatus(res.data.storage_backend))
      .catch(() => setStorageStatus('unknown'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchHistory = useCallback((deviceUid: string) => {
    api.get(`/sensors/devices/${deviceUid}/history?limit=30`).then((res) => {
      setHistory([...res.data].reverse())
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedDevice) return
    fetchHistory(selectedDevice)
    const interval = setInterval(() => fetchHistory(selectedDevice), POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [selectedDevice, fetchHistory])

  // The current-reading row and fertility score are driven entirely by the
  // live USB connection — never by whatever was last stored in the database.
  // The instant the connection drops, these reset to null so the UI can
  // never show a stale or fabricated "current" value.
  useEffect(() => {
    if (!liveConnected || !esp32Reading) {
      setIndicators({})
      setFertilityScore(null)
      return
    }
    api.post('/reports/soil-health', {
      nitrogen: esp32Reading.nitrogen, phosphorus: esp32Reading.phosphorus, potassium: esp32Reading.potassium,
      ph: esp32Reading.ph, moisture: esp32Reading.moisture,
    }).then((res) => {
      setIndicators(res.data.indicators)
      setFertilityScore(res.data.fertility_score)
    }).catch(() => {})
  }, [liveConnected, esp32Reading])

  const chartData = history.map((r) => ({
    time: new Date(r.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    moisture: r.moisture, temperature: r.temperature, humidity: r.humidity, ph: r.ph,
  }))

  const handleConnectClick = () => {
    if (!isWebSerialSupported()) return
    connect()
  }

  const handlePredict = async () => {
    if (!esp32Reading) return
    setPredicting(true)
    setPredictError('')
    setResult(null)
    try {
      await api.post('/sensors/ingest', {
        device_uid: esp32Reading.device_uid,
        moisture: esp32Reading.moisture,
        ph: esp32Reading.ph,
        temperature: esp32Reading.temperature,
        humidity: esp32Reading.humidity,
        nitrogen: esp32Reading.nitrogen,
        phosphorus: esp32Reading.phosphorus,
        potassium: esp32Reading.potassium,
      })
      const { data } = await api.post('/predictions/from-device', {
        device_uid: esp32Reading.device_uid,
        season: season || undefined,
        location: location || undefined,
      })
      setResult(data)
    } catch (err) {
      setPredictError(getErrorMessage(err, t))
    } finally {
      setPredicting(false)
    }
  }

  const seasonOptions: { value: string; emoji: string; labelKey: string; rangeKey: string }[] = [
    { value: 'spring', emoji: '🌸', labelKey: 'manualInput.seasonSpring', rangeKey: 'manualInput.seasonSpringRange' },
    { value: 'summer', emoji: '☀️', labelKey: 'manualInput.seasonSummer', rangeKey: 'manualInput.seasonSummerRange' },
    { value: 'autumn', emoji: '🍂', labelKey: 'manualInput.seasonAutumn', rangeKey: 'manualInput.seasonAutumnRange' },
    { value: 'winter', emoji: '❄️', labelKey: 'manualInput.seasonWinter', rangeKey: 'manualInput.seasonWinterRange' },
  ]

  const buildCard = (
    crop: string, confidence: number, details: Record<string, unknown>, highlight: boolean,
  ): CropCardData => ({
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
    explanation: highlight ? result?.explanation : undefined,
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-8">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-forest-dark">{t('dashboard.title')}</h1>
        {devices.length > 0 && (
          <select
            value={selectedDevice ?? ''}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="border border-forest/30 rounded-lg px-3 py-2"
          >
            {devices.map((d) => (
              <option key={d.device_uid} value={d.device_uid}>{d.name} ({d.device_uid})</option>
            ))}
          </select>
        )}
      </div>

      {error && (
        <div className="card p-4 flex items-center gap-2 text-sm font-semibold text-red-700 bg-red-50 border border-red-200">
          <AlertTriangle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      {loading && (
        <div className="card p-6 text-center text-earth-dark">{t('common.loading')}</div>
      )}

      {!loading && devices.length === 0 && !error && (
        <div className="card p-6 text-center text-earth-dark">
          {t('dashboard.noDevicesPrefix')}{' '}
          <a href="/manual-input" className="text-forest font-semibold underline">{t('nav.manualInput')}</a>{' '}
          {t('dashboard.noDevicesSuffix')}
        </div>
      )}

      {esp32Status === 'unsupported' && (
        <div className="card p-6 flex items-start gap-3 bg-amber-50 border border-amber-200">
          <Usb className="text-amber-700 shrink-0 mt-1" />
          <div>
            <p className="font-semibold text-amber-900">{t('liveSensor.unsupportedTitle')}</p>
            <p className="text-sm text-amber-800">{t('liveSensor.unsupportedBody')}</p>
          </div>
        </div>
      )}

      {esp32Status !== 'unsupported' && (
        <div className="card p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              {esp32Status === 'connected' ? (
                <PlugZap className="text-forest" />
              ) : esp32Status === 'connecting' ? (
                <Loader2 className="text-forest animate-spin" />
              ) : (
                <Plug className="text-earth-dark" />
              )}
              <div>
                <p className="font-semibold text-forest-dark">
                  {esp32Status === 'connected' && t('liveSensor.statusConnected')}
                  {esp32Status === 'connecting' && t('liveSensor.statusConnecting')}
                  {esp32Status === 'disconnected' && t('liveSensor.statusDisconnected')}
                </p>
                {esp32Reading && (
                  <p className="text-xs text-earth-dark">
                    {t('liveSensor.deviceLabel')}: <span className="font-mono">{esp32Reading.device_uid}</span>
                  </p>
                )}
              </div>
            </div>

            {esp32Status === 'connected' ? (
              <button onClick={disconnect} className="btn-secondary !py-2 !px-5 !text-sm">
                {t('liveSensor.disconnect')}
              </button>
            ) : (
              <button
                onClick={handleConnectClick}
                disabled={esp32Status === 'connecting'}
                className="btn-primary !py-2 !px-5 !text-sm disabled:opacity-60 flex items-center gap-2"
              >
                <Usb size={16} /> {t('liveSensor.connectButton')}
              </button>
            )}
          </div>

          {errorReason && (
            <p className="text-red-600 text-sm font-semibold">
              {t(errorReason === 'lost' ? 'liveSensor.errorLostConnection' : 'liveSensor.errorConnectFailed')}
            </p>
          )}
          {esp32Status === 'disconnected' && !errorReason && (
            <p className="text-sm text-earth-dark">{t('liveSensor.connectHint')}</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <SoilIndicator label={t('dashboard.soilMoisture')} value={esp32Reading?.moisture} unit="%" status={indicators.moisture?.status ?? 'unknown'} />
        <SoilIndicator label={t('dashboard.temperature')} value={esp32Reading?.temperature} unit="°C" status="good" />
        <SoilIndicator label={t('dashboard.humidity')} value={esp32Reading?.humidity} unit="%" status="good" />
        <SoilIndicator label={t('dashboard.phLevel')} value={esp32Reading?.ph} status={indicators.ph?.status ?? 'unknown'} />
        <SoilIndicator label={t('dashboard.nitrogen')} value={esp32Reading?.nitrogen} status={indicators.nitrogen?.status ?? 'unknown'} />
        <SoilIndicator label={t('dashboard.fertilityScore')} value={fertilityScore} unit="/100" status={
          fertilityScore == null ? 'unknown' : fertilityScore >= 80 ? 'excellent' : fertilityScore >= 65 ? 'good' : fertilityScore >= 50 ? 'average' : 'poor'
        } />
      </div>

      <div className="card p-6 grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        <label className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('manualInput.season')}
          <select
            value={season}
            onChange={(e) => setSeason(e.target.value)}
            className="border border-forest/30 rounded-lg px-3 py-2 focus:outline-none focus:border-forest"
          >
            <option value="">{t('manualInput.seasonAuto')}</option>
            {seasonOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.emoji} {t(opt.labelKey)} ({t(opt.rangeKey)})
              </option>
            ))}
          </select>
        </label>

        <div className="flex flex-col gap-1 text-sm font-semibold text-earth-dark">
          {t('auth.location')}
          <LocationPicker value={location} onChange={setLocation} />
        </div>

        <button
          onClick={handlePredict}
          disabled={predicting || !esp32Reading}
          className="btn-primary disabled:opacity-60"
          title={!esp32Reading ? t('liveSensor.connectHint') : undefined}
        >
          {predicting ? t('common.loading') : t('liveSensor.getRecommendation')}
        </button>
      </div>

      {predictError && <p className="text-red-600 font-semibold">{predictError}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-4">
            <div className="card px-5 py-4 flex flex-col gap-1 min-w-[10rem]">
              <span className="text-xs font-semibold text-earth-dark uppercase tracking-wide">
                {t('cropRecommendation.predictionConfidence')}
              </span>
              <span className="text-2xl font-extrabold text-forest-dark">
                {(result.confidence * 100).toFixed(1)}%
              </span>
            </div>
            {modelInfo?.accuracy != null && (
              <div className="card px-5 py-4 flex flex-col gap-1 min-w-[10rem]">
                <span className="text-xs font-semibold text-earth-dark uppercase tracking-wide">
                  {t('cropRecommendation.modelAccuracy')}
                </span>
                <span className="text-2xl font-extrabold text-forest-dark">
                  {(modelInfo.accuracy * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          <h2 className="text-xl font-bold text-forest-dark">{t('cropRecommendation.title')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {result.alternatives.map((alt, index) => (
              <CropCard key={alt.crop} data={buildCard(alt.crop, alt.confidence, alt.crop_details, index === 0)} />
            ))}
          </div>
        </div>
      )}

      <div className="card p-6">
        <h2 className="text-lg font-bold text-forest-dark mb-4">{t('dashboard.historicalTrends')}</h2>
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e4e7" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="moisture" stroke="#2E7D32" strokeWidth={2} dot={false} name={t('dashboard.soilMoisture')} />
              <Line type="monotone" dataKey="temperature" stroke="#8D6E46" strokeWidth={2} dot={false} name={t('dashboard.temperature')} />
              <Line type="monotone" dataKey="humidity" stroke="#66BB6A" strokeWidth={2} dot={false} name={t('dashboard.humidity')} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        <div className="card p-4">
          <p className="font-semibold text-earth-dark">{t('dashboard.storageStatus')}</p>
          <p className="text-forest-dark font-bold">{storageStatus}</p>
        </div>
        <div className="card p-4">
          <p className="font-semibold text-earth-dark">{t('dashboard.connectedDevices')}</p>
          <p className="text-forest-dark font-bold">{devices.length}</p>
        </div>
        <div className="card p-4">
          <p className="font-semibold text-earth-dark">{t('dashboard.lastUpdated')}</p>
          <p className="text-forest-dark font-bold">
            {liveConnected && esp32LastUpdated ? esp32LastUpdated.toLocaleString() : '--'}
          </p>
        </div>
      </div>
    </div>
  )
}
