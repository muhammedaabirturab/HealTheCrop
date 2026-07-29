import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Users, ShieldCheck, Sprout, Bug, Radio, Download, Ban, CheckCircle2, Trash2, AlertTriangle,
} from 'lucide-react'
import { api } from '../lib/api'
import { getErrorMessage } from '../lib/errors'
import { downloadAuthenticatedFile } from '../lib/download'
import AuthenticatedImage from '../components/AuthenticatedImage'

interface Stats {
  total_users: number
  total_farmers: number
  total_admins: number
  active_users: number
  deactivated_users: number
  total_predictions: number
  total_pest_scans: number
  total_devices: number
  total_sensor_readings: number
}

interface AdminUser {
  id: number
  name: string
  email: string
  phone: string | null
  location: string | null
  preferred_language: string
  role: 'farmer' | 'admin'
  is_active: boolean
  created_at: string
}

interface LoginEvent {
  id: number
  user_id: number | null
  email_attempted: string
  success: boolean
  remember_me: boolean
  ip_address: string | null
  created_at: string
}

interface AdminPrediction {
  id: number
  user_id: number
  user_email: string | null
  recommended_crop: string
  confidence: number
  season: string | null
  source: string
  created_at: string
}

interface AdminPestScan {
  id: number
  user_id: number
  user_email: string | null
  image_key: string
  model_used: string
  top_confidence: number | null
  created_at: string
}

