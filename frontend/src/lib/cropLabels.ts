import type { TFunction } from 'i18next'

// Maps the exact English enum strings stored in ml/data/crop_metadata.json
// (soil_suitability, water_requirement, season) to translation keys, so the
// UI can render them in whichever of the 6 supported languages is active
// without needing per-language copies of the metadata file itself.
const SOIL_KEYS: Record<string, string> = {
  "Alluvial": "alluvial", "Black Cotton Soil": "blackCottonSoil", "Clayey": "clayey",
  "Coastal Alluvial": "coastalAlluvial", "Loamy": "loamy", "Red Laterite": "redLaterite",
  "Sandy": "sandy", "Sandy Loam": "sandyLoam", "Well-drained": "wellDrained",
}
const WATER_KEYS: Record<string, string> = { "Low": "low", "Medium": "medium", "High": "high" }
const SEASON_KEYS: Record<string, string> = { "Annual": "annual", "Kharif": "kharif", "Rabi": "rabi", "Zaid": "zaid" }

export function cropDisplayName(t: TFunction, cropSlug: string, fallback: string): string {
  return t(`crops.${cropSlug}`, { defaultValue: fallback })
}

export function translateWaterRequirement(t: TFunction, value: string): string {
  const key = WATER_KEYS[value]
  return key ? t(`cropAttributes.water.${key}`) : value
}

export function translateSoilSuitability(t: TFunction, values: string[]): string {
  return values.map((v) => {
    const key = SOIL_KEYS[v]
    return key ? t(`cropAttributes.soil.${key}`) : v
  }).join(', ')
}

export function translateSeasons(t: TFunction, values: string[]): string {
  return values.map((v) => {
    const key = SEASON_KEYS[v]
    return key ? t(`cropAttributes.season.${key}`) : v
  }).join(', ')
}
