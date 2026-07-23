import { useTranslation } from 'react-i18next'

export type SoilStatus = 'excellent' | 'good' | 'average' | 'poor' | 'critical' | 'unknown'

const STATUS_COLORS: Record<SoilStatus, string> = {
  excellent: 'bg-emerald-500',
  good: 'bg-leaf',
  average: 'bg-amber-400',
  poor: 'bg-orange-500',
  critical: 'bg-red-600',
  unknown: 'bg-gray-300',
}

export default function SoilIndicator({
  label,
  value,
  unit,
  status,
}: {
  label: string
  value: number | string | null | undefined
  unit?: string
  status: SoilStatus
}) {
  const { t } = useTranslation()
  return (
    <div className="card p-4 flex flex-col gap-2 min-w-[150px]">
      <span className="text-sm text-earth-dark font-medium">{label}</span>
      <span className="text-2xl font-bold text-forest-dark">
        {value ?? '--'}
        {unit && <span className="text-base font-medium text-earth-dark ml-1">{unit}</span>}
      </span>
      <div className="flex items-center gap-2">
        <span className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[status]}`} />
        <span className="text-xs font-semibold text-gray-500 capitalize">
          {t(`soilHealth.${status}`, status)}
        </span>
      </div>
    </div>
  )
}
