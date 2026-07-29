import type { TFunction } from 'i18next'

export interface ExplanationFactor {
  feature: string // N | P | K | temperature | humidity | ph | rainfall
  level: string // ideal | low | high
}

export interface RecommendationExplanation {
  crop: string
  season: string
  factors: ExplanationFactor[]
}

const FEATURE_KEYS: Record<string, string> = {
  N: 'cropRecommendation.featureN', P: 'cropRecommendation.featureP', K: 'cropRecommendation.featureK',
  temperature: 'cropRecommendation.featureTemperature', humidity: 'cropRecommendation.featureHumidity',
  ph: 'cropRecommendation.featurePh', rainfall: 'cropRecommendation.featureRainfall',
  moisture: 'cropRecommendation.featureMoisture',
}
const LEVEL_KEYS: Record<string, string> = {
  ideal: 'cropRecommendation.levelIdeal', low: 'cropRecommendation.levelLow', high: 'cropRecommendation.levelHigh',
}
const SEASON_KEYS: Record<string, string> = {
  spring: 'manualInput.seasonSpring', summer: 'manualInput.seasonSummer',
  autumn: 'manualInput.seasonAutumn', winter: 'manualInput.seasonWinter',
}

/**
 * Composes the "why this crop?" sentence from the backend's structured
 * explanation data (crop, season, factors) using translated phrase templates —
 * the backend deliberately never returns a hardcoded English sentence, since
 * that couldn't be localized for the app's other 5 supported languages.
 */
export function composeExplanation(
  t: TFunction,
  cropDisplayName: string,
  explanation: RecommendationExplanation,
): string {
  const seasonKey = SEASON_KEYS[explanation.season]
  const seasonLabel = seasonKey ? t(seasonKey) : explanation.season

  if (explanation.factors.length === 0) {
    return `${cropDisplayName} ${t('cropRecommendation.whyFallback', { season: seasonLabel })}`
  }

  const parts = explanation.factors.map((factor) => {
    const featureKey = FEATURE_KEYS[factor.feature]
    const levelKey = LEVEL_KEYS[factor.level]
    if (!featureKey || !levelKey) return null
    return `${t(featureKey)} ${t(levelKey)}`
  }).filter((p): p is string => Boolean(p))

  if (parts.length === 0) {
    return `${cropDisplayName} ${t('cropRecommendation.whyFallback', { season: seasonLabel })}`
  }

  const joinedConditions = parts.length > 1 ? `${parts[0]} ${t('cropRecommendation.and')} ${parts[1]}` : parts[0]
  return `${cropDisplayName} ${t('cropRecommendation.whyIntro')} ${joinedConditions}, ${t('cropRecommendation.whyOutro', { season: seasonLabel })}`
}
