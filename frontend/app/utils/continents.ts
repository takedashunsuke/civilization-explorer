export const CONTINENT_IDS = ['africa', 'europe', 'asia', 'america', 'oceania'] as const

export type ContinentId = (typeof CONTINENT_IDS)[number]

/** STEP1 表の行。立地の違い（内地／海側／島国）を軸にする。 */
export const BACKGROUND_ROWS = ['inland', 'coast', 'island', 'climate', 'food', 'disaster'] as const

export type BackgroundRow = (typeof BACKGROUND_ROWS)[number]

export type ContinentPreset = {
  landform: 'continent' | 'island'
  climate: 'temperate' | 'cold' | 'wetland' | 'arid'
  resourcePool: number
  disasterFrequency: number
}

export const CONTINENT_PRESETS: Record<ContinentId, ContinentPreset> = {
  africa: { landform: 'continent', climate: 'arid', resourcePool: 72, disasterFrequency: 0.32 },
  europe: { landform: 'continent', climate: 'temperate', resourcePool: 118, disasterFrequency: 0.14 },
  asia: { landform: 'continent', climate: 'wetland', resourcePool: 108, disasterFrequency: 0.28 },
  america: { landform: 'continent', climate: 'temperate', resourcePool: 124, disasterFrequency: 0.2 },
  oceania: { landform: 'island', climate: 'wetland', resourcePool: 78, disasterFrequency: 0.38 },
}

export type RegionDraft = {
  id: ContinentId
  institution: string
  taxRate: number
  education: number
  religion: string
  cooperation: number
  authorityAcceptance: number
  ambition: number
  inequality: number
}

export function defaultRegionDraft(id: ContinentId): RegionDraft {
  return {
    id,
    institution: 'democracy',
    taxRate: 0.1,
    education: 0.5,
    religion: 'folk',
    cooperation: 0.5,
    authorityAcceptance: 0.5,
    ambition: 0.5,
    inequality: 0.35,
  }
}
