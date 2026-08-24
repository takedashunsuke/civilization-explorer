export const CONTINENT_IDS = ['africa', 'europe', 'asia', 'america', 'oceania'] as const

export type ContinentId = (typeof CONTINENT_IDS)[number]

/** UN M49 サブ地域。比較列はマクロ5のまま、列内で1つ選ぶ。 */
export const SUBREGIONS_BY_MACRO: Record<ContinentId, readonly string[]> = {
  africa: ['northern_africa', 'eastern_africa', 'middle_africa', 'western_africa', 'southern_africa'],
  europe: ['western_europe', 'eastern_europe', 'northern_europe', 'southern_europe'],
  asia: ['eastern_asia', 'south_eastern_asia', 'southern_asia', 'central_asia', 'western_asia'],
  america: ['northern_america', 'central_america', 'caribbean', 'south_america'],
  oceania: ['australasia', 'melanesia', 'micronesia', 'polynesia'],
}

export const DEFAULT_SUBREGION: Record<ContinentId, string> = {
  africa: 'western_africa',
  europe: 'western_europe',
  asia: 'eastern_asia',
  america: 'northern_america',
  oceania: 'australasia',
}

export type SubregionTheater = {
  id: string
  west: number
  east: number
  south: number
  north: number
}

export const SUBREGION_THEATERS: SubregionTheater[] = [
  { id: 'northern_africa', west: -18, east: 37, south: 15, north: 37 },
  { id: 'eastern_africa', west: 28, east: 52, south: -12, north: 18 },
  { id: 'middle_africa', west: 8, east: 32, south: -14, north: 12 },
  { id: 'western_africa', west: -18, east: 16, south: 0, north: 20 },
  { id: 'southern_africa', west: 10, east: 41, south: -35, north: -10 },
  { id: 'eastern_asia', west: 100, east: 150, south: 18, north: 54 },
  { id: 'south_eastern_asia', west: 92, east: 141, south: -11, north: 24 },
  { id: 'southern_asia', west: 60, east: 98, south: 5, north: 38 },
  { id: 'central_asia', west: 46, east: 88, south: 35, north: 56 },
  { id: 'western_asia', west: 26, east: 66, south: 12, north: 43 },
  { id: 'western_europe', west: -12, east: 16, south: 42, north: 60 },
  { id: 'eastern_europe', west: 18, east: 42, south: 44, north: 72 },
  { id: 'northern_europe', west: -10, east: 32, south: 54, north: 72 },
  { id: 'southern_europe', west: -10, east: 30, south: 34, north: 48 },
  { id: 'northern_america', west: -130, east: -52, south: 24, north: 60 },
  { id: 'central_america', west: -118, east: -77, south: 7, north: 33 },
  { id: 'caribbean', west: -85, east: -59, south: 10, north: 28 },
  { id: 'south_america', west: -82, east: -34, south: -56, north: 13 },
  { id: 'australasia', west: 110, east: 180, south: -48, north: -10 },
  { id: 'melanesia', west: 140, east: 180, south: -22, north: 0 },
  { id: 'micronesia', west: 130, east: 175, south: 0, north: 22 },
  { id: 'polynesia', west: -175, east: -130, south: -25, north: 0 },
]

/** STEP1 表の行。立地の違い（内地／海側／島国）を軸にする。 */
export const BACKGROUND_ROWS = ['inland', 'coast', 'island', 'climate', 'food', 'disaster', 'sanitation'] as const

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
  subregion: string
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
    subregion: DEFAULT_SUBREGION[id],
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

export function subregionChoices(id: ContinentId) {
  return SUBREGIONS_BY_MACRO[id]
}

export const SUBREGION_MACRO: Record<string, ContinentId> = Object.fromEntries(
  CONTINENT_IDS.flatMap((macro) => SUBREGIONS_BY_MACRO[macro].map((sid) => [sid, macro])),
)

export function macroOf(id?: string | null): ContinentId | null {
  if (!id) return null
  if ((CONTINENT_IDS as readonly string[]).includes(id)) return id as ContinentId
  return SUBREGION_MACRO[id] ?? null
}
