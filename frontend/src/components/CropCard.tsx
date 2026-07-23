import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Droplets, CalendarDays, Sprout, TrendingUp, Lightbulb } from 'lucide-react'
import { composeExplanation, type RecommendationExplanation } from '../lib/explanation'

export interface CropCardData {
  crop: string
  confidence: number
  display_name: string
  image: string
  season: string[]
  water_requirement: string
  harvest_duration_days: number
  soil_suitability: string[]
  expected_yield: string
  highlight?: boolean
  explanation?: RecommendationExplanation
}

export default function CropCard({ data }: { data: CropCardData }) {
  const { t } = useTranslation()
  const [imgError, setImgError] = useState(false)
  const imageUrl = `/crop-images/${data.image}`

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`card overflow-hidden flex flex-col ${data.highlight ? 'ring-4 ring-leaf' : ''}`}
    >
      <div className="h-52 w-full bg-gradient-to-br from-leaf/40 to-forest/60 flex items-center justify-center">
        {!imgError ? (
          <img
            src={imageUrl}
            alt={data.display_name}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <Sprout size={56} className="text-white" />
        )}
      </div>
      <div className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-forest-dark">{data.display_name}</h3>
          <span className="text-sm font-bold bg-forest/10 text-forest-dark px-2 py-1 rounded-full">
            {Math.round(data.confidence * 100)}%
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs text-earth-dark">
          <div className="flex items-center gap-1.5">
            <CalendarDays size={14} />
            {data.season.join(', ')}
          </div>
          <div className="flex items-center gap-1.5">
            <Droplets size={14} />
            {t(`cropRecommendation.waterRequirement`)}: {data.water_requirement}
          </div>
          <div className="flex items-center gap-1.5">
            <Sprout size={14} />
            {data.harvest_duration_days} {t('cropRecommendation.days')}
          </div>
          <div className="flex items-center gap-1.5">
            <TrendingUp size={14} />
            {data.expected_yield}
          </div>
        </div>

        <p className="text-xs text-gray-500">
          {t('cropRecommendation.soilSuitability')}: {data.soil_suitability.join(', ')}
        </p>

        {data.explanation && (
          <div className="mt-1 flex flex-col gap-1.5 rounded-xl bg-leaf/10 p-3">
            <div className="flex items-center gap-1.5 text-xs font-bold text-forest-dark">
              <Lightbulb size={14} className="text-forest" />
              {t('cropRecommendation.whyTitle')}
            </div>
            <p className="text-xs text-earth-dark leading-relaxed">
              {composeExplanation(t, data.display_name, data.explanation)}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  )
}
