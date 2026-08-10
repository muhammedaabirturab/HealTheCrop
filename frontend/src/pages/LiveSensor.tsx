import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Usb, Plug, PlugZap, Loader2 } from 'lucide-react'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'
import type { RecommendationExplanation } from '../lib/explanation'
import CropCard, { type CropCardData } from '../components/CropCard'
import LocationPicker from '../components/LocationPicker'

const SENSOR_TAG = '<<SENSOR>>'
const SERIAL_BAUD_RATE = 115200

interface LiveReading {
  device_uid: string
  moisture: number | null
  ph: number | null
  temperature: number | null
  humidity: number | null
  nitrogen: number | null
  phosphorus: number | null
  potassium: number | null
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

type ConnectionStatus = 'unsupported' | 'disconnected' | 'connecting' | 'connected'

function isSerialSupported(): boolean {
  return typeof navigator !== 'undefined' && 'serial' in navigator
}

export default function LiveSensor() {
  const { t } = useTranslation()
  const [status, setStatus] = useState<ConnectionStatus>(isSerialSupported() ? 'disconnected' : 'unsupported')
  const [connectError, setConnectError] = useState('')
  const [reading, setReading] = useState<LiveReading | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const [season, setSeason] = useState('')
  const [location, setLocation] = useState('')
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [predicting, setPredicting] = useState(false)
  const [predictError, setPredictError] = useState('')
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null)

  const portRef = useRef<SerialPort | null>(null)
  const readerRef = useRef<ReadableStreamDefaultReader<string> | null>(null)
  const keepReadingRef = useRef(false)
  const connectingRef = useRef(false)

  useEffect(() => {
    api.get('/predictions/model-info').then((res) => setModelInfo(res.data)).catch(() => setModelInfo(null))
  }, [])

  const parseLine = useCallback((line: string) => {
    const tagIndex = line.indexOf(SENSOR_TAG)
    if (tagIndex === -1) return
    const jsonStart = line.indexOf('{', tagIndex)
    if (jsonStart === -1) return
    try {
      const parsed = JSON.parse(line.slice(jsonStart)) as Partial<LiveReading>
      if (parsed && typeof parsed === 'object' && parsed.device_uid) {
        setReading(parsed as LiveReading)
        setLastUpdated(new Date())
      }
    } catch {
      // A line can arrive mid-write (e.g. right as the board resets) — the
      // next 30s reading will parse cleanly, so just drop this one.
    }
  }, [])

  const readLoop = useCallback(async (port: SerialPort) => {
    const textDecoder = new TextDecoderStream()
    const readableStreamClosed = port.readable!.pipeTo(textDecoder.writable as WritableStream<Uint8Array>)
    const reader = textDecoder.readable.getReader()
    readerRef.current = reader
    let buffer = ''
    try {
      while (keepReadingRef.current) {
        const { value, done } = await reader.read()
        if (done) break
        if (value) {
          buffer += value
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''
          for (const line of lines) parseLine(line)
        }
      }
    } catch {
      if (keepReadingRef.current) setConnectError(t('liveSensor.errorLostConnection'))
    } finally {
      reader.releaseLock()
      await readableStreamClosed.catch(() => {})
    }
  }, [parseLine, t])

  const disconnect = useCallback(async () => {
    keepReadingRef.current = false
    try {
      await readerRef.current?.cancel()
    } catch {
      // already closed/cancelled — nothing to do
    }
    try {
      await portRef.current?.close()
    } catch {
      // already closed — nothing to do
    }
    portRef.current = null
    readerRef.current = null
    setStatus('disconnected')
  }, [])

  const connectToPort = useCallback(async (port: SerialPort) => {
    if (connectingRef.current || portRef.current) return
    connectingRef.current = true
    setStatus('connecting')
    setConnectError('')
    try {
      await port.open({ baudRate: SERIAL_BAUD_RATE })
      portRef.current = port
      keepReadingRef.current = true
      setStatus('connected')
      readLoop(port).finally(() => {
        if (keepReadingRef.current) {
          // The board dropped the line unexpectedly (unplugged, reset, etc).
          keepReadingRef.current = false
          portRef.current = null
          readerRef.current = null
          setStatus('disconnected')
        }
      })
    } catch {
      setConnectError(t('liveSensor.errorConnectFailed'))
      setStatus('disconnected')
    } finally {
      connectingRef.current = false
    }
  }, [readLoop, t])

  const handleConnectClick = async () => {
    if (!isSerialSupported()) return
    try {
      const port = await navigator.serial.requestPort()
      await connectToPort(port)
    } catch {
      // User dismissed the browser's device picker — not an error to surface.
    }
  }

