import {
  CONTINENT_IDS,
  type ContinentId,
  type RegionDraft,
  defaultRegionDraft,
} from '~/utils/continents'

export type ScenarioTemplateId =
  | 'controlled_experiment'
  | 'diverse_world'
  | 'tax_contrast'
  | 'institution_lab'
  | 'uniform_baseline'
  | 'demo_pitch'

export const SCENARIO_TEMPLATE_IDS: ScenarioTemplateId[] = [
  'controlled_experiment',
  'diverse_world',
  'demo_pitch',
  'tax_contrast',
  'institution_lab',
  'uniform_baseline',
]

/** 列ごとの「性格」— 五地域が最初から違う社会として見えるようにする */
const REGION_CHARACTER: Record<ContinentId, Partial<RegionDraft>> = {
  africa: {
    subregion: 'western_africa',
    institution: 'anarchy',
    taxRate: 0.05,
    education: 0.35,
    religion: 'folk',
    tradeOpenness: 0.35,
    cooperation: 0.45,
    authorityAcceptance: 0.4,
    ambition: 0.55,
    inequality: 0.55,
    traitRate: 0.13,
    welfareRate: 0.07,
    population: 2000,
  },
  europe: {
    subregion: 'western_europe',
    institution: 'democracy',
    taxRate: 0.2,
    education: 0.65,
    religion: 'secular',
    tradeOpenness: 0.65,
    cooperation: 0.55,
    authorityAcceptance: 0.6,
    ambition: 0.45,
    inequality: 0.35,
    traitRate: 0.1,
    welfareRate: 0.21,
    population: 3000,
  },
  asia: {
    subregion: 'eastern_asia',
    institution: 'autocracy',
    taxRate: 0.15,
    education: 0.55,
    religion: 'polytheism',
    tradeOpenness: 0.5,
    cooperation: 0.5,
    authorityAcceptance: 0.65,
    ambition: 0.5,
    inequality: 0.45,
    traitRate: 0.12,
    welfareRate: 0.14,
    population: 4000,
  },
  america: {
    subregion: 'northern_america',
    institution: 'democracy',
    taxRate: 0.1,
    education: 0.6,
    religion: 'monotheism',
    tradeOpenness: 0.55,
    cooperation: 0.5,
    authorityAcceptance: 0.5,
    ambition: 0.6,
    inequality: 0.5,
    traitRate: 0.175,
    welfareRate: 0,
    population: 2500,
  },
  oceania: {
    subregion: 'australasia',
    institution: 'democracy',
    taxRate: 0.1,
    education: 0.5,
    religion: 'folk',
    tradeOpenness: 0.45,
    cooperation: 0.55,
    authorityAcceptance: 0.45,
    ambition: 0.5,
    inequality: 0.4,
    traitRate: 0.085,
    welfareRate: 0.14,
    population: 1500,
  },
}

function mergeDraft(id: ContinentId, patch: Partial<RegionDraft>): RegionDraft {
  return { ...defaultRegionDraft(id), ...REGION_CHARACTER[id], ...patch }
}

function cloneRegions(regions: RegionDraft[]): RegionDraft[] {
  return regions.map((r) => ({ ...r }))
}

function diverseWorld(): RegionDraft[] {
  return CONTINENT_IDS.map((id) => mergeDraft(id, {}))
}

function taxContrast(): RegionDraft[] {
  return CONTINENT_IDS.map((id) => {
    const base = mergeDraft(id, {})
    if (id === 'europe') return { ...base, institution: 'autocracy', taxRate: 0.25, welfareRate: 0.07 }
    if (id === 'america') return { ...base, institution: 'democracy', taxRate: 0.05, ambition: 0.65 }
    if (id === 'asia') return { ...base, taxRate: 0.15 }
    return base
  })
}

function institutionLab(): RegionDraft[] {
  return [
    mergeDraft('africa', { institution: 'anarchy', taxRate: 0.05, welfareRate: 0 }),
    mergeDraft('europe', { institution: 'democracy', taxRate: 0.15, welfareRate: 0.21 }),
    mergeDraft('asia', { institution: 'autocracy', taxRate: 0.2, authorityAcceptance: 0.7 }),
    mergeDraft('america', { institution: 'democracy', taxRate: 0.1, cooperation: 0.6 }),
    mergeDraft('oceania', { institution: 'anarchy', taxRate: 0.08, tradeOpenness: 0.7 }),
  ]
}

function uniformBaseline(): RegionDraft[] {
  return CONTINENT_IDS.map((id) =>
    mergeDraft(id, {
      institution: 'democracy',
      taxRate: 0.1,
      education: 0.5,
      religion: 'folk',
      tradeOpenness: 0.5,
      cooperation: 0.5,
      authorityAcceptance: 0.5,
      ambition: 0.5,
      inequality: 0.5,
      traitRate: 0.1,
      welfareRate: 0,
      population: 1000,
    }),
  )
}

/** 発表向け: 欧州＝高税独裁 vs 米州＝低税民主、他列は多様なまま */
function demoPitch(): RegionDraft[] {
  return CONTINENT_IDS.map((id) => {
    const base = mergeDraft(id, {})
    if (id === 'europe') {
      return {
        ...base,
        institution: 'autocracy',
        taxRate: 0.25,
        authorityAcceptance: 0.55,
        welfareRate: 0.07,
        population: 2000,
      }
    }
    if (id === 'america') {
      return {
        ...base,
        institution: 'democracy',
        taxRate: 0.05,
        ambition: 0.65,
        inequality: 0.55,
        population: 2000,
      }
    }
    return { ...base, population: 1500 }
  })
}

export type ScenarioTemplate = {
  id: ScenarioTemplateId
  startYear: number
  era: 'ad' | 'bc'
  regions: RegionDraft[]
}

export function buildScenarioTemplate(id: ScenarioTemplateId): ScenarioTemplate {
  const builders: Record<ScenarioTemplateId, () => RegionDraft[]> = {
    controlled_experiment: uniformBaseline,
    diverse_world: diverseWorld,
    tax_contrast: taxContrast,
    institution_lab: institutionLab,
    uniform_baseline: uniformBaseline,
    demo_pitch: demoPitch,
  }
  const startYears: Record<ScenarioTemplateId, number> = {
    controlled_experiment: 1000,
    diverse_world: 1000,
    tax_contrast: 1000,
    institution_lab: 800,
    uniform_baseline: 1000,
    demo_pitch: 1000,
  }
  return {
    id,
    startYear: startYears[id],
    era: 'ad',
    regions: cloneRegions(builders[id]()),
  }
}

export function defaultScenarioTemplateId(): ScenarioTemplateId {
  return 'controlled_experiment'
}

export function isControlledExperimentTemplate(id: ScenarioTemplateId): boolean {
  return id === 'controlled_experiment'
}