interface AdminSensorReading {
  id: number
  device_id: number
  device_uid: string | null
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

type Tab = 'users' | 'logins' | 'predictions' | 'pests' | 'sensors'

const fmtDate = (iso: string) => new Date(iso).toLocaleString()

export default function AdminDashboard() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('users')
  const [stats, setStats] = useState<Stats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [logins, setLogins] = useState<LoginEvent[]>([])
  const [predictions, setPredictions] = useState<AdminPrediction[]>([])
  const [pestScans, setPestScans] = useState<AdminPestScan[]>([])
  const [sensorReadings, setSensorReadings] = useState<AdminSensorReading[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/admin/stats').then((res) => setStats(res.data)).catch(() => setStats(null))
  }, [])

  useEffect(() => {
    setLoading(true)
    setError('')
    const loaders: Record<Tab, () => Promise<void>> = {
      users: async () => setUsers((await api.get('/admin/users')).data),
      logins: async () => setLogins((await api.get('/admin/login-history')).data),
      predictions: async () => setPredictions((await api.get('/admin/predictions')).data),
      pests: async () => setPestScans((await api.get('/admin/pest-scans')).data),
      sensors: async () => setSensorReadings((await api.get('/admin/sensor-readings')).data),
    }
    loaders[tab]()
      .catch((err) => setError(getErrorMessage(err, t)))
      .finally(() => setLoading(false))
  }, [tab, t])

  const refreshUsers = () => api.get('/admin/users').then((res) => setUsers(res.data))

  const toggleUserStatus = async (user: AdminUser) => {
    try {
      await api.patch(`/admin/users/${user.id}/status`, { is_active: !user.is_active })
      await refreshUsers()
    } catch (err) {
      setError(getErrorMessage(err, t))
    }
  }

  const deleteUser = async (user: AdminUser) => {
    if (!window.confirm(t('admin.confirmDelete', { name: user.name }))) return
    try {
      await api.delete(`/admin/users/${user.id}`)
      await refreshUsers()
    } catch (err) {
      setError(getErrorMessage(err, t))
    }
  }

  const tabs: { key: Tab; label: string; icon: typeof Users }[] = [
    { key: 'users', label: t('admin.tabUsers'), icon: Users },
    { key: 'logins', label: t('admin.tabLogins'), icon: ShieldCheck },
    { key: 'predictions', label: t('admin.tabPredictions'), icon: Sprout },
    { key: 'pests', label: t('admin.tabPestScans'), icon: Bug },
    { key: 'sensors', label: t('admin.tabSensors'), icon: Radio },
  ]

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-forest-dark">{t('admin.title')}</h1>
        <p className="text-earth-dark">{t('admin.subtitle')}</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label={t('admin.statTotalUsers')} value={stats.total_users} />
          <StatCard label={t('admin.statActiveUsers')} value={stats.active_users} />
          <StatCard label={t('admin.statPredictions')} value={stats.total_predictions} />
          <StatCard label={t('admin.statPestScans')} value={stats.total_pest_scans} />
          <StatCard label={t('admin.statDevices')} value={stats.total_devices} />
          <StatCard label={t('admin.statSensorReadings')} value={stats.total_sensor_readings} />
          <StatCard label={t('admin.statDeactivated')} value={stats.deactivated_users} />
          <StatCard label={t('admin.statAdmins')} value={stats.total_admins} />
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full font-semibold text-sm transition-colors ${
              tab === key ? 'bg-forest text-white' : 'bg-white text-forest-dark border border-forest/30'
            }`}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="card p-4 flex items-center gap-2 text-sm font-semibold text-red-700 bg-red-50 border border-red-200">
          <AlertTriangle size={16} className="shrink-0" /> {error}
        </div>
      )}

      {loading && <div className="card p-6 text-center text-earth-dark">{t('common.loading')}</div>}

      {!loading && tab === 'users' && (
        <div className="card p-4 overflow-x-auto flex flex-col gap-4">
          <div className="flex justify-end">
            <ExportButton path="/admin/export/users.csv" filename="healthecrop_users.csv" />
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-earth-dark border-b border-forest/10">
                <th className="py-2 pr-3">{t('admin.colName')}</th>
                <th className="py-2 pr-3">{t('admin.colEmail')}</th>
                <th className="py-2 pr-3">{t('admin.colLocation')}</th>
                <th className="py-2 pr-3">{t('admin.colRole')}</th>
                <th className="py-2 pr-3">{t('admin.colStatus')}</th>
                <th className="py-2 pr-3">{t('admin.colJoined')}</th>
                <th className="py-2 pr-3">{t('admin.colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-forest/5">
                  <td className="py-2 pr-3 font-semibold text-forest-dark">{u.name}</td>
                  <td className="py-2 pr-3">{u.email}</td>
                  <td className="py-2 pr-3">{u.location || '—'}</td>
                  <td className="py-2 pr-3 capitalize">{u.role}</td>
                  <td className="py-2 pr-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${u.is_active ? 'bg-forest/10 text-forest-dark' : 'bg-red-100 text-red-700'}`}>
                      {u.is_active ? t('admin.active') : t('admin.deactivated')}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-xs text-gray-500">{fmtDate(u.created_at)}</td>
                  <td className="py-2 pr-3">
                    {u.role !== 'admin' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => toggleUserStatus(u)}
                          title={u.is_active ? t('admin.deactivate') : t('admin.activate')}
                          className="text-earth-dark hover:text-forest"
                        >
                          {u.is_active ? <Ban size={16} /> : <CheckCircle2 size={16} />}
                        </button>
                        <button
                          onClick={() => deleteUser(u)}
                          title={t('admin.delete')}
                          className="text-earth-dark hover:text-red-600"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && tab === 'logins' && (
        <div className="card p-4 overflow-x-auto flex flex-col gap-4">
          <div className="flex justify-end">
            <ExportButton path="/admin/export/login-history.csv" filename="healthecrop_login_history.csv" />
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-earth-dark border-b border-forest/10">
                <th className="py-2 pr-3">{t('admin.colEmail')}</th>
                <th className="py-2 pr-3">{t('admin.colResult')}</th>
                <th className="py-2 pr-3">{t('auth.rememberMe')}</th>
                <th className="py-2 pr-3">IP</th>
                <th className="py-2 pr-3">{t('admin.colTime')}</th>
              </tr>
            </thead>
            <tbody>
              {logins.map((l) => (
                <tr key={l.id} className="border-b border-forest/5">
                  <td className="py-2 pr-3">{l.email_attempted}</td>
                  <td className="py-2 pr-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${l.success ? 'bg-forest/10 text-forest-dark' : 'bg-red-100 text-red-700'}`}>
                      {l.success ? t('admin.success') : t('admin.failed')}
                    </span>
                  </td>
                  <td className="py-2 pr-3">{l.remember_me ? t('common.yes') : t('common.no')}</td>
                  <td className="py-2 pr-3 text-xs text-gray-500">{l.ip_address || '—'}</td>
                  <td className="py-2 pr-3 text-xs text-gray-500">{fmtDate(l.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && tab === 'predictions' && (
        <div className="card p-4 overflow-x-auto flex flex-col gap-4">
          <div className="flex justify-end">
            <ExportButton path="/admin/export/predictions.csv" filename="healthecrop_predictions.csv" />
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-earth-dark border-b border-forest/10">
                <th className="py-2 pr-3">{t('admin.colEmail')}</th>
                <th className="py-2 pr-3">{t('cropRecommendation.title')}</th>
                <th className="py-2 pr-3">{t('common.confidence')}</th>
                <th className="py-2 pr-3">{t('manualInput.season')}</th>
                <th className="py-2 pr-3">{t('admin.colSource')}</th>
                <th className="py-2 pr-3">{t('admin.colTime')}</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((p) => (
                <tr key={p.id} className="border-b border-forest/5">
                  <td className="py-2 pr-3">{p.user_email}</td>
                  <td className="py-2 pr-3 font-semibold text-forest-dark capitalize">{p.recommended_crop}</td>
                  <td className="py-2 pr-3">{Math.round(p.confidence * 100)}%</td>
                  <td className="py-2 pr-3 capitalize">{p.season || '—'}</td>
                  <td className="py-2 pr-3 capitalize">{p.source}</td>
                  <td className="py-2 pr-3 text-xs text-gray-500">{fmtDate(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && tab === 'pests' && (
        <div className="card p-4 overflow-x-auto flex flex-col gap-4">
          <div className="flex justify-end">
            <ExportButton path="/admin/export/pest-scans.csv" filename="healthecrop_pest_scans.csv" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {pestScans.map((p) => (
              <div key={p.id} className="border border-forest/10 rounded-xl overflow-hidden flex flex-col">
                <AuthenticatedImage
                  src={`/admin/pest-scans/${p.id}/image`}
                  alt={`Pest scan ${p.id}`}
                  className="h-32 w-full object-cover"
                />
                <div className="p-3 text-xs flex flex-col gap-1">
                  <span className="font-semibold text-forest-dark">{p.user_email}</span>
                  <span className="text-gray-500">
                    {p.model_used} · {p.top_confidence != null ? `${Math.round(p.top_confidence * 100)}%` : '—'}
                  </span>
                  <span className="text-gray-400">{fmtDate(p.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && tab === 'sensors' && (
        <div className="card p-4 overflow-x-auto flex flex-col gap-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-earth-dark border-b border-forest/10">
                <th className="py-2 pr-3">Device</th>
                <th className="py-2 pr-3">N</th>
                <th className="py-2 pr-3">P</th>
                <th className="py-2 pr-3">K</th>
                <th className="py-2 pr-3">{t('dashboard.soilMoisture')}</th>
                <th className="py-2 pr-3">{t('dashboard.temperature')}</th>
                <th className="py-2 pr-3">{t('dashboard.humidity')}</th>
                <th className="py-2 pr-3">{t('dashboard.phLevel')}</th>
                <th className="py-2 pr-3">{t('admin.colTime')}</th>
              </tr>
            </thead>
            <tbody>
              {sensorReadings.map((r) => (
                <tr key={r.id} className="border-b border-forest/5">
                  <td className="py-2 pr-3 font-semibold text-forest-dark">{r.device_uid}</td>
                  <td className="py-2 pr-3">{r.nitrogen ?? '—'}</td>
                  <td className="py-2 pr-3">{r.phosphorus ?? '—'}</td>
                  <td className="py-2 pr-3">{r.potassium ?? '—'}</td>
                  <td className="py-2 pr-3">{r.moisture ?? '—'}</td>
                  <td className="py-2 pr-3">{r.temperature ?? '—'}</td>
                  <td className="py-2 pr-3">{r.humidity ?? '—'}</td>
                  <td className="py-2 pr-3">{r.ph ?? '—'}</td>
                  <td className="py-2 pr-3 text-xs text-gray-500">{fmtDate(r.recorded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      <span className="text-xs font-semibold text-earth-dark uppercase tracking-wide">{label}</span>
      <span className="text-2xl font-extrabold text-forest-dark">{value}</span>
    </div>
  )
}

function ExportButton({ path, filename }: { path: string; filename: string }) {
  const { t } = useTranslation()
  const [downloading, setDownloading] = useState(false)
  return (
    <button
      onClick={async () => {
        setDownloading(true)
        try {
          await downloadAuthenticatedFile(path, filename)
        } finally {
          setDownloading(false)
        }
      }}
      disabled={downloading}
      className="flex items-center gap-2 text-sm font-semibold text-forest-dark border border-forest/30 rounded-full px-4 py-2 hover:bg-forest/5 disabled:opacity-60"
    >
      <Download size={14} /> {downloading ? t('common.loading') : t('admin.exportCsv')}
    </button>
  )
}
