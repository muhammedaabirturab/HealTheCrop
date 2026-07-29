import type { TFunction } from 'i18next'

// Canonical English names — these are what's sent to the backend/ML model and
// stored internally, regardless of display language. Never translate these
// arrays themselves; only the displayed label (see translateRegion below).
export const INDIAN_STATES: string[] = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat',
  'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
  'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan',
  'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
]

export const INDIAN_UNION_TERRITORIES: string[] = [
  'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi (NCT)', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry',
]

export const ALL_INDIAN_REGIONS: string[] = [...INDIAN_STATES, ...INDIAN_UNION_TERRITORIES]

/**
 * Translates a canonical English state/UT name into the active language for
 * display only — the value passed to onChange()/the backend always stays the
 * canonical English string from INDIAN_STATES/INDIAN_UNION_TERRITORIES above.
 */
export function translateRegion(t: TFunction, region: string): string {
  return t(`states.${region}`, { defaultValue: region })
}
