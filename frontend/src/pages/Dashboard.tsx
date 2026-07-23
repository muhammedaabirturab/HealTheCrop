import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../lib/api'
import SoilIndicator, { type SoilStatus } from '../components/SoilIndicator'

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

  useEffect(() => {
    api.get('/sensors/devices').then((res) => {
      setDevices(res.data)
      if (res.data.length > 0) setSelectedDevice(res.data[0].device_uid)
    })
    api.get(import.meta.env.VITE_API_BASE_URL?.replace('/api/v1', '') + '/health' || 'http://localhost:8000/health')
      .then((res) => setStorageStatus(res.data.storage_backend))
      .catch(() => setStorageStatus('unknown'))
  }, [])

  useEffect(() => {
    if (!selectedDevice) return
    api.get(`/sensors/devices/${selectedDevice}/latest`).then(async (res) => {
      setLatest(res.data)
      const health = await api.post('/reports/soil-health', {
        nitrogen: res.data.nitrogen, phosphorus: res.data.phosphorus, potassium: res.data.potassium,
        ph: res.data.ph, moisture: res.data.moisture,
      })
      setIndicators(health.data.indicators)
      setFertilityScore(health.data.fertility_score)
    }).catch(() => setLatest(null))

    api.get(`/sensors/devices/${selectedDevice}/history?limit=30`).then((res) => {
      setHistory([...res.data].reverse())
    }).catch(() => setHistory([]))
  }, [selectedDevice])

  const chartData = history.map((r) => ({
    time: new Date(r.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    moisture: r.moisture, temperature: r.temperature, humidity: r.humidity, ph: r.ph,
  }))

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

      {devices.length === 0 && (
        <div className="card p-6 text-center text-earth-dark">
          {t('dashboard.connectedDevices')}: 0 — connect an ESP32 field node or use{' '}
          <a href="/manual-input" className="text-forest font-semibold underline">{t('nav.manualInput')}</a> instead.
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