  // Auto-detect: reconnect to a previously authorized port on load, and react
  // live to the board being plugged in or unplugged while this page is open.
  useEffect(() => {
    if (!isSerialSupported()) return

    navigator.serial.getPorts().then((ports) => {
      if (ports.length > 0) connectToPort(ports[0])
    })

    const handleConnect = () => {
      navigator.serial.getPorts().then((ports) => {
        if (ports.length > 0) connectToPort(ports[0])
      })
    }
    const handleDisconnect = () => {
      if (portRef.current) disconnect()
    }

    navigator.serial.addEventListener('connect', handleConnect)
    navigator.serial.addEventListener('disconnect', handleDisconnect)
    return () => {
      navigator.serial.removeEventListener('connect', handleConnect)
      navigator.serial.removeEventListener('disconnect', handleDisconnect)
      keepReadingRef.current = false
      readerRef.current?.cancel().catch(() => {})
      portRef.current?.close().catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleGetRecommendation = async () => {
    if (!reading) return
    setPredicting(true)
    setPredictError('')
    setResult(null)
    try {
      await api.post('/sensors/ingest', {
        device_uid: reading.device_uid,
        moisture: reading.moisture,
        ph: reading.ph,
        temperature: reading.temperature,
        humidity: reading.humidity,
        nitrogen: reading.nitrogen,
        phosphorus: reading.phosphorus,
        potassium: reading.potassium,
      })
      const { data } = await api.post('/predictions/from-device', {
        device_uid: reading.device_uid,
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

  const readingFields: { key: keyof LiveReading; label: string; unit: string }[] = [
    { key: 'moisture', label: t('dashboard.soilMoisture'), unit: '%' },
    { key: 'ph', label: t('dashboard.phLevel'), unit: '' },
    { key: 'temperature', label: t('dashboard.temperature'), unit: '°C' },
    { key: 'humidity', label: t('dashboard.humidity'), unit: '%' },
    { key: 'nitrogen', label: t('dashboard.nitrogen'), unit: '' },
    { key: 'phosphorus', label: t('dashboard.phosphorus'), unit: '' },
    { key: 'potassium', label: t('dashboard.potassium'), unit: '' },
  ]

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-forest-dark">{t('liveSensor.title')}</h1>
        <p className="text-earth-dark">{t('liveSensor.subtitle')}</p>
      </div>

      {status === 'unsupported' && (
        <div className="card p-6 flex items-start gap-3 bg-amber-50 border border-amber-200">
          <Usb className="text-amber-700 shrink-0 mt-1" />
          <div>
            <p className="font-semibold text-amber-900">{t('liveSensor.unsupportedTitle')}</p>
            <p className="text-sm text-amber-800">{t('liveSensor.unsupportedBody')}</p>
          </div>
        </div>
      )}

      {status !== 'unsupported' && (
        <div className="card p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              {status === 'connected' ? (
                <PlugZap className="text-forest" />
              ) : status === 'connecting' ? (
                <Loader2 className="text-forest animate-spin" />
              ) : (
                <Plug className="text-earth-dark" />
              )}
              <div>
                <p className="font-semibold text-forest-dark">
                  {status === 'connected' && t('liveSensor.statusConnected')}
                  {status === 'connecting' && t('liveSensor.statusConnecting')}
                  {status === 'disconnected' && t('liveSensor.statusDisconnected')}
                </p>
                {reading && (
                  <p className="text-xs text-earth-dark">
                    {t('liveSensor.deviceLabel')}: <span className="font-mono">{reading.device_uid}</span>
                  </p>
                )}
              </div>
            </div>

            {status === 'connected' ? (
              <button onClick={disconnect} className="btn-secondary !py-2 !px-5 !text-sm">
                {t('liveSensor.disconnect')}
              </button>
            ) : (
              <button
                onClick={handleConnectClick}
                disabled={status === 'connecting'}
                className="btn-primary !py-2 !px-5 !text-sm disabled:opacity-60 flex items-center gap-2"
              >
                <Usb size={16} /> {t('liveSensor.connectButton')}
              </button>
            )}
          </div>

          {connectError && <p className="text-red-600 text-sm font-semibold">{connectError}</p>}
          {status === 'disconnected' && !connectError && (
            <p className="text-sm text-earth-dark">{t('liveSensor.connectHint')}</p>
          )}
        </div>
      )}

      {reading && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-lg font-bold text-forest-dark">{t('liveSensor.readingsTitle')}</h2>
            {lastUpdated && (
              <span className="text-xs text-earth-dark">
                {t('dashboard.lastUpdated')}: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {readingFields.map((f) => (
              <div key={f.key} className="card px-4 py-3 flex flex-col gap-1">
                <span className="text-xs font-semibold text-earth-dark uppercase tracking-wide">{f.label}</span>
                <span className="text-xl font-extrabold text-forest-dark">
                  {reading[f.key] == null ? t('liveSensor.noSensor') : `${reading[f.key]}${f.unit}`}
                </span>
              </div>
            ))}
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
              onClick={handleGetRecommendation}
              disabled={predicting}
              className="btn-primary disabled:opacity-60"
            >
              {predicting ? t('common.loading') : t('liveSensor.getRecommendation')}
            </button>
          </div>
        </div>
      )}

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
    </div>
  )
}
