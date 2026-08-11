import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'
import SoilIndicator, { type SoilStatus } from '../components/SoilIndicator'

// How often the dashboard re-polls the selected device's latest reading and
// history. Comfortably faster than the firmware's own 5s upload interval so
// a fresh reading never waits more than a few seconds to appear on screen.
const POLL_INTERVAL_MS = 4000
// A device is shown as "stale" once its last reading is older than this —
// generous enough to tolerate one or two missed upload cycles without
// flapping between online/offline on every poll.
const STALE_THRESHOLD_MS = 20000

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

export default function Dashboard() {
  const { t } = useTranslation()
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [latest, setLatest] = useState<SensorReading | null>(null)
  const [history, setHistory] = useState<SensorReading[]>([])
  const [indicators, setIndicators] = useState<Record<string, SoilHealthIndicator>>({})
  const [fertilityScore, setFertilityScore] = useState<number | null>(null)
  const [storageStatus, setStorageStatus] = useState<string>('--')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [readingMissing, setReadingMissing] = useState(false)
  const [now, setNow] = useState(() => Date.now())

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

  // isPolling suppresses the error banner on background refreshes — a single
  // dropped poll shouldn't flash a scary red error over data that's still
  // perfectly readable; only the initial load surfaces a hard error.
  const fetchLatest = useCallback((deviceUid: string, isPolling: boolean) => {
    api.get(`/sensors/devices/${deviceUid}/latest`).then(async (res) => {
      setLatest(res.data)
      setReadingMissing(false)
      if (!isPolling) setError('')
      const health = await api.post('/reports/soil-health', {
        nitrogen: res.data.nitrogen, phosphorus: res.data.phosphorus, potassium: res.data.potassium,
        ph: res.data.ph, moisture: res.data.moisture,
      })
      setIndicators(health.data.indicators)
      setFertilityScore(health.data.fertility_score)
    }).catch((err) => {
      if (err?.response?.status === 404) {
        // Device is registered but hasn't sent a reading yet — not an error,
        // just an empty state the UI should explain clearly.
        setLatest(null)
        setReadingMissing(true)
        if (!isPolling) setError('')
        return
      }
      if (!isPolling) {
        setLatest(null)
        setError(getErrorMessage(err, t))
      }
      // A polling request that fails for any other reason (e.g. a momentary
      // network blip) just keeps showing the last-known reading and retries
      // on the next interval tick.
    })

    api.get(`/sensors/devices/${deviceUid}/history?limit=30`).then((res) => {
      setHistory([...res.data].reverse())
    }).catch(() => {
      if (!isPolling) setHistory([])
    })
  }, [t])

  useEffect(() => {
    if (!selectedDevice) return
    fetchLatest(selectedDevice, false)

    const interval = setInterval(() => fetchLatest(selectedDevice, true), POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [selectedDevice, fetchLatest])

  // Drives the stale/online badge and re-evaluates it every second so a
  // device that stops sending flips to "stale" on its own, without needing
  // a new reading to arrive first.
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(tick)
  }, [])

  const isStale = latest ? now - new Date(latest.recorded_at).getTime() > STALE_THRESHOLD_MS : false

  const chartData = history.map((r) => ({
    time: new Date(r.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    moisture: r.moisture, temperature: r.temperature, humidity: r.humidity, ph: r.ph,
  }))

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-8">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-forest-dark">{t('dashboard.title')}</h1>
        {devices.length > 0 && (
          <div className="flex items-center gap-3">
            {latest && !readingMissing && (
              <span className={`flex items-center gap-1.5 text-xs font-semibold ${isStale ? 'text-amber-700' : 'text-forest'}`}>
                <span className={`inline-block w-2 h-2 rounded-full ${isStale ? 'bg-amber-500' : 'bg-forest animate-pulse'}`} />
                {isStale ? t('dashboard.deviceStale') : t('dashboard.deviceOnline')}
              </span>
            )}
            <select
              value={selectedDevice ?? ''}
              onChange={(e) => setSelectedDevice(e.target.value)}
              className="border border-forest/30 rounded-lg px-3 py-2"
            >
              {devices.map((d) => (
                <option key={d.device_uid} value={d.device_uid}>{d.name} ({d.device_uid})</option>
              ))}
            </select>
          </div>
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

      {!loading && readingMissing && (
        <div className="card p-6 text-center text-earth-dark flex items-center justify-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          {t('dashboard.waitingForFirstReading')}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <SoilIndicator label={t('dashboard.soilMoisture')} value={latest?.moisture} unit="%" status={indicators.moisture?.status ?? 'unknown'} />
        <SoilIndicator label={t('dashboard.temperature')} value={latest?.temperature} unit="°C" status="good" />
        <SoilIndicator label={t('dashboard.humidity')} value={latest?.humidity} unit="%" status="good" />
        <SoilIndicator label={t('dashboard.phLevel')} value={latest?.ph} status={indicators.ph?.status ?? 'unknown'} />
        <SoilIndicator label={t('dashboard.nitrogen')} value={latest?.nitrogen} status={indicators.nitrogen?.status ?? 'unknown'} />
        <SoilIndicator label={t('dashboard.fertilityScore')} value={fertilityScore} unit="/100" status={
          fertilityScore == null ? 'unknown' : fertilityScore >= 80 ? 'excellent' : fertilityScore >= 65 ? 'good' : fertilityScore >= 50 ? 'average' : 'poor'
        } />
      </div>

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
            {latest?.recorded_at ? new Date(latest.recorded_at).toLocaleString() : '--'}
          </p>
        </div>
      </div>
    </div>
  )
}
