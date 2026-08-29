<script setup lang="ts">
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import Slider from 'primevue/slider'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import { polityKind, settlementColor } from '~/utils/groupColors'
import WorldMap2D from '~/components/WorldMap2D.vue'
import SimulationConceptIntro from '~/components/SimulationConceptIntro.vue'
import SimulationMilestoneModal, { type MilestoneSnapshot } from '~/components/SimulationMilestoneModal.vue'
import { buildTurnDigest } from '~/utils/turnDigest'
import {
  ADVANCED_SCENARIO_IDS,
  CUSTOM_PRESET_IDS,
  buildScenarioTemplate,
  defaultScenarioTemplateId,
  isControlledExperimentTemplate,
  type ScenarioMode,
  type ScenarioTemplateId,
} from '~/utils/scenarioTemplates'
import {
  EXPERIMENT_SEED,
  EXPERIMENT_VARIANT_IDS,
  type ExperimentSummary,
  type ExperimentVariantId,
} from '~/utils/experimentWorlds'
import { buildOpeningStory, buildOutcomeArc, buildTurnStory } from '~/utils/storyNarrative'
import {
  buildMilestoneExportText,
  downloadTextFile,
  milestoneExportFilename,
} from '~/utils/milestoneExport'
import { BACKGROUND_ROWS, CONTINENT_IDS, DEFAULT_SUBREGION, macroOf, subregionChoices, type ContinentId, type RegionDraft } from '~/utils/continents'

type Agent = {
  id: string
  name: string
  position: { x: number; y: number }
  wealth: number
  happiness: number
  settlement_id: string | null
  alive: boolean
    traits?: string[]
    personality?: { cooperation: number; aggression: number; ambition: number }
    age?: number
    region_id?: string | null
    subregion_id?: string | null
  }

type Metrics = {
  inequality: number
  mean_trust: number
  cooperation_rate: number
  authority: number
  mean_happiness: number
  world_summary?: string
  reading_source?: string
  regions?: RegionMetrics[]
}

type RegionMetrics = {
  region_id: string
  subregion_id?: string | null
  inequality: number
  mean_trust: number
  cooperation_rate: number
  authority: number
  mean_happiness: number
  tension?: number
  prosperity?: number
  discontent?: number
  cohesion?: number
  rising_archetype?: string
  trajectory?: string
  summary?: string
  reading_source?: string
}

type EventRow = {
  turn: number
  actor_id: string
  action: string
  target_id?: string | null
  detail: string
  detail_key?: string
  success?: boolean | null
  deltas?: Record<string, number>
  lon?: number | null
  lat?: number | null
  alert?: string | null
  extra?: Record<string, string>
}

type Settlement = {
  id: string
  position: { x: number; y: number }
  member_ids: string[]
  shared_wealth?: number
  leader_id?: string | null
  region_id?: string | null
  subregion_id?: string | null
}

type Terrain = {
  cols: number
  rows: number
  biomes: string[]
}

type Simulation = {
  id: string
  status: string
  world: {
    turn: number
    seed: number
    tax_rate: number
    education_level: number
    institution: string
    resource_pool: number
    start_year: number
    geography?: string
    landform?: string
    climate?: string
    disaster_frequency?: number
    religion?: string
    years_per_turn?: number
    regions?: Array<{
      id: string
      subregion_id?: string | null
      institution?: string
      tax_rate?: number
      education_level?: number
      religion?: string
      trade_openness?: number
      trait_rate?: number
      welfare_rate?: number
      initial_values?: {
        cooperation?: number
        authority_acceptance?: number
        ambition?: number
        inequality?: number
      }
    }>
    terrain?: Terrain
    initial_population?: number
    initial_total_wealth?: number
    population_cap?: number
  }
  agents: Agent[]
  settlements?: Settlement[]
  events: EventRow[]
  last_metrics: Metrics | null
  region_readings?: Array<{
    region_id: string
    subregion_id?: string | null
    tension: number
    prosperity: number
    discontent: number
    cohesion: number
    rising_archetype: string
    trajectory: string
    summary: string
    source?: string
  }>
  region_policies?: Array<{
    region_id: string
    subregion_id?: string | null
    action: string
    intensity: number
    reason: string
    source?: string
  }>
  world_summary?: string
  controlled_experiment?: boolean
  experiment_variant?: string
  experiment_seed?: number
  experiment_summary?: ExperimentSummary
}

const AUTO_INTERVAL_MS = 800

const { t, locale, setLocale } = useI18n()

useHead(() => ({
  title: t('brand'),
}))

const conditionsOpen = ref(true)
const conceptOpen = ref(false)
const milestoneOpen = ref(false)
const milestoneYear = ref(0)
const lastAcknowledgedMilestoneYear = ref(0)
type DigestSidebarTab = 'situation' | 'events'
const digestSidebarTab = ref<DigestSidebarTab>('situation')
const selectedDigestRegionId = ref<string | null>(null)

const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

type LlmHealth = {
  provider: string
  ollama_model?: string
  openai_model?: string
  note?: string
  wired?: boolean
  mode?: string
  max_agents_per_turn?: number
  group_sample_per_region?: number
  timeout_sec?: number
}

const llmHealth = ref<LlmHealth | null>(null)
const apiReachable = ref(false)

const llmDecisionWired = computed(() => {
  const h = llmHealth.value
  if (!h) return false
  if (typeof h.wired === 'boolean') return h.wired
  const note = h.note ?? ''
  return !note.toLowerCase().includes('heuristic') && !note.toLowerCase().includes('phase 2')
})

const llmProviderLabel = computed(() => {
  const h = llmHealth.value
  if (!apiReachable.value) return t('llmStatus.unreachable')
  if (!h) return t('llmStatus.unreachable')
  if (h.provider === 'ollama') return t('llmStatus.providerOllama', { model: h.ollama_model || '—' })
  if (h.provider === 'openai') return t('llmStatus.providerOpenai', { model: h.openai_model || '—' })
  if (h.provider === 'stub') return t('llmStatus.providerStub')
  return t('llmStatus.provider', { provider: h.provider })
})

const llmDecisionLabel = computed(() =>
  llmDecisionWired.value ? t('llmStatus.decisionLlm') : t('llmStatus.decisionHeuristic'),
)

async function refreshHealth() {
  try {
    const res = await $fetch<{ ok: boolean; llm?: LlmHealth }>(`${apiBase}/health`)
    apiReachable.value = Boolean(res?.ok)
    llmHealth.value = res.llm ?? null
  } catch {
    apiReachable.value = false
    llmHealth.value = null
  }
}

onMounted(() => {
  applyScenarioTemplate(selectedTemplateId.value)
  void refreshHealth()
})

const sim = ref<Simulation | null>(null)
const busy = ref(false)
const creating = ref(false)
const error = ref('')
const autoPlaying = ref(false)
const autoSpeedX5 = ref(false)
let autoTimer: ReturnType<typeof setInterval> | null = null
let tickInFlight = false

const calendarEra = ref<'bc' | 'ad'>('ad')
const calendarYear = ref(1000)
const conditionStep = ref(1)
const scenarioSetupStep = ref(1)
const conditionsFieldsEl = ref<HTMLElement | null>(null)
const selectedTemplateId = ref<ScenarioTemplateId>(defaultScenarioTemplateId())
const activeExperimentVariant = ref<ExperimentVariantId>('balanced')
const experimentSummaries = ref<Partial<Record<ExperimentVariantId, ExperimentSummary>>>({})
const selectedAgentId = ref<string | null>(null)
const selectedSettlementId = ref<string | null>(null)

const isControlledMode = computed(
  () => sim.value?.controlled_experiment || isControlledExperimentTemplate(selectedTemplateId.value),
)

const isMidrunConditionsEdit = computed(
  () => Boolean(sim.value && sim.value.world.turn > 0),
)

const experimentWorldLabels: Record<ExperimentVariantId, string> = {
  lush: 'experiment.worldLush',
  lean: 'experiment.worldLean',
  volatile: 'experiment.worldVolatile',
  balanced: 'experiment.worldBalanced',
}

const experimentComparisonRows = computed(() =>
  EXPERIMENT_VARIANT_IDS.map((id) => ({
    id,
    summary: experimentSummaries.value[id],
  })).filter((row) => row.summary),
)

const spotlightAgent = computed(() => {
  const id = selectedAgentId.value || sim.value?.experiment_summary?.spotlight_agent_id
  if (!id || !sim.value) return null
  return sim.value.agents.find((a) => a.id === id && a.alive) ?? sim.value.agents.find((a) => a.id === id)
})

const spotlightSettlement = computed(() => {
  const agent = spotlightAgent.value
  if (!agent?.settlement_id || !sim.value?.settlements) return null
  return sim.value.settlements.find((s) => s.id === agent.settlement_id)
})

const spotlightRegionReading = computed(() => {
  const agent = spotlightAgent.value
  if (!agent || !sim.value?.region_readings) return null
  const key = agent.subregion_id || agent.region_id
  return sim.value.region_readings.find((r) => (r.subregion_id || r.region_id) === key)
})

const selectedSettlement = computed(() => {
  const id = selectedSettlementId.value
  if (!id || !sim.value?.settlements) return null
  return sim.value.settlements.find((s) => s.id === id) ?? null
})

const selectedSettlementKind = computed(() => {
  const settlement = selectedSettlement.value
  if (!settlement) return null
  return polityKind(settlement.member_ids.length)
})

const selectedSettlementMembers = computed(() => {
  const settlement = selectedSettlement.value
  if (!settlement || !sim.value) return []
  const ids = new Set(settlement.member_ids)
  return sim.value.agents.filter((a) => a.alive && ids.has(a.id))
})

const selectedSettlementLeader = computed(() => {
  const settlement = selectedSettlement.value
  if (!settlement?.leader_id || !sim.value) return null
  return sim.value.agents.find((a) => a.id === settlement.leader_id) ?? null
})

const selectedSettlementRegionReading = computed(() => {
  const settlement = selectedSettlement.value
  if (!settlement || !sim.value?.region_readings) return null
  const key = settlement.region_id || settlement.subregion_id
  return sim.value.region_readings.find((r) => r.region_id === key || r.subregion_id === key) ?? null
})

const selectedSettlementPolicy = computed(() => {
  const settlement = selectedSettlement.value
  if (!settlement || !sim.value?.region_policies) return null
  const key = settlement.region_id
  return sim.value.region_policies.find((p) => p.region_id === key) ?? null
})

const selectedSettlementTurnEvents = computed(() => {
  const settlement = selectedSettlement.value
  if (!settlement || !sim.value) return []
  const turn = sim.value.world.turn
  return sim.value.events.filter(
    (event) => event.turn === turn && (event.actor_id === settlement.id || event.target_id === settlement.id),
  )
})

const selectedSettlementStats = computed(() => {
  const members = selectedSettlementMembers.value
  if (!members.length) return null
  const n = members.length
  return {
    meanWealth: members.reduce((sum, agent) => sum + agent.wealth, 0) / n,
    meanHappiness: members.reduce((sum, agent) => sum + agent.happiness, 0) / n,
  }
})

const focusedAgent = computed(() => {
  if (!selectedAgentId.value || !sim.value) return null
  return sim.value.agents.find((a) => a.id === selectedAgentId.value) ?? null
})

const digestHasFocus = computed(() => Boolean(selectedSettlementId.value || selectedAgentId.value))

const selectedGroupHeadline = computed(() => {
  const settlement = selectedSettlement.value
  if (!settlement || selectedAgentId.value) return ''
  const kind = t(`map.polity.${polityKind(settlement.member_ids.length)}`)
  const region = settlement.region_id ? digestRegionLabel(settlement.region_id) : ''
  return region
    ? t('digest.groupHeadline', { kind, n: settlement.member_ids.length, region })
    : t('digest.groupHeadlineNoRegion', { kind, n: settlement.member_ids.length })
})

const selectedGroupBody = computed(() => {
  const events = selectedSettlementTurnEvents.value
  if (events.length) {
    const event = events[0]
    let line = actionTypeLabel(event.action)
    if (event.target_id) line += ` → ${actorLabel(event.target_id)}`
    return line
  }
  const policy = selectedSettlementPolicy.value
  if (policy?.reason && !isRawMetricDump(policy.reason)) return policy.reason
  const reading = selectedSettlementRegionReading.value
  if (reading) {
    return digestCausalSummary({
      tension: reading.tension,
      prosperity: reading.prosperity,
      discontent: reading.discontent,
      cohesion: reading.cohesion,
      risingArchetype: reading.rising_archetype,
      trajectory: reading.trajectory,
      summary: reading.summary,
    })
  }
  const leader = selectedSettlementLeader.value
  if (leader) return t('digest.groupLeaderOnly', { name: leader.name })
  return t('digest.groupQuiet')
})

const selectedAgentHeadline = computed(() => {
  const agent = focusedAgent.value
  if (!agent) return ''
  const settlement = selectedSettlement.value
  if (settlement && selectedSettlementKind.value) {
    return t('digest.agentHeadlineWithGroup', {
      name: agent.name,
      kind: t(`map.polity.${selectedSettlementKind.value}`),
      n: settlement.member_ids.length,
    })
  }
  return agent.name
})

const selectedAgentBody = computed(() => {
  const agent = focusedAgent.value
  if (!agent) return ''
  const reading = spotlightRegionReading.value
  if (reading) {
    return digestCausalSummary({
      tension: reading.tension,
      prosperity: reading.prosperity,
      discontent: reading.discontent,
      cohesion: reading.cohesion,
      risingArchetype: reading.rising_archetype,
      trajectory: reading.trajectory,
      summary: reading.summary,
    })
  }
  return t('digest.agentTraits', {
    coop: pctTrait(agent.personality?.cooperation),
    ambit: pctTrait(agent.personality?.ambition),
  })
})

function clearMapSelection() {
  selectedAgentId.value = null
  selectedSettlementId.value = null
}

function pctTrait(value: number | undefined): number {
  return Math.round((Number(value) || 0) * 100)
}

function storeExperimentSummary(summary: ExperimentSummary | undefined) {
  if (!summary?.variant) return
  const id = summary.variant as ExperimentVariantId
  experimentSummaries.value[id] = summary
}

const activeTemplateId = ref<ScenarioTemplateId>(defaultScenarioTemplateId())
const scenarioMode = ref<ScenarioMode>('experiment')
const showAdvancedScenarios = ref(false)
const digestStoryOpen = ref(false)
const regionDrafts = ref<RegionDraft[]>(buildScenarioTemplate(defaultScenarioTemplateId()).regions)

const advancedTemplateOptions = computed(() =>
  ADVANCED_SCENARIO_IDS.map((id) => ({
    label: t(`templates.${id}.name`),
    value: id,
  })),
)

function setScenarioMode(mode: ScenarioMode) {
  if (isMidrunConditionsEdit.value) return
  scenarioMode.value = mode
  if (mode === 'experiment') {
    applyScenarioTemplate('controlled_experiment')
    return
  }
  if (isControlledExperimentTemplate(selectedTemplateId.value)) {
    applyScenarioTemplate('diverse_world')
  }
  conditionStep.value = 1
}

function applyScenarioTemplate(id: ScenarioTemplateId) {
  if (isMidrunConditionsEdit.value) return
  selectedTemplateId.value = id
  conditionStep.value = 1
  const tpl = buildScenarioTemplate(id)
  regionDrafts.value = tpl.regions.map((region) => ({ ...region }))
  calendarEra.value = tpl.era
  calendarYear.value = tpl.startYear
  if (id === 'controlled_experiment') {
    scenarioMode.value = 'experiment'
  } else {
    scenarioMode.value = 'custom'
  }
}

function syncRegionDraftsFromSimRegions() {
  const regions = sim.value?.world.regions
  if (!regions?.length) return
  regionDrafts.value = regions.map((region) => {
    const id = region.id as ContinentId
    const iv = region.initial_values ?? {}
    const existing = regionDrafts.value.find((row) => row.id === id)
    return {
      id,
      subregion: region.subregion_id ?? DEFAULT_SUBREGION[id],
      institution: region.institution ?? 'democracy',
      taxRate: region.tax_rate ?? 0.1,
      education: region.education_level ?? 0.5,
      religion: region.religion ?? 'folk',
      tradeOpenness: region.trade_openness ?? 0.5,
      cooperation: iv.cooperation ?? existing?.cooperation ?? 0.5,
      authorityAcceptance: iv.authority_acceptance ?? existing?.authorityAcceptance ?? 0.5,
      ambition: iv.ambition ?? existing?.ambition ?? 0.5,
      inequality: iv.inequality ?? existing?.inequality ?? 0.5,
      traitRate: region.trait_rate ?? 0.1,
      welfareRate: region.welfare_rate ?? 0,
      population: existing?.population ?? 1000,
    }
  })
}

function regionConditionsPayload() {
  return regionDrafts.value.map((region) => ({
    id: region.id,
    institution: region.institution,
    tax_rate: region.taxRate,
    education_level: region.education,
    religion: region.religion,
    trade_openness: region.tradeOpenness,
    welfare_rate: region.welfareRate,
    trait_rate: region.traitRate,
  }))
}

function syncConditionsFromSim() {
  if (!sim.value) return
  conditionStep.value = 1
  if (sim.value.controlled_experiment) {
    scenarioMode.value = 'experiment'
    activeExperimentVariant.value = (sim.value.experiment_variant || 'balanced') as ExperimentVariantId
    activeTemplateId.value = 'controlled_experiment'
  } else {
    scenarioMode.value = 'custom'
  }
  syncRegionDraftsFromSimRegions()
}

function scrollConditionsToTop() {
  nextTick(() => {
    conditionsFieldsEl.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function goToScenarioSetupStep(step: 1 | 2) {
  scenarioSetupStep.value = step
  if (step === 2) conditionStep.value = 1
  scrollConditionsToTop()
}

function handleCustomWizardBack() {
  if (conditionStep.value > 1) {
    conditionStep.value -= 1
    scrollConditionsToTop()
    return
  }
  goToScenarioSetupStep(1)
}

function toggleConditionsModal() {
  if (conditionsOpen.value) {
    conditionsOpen.value = false
    return
  }
  if (isMidrunConditionsEdit.value) {
    syncConditionsFromSim()
  } else {
    scenarioSetupStep.value = 1
    conditionStep.value = 1
  }
  conditionsOpen.value = true
}

function storyRegionsFromDrafts(): Array<{
  id: string
  subregion_id?: string | null
  institution?: string
  tax_rate?: number
  religion?: string
}> {
  return regionDrafts.value.map((region) => ({
    id: region.id,
    subregion_id: region.subregion,
    institution: region.institution,
    tax_rate: region.taxRate,
    religion: region.religion,
  }))
}

function subregionOptions(id: ContinentId) {
  return subregionChoices(id).map((sid) => ({ label: t(`subregions.${sid}`), value: sid }))
}

const institutionOptions = computed(() => [
  { label: t('institutions.democracy'), value: 'democracy' },
  { label: t('institutions.autocracy'), value: 'autocracy' },
  { label: t('institutions.anarchy'), value: 'anarchy' },
])

const religionOptions = computed(() => [
  { label: t('religions.folk'), value: 'folk' },
  { label: t('religions.polytheism'), value: 'polytheism' },
  { label: t('religions.monotheism'), value: 'monotheism' },
  { label: t('religions.secular'), value: 'secular' },
])

const levelLabels = computed(() => [
  t('wizard.levels.veryLow'),
  t('wizard.levels.low'),
  t('wizard.levels.mid'),
  t('wizard.levels.high'),
  t('wizard.levels.veryHigh'),
])
const welfareLabels = computed(() => [
  t('wizard.welfare.none'),
  t('wizard.welfare.thin'),
  t('wizard.welfare.mid'),
  t('wizard.welfare.thick'),
  t('wizard.welfare.high'),
])
const LEVEL_STEPS = [0.2, 0.35, 0.5, 0.65, 0.8]
const TAX_STEPS = [0.05, 0.1, 0.15, 0.2, 0.25]
const NOTABLE_STEPS = [0.04, 0.085, 0.13, 0.175, 0.22]
const WELFARE_STEPS = [0, 0.07, 0.14, 0.21, 0.28]
const COLUMN_POP_MIN = 1000
const COLUMN_POP_MAX = 10000

const mapSeed = computed(() => sim.value?.world.seed ?? 0)

const calendarEraOptions = computed(() => [
  { label: t('calendarEra.bc'), value: 'bc' as const },
  { label: t('calendarEra.ad'), value: 'ad' as const },
])

const MAX_CALENDAR_YEAR = 2500
const BC_YEAR_MAX = 50000

const calendarYearMin = computed(() => (calendarEra.value === 'ad' ? 0 : 1))
const calendarYearMax = computed(() => (calendarEra.value === 'ad' ? MAX_CALENDAR_YEAR : BC_YEAR_MAX))

watch(calendarEra, (era) => {
  if (era === 'bc' && calendarYear.value < 1) calendarYear.value = 1
  if (era === 'ad' && calendarYear.value > MAX_CALENDAR_YEAR) calendarYear.value = MAX_CALENDAR_YEAR
})

watch(calendarYear, (year) => {
  if (year == null) return
  const max = calendarYearMax.value
  if (year > max) calendarYear.value = max
})

const step2Axes = [
  { key: 'institution' },
  { key: 'taxRate' },
  { key: 'education' },
  { key: 'religion' },
  { key: 'trade' },
  { key: 'cooperation' },
  { key: 'ambition' },
  { key: 'inequality' },
] as const

const midrunPolicyAxes = [
  { key: 'institution' },
  { key: 'taxRate' },
  { key: 'education' },
  { key: 'religion' },
  { key: 'trade' },
  { key: 'welfare' },
  { key: 'notable' },
] as const

function midrunPolicyAxisLabel(key: (typeof midrunPolicyAxes)[number]['key']): string {
  if (key === 'notable') return t('wizard.notable')
  if (key === 'welfare') return t('wizard.welfare.label')
  return step2AxisLabel(key as (typeof step2Axes)[number]['key'])
}

function step2AxisLabel(key: (typeof step2Axes)[number]['key']): string {
  if (key === 'trade') return t('wizard.trade')
  if (key === 'taxRate') return t('taxRate')
  if (key === 'education') return t('education')
  if (key === 'religion') return t('religion')
  if (key === 'cooperation') return t('cooperation')
  if (key === 'ambition') return t('ambition')
  if (key === 'inequality') return t('inequality')
  return t('institution')
}

const step3Axes = [
  { key: 'notable' },
  { key: 'welfare' },
  { key: 'columnPop' },
] as const

function step3AxisLabel(key: (typeof step3Axes)[number]['key']): string {
  if (key === 'notable') return t('wizard.notable')
  if (key === 'welfare') return t('wizard.welfare.label')
  return t('wizard.columnPop')
}

function step3AxisHint(key: (typeof step3Axes)[number]['key']): string {
  if (key === 'notable') return t('wizard.notableHint')
  if (key === 'welfare') return t('wizard.welfareHint')
  return t('wizard.columnPopHint')
}

const HEADLINE_RANK: Record<string, number> = {
  historic_quake: 12,
  disaster_earthquake: 11,
  disaster_typhoon: 10,
  epidemic: 9,
  regime_shift: 8,
  group_conflict_out: 7,
  group_conflict_in: 6,
  disaster_flood: 5,
  weather_storm: 5,
  disaster_heatwave: 4,
  weather_heat: 4,
  disaster_frost: 3,
  weather_blizzard: 3,
  weather_drought: 3,
}

const draftAstroYear = computed(() => toAstronomicalYear(calendarEra.value, calendarYear.value))

const currentAstroYear = computed(() => {
  if (!sim.value) return draftAstroYear.value
  const start = sim.value.world.start_year ?? draftAstroYear.value
  const years = sim.value.world.years_per_turn ?? 10
  return start + sim.value.world.turn * years
})

const atYearCap = computed(() => currentAstroYear.value >= MAX_CALENDAR_YEAR)

function turnsUntilYearCap(): number {
  if (!sim.value) return 0
  const years = Math.max(1, sim.value.world.years_per_turn ?? 10)
  const start = sim.value.world.start_year ?? draftAstroYear.value
  const maxTurn = Math.floor((MAX_CALENDAR_YEAR - start) / years)
  return Math.max(0, maxTurn - sim.value.world.turn)
}

function formatYearLabel(astro: number): string {
  const { era, year } = fromAstronomicalYear(astro)
  return t(`yearLabel.${era}`, { year })
}

function japanEraName(astro: number): string {
  const periodLabel = t(`eras.japan.${japanPeriodKey(astro)}`)
  return formatJapanEraLabel(astro, periodLabel, locale.value)
}

function worldEraName(astro: number): string {
  return t(`eras.world.${worldPeriodKey(astro)}`)
}

const draftYearLabel = computed(() => formatYearLabel(draftAstroYear.value))
const draftJapanEra = computed(() => japanEraName(draftAstroYear.value))
const draftWorldEra = computed(() => worldEraName(draftAstroYear.value))

const liveYearLabel = computed(() => formatYearLabel(currentAstroYear.value))
const liveJapanEra = computed(() => japanEraName(currentAstroYear.value))
const liveWorldEra = computed(() => worldEraName(currentAstroYear.value))

const aliveCount = computed(() => (sim.value?.agents ?? []).filter((a) => a.alive).length)
const totalAgents = computed(() => sim.value?.agents.length ?? 0)
const initialPopulation = computed(
  () => sim.value?.world.initial_population ?? 1000,
)
const populationCap = computed(() => sim.value?.world.population_cap ?? 10000)
const populationDelta = computed(() => aliveCount.value - initialPopulation.value)
const settlementCount = computed(() => sim.value?.settlements?.length ?? 0)
const polityCounts = computed(() => {
  let band = 0
  let city = 0
  let nation = 0
  for (const settlement of sim.value?.settlements ?? []) {
    if (settlement.member_ids.length < 2) continue
    const kind = polityKind(settlement.member_ids.length)
    if (kind === 'nation') nation += 1
    else if (kind === 'city') city += 1
    else band += 1
  }
  return { band, city, nation, groups: band + city + nation }
})
const loneCount = computed(() =>
  (sim.value?.agents ?? []).filter((a) => a.alive && !a.settlement_id).length,
)
const turnActionCounts = computed(() => {
  const turn = sim.value?.world.turn
  const events = (sim.value?.events ?? []).filter((e) => e.turn === turn)
  return {
    conflict: events.filter((e) => e.action === 'conflict').length,
    cooperate: events.filter((e) => e.action === 'cooperate').length,
  }
})
const notableCount = computed(
  () => (sim.value?.agents ?? []).filter((a) => a.alive && (a.traits?.length ?? 0) > 0).length,
)

const turnOnlyLabel = computed(() => {
  if (!sim.value) return ''
  return t('turnLabel', { turn: sim.value.world.turn })
})

const turnDigest = computed(() => buildTurnDigest(sim.value))

const sortedRegionObservations = computed(() => {
  const rows = turnDigest.value?.regionObservations ?? []
  const order = new Map(CONTINENT_IDS.map((id, idx) => [id, idx]))
  return [...rows].sort(
    (a, b) => (order.get(a.regionId as ContinentId) ?? 99) - (order.get(b.regionId as ContinentId) ?? 99),
  )
})

const selectedDigestRegionRow = computed(() => {
  const rows = sortedRegionObservations.value
  if (!rows.length) return null
  const id = selectedDigestRegionId.value
  return rows.find((row) => row.regionId === id) ?? rows[0]
})

const selectedDigestRegionIndex = computed(() => {
  const rows = sortedRegionObservations.value
  const id = selectedDigestRegionId.value ?? rows[0]?.regionId
  const idx = rows.findIndex((row) => row.regionId === id)
  return idx >= 0 ? idx : 0
})

const regionSlideTransition = ref('region-slide-left')
const regionChipPickerRef = ref<HTMLElement | null>(null)
let regionSwipeStartX: number | null = null

function shiftDigestRegion(delta: -1 | 1) {
  const rows = sortedRegionObservations.value
  if (rows.length <= 1) return
  const next = (selectedDigestRegionIndex.value + delta + rows.length) % rows.length
  regionSlideTransition.value = delta > 0 ? 'region-slide-left' : 'region-slide-right'
  selectedDigestRegionId.value = rows[next].regionId
}

function selectDigestRegion(regionId: string) {
  const rows = sortedRegionObservations.value
  const nextIdx = rows.findIndex((row) => row.regionId === regionId)
  if (nextIdx < 0) return
  const currentIdx = selectedDigestRegionIndex.value
  if (nextIdx !== currentIdx) {
    regionSlideTransition.value = nextIdx > currentIdx ? 'region-slide-left' : 'region-slide-right'
  }
  selectedDigestRegionId.value = regionId
}

function onRegionSwipeStart(event: TouchEvent) {
  regionSwipeStartX = event.touches[0]?.clientX ?? null
}

function onRegionSwipeEnd(event: TouchEvent) {
  if (regionSwipeStartX == null) return
  const endX = event.changedTouches[0]?.clientX ?? regionSwipeStartX
  const deltaX = endX - regionSwipeStartX
  regionSwipeStartX = null
  if (Math.abs(deltaX) < 48) return
  shiftDigestRegion(deltaX < 0 ? 1 : -1)
}

function scrollActiveRegionChipIntoView() {
  nextTick(() => {
    const picker = regionChipPickerRef.value
    if (!picker) return
    const active = picker.querySelector('.digest-region-chip.active')
    active?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
  })
}

watch(selectedDigestRegionId, scrollActiveRegionChipIntoView)

watch(
  () => sortedRegionObservations.value.map((row) => row.regionId).join(','),
  () => {
    const rows = sortedRegionObservations.value
    if (!rows.length) {
      selectedDigestRegionId.value = null
      return
    }
    const ids = rows.map((row) => row.regionId)
    if (selectedDigestRegionId.value && ids.includes(selectedDigestRegionId.value)) return
    const hottest = [...rows].sort((a, b) => b.tension - a.tension)[0]
    selectedDigestRegionId.value = hottest?.regionId ?? rows[0].regionId
  },
  { immediate: true },
)

const openingStory = computed(() => {
  const regions = sim.value?.world.regions?.length
    ? sim.value.world.regions.map((region) => ({
        id: region.id,
        subregion_id: region.subregion_id,
        institution: region.institution,
        tax_rate: region.tax_rate,
        religion: region.religion,
      }))
    : storyRegionsFromDrafts()
  const year = sim.value?.world.start_year ?? draftAstroYear.value
  return buildOpeningStory(regions, activeTemplateId.value, year, t)
})

const turnStory = computed(() => {
  const digest = turnDigest.value
  if (!digest) return null
  const regions =
    sim.value?.world.regions?.map((region) => ({
      id: region.id,
      subregion_id: region.subregion_id,
      institution: region.institution,
      tax_rate: region.tax_rate,
      religion: region.religion,
    })) ?? storyRegionsFromDrafts()
  return buildTurnStory(digest, regions, t)
})

const outcomeArc = computed(() => {
  const digest = turnDigest.value
  if (!digest) return ''
  return buildOutcomeArc(digest, t)
})

const experimentSetup = computed(() => {
  const regions = sim.value?.world.regions ?? []
  if (!regions.length) return ''
  return regions
    .map((region) =>
      t('digest.regionSetup', {
        region: t(`geographies.${region.id}`),
        sub: region.subregion_id ? t(`subregions.${region.subregion_id}`) : '—',
        institution: t(`institutions.${region.institution}`),
        tax: Math.round((region.tax_rate ?? 0) * 100),
      }),
    )
    .join(t('digest.setupSep'))
})

const digestOneLiner = computed(() => {
  const digest = turnDigest.value
  if (!digest) return ''
  const { turn, totals } = digest
  const hasActivity =
    totals.conflicts + totals.cooperations + totals.births + totals.deaths + totals.disasters + totals.regimeShifts > 0
  const key = hasActivity ? 'digest.oneLiner' : 'digest.oneLinerQuiet'
  return t(key, { turn, ...totals })
})

const digestWorldLine = computed(() => {
  const digest = turnDigest.value
  if (!digest) return ''
  const raw = digest.worldSummary?.trim() || ''
  if (raw && isUsableWorldSummary(raw)) {
    return raw
  }
  const ranked = [...digest.regionObservations].sort(
    (a, b) => b.discontent + b.tension - (a.discontent + a.tension),
  )
  const top = ranked.slice(0, 2).filter((row) => row.population > 0 || row.summary)
  if (!top.length) return ''
  return top
    .map((row) => `${digestRegionLabel(row.regionId)}: ${digestCausalSummary(row)}`)
    .join(' · ')
})

function digestRegionLabel(id: string): string {
  const key = `geographies.${id}`
  const label = t(key)
  return label === key ? id : label
}

function digestRegionShortLabel(id: string): string {
  const key = `digest.regionShort.${id}`
  const label = t(key)
  return label === key ? digestRegionLabel(id).slice(0, 2) : label
}

function digestRegionColor(id: string): string {
  return settlementColor(id)
}

function pct(value: number): string {
  return `${Math.round((Number(value) || 0) * 100)}%`
}

function digestArchetypeLabel(key: string): string {
  const path = `digest.archetypes.${key}`
  const translated = t(path)
  return translated === path ? key : translated
}

function digestTrajectoryLabel(key: string): string {
  const path = `digest.trajectories.${key}`
  const translated = t(path)
  return translated === path ? key : translated
}

function isRawMetricDump(summary: string): boolean {
  return /tension\s*=|prosperity\s*=|→\s*\w+\/\w+|tax=|shocks=/.test(summary)
}

function hasJapanese(text: string): boolean {
  return /[\u3040-\u30ff\u3400-\u9fff]/.test(text)
}

function isUsableWorldSummary(raw: string): boolean {
  if (isRawMetricDump(raw)) return false
  if (/^(LLM read|Heuristic|Group LLM steered|集団LLM|ヒューリスティック)/i.test(raw)) return false
  if (locale.value === 'ja') return hasJapanese(raw)
  return true
}

function isUsableNarrativeSummary(summary: string): boolean {
  if (!summary || summary.startsWith('{') || isRawMetricDump(summary)) return false
  if (/^(high discontent|stable mood|scarce resources|resource slack)/i.test(summary)) return false
  if (/^[a-z]+:\s*(stagnation|war|industry|reform|exodus|faith)\b/i.test(summary)) return false
  if (/trajectory\s+\w+/i.test(summary)) return false
  if (/→\s*\w+\s+rising/i.test(summary)) return false
  if (locale.value === 'ja') return hasJapanese(summary)
  return true
}

function digestPrimarySignal(row: {
  tension: number
  prosperity: number
  discontent: number
  cohesion: number
}): string {
  const ranked: Array<[string, number]> = [
    ['highDiscontent', row.discontent],
    ['highTension', row.tension],
    ['highProsperity', row.prosperity],
    ['lowCohesion', 1 - row.cohesion],
  ]
  ranked.sort((a, b) => b[1] - a[1])
  const [key, score] = ranked[0]
  if (score < 0.45) {
    if (row.prosperity >= 0.55) return t('digest.signal.highProsperity')
    if (row.cohesion >= 0.55) return t('digest.signal.highCohesion')
    return t('digest.signal.lowTension')
  }
  return t(`digest.signal.${key}`)
}

function digestCausalSummary(row: {
  tension: number
  prosperity: number
  discontent: number
  cohesion: number
  risingArchetype: string
  trajectory: string
  summary: string
}): string {
  if (isUsableNarrativeSummary(row.summary)) {
    return row.summary
  }
  return [
    digestPrimarySignal(row),
    digestTrajectoryLabel(row.trajectory),
    digestArchetypeLabel(row.risingArchetype),
  ].join(' → ')
}

function meterTone(kind: 'tension' | 'prosperity' | 'discontent' | 'cohesion', value: number): string {
  if (kind === 'tension' || kind === 'discontent') {
    if (value >= 0.65) return 'hot'
    if (value >= 0.4) return 'warm'
    return 'cool'
  }
  if (value >= 0.65) return 'good'
  if (value >= 0.4) return 'warm'
  return 'dim'
}

function actorLabel(actorId: string): string {
  if (actorId === 'world') return t('events.world')
  if (actorId === 'lone') return t('events.lone')
  const subKey = `subregions.${actorId}`
  const sub = t(subKey)
  if (sub !== subKey) return sub
  const macro = macroOf(actorId)
  if (macro) return t(`geographies.${macro}`)
  if (actorId.startsWith('s')) {
    const settlement = sim.value?.settlements?.find((s) => s.id === actorId)
    if (settlement) {
      const kind = polityKind(settlement.member_ids.length)
      return `${t(`map.polity.${kind}`)} · ${settlement.member_ids.length}`
    }
    return actorId
  }
  const agent = sim.value?.agents.find((a) => a.id === actorId)
  return agent?.name ?? actorId
}

function actionTypeLabel(action: string): string {
  const key = `actionTypes.${action}` as const
  const translated = t(key)
  return translated === key ? action : translated
}

function eventGroupId(actorId: string): string | null {
  if (!actorId || actorId === 'world' || actorId === 'lone') return null
  const macro = macroOf(actorId)
  if (macro) return macro
  if (actorId.startsWith('s')) return actorId
  const agent = sim.value?.agents.find((a) => a.id === actorId)
  return agent?.region_id ?? agent?.settlement_id ?? null
}

function isGroupId(id: string | null | undefined): boolean {
  return !id || id === 'world' || id === 'lone' || id.startsWith('s') || Boolean(macroOf(id))
}

function eventActorColor(actorId: string): string {
  return settlementColor(eventGroupId(actorId))
}

function actionLabel(action: string): string {
  const key = `actionTypes.${action}`
  const translated = t(key)
  return translated === key ? action : translated
}

function inferDetailKey(row: EventRow): string {
  if (row.detail_key) return row.detail_key
  if (row.action === 'cooperate') return row.success ? 'cooperate_success' : 'cooperate_failed'
  if (row.action === 'conflict') return row.success ? 'conflict_win' : 'conflict_lose'
  if (row.action === 'migrate') return 'migrate'
  if (row.action === 'obey') return 'obey'
  if (row.action === 'resist') return 'resist'
  if (row.action === 'birth') return 'birth'
  if (row.action === 'death') return 'death'
  if (row.action === 'lead') return row.target_id ? 'lead_takeover' : 'lead_new'
  if (row.action === 'trait') return row.success ? 'trait_gain_charisma' : 'trait_lose_charisma'
  return 'wait'
}

function isHeadlineEvent(row: EventRow): boolean {
  const key = inferDetailKey(row)
  if (key in HEADLINE_RANK) return true
  return row.action === 'regime' || row.action === 'disaster'
}

function headlineText(row: EventRow): string {
  const key = inferDetailKey(row)
  const group = actorLabel(row.actor_id)
  const other = row.target_id ? actorLabel(row.target_id) : ''
  const from = row.extra?.from ? t(`institutions.${row.extra.from}`) : ''
  const to = row.extra?.to ? t(`institutions.${row.extra.to}`) : ''
  const map: Record<string, string> = {
    epidemic: t('headlines.epidemic', { group }),
    regime_shift: t('headlines.revolution', { group, from, to }),
    group_conflict_out: t('headlines.warOut', { group, other }),
    group_conflict_in: t('headlines.warIn', { group }),
    disaster_typhoon: t('headlines.typhoon', { group }),
    disaster_earthquake: t('headlines.quake', { group }),
    historic_quake: t('headlines.quake', { group }),
    disaster_flood: t('headlines.flood', { group }),
    disaster_heatwave: t('headlines.heat', { group }),
    weather_heat: t('headlines.heat', { group }),
    disaster_frost: t('headlines.frost', { group }),
    weather_blizzard: t('headlines.frost', { group }),
    weather_drought: t('headlines.drought', { group }),
    weather_storm: t('headlines.storm', { group }),
  }
  return map[key] || t('headlines.disaster', { group })
}

const headerHeadline = computed(() => {
  const rows = (sim.value?.events ?? []).filter(isHeadlineEvent)
  if (!rows.length) return null
  const latestTurn = rows[rows.length - 1].turn
  const sameTurn = rows.filter((row) => row.turn === latestTurn)
  sameTurn.sort((a, b) => (HEADLINE_RANK[inferDetailKey(b)] ?? 1) - (HEADLINE_RANK[inferDetailKey(a)] ?? 1))
  const picked = sameTurn.slice(0, 2)
  const texts = [...new Set(picked.map(headlineText))]
  return {
    text: texts.join(' · '),
    alert: picked.some((row) => row.alert === 'red') ? 'red' : 'yellow',
  }
})

function notableEventText(ref: { key: string; actorId: string; targetId?: string | null; extra?: Record<string, string> }): string {
  return headlineText({
    turn: sim.value?.world.turn ?? 0,
    actor_id: ref.actorId,
    action: ref.key.startsWith('group_') ? 'conflict' : ref.key === 'regime_shift' ? 'regime' : 'disaster',
    target_id: ref.targetId,
    detail_key: ref.key,
    detail: '',
    extra: ref.extra,
  })
}

const feedEvents = computed(() => {
  const events = sim.value?.events ?? []
  if (!events.length) return [] as Array<{ turn: number; text: string; alert?: string | null }>
  const turns = [...new Set(events.map((e) => e.turn))].sort((a, b) => b - a)
  const picked: Array<{ turn: number; text: string; alert?: string | null }> = []
  for (const turn of turns) {
    if (picked.length >= 20) break
    const turnEvents = events.filter((e) => e.turn === turn)
    const headlines = turnEvents.filter(isHeadlineEvent)
    if (headlines.length) {
      headlines.sort(
        (a, b) => (HEADLINE_RANK[inferDetailKey(b)] ?? 0) - (HEADLINE_RANK[inferDetailKey(a)] ?? 0),
      )
      const seen = new Set<string>()
      for (const row of headlines.slice(0, 2)) {
        const key = inferDetailKey(row)
        if (seen.has(key)) continue
        seen.add(key)
        picked.push({ turn, text: headlineText(row), alert: row.alert })
      }
      continue
    }
    const births = turnEvents.filter((e) => e.action === 'birth').length
    const deaths = turnEvents.filter((e) => e.action === 'death').length
    const conflicts = turnEvents.filter((e) => e.action === 'conflict').length
    const coops = turnEvents.filter((e) => e.action === 'cooperate').length
    if (births + deaths + conflicts + coops > 0) {
      picked.push({
        turn,
        text: t('events.turnSummary', { births, deaths, conflicts, coops }),
      })
    }
  }
  return picked
})

const experimentEmergenceLine = computed(() => {
  const summary = sim.value?.experiment_summary
  if (!summary?.spotlight_agent_id) return ''
  const agent = sim.value?.agents.find((a) => a.id === summary.spotlight_agent_id)
  const name = agent?.name || summary.spotlight_agent_id
  const role = summary.spotlight_role ? digestArchetypeLabel(summary.spotlight_role) : t('digest.archetypes.none')
  return t('experiment.emergenceLine', { name, role, id: summary.spotlight_agent_id })
})

function eventDetail(row: EventRow): string {
  if (row.action === 'observe') {
    return row.extra?.reason || row.detail || t('eventDetails.world_reading')
  }
  const key = `eventDetails.${inferDetailKey(row)}`
  const personId = isGroupId(row.target_id) ? row.actor_id : (row.target_id || row.actor_id)
  const name = locale.value === 'ja' ? (row.extra?.name_ja || row.extra?.name_en || '') : (row.extra?.name_en || row.extra?.name_ja || '')
  const translated = t(key, {
    group: actorLabel(row.actor_id),
    other: row.target_id ? actorLabel(row.target_id) : '',
    n: row.deltas?.n != null ? String(Math.round(row.deltas.n)) : '',
    actor: actorLabel(personId),
    target: row.target_id ? actorLabel(row.target_id) : '',
    child: row.target_id ? actorLabel(row.target_id) : '',
    x: row.deltas?.x != null ? row.deltas.x.toFixed(0) : '',
    y: row.deltas?.y != null ? row.deltas.y.toFixed(0) : '',
    tax: row.deltas?.tax != null ? row.deltas.tax.toFixed(1) : '',
    stolen: row.deltas?.stolen != null ? row.deltas.stolen.toFixed(1) : '',
    age: row.deltas?.age != null ? String(Math.round(row.deltas.age)) : '',
    heir: row.target_id ? actorLabel(row.target_id) : '',
    name,
    mag: row.extra?.mag_label || (row.deltas?.magnitude != null ? String(row.deltas.magnitude) : ''),
    year: row.extra?.year || '',
    from: row.extra?.from ? t(`institutions.${row.extra.from}`) : '',
    to: row.extra?.to ? t(`institutions.${row.extra.to}`) : '',
  })
  return translated === key ? row.detail : translated
}

function onSelectAgent(agentId: string) {
  selectedAgentId.value = agentId
  const settlementId = sim.value?.agents.find((a) => a.id === agentId)?.settlement_id ?? null
  selectedSettlementId.value = settlementId
  focusDigestRegionFromSettlement(settlementId)
  digestStoryOpen.value = false
}

function onSelectSettlement(settlementId: string) {
  selectedSettlementId.value = settlementId
  selectedAgentId.value = null
  focusDigestRegionFromSettlement(settlementId)
  digestStoryOpen.value = false
}

function focusDigestRegionFromSettlement(settlementId: string | null | undefined) {
  if (!settlementId || !sim.value?.settlements) return
  const settlement = sim.value.settlements.find((s) => s.id === settlementId)
  const regionId = settlement?.region_id
  if (!regionId) return
  selectDigestRegion(macroOf(regionId) ?? regionId)
}

async function switchExperimentWorld(variant: ExperimentVariantId) {
  if (busy.value || creating.value) return
  activeExperimentVariant.value = variant
  await createControlledWorld(variant)
}

async function onLocaleChange(code: string) {
  if (!code || code === locale.value) return
  await setLocale(code)
}

async function api<T>(path: string, options?: Parameters<typeof $fetch<T>>[1]): Promise<T> {
  return await $fetch<T>(`${apiBase}${path}`, options)
}

function formatApiError(e: unknown): string {
  const err = e as { statusCode?: number; status?: number; message?: string; data?: { detail?: string } }
  const status = err.statusCode ?? err.status
  if (status === 404) return t('errors.simLost')
  if (err.data?.detail) return String(err.data.detail)
  if (e instanceof Error && e.message) return e.message
  return String(e)
}

function cumulativeActionCounts(): { conflicts: number; cooperations: number } {
  const events = sim.value?.events ?? []
  return {
    conflicts: events.filter((e) => e.action === 'conflict').length,
    cooperations: events.filter((e) => e.action === 'cooperate').length,
  }
}

function findCrossedMilestoneYear(beforeTurn: number, afterTurn: number): number | null {
  if (!sim.value) return null
  const start = sim.value.world.start_year ?? draftAstroYear.value
  const years = sim.value.world.years_per_turn ?? 10
  const beforeYear = start + beforeTurn * years
  const afterYear = start + afterTurn * years
  let latest: number | null = null
  for (let y = Math.ceil(beforeYear / 100) * 100; y <= afterYear; y += 100) {
    if (y > beforeYear && y <= afterYear && y > start && y > lastAcknowledgedMilestoneYear.value) {
      latest = y
    }
  }
  return latest
}

function maybeShowMilestone(beforeTurn: number) {
  if (!sim.value || milestoneOpen.value) return
  const crossed = findCrossedMilestoneYear(beforeTurn, sim.value.world.turn)
  if (crossed == null) return
  stopAutoPlay()
  milestoneYear.value = crossed
  milestoneOpen.value = true
}

const milestoneSnapshot = computed((): MilestoneSnapshot | null => {
  if (!sim.value || !milestoneOpen.value) return null
  const summary = sim.value.experiment_summary
  const actions = cumulativeActionCounts()
  const metrics = sim.value.last_metrics
  const archetypeKey = summary?.dominant_archetype
  const astro = milestoneYear.value || currentAstroYear.value
  return {
    yearLabel: formatYearLabel(astro),
    japanEra: japanEraName(astro),
    worldEra: worldEraName(astro),
    turn: sim.value.world.turn,
    headline: turnStory.value?.headline || digestOneLiner.value,
    summary: outcomeArc.value || digestWorldLine.value,
    population: summary?.population_alive ?? aliveCount.value,
    populationDelta: populationDelta.value,
    settlements: settlementCount.value,
    conflicts: summary?.conflicts_total ?? actions.conflicts,
    cooperations: summary?.cooperations_total ?? actions.cooperations,
    inequality: metrics?.inequality,
    trust: metrics?.mean_trust,
    happiness: metrics?.mean_happiness,
    dominantArchetype:
      archetypeKey && archetypeKey !== 'none' ? digestArchetypeLabel(archetypeKey) : undefined,
  }
})

function resetMilestoneState() {
  lastAcknowledgedMilestoneYear.value = 0
  milestoneOpen.value = false
  milestoneYear.value = 0
}

function continueFromMilestone() {
  lastAcknowledgedMilestoneYear.value = milestoneYear.value
  milestoneOpen.value = false
  void startAutoPlay()
}

function changeConditionsFromMilestone() {
  lastAcknowledgedMilestoneYear.value = milestoneYear.value
  milestoneOpen.value = false
  syncConditionsFromSim()
  conditionsOpen.value = true
}

function exportMilestoneReport() {
  if (!sim.value || !milestoneSnapshot.value) return
  const formatters = {
    formatYearLabel,
    actionLabel,
    actorLabel,
    eventDetail,
    isHeadlineEvent,
    headlineText,
    archetypeLabel: digestArchetypeLabel,
    trajectoryLabel: digestTrajectoryLabel,
    regionLabel: digestRegionLabel,
    institutionLabel: (key: string) => {
      const path = `institutions.${key}`
      const translated = t(path)
      return translated === path ? key : translated
    },
    variantLabel: (variant: string) => {
      const key = experimentWorldLabels[variant as ExperimentVariantId]
      return key ? t(key) : variant
    },
  }
  const text = buildMilestoneExportText(
    sim.value,
    milestoneYear.value,
    milestoneSnapshot.value,
    formatters,
  )
  downloadTextFile(milestoneExportFilename(sim.value, milestoneYear.value), text)
}

function stopAutoPlay() {
  autoPlaying.value = false
  if (autoTimer != null) {
    clearInterval(autoTimer)
    autoTimer = null
  }
}

async function applySimulationConditions() {
  if (!sim.value) return
  stopAutoPlay()
  busy.value = true
  error.value = ''
  try {
    const regions = regionConditionsPayload()
    const body = sim.value.controlled_experiment
      ? {
          experiment_variant: activeExperimentVariant.value,
          regions,
        }
      : { regions }
    sim.value = await api<Simulation>(`/simulations/${sim.value.id}/conditions`, {
      method: 'PATCH',
      body,
    })
    storeExperimentSummary(sim.value.experiment_summary)
    conditionsOpen.value = false
  } catch (e: unknown) {
    error.value = formatApiError(e)
  } finally {
    busy.value = false
  }
}

async function createControlledWorld(variant: ExperimentVariantId) {
  stopAutoPlay()
  resetMilestoneState()
  busy.value = true
  creating.value = true
  error.value = ''
  selectedAgentId.value = null
  selectedSettlementId.value = null
  try {
    const result = await api<Simulation>('/simulations', {
      method: 'POST',
      body: {
        start_year: draftAstroYear.value,
        geography: 'world',
        controlled_experiment: true,
        experiment_variant: variant,
        experiment_seed: EXPERIMENT_SEED,
      },
    })
    sim.value = result
    storeExperimentSummary(result.experiment_summary)
    activeExperimentVariant.value = variant
    activeTemplateId.value = 'controlled_experiment'
    if (result.experiment_summary?.spotlight_agent_id) {
      selectedAgentId.value = result.experiment_summary.spotlight_agent_id
    }
    conditionsOpen.value = false
    await startAutoPlay()
  } catch (e: unknown) {
    error.value = formatApiError(e)
  } finally {
    busy.value = false
    creating.value = false
  }
}

async function createSimulation() {
  if (isControlledExperimentTemplate(selectedTemplateId.value)) {
    await createControlledWorld(activeExperimentVariant.value)
    return
  }
  stopAutoPlay()
  resetMilestoneState()
  busy.value = true
  creating.value = true
  error.value = ''
  selectedAgentId.value = null
  selectedSettlementId.value = null
  try {
    sim.value = await api<Simulation>('/simulations', {
      method: 'POST',
      body: {
        start_year: draftAstroYear.value,
        geography: 'world',
        regions: regionDrafts.value.map((region) => ({
          id: region.id,
          subregion: region.subregion,
          population: region.population,
          institution: region.institution,
          tax_rate: region.taxRate,
          education_level: region.education,
          religion: region.religion,
          trade_openness: region.tradeOpenness,
          trait_rate: region.traitRate,
          welfare_rate: region.welfareRate,
          initial_values: {
            cooperation: region.cooperation,
            authority_acceptance: region.authorityAcceptance,
            ambition: region.ambition,
            inequality: region.inequality,
          },
        })),
      },
    })
    activeTemplateId.value = selectedTemplateId.value
    conditionsOpen.value = false
    await startAutoPlay()
  } catch (e: unknown) {
    error.value = formatApiError(e)
  } finally {
    busy.value = false
    creating.value = false
  }
}

async function tick(n = 1, opts?: { silent?: boolean }) {
  if (!sim.value || tickInFlight) return
  const remaining = turnsUntilYearCap()
  if (remaining <= 0) {
    stopAutoPlay()
    return
  }
  n = Math.min(n, remaining)
  tickInFlight = true
  // Always show progress — group LLM can take many seconds per turn.
  busy.value = true
  if (!opts?.silent) error.value = ''
  const beforeTurn = sim.value.world.turn
  try {
    sim.value = await api<Simulation>(`/simulations/${sim.value.id}/tick`, {
      method: 'POST',
      body: { n },
    })
    storeExperimentSummary(sim.value.experiment_summary)
    maybeShowMilestone(beforeTurn)
    if (turnsUntilYearCap() <= 0) stopAutoPlay()
  } catch (e: unknown) {
    const err = e as { statusCode?: number; status?: number }
    const status = err.statusCode ?? err.status
    error.value = formatApiError(e)
    stopAutoPlay()
    if (status === 404) {
      sim.value = null
      scenarioSetupStep.value = 1
      conditionStep.value = 1
      conditionsOpen.value = true
    }
  } finally {
    tickInFlight = false
    busy.value = false
  }
}

function autoTickCount(): number {
  return autoSpeedX5.value ? 5 : 1
}

async function startAutoPlay() {
  if (!sim.value || atYearCap.value || milestoneOpen.value) return
  autoPlaying.value = true
  await tick(autoTickCount(), { silent: true })
  if (!autoPlaying.value || milestoneOpen.value) return
  autoTimer = setInterval(() => {
    if (!sim.value || !autoPlaying.value || milestoneOpen.value) return
    void tick(autoTickCount(), { silent: true })
  }, AUTO_INTERVAL_MS)
}

async function toggleAutoPlay() {
  if (autoPlaying.value) {
    stopAutoPlay()
    return
  }
  await startAutoPlay()
}

onBeforeUnmount(() => {
  stopAutoPlay()
})
</script>

<template>
  <div class="layout">
    <div class="lang" role="group" :aria-label="t('language')">
      <button
        type="button"
        class="lang-btn"
        :class="{ active: locale === 'ja' }"
        :aria-pressed="locale === 'ja'"
        @click="onLocaleChange('ja')"
      >
        JA
      </button>
      <span class="lang-sep" aria-hidden="true">/</span>
      <button
        type="button"
        class="lang-btn"
        :class="{ active: locale === 'en' }"
        :aria-pressed="locale === 'en'"
        @click="onLocaleChange('en')"
      >
        EN
      </button>
    </div>
    <header class="header">
      <div class="header-top">
        <div class="header-left">
          <p class="eyebrow">{{ t('brand') }}</p>
          <h1 :title="t('consoleTitle')">{{ t('consoleTitle') }}</h1>
          <p class="llm-status" :title="llmHealth?.note || undefined">
            <span>{{ llmDecisionLabel }}</span>
            <span class="header-era-sep" aria-hidden="true">·</span>
            <span>{{ llmProviderLabel }}</span>
          </p>
          <p v-if="error" class="header-error" role="alert">{{ error }}</p>
        </div>
        <p
          class="header-headline"
          :class="headerHeadline?.alert"
          :title="headerHeadline?.text || undefined"
          aria-live="polite"
        >{{ headerHeadline?.text || '' }}</p>
        <div class="header-controls">
          <Button
            :label="conditionsOpen ? t('layout.hideConditions') : t('layout.showConditions')"
            icon="pi pi-sliders-h"
            class="header-btn"
            :severity="conditionsOpen ? 'info' : 'secondary'"
            @click="toggleConditionsModal"
          />
          <Button
            :label="t('actions.speedX5')"
            icon="pi pi-forward"
            class="header-btn"
            :disabled="!sim"
            :severity="autoSpeedX5 ? 'help' : 'secondary'"
            :aria-pressed="autoSpeedX5"
            @click="autoSpeedX5 = !autoSpeedX5"
          />
          <Button
            :label="autoPlaying ? t('actions.autoStop') : t('actions.autoPlay')"
            :icon="autoPlaying ? 'pi pi-stop' : 'pi pi-play'"
            class="header-btn"
            :disabled="!sim || milestoneOpen || (!autoPlaying && atYearCap)"
            :severity="autoPlaying ? 'danger' : 'secondary'"
            @click="toggleAutoPlay"
          />
        </div>
        <div class="header-meta">
          <div v-if="isControlledMode && sim" class="experiment-worlds" role="group" :aria-label="t('experiment.worldsTitle')">
            <span class="experiment-worlds-label">{{ t('experiment.worldsTitle') }}</span>
            <button
              v-for="variant in EXPERIMENT_VARIANT_IDS"
              :key="variant"
              type="button"
              class="experiment-world-btn"
              :class="{ active: activeExperimentVariant === variant }"
              :disabled="busy || creating"
              @click="switchExperimentWorld(variant)"
            >
              {{ t(experimentWorldLabels[variant]) }}
            </button>
          </div>
          <div v-if="sim && !creating" class="header-turn-row">
            <span
              class="tick-status"
              :class="{ 'tick-status--hidden': !busy }"
              role="status"
              aria-live="polite"
              :aria-hidden="!busy"
            >{{ t('actions.ticking') }}</span>
          </div>
        </div>
      </div>
      <div v-if="sim" class="header-era" aria-live="polite">
        <div class="header-era-row">
          <span class="era-banner-year">{{ liveYearLabel }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('eraPreview.japan') }}</span>{{ liveJapanEra }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('eraPreview.world') }}</span>{{ liveWorldEra }}</span>
        </div>
        <div class="header-era-row">
          <span><span class="era-k">{{ t('headerStats.groups') }}</span>{{ polityCounts.groups }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('headerStats.cities') }}</span>{{ polityCounts.city }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('headerStats.nations') }}</span>{{ polityCounts.nation }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('headerStats.lone') }}</span>{{ loneCount }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('headerStats.clashes') }}</span>{{ turnActionCounts.conflict }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('headerStats.coops') }}</span>{{ turnActionCounts.cooperate }}</span>
          <span class="header-era-sep" aria-hidden="true">·</span>
          <span><span class="era-k">{{ t('headerStats.notables') }}</span>{{ notableCount }}</span>
        </div>
      </div>
    </header>

    <div class="grid" :class="{ 'grid-with-digest': sim && turnDigest }">
      <aside
        v-if="sim && turnDigest"
        class="digest-sidebar panel"
        :aria-label="t('digest.title')"
      >
        <div class="panel-heading events-heading digest-heading">
          <h2>{{ t('digest.title') }}</h2>
          <Tag v-if="sim" :value="turnOnlyLabel" severity="secondary" />
        </div>
        <p class="digest-one-liner">{{ turnStory?.headline || digestOneLiner }}</p>
        <div class="digest-tabs" role="tablist" :aria-label="t('digest.title')">
          <button
            type="button"
            role="tab"
            class="digest-tab"
            :class="{ active: digestSidebarTab === 'situation' }"
            :aria-selected="digestSidebarTab === 'situation'"
            @click="digestSidebarTab = 'situation'"
          >
            {{ t('digest.tabSituation') }}
          </button>
          <button
            type="button"
            role="tab"
            class="digest-tab"
            :class="{ active: digestSidebarTab === 'events' }"
            :aria-selected="digestSidebarTab === 'events'"
            @click="digestSidebarTab = 'events'"
          >
            {{ t('digest.tabEvents') }}
            <span v-if="feedEvents.length" class="digest-tab-badge">{{ feedEvents.length }}</span>
          </button>
        </div>
        <div class="digest-body">
          <div v-show="digestSidebarTab === 'situation'" class="digest-tab-panel">
              <p v-if="isControlledMode && experimentEmergenceLine" class="digest-emergence">{{ experimentEmergenceLine }}</p>

              <section v-if="digestHasFocus" class="digest-focus-card">
                <div class="digest-focus-head">
                  <span class="digest-focus-label">
                    {{ selectedAgentId ? t('digest.focusAgent') : t('digest.focusGroup') }}
                  </span>
                  <button type="button" class="digest-focus-clear" @click="clearMapSelection">
                    {{ t('digest.clearFocus') }}
                  </button>
                </div>
                <p v-if="selectedAgentId" class="digest-focus-title">{{ selectedAgentHeadline }}</p>
                <p v-else class="digest-focus-title">{{ selectedGroupHeadline }}</p>
                <p class="digest-focus-body">
                  {{ selectedAgentId ? selectedAgentBody : selectedGroupBody }}
                </p>
              </section>

              <p v-else-if="digestWorldLine" class="digest-notable-line digest-world-brief">{{ digestWorldLine }}</p>

              <button type="button" class="digest-collapse-btn digest-story-btn" @click="digestStoryOpen = !digestStoryOpen">
                {{ t('digest.storyToggle') }}
                <span aria-hidden="true">{{ digestStoryOpen ? '−' : '+' }}</span>
              </button>

              <div v-if="digestStoryOpen" class="digest-story-block">
                <section v-if="turnStory?.paragraphs.length" class="digest-section digest-section-story">
                  <h3>{{ t('digest.storyTitle') }}</h3>
                  <p v-for="(para, idx) in turnStory.paragraphs" :key="idx" class="digest-story-p">{{ para }}</p>
                </section>
                <section v-if="openingStory && turnDigest.turn <= 1" class="digest-section digest-section-opening">
                  <h3>{{ t('digest.openingTitle') }}</h3>
                  <p class="digest-opening-text">{{ openingStory }}</p>
                </section>
                <section v-if="outcomeArc && turnDigest.turn > 1" class="digest-section digest-section-outcome">
                  <h3>{{ t('digest.outcomeTitle') }}</h3>
                  <p class="digest-outcome-text">{{ outcomeArc }}</p>
                </section>
                <section v-if="turnDigest.notableEvents.length" class="digest-section digest-section-notable">
                  <h3>{{ t('digest.notableTitle') }}</h3>
                  <p class="digest-notable-line">
                    {{ turnDigest.notableEvents.slice(0, 3).map((item) => notableEventText(item)).join(' · ') }}
                  </p>
                </section>
              </div>

              <section class="digest-section digest-section-obs">
                <h3>
                  {{ t('digest.societyTitle') }}
                  <span class="digest-obs-source">{{ turnDigest.readingSource === 'llm' ? t('digest.obsLlm') : t('digest.obsHeuristic') }}</span>
                </h3>
                <div
                  ref="regionChipPickerRef"
                  class="digest-region-picker"
                  role="tablist"
                  :aria-label="t('digest.regionPickerLabel')"
                >
                  <button
                    v-for="row in sortedRegionObservations"
                    :key="row.regionId"
                    type="button"
                    role="tab"
                    class="digest-region-chip"
                    :class="{ active: selectedDigestRegionRow?.regionId === row.regionId }"
                    :aria-selected="selectedDigestRegionRow?.regionId === row.regionId"
                    :style="{ '--region-color': digestRegionColor(row.regionId) }"
                    @click="selectDigestRegion(row.regionId)"
                  >
                    <span class="digest-region-chip-dot" aria-hidden="true" />
                    <span class="digest-region-chip-text">
                      <span class="digest-region-chip-name">{{ digestRegionShortLabel(row.regionId) }}</span>
                      <span class="digest-region-chip-sub">{{ digestTrajectoryLabel(row.trajectory) }}</span>
                    </span>
                  </button>
                </div>
                <div v-if="selectedDigestRegionRow" class="digest-region-slider">
                  <div class="digest-region-slider-nav">
                    <button
                      type="button"
                      class="digest-region-slider-btn"
                      :disabled="sortedRegionObservations.length <= 1"
                      :aria-label="t('digest.regionPrev')"
                      @click="shiftDigestRegion(-1)"
                    >
                      ‹
                    </button>
                    <span class="digest-region-slider-pos">
                      {{ t('digest.regionPosition', {
                        current: selectedDigestRegionIndex + 1,
                        total: sortedRegionObservations.length,
                      }) }}
                    </span>
                    <button
                      type="button"
                      class="digest-region-slider-btn"
                      :disabled="sortedRegionObservations.length <= 1"
                      :aria-label="t('digest.regionNext')"
                      @click="shiftDigestRegion(1)"
                    >
                      ›
                    </button>
                  </div>
                  <div
                    class="digest-region-slider-stage"
                    @touchstart.passive="onRegionSwipeStart"
                    @touchend="onRegionSwipeEnd"
                  >
                    <Transition :name="regionSlideTransition" mode="out-in">
                      <article
                        :key="selectedDigestRegionRow.regionId"
                        class="digest-region-card"
                      >
                        <header class="digest-region-head">
                          <strong :style="{ color: digestRegionColor(selectedDigestRegionRow.regionId) }">{{ digestRegionLabel(selectedDigestRegionRow.regionId) }}</strong>
                          <span class="digest-region-pop">{{ t('digest.meterPop', { n: selectedDigestRegionRow.population }) }}</span>
                        </header>
                        <div class="digest-flow" :aria-label="t('digest.causalTitle')">
                          <span class="digest-flow-chip signal">{{ digestPrimarySignal(selectedDigestRegionRow) }}</span>
                          <span class="digest-flow-arrow" aria-hidden="true">→</span>
                          <span class="digest-flow-chip trajectory" :data-traj="selectedDigestRegionRow.trajectory">{{ digestTrajectoryLabel(selectedDigestRegionRow.trajectory) }}</span>
                          <span class="digest-flow-arrow" aria-hidden="true">→</span>
                          <span class="digest-flow-chip archetype">{{ digestArchetypeLabel(selectedDigestRegionRow.risingArchetype) }}</span>
                        </div>
                        <ul class="digest-meters">
                          <li>
                            <span>{{ t('digest.colTension') }}</span>
                            <div class="digest-meter-track"><i class="digest-meter-fill" :class="meterTone('tension', selectedDigestRegionRow.tension)" :style="{ width: pct(selectedDigestRegionRow.tension) }" /></div>
                            <em>{{ pct(selectedDigestRegionRow.tension) }}</em>
                          </li>
                          <li>
                            <span>{{ t('digest.colProsperity') }}</span>
                            <div class="digest-meter-track"><i class="digest-meter-fill" :class="meterTone('prosperity', selectedDigestRegionRow.prosperity)" :style="{ width: pct(selectedDigestRegionRow.prosperity) }" /></div>
                            <em>{{ pct(selectedDigestRegionRow.prosperity) }}</em>
                          </li>
                          <li>
                            <span>{{ t('digest.colDiscontent') }}</span>
                            <div class="digest-meter-track"><i class="digest-meter-fill" :class="meterTone('discontent', selectedDigestRegionRow.discontent)" :style="{ width: pct(selectedDigestRegionRow.discontent) }" /></div>
                            <em>{{ pct(selectedDigestRegionRow.discontent) }}</em>
                          </li>
                          <li>
                            <span>{{ t('digest.colCohesion') }}</span>
                            <div class="digest-meter-track"><i class="digest-meter-fill" :class="meterTone('cohesion', selectedDigestRegionRow.cohesion)" :style="{ width: pct(selectedDigestRegionRow.cohesion) }" /></div>
                            <em>{{ pct(selectedDigestRegionRow.cohesion) }}</em>
                          </li>
                        </ul>
                        <p v-if="digestCausalSummary(selectedDigestRegionRow)" class="digest-region-summary">{{ digestCausalSummary(selectedDigestRegionRow) }}</p>
                      </article>
                    </Transition>
                  </div>
                </div>
              </section>
          </div>

          <div v-show="digestSidebarTab === 'events'" class="digest-tab-panel digest-tab-panel-events">
            <p v-if="!feedEvents.length" class="hint">{{ t('events.empty') }}</p>
            <ol v-else class="event-feed-simple">
              <li
                v-for="(item, idx) in feedEvents"
                :key="`${item.turn}-${idx}`"
                class="event-feed-item"
                :class="{ 'event-alert-red': item.alert === 'red', 'event-alert-yellow': item.alert === 'yellow' }"
              >
                <span class="event-turn-label">{{ t('events.turnLabel', { turn: item.turn }) }}</span>
                <span class="event-text">{{ item.text }}</span>
              </li>
            </ol>
          </div>
            </div>
      </aside>

      <main class="viewport panel">
        <div class="panel-heading">
          <div class="map-heading">
            <h2>{{ t('map.title') }}</h2>
          </div>
          <p v-if="sim" class="map-stats">
            {{ t('map.population', {
              alive: aliveCount,
              initial: initialPopulation,
              cap: populationCap,
              delta: populationDelta > 0 ? `+${populationDelta}` : String(populationDelta),
            }) }}
            ·
            {{ t('map.settlements', { count: settlementCount }) }}
            ·
            {{ t('map.resources', { value: sim.world.resource_pool.toFixed(1) }) }}
            ·
            {{ t('map.fiveContinents') }}
          </p>
        </div>
        <p class="hint map-legend">{{ t('map.legend') }} {{ t('map.zoomHintFlat') }}</p>
        <div class="map-stage">
          <WorldMap2D
            :sim="sim"
            geography="world"
            :seed="mapSeed"
            :selected-settlement-id="selectedSettlementId"
            @select-agent="onSelectAgent"
            @select-settlement="onSelectSettlement"
          />
        </div>
      </main>
    </div>

    <div v-if="conceptOpen" class="modal-backdrop" @click="conceptOpen = false" />
    <aside
      v-if="conceptOpen"
      class="concept-modal panel"
      role="dialog"
      aria-modal="true"
      :aria-label="t('concept.modalTitle')"
    >
      <div class="panel-heading events-heading">
        <h2>{{ t('concept.modalTitle') }}</h2>
        <button type="button" class="events-close" :aria-label="t('layout.closeConcept')" @click="conceptOpen = false">×</button>
      </div>
      <div class="concept-body">
        <SimulationConceptIntro />
      </div>
    </aside>

    <SimulationMilestoneModal
      :open="milestoneOpen"
      :snapshot="milestoneSnapshot"
      :busy="busy"
      @continue="continueFromMilestone"
      @change-conditions="changeConditionsFromMilestone"
      @export="exportMilestoneReport"
    />

    <div v-if="conditionsOpen" class="modal-backdrop" @click="!creating && (conditionsOpen = false)" />
    <aside
      v-if="conditionsOpen"
      class="conditions-modal panel"
      role="dialog"
      aria-modal="true"
      :aria-label="t('initialConditions')"
    >
      <div class="panel-heading events-heading">
        <h2>{{ isMidrunConditionsEdit ? t('scenario.midrunTitle') : t('scenario.modalTitle') }}</h2>
        <button type="button" class="events-close" :aria-label="t('layout.closeConditions')" :disabled="creating" @click="conditionsOpen = false">×</button>
      </div>
      <div class="conditions-form">
        <div ref="conditionsFieldsEl" class="conditions-fields">
          <template v-if="isMidrunConditionsEdit">
            <p class="conditions-midrun-lead">{{ t('scenario.midrunLead') }}</p>
            <section v-if="scenarioMode === 'experiment'" class="conditions-section scenario-worlds-section">
              <p class="conditions-lead">{{ t('scenario.experimentPickWorld') }}</p>
              <div class="world-card-grid">
                <button
                  v-for="variant in EXPERIMENT_VARIANT_IDS"
                  :key="variant"
                  type="button"
                  class="world-card"
                  :class="{ active: activeExperimentVariant === variant }"
                  :disabled="creating"
                  @click="activeExperimentVariant = variant"
                >
                  <strong>{{ t(experimentWorldLabels[variant]) }}</strong>
                  <span>{{ t(`experiment.worldDesc.${variant}`) }}</span>
                </button>
              </div>
              <p class="hint scenario-fixed-hint">{{ t('scenario.experimentMidrunHint') }}</p>
            </section>
            <section class="conditions-section conditions-midrun-policy">
              <p class="conditions-lead">{{ t('scenario.midrunSocialLead') }}</p>
              <DataTable :value="midrunPolicyAxes" class="conditions-dt">
                <Column :header="t('wizard.axis')" class="dt-axis">
                  <template #body="{ data }">
                    <span class="axis-label">
                      {{ midrunPolicyAxisLabel(data.key) }}
                      <i
                        v-if="data.key === 'institution'"
                        v-tooltip.right="t('institutionHint')"
                        class="pi pi-info-circle axis-info"
                        tabindex="0"
                      />
                    </span>
                  </template>
                </Column>
                <Column v-for="region in regionDrafts" :key="region.id">
                  <template #header>
                    <div class="col-head">
                      <span>{{ t(`geographies.${region.id}`) }}</span>
                      <span class="col-sub">{{ t(`subregions.${region.subregion}`) }}</span>
                    </div>
                  </template>
                  <template #body="{ data }">
                    <Dropdown
                      v-if="data.key === 'institution'"
                      v-model="region.institution"
                      :options="institutionOptions"
                      option-label="label"
                      option-value="value"
                      class="field-control"
                    />
                    <LevelRating
                      v-else-if="data.key === 'taxRate'"
                      v-model="region.taxRate"
                      :steps="TAX_STEPS"
                      :labels="levelLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'education'"
                      v-model="region.education"
                      :steps="LEVEL_STEPS"
                      :labels="levelLabels"
                    />
                    <Dropdown
                      v-else-if="data.key === 'religion'"
                      v-model="region.religion"
                      :options="religionOptions"
                      option-label="label"
                      option-value="value"
                      class="field-control"
                    />
                    <LevelRating
                      v-else-if="data.key === 'trade'"
                      v-model="region.tradeOpenness"
                      :steps="LEVEL_STEPS"
                      :labels="levelLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'welfare'"
                      v-model="region.welfareRate"
                      :steps="WELFARE_STEPS"
                      :labels="welfareLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'notable'"
                      v-model="region.traitRate"
                      :steps="NOTABLE_STEPS"
                      :labels="levelLabels"
                    />
                  </template>
                </Column>
              </DataTable>
            </section>
          </template>

          <template v-else-if="scenarioSetupStep === 1">
            <SimulationConceptIntro compact />
            <section class="scenario-mode-picker">
              <p class="setup-step-label">{{ t('scenario.step1Label') }}</p>
              <p class="scenario-mode-lead">{{ t('scenario.pickMode') }}</p>
              <div class="scenario-mode-cards">
                <button
                  type="button"
                  class="scenario-mode-card"
                  :class="{ active: scenarioMode === 'experiment' }"
                  :disabled="creating"
                  @click="setScenarioMode('experiment')"
                >
                  <strong>{{ t('scenario.modeExperiment') }}</strong>
                  <span>{{ t('scenario.modeExperimentDesc') }}</span>
                </button>
                <button
                  type="button"
                  class="scenario-mode-card"
                  :class="{ active: scenarioMode === 'custom' }"
                  :disabled="creating"
                  @click="setScenarioMode('custom')"
                >
                  <strong>{{ t('scenario.modeCustom') }}</strong>
                  <span>{{ t('scenario.modeCustomDesc') }}</span>
                </button>
              </div>
            </section>
          </template>

          <template v-else>
            <p class="setup-step-label">
              {{ scenarioMode === 'experiment' ? t('scenario.step2LabelExperiment') : t('scenario.step2LabelCustom') }}
            </p>

            <section v-if="scenarioMode === 'experiment'" class="conditions-section scenario-worlds-section">
              <p class="conditions-lead">{{ t('scenario.experimentPickWorld') }}</p>
              <div class="world-card-grid">
                <button
                  v-for="variant in EXPERIMENT_VARIANT_IDS"
                  :key="variant"
                  type="button"
                  class="world-card"
                  :class="{ active: activeExperimentVariant === variant }"
                  :disabled="creating"
                  @click="activeExperimentVariant = variant"
                >
                  <strong>{{ t(experimentWorldLabels[variant]) }}</strong>
                  <span>{{ t(`experiment.worldDesc.${variant}`) }}</span>
                </button>
              </div>
              <p class="hint scenario-fixed-hint">{{ t('scenario.experimentFixed') }}</p>
            </section>

            <template v-else>
              <section class="custom-preset-picker">
                <p class="conditions-lead">{{ t('scenario.customLead') }}</p>
                <div class="custom-preset-cards">
                  <button
                    v-for="presetId in CUSTOM_PRESET_IDS"
                    :key="presetId"
                    type="button"
                    class="custom-preset-card"
                    :class="{ active: selectedTemplateId === presetId }"
                    :disabled="creating"
                    @click="applyScenarioTemplate(presetId)"
                  >
                    <strong>{{ t(`templates.${presetId}.name`) }}</strong>
                    <span>{{ t(`templates.${presetId}.blurb`) }}</span>
                  </button>
                </div>
                <button
                  type="button"
                  class="advanced-toggle"
                  @click="showAdvancedScenarios = !showAdvancedScenarios"
                >
                  {{ showAdvancedScenarios ? t('scenario.hideAdvanced') : t('scenario.showAdvanced') }}
                </button>
                <div v-if="showAdvancedScenarios" class="advanced-template-row">
                  <Dropdown
                    input-id="scenario-template-advanced"
                    :model-value="selectedTemplateId"
                    :options="advancedTemplateOptions"
                    option-label="label"
                    option-value="value"
                    class="template-select field-control"
                    :disabled="creating"
                    @update:model-value="applyScenarioTemplate($event as ScenarioTemplateId)"
                  />
                </div>
              </section>

              <nav class="step-nav" aria-label="steps">
                <button type="button" class="step-tab" :class="{ active: conditionStep === 1 }" @click="conditionStep = 1; scrollConditionsToTop()">{{ t('wizard.stepSocial') }}</button>
                <button type="button" class="step-tab" :class="{ active: conditionStep === 2 }" @click="conditionStep = 2; scrollConditionsToTop()">{{ t('wizard.stepPop') }}</button>
              </nav>
              <p class="conditions-lead">{{ conditionStep === 1 ? t('wizard.leadSocial') : t('wizard.leadPop') }}</p>

              <section v-if="conditionStep === 1" class="conditions-section">
                <DataTable :value="step2Axes" class="conditions-dt">
                <Column :header="t('wizard.axis')" class="dt-axis">
                  <template #body="{ data }">
                    <span class="axis-label">
                      {{ step2AxisLabel(data.key) }}
                      <i
                        v-if="data.key === 'institution'"
                        v-tooltip.right="t('institutionHint')"
                        class="pi pi-info-circle axis-info"
                        tabindex="0"
                      />
                    </span>
                  </template>
                </Column>
                <Column v-for="region in regionDrafts" :key="region.id">
                  <template #header>
                    <div class="col-head">
                      <span>{{ t(`geographies.${region.id}`) }}</span>
                      <span class="col-sub">{{ t(`subregions.${region.subregion}`) }}</span>
                    </div>
                  </template>
                  <template #body="{ data }">
                    <Dropdown
                      v-if="data.key === 'institution'"
                      v-model="region.institution"
                      :options="institutionOptions"
                      option-label="label"
                      option-value="value"
                      class="field-control"
                    />
                    <LevelRating
                      v-else-if="data.key === 'taxRate'"
                      v-model="region.taxRate"
                      :steps="TAX_STEPS"
                      :labels="levelLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'education'"
                      v-model="region.education"
                      :steps="LEVEL_STEPS"
                      :labels="levelLabels"
                    />
                    <Dropdown
                      v-else-if="data.key === 'religion'"
                      v-model="region.religion"
                      :options="religionOptions"
                      option-label="label"
                      option-value="value"
                      class="field-control"
                    />
                    <LevelRating
                      v-else-if="data.key === 'trade'"
                      v-model="region.tradeOpenness"
                      :steps="LEVEL_STEPS"
                      :labels="levelLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'cooperation'"
                      v-model="region.cooperation"
                      :steps="LEVEL_STEPS"
                      :labels="levelLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'ambition'"
                      v-model="region.ambition"
                      :steps="LEVEL_STEPS"
                      :labels="levelLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'inequality'"
                      v-model="region.inequality"
                      :steps="LEVEL_STEPS"
                      :labels="levelLabels"
                    />
                  </template>
                </Column>
              </DataTable>
              <div class="year-block">
                <div class="conditions-field year-field">
                  <label>{{ t('calendarYear') }}</label>
                  <div class="year-row">
                    <Dropdown
                      v-model="calendarEra"
                      :options="calendarEraOptions"
                      option-label="label"
                      option-value="value"
                      class="era-select"
                    />
                    <InputNumber
                      v-model="calendarYear"
                      :min="calendarYearMin"
                      :max="calendarYearMax"
                      :step="100"
                      show-buttons
                      class="year-input"
                    />
                  </div>
                </div>
                <div class="era-preview" aria-live="polite">
                  <span class="era-preview-title">{{ t('eraPreview.title') }}</span>
                  <span class="era-banner-year">{{ draftYearLabel }}</span>
                  <span class="header-era-sep" aria-hidden="true">·</span>
                  <span><span class="era-k">{{ t('eraPreview.japan') }}</span>{{ draftJapanEra }}</span>
                  <span class="header-era-sep" aria-hidden="true">·</span>
                  <span><span class="era-k">{{ t('eraPreview.world') }}</span>{{ draftWorldEra }}</span>
                </div>
                <p class="hint year-hint">{{ t('calendarYearHint') }}</p>
              </div>
                <details class="geo-details">
                  <summary>{{ t('wizard.geoDetails') }}</summary>
                  <div class="bg-table" role="table">
                    <div class="bg-row bg-head" role="row">
                      <div class="bg-stub" role="columnheader">{{ t('wizard.axis') }}</div>
                      <div v-for="region in regionDrafts" :key="`${region.id}-h1`" class="bg-cell col-head" role="columnheader">
                        <span>{{ t(`geographies.${region.id}`) }}</span>
                        <span class="col-sub">{{ t(`subregions.${region.subregion}`) }}</span>
                      </div>
                    </div>
                    <div class="bg-row bg-form" role="row">
                      <div class="bg-stub" role="rowheader">{{ t('wizard.rows.subregion') }}</div>
                      <div v-for="region in regionDrafts" :key="`${region.id}-sub`" class="bg-cell" role="cell">
                        <Dropdown v-model="region.subregion" :options="subregionOptions(region.id)" option-label="label" option-value="value" class="field-control" />
                      </div>
                    </div>
                    <div class="bg-row" role="row">
                      <div class="bg-stub" role="rowheader">{{ t('wizard.rows.focus') }}</div>
                      <div v-for="region in regionDrafts" :key="`${region.id}-focus`" class="bg-cell bg-focus" role="cell">{{ t(`wizard.blurbs.${region.subregion}`) }}</div>
                    </div>
                    <div v-for="row in BACKGROUND_ROWS" :key="row" class="bg-row" role="row">
                      <div class="bg-stub" role="rowheader">{{ t(`wizard.rows.${row}`) }}</div>
                      <div v-for="region in regionDrafts" :key="`${region.id}-${row}`" class="bg-cell" role="cell">{{ t(`wizard.table.${region.subregion}.${row}`) }}</div>
                    </div>
                  </div>
                </details>
              </section>

              <section v-else class="conditions-section">
                <DataTable :value="step3Axes" class="conditions-dt">
                <Column :header="t('wizard.axis')" class="dt-axis">
                  <template #body="{ data }">
                    <span class="axis-label">
                      {{ step3AxisLabel(data.key) }}
                      <i v-tooltip.right="step3AxisHint(data.key)" class="pi pi-info-circle axis-info" tabindex="0" />
                    </span>
                  </template>
                </Column>
                <Column v-for="region in regionDrafts" :key="region.id">
                  <template #header>
                    <div class="col-head">
                      <span>{{ t(`geographies.${region.id}`) }}</span>
                      <span class="col-sub">{{ t(`subregions.${region.subregion}`) }}</span>
                    </div>
                  </template>
                  <template #body="{ data }">
                    <LevelRating
                      v-if="data.key === 'notable'"
                      v-model="region.traitRate"
                      :steps="NOTABLE_STEPS"
                      :labels="levelLabels"
                    />
                    <LevelRating
                      v-else-if="data.key === 'welfare'"
                      v-model="region.welfareRate"
                      :steps="WELFARE_STEPS"
                      :labels="welfareLabels"
                    />
                    <div v-else class="pop-slider">
                      <Slider
                        v-model="region.population"
                        :min="COLUMN_POP_MIN"
                        :max="COLUMN_POP_MAX"
                        :step="100"
                      />
                      <span class="pop-slider-value">{{ t('wizard.columnPopCount', { n: region.population }) }}</span>
                    </div>
                  </template>
                </Column>
              </DataTable>
              </section>
            </template>
          </template>
          <p v-if="error" class="error">{{ error }}</p>
        </div>
        <div class="conditions-footer step-footer">
          <template v-if="isMidrunConditionsEdit">
            <Button
              :label="t('actions.applyConditions')"
              icon="pi pi-check"
              class="action-btn"
              :loading="busy"
              :disabled="creating"
              @click="applySimulationConditions"
            />
          </template>
          <template v-else-if="scenarioSetupStep === 1">
            <Button
              :label="t('wizard.next')"
              class="action-btn"
              :disabled="creating"
              @click="goToScenarioSetupStep(2)"
            />
          </template>
          <template v-else-if="scenarioMode === 'experiment'">
            <Button
              :label="t('wizard.back')"
              class="action-btn"
              severity="secondary"
              :disabled="creating"
              @click="goToScenarioSetupStep(1)"
            />
            <Button
              :label="t('actions.create')"
              icon="pi pi-plus"
              class="action-btn"
              :loading="busy && !autoPlaying"
              :disabled="creating"
              @click="createControlledWorld(activeExperimentVariant)"
            />
          </template>
          <template v-else>
            <Button
              :label="t('wizard.back')"
              class="action-btn"
              severity="secondary"
              :disabled="creating"
              @click="handleCustomWizardBack"
            />
            <Button
              v-if="conditionStep < 2"
              :label="t('wizard.next')"
              class="action-btn"
              :disabled="creating"
              @click="conditionStep += 1; scrollConditionsToTop()"
            />
            <Button
              v-else
              :label="t('actions.create')"
              icon="pi pi-plus"
              class="action-btn"
              :loading="busy && !autoPlaying"
              :disabled="creating"
              @click="createSimulation"
            />
          </template>
        </div>
      </div>
    </aside>

    <div v-if="creating" class="creating-overlay" role="status" aria-live="polite" aria-busy="true">
      <div class="creating-card">
        <p class="creating-label">{{ t('actions.preparing') }}</p>
        <div class="creating-bar">
          <ProgressBar mode="indeterminate" />
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.layout {
  max-width: none;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0 0.75rem 0.75rem;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  word-break: keep-all;
  overflow-wrap: anywhere;
  line-break: strict;
}

.header {
  --header-bar-h: 2.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-height: 0;
  padding-top: 0.25rem;
  padding-right: 4.25rem;
  margin-bottom: 0.6rem;
  flex: 0 0 auto;
}

.header-top {
  display: grid;
  grid-template-columns: minmax(7.5rem, auto) minmax(0, 1fr) max-content max-content;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.header-headline {
  margin: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  font-size: 0.82rem;
  font-weight: 650;
  line-height: var(--header-bar-h);
  color: var(--text);
}

.header-headline.yellow {
  color: #efc15a;
}

.header-headline.red {
  color: #ff7a6e;
}

.header-left {
  min-width: 0;
}

.header-left h1 {
  margin: 0.2rem 0 0;
  font-size: 0.95rem;
  font-weight: 650;
  line-height: 1.25;
  min-height: 0;
  white-space: nowrap;
}

.llm-status {
  margin: 0.15rem 0 0;
  font-size: 0.68rem;
  line-height: 1.3;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-error {
  margin: 0.35rem 0 0;
  max-width: 28rem;
  font-size: 0.78rem;
  line-height: 1.35;
  color: #c45c4a;
}

.header-era {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  min-width: 0;
  padding: 0.4rem 0.7rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 85%, #1e2a38);
  font-size: 0.8rem;
  line-height: 1.2;
  color: var(--text);
  box-sizing: border-box;
}

.header-era-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 0.55rem;
}

.header-era-sep {
  color: var(--muted);
  opacity: 0.55;
  flex: 0 0 auto;
}

.era-banner-year {
  flex: 0 0 auto;
  font-size: 0.88rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--accent);
}

.era-k {
  color: #dbe4ee;
  font-size: 0.72rem;
  margin-right: 0.25rem;
}

.header-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  min-width: 0;
}

.header-meta .experiment-worlds {
  margin-top: 0;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex: 0 0 auto;
}

.tick-status {
  display: inline-flex;
  align-items: center;
  height: var(--header-bar-h);
  padding: 0 0.55rem;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: color-mix(in srgb, var(--text, #1c2430) 78%, #3a6ea5);
  background: color-mix(in srgb, #3a6ea5 12%, transparent);
  white-space: nowrap;
  flex: 0 0 auto;
}

.tick-status--hidden {
  visibility: hidden;
}

.header-turn-row {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex: 0 0 auto;
}

.header-btn {
  height: var(--header-bar-h);
  min-height: var(--header-bar-h);
  padding: 0 0.7rem;
  min-width: 0;
}

.header-btn :deep(.p-button-label) {
  font-weight: 650;
  line-height: 1;
}

.header-btn :deep(.p-button-icon) {
  font-size: 0.85rem;
}

.header-meta :deep(.p-tag) {
  height: var(--header-bar-h);
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  box-sizing: border-box;
}

.year-row {
  display: grid;
  grid-template-columns: minmax(7.5rem, 0.9fr) minmax(0, 1.1fr);
  gap: 0.45rem;
  align-items: stretch;
}

.era-select,
.year-input {
  width: 100%;
}

.era-preview {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  margin: 0;
  min-height: 2.15rem;
  padding: 0.2rem 0.65rem;
  border-radius: 8px;
  border: 1px dashed var(--line);
  background: color-mix(in srgb, var(--panel) 70%, #121820);
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  font-size: 0.78rem;
  line-height: 1.2;
  color: var(--text);
}

.era-preview-title {
  margin: 0;
  flex: 0 0 auto;
  font-size: 0.72rem;
  font-weight: 600;
  color: #e6eef5;
}

.lang {
  position: fixed;
  top: 0.3rem;
  right: 0.75rem;
  z-index: 20;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  line-height: 1;
}

.lang-btn {
  margin: 0;
  padding: 0.1rem 0.15rem;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  opacity: 0.7;
}

.lang-btn:hover {
  opacity: 1;
  color: var(--text);
}

.lang-btn.active {
  color: var(--text);
  opacity: 1;
}

.lang-sep {
  color: var(--muted);
  font-size: 0.65rem;
  opacity: 0.5;
}

.eyebrow {
  margin: 0;
  color: var(--muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.75rem;
}

h1 {
  margin: 0.2rem 0 0;
  font-size: 1.5rem;
  font-weight: 650;
  line-height: 1.25;
  min-height: 1.875rem;
}

h2 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: var(--text);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
  align-items: stretch;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.grid-with-digest {
  grid-template-columns: min(22rem, 32vw) minmax(0, 1fr);
  gap: 0.65rem;
}

.digest-sidebar {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  padding: 0.65rem 0.75rem;
}

.panel {
  background: color-mix(in srgb, var(--panel) 92%, transparent);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1rem;
  min-width: 0;
  min-height: 0;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 35;
  background: rgba(4, 8, 14, 0.55);
}

.creating-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(4, 8, 14, 0.4);
}

.creating-card {
  width: min(28rem, calc(100vw - 2rem));
  padding: 1.1rem 1.25rem 1.2rem;
  border-radius: 0.6rem;
  background: #1c252f;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.45);
}

.creating-label {
  margin: 0 0 0.75rem;
  text-align: center;
  font-size: 0.95rem;
  color: #e8eef4;
}

.creating-bar :deep(.p-progressbar) {
  height: 6px;
  border-radius: 6px;
  background: #2b3845;
  border: 0;
}

.creating-bar :deep(.p-progressbar-value) {
  background: #3b82f6;
}

.concept-modal {
  position: fixed;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 45;
  width: min(34rem, calc(100vw - 1.5rem));
  max-height: calc(100dvh - 2rem);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0.7rem 0.85rem 0.75rem;
  background: #1c252f;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
}

.concept-body {
  overflow-y: auto;
  min-height: 0;
  flex: 1 1 auto;
  padding-right: 0.15rem;
}

.conditions-modal {
  position: fixed;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 40;
  width: min(88rem, calc(100vw - 1.5rem));
  height: calc((100dvh - 2rem) * 0.8);
  max-height: calc((100dvh - 2rem) * 0.8);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0.7rem 0.85rem 0.65rem;
  background: #1c252f;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
}

.conditions-form {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  overflow: hidden;
  min-height: 0;
  flex: 1 1 auto;
}

.conditions-fields {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  overflow-x: hidden;
  overflow-y: auto;
  min-height: 0;
  flex: 1 1 auto;
  padding-right: 0.2rem;
}

.scenario-mode-picker {
  margin-bottom: 0.75rem;
}

.setup-step-label {
  margin: 0 0 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #8eb4d9;
}

.conditions-midrun-policy {
  margin-top: 0.35rem;
  padding-top: 0.55rem;
  border-top: 1px solid var(--line);
}

.conditions-midrun-lead {
  margin: 0 0 0.55rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid color-mix(in srgb, var(--line) 80%, #3b82f6);
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 90%, #1e3a5f);
  font-size: 0.78rem;
  line-height: 1.45;
  color: #c5d0dc;
}

.scenario-mode-lead {
  margin: 0 0 0.45rem;
  font-size: 0.72rem;
  color: var(--muted);
}

.scenario-mode-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
}

.scenario-mode-card,
.world-card,
.custom-preset-card {
  margin: 0;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 88%, #0b1218);
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.scenario-mode-card strong,
.world-card strong,
.custom-preset-card strong {
  display: block;
  font-size: 0.78rem;
  margin-bottom: 0.2rem;
}

.scenario-mode-card span,
.world-card span,
.custom-preset-card span {
  display: block;
  font-size: 0.66rem;
  line-height: 1.4;
  color: var(--muted);
}

.scenario-mode-card.active,
.world-card.active,
.custom-preset-card.active {
  border-color: color-mix(in srgb, var(--accent) 55%, var(--line));
  background: color-mix(in srgb, var(--accent) 12%, var(--panel));
}

.scenario-mode-card:disabled,
.world-card:disabled,
.custom-preset-card:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.world-card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
}

.scenario-fixed-hint {
  margin: 0.45rem 0 0;
  font-size: 0.66rem;
}

.custom-preset-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
  margin-bottom: 0.45rem;
}

.advanced-toggle {
  margin: 0 0 0.35rem;
  border: 0;
  background: transparent;
  color: var(--accent);
  font-size: 0.68rem;
  cursor: pointer;
  padding: 0;
}

.advanced-toggle:hover {
  text-decoration: underline;
}

.advanced-template-row {
  margin-bottom: 0.5rem;
}

.geo-details {
  margin-top: 0.65rem;
}

.geo-details summary {
  cursor: pointer;
  font-size: 0.68rem;
  color: var(--muted);
  margin-bottom: 0.35rem;
}

.template-picker {
  padding: 0.55rem 0.65rem;
  border: 1px solid color-mix(in srgb, var(--line) 85%, #3d5a80);
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 55%, #0f1720);
}

.template-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text);
}

.template-select {
  width: 100%;
}

.template-blurb {
  margin: 0.45rem 0 0.2rem;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--text);
}

.template-hint {
  margin: 0;
  font-size: 0.66rem;
}

.conditions-footer {
  flex: 0 0 auto;
  padding-top: 0.45rem;
  border-top: 1px solid var(--line);
}

.step-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.step-footer .action-btn {
  width: auto;
  min-width: 8rem;
}

.step-nav {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.35rem;
  margin-bottom: 0.35rem;
}

.step-tab {
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: transparent;
  color: #e8eef4;
  padding: 0.4rem 0.5rem;
  font-size: 0.78rem;
  cursor: pointer;
}

.step-tab.active {
  background: color-mix(in srgb, var(--accent) 28%, #1c252f);
  border-color: var(--accent);
}

.continent-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(9.5rem, 1fr));
  gap: 0.45rem;
  margin-top: 0.5rem;
}

.continent-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.45rem 0.5rem 0.55rem;
  background: color-mix(in srgb, #121820 70%, var(--panel));
  min-width: 0;
}

.continent-card h3 {
  margin: 0 0 0.35rem;
  font-size: 0.88rem;
  color: var(--text);
}

.year-block {
  display: grid;
  grid-template-columns: minmax(14rem, 18rem) minmax(0, 1fr);
  grid-template-areas:
    'year era'
    'hint hint';
  gap: 0.35rem 0.75rem;
  align-items: end;
  margin-top: 0.7rem;
}

.year-field {
  grid-area: year;
}

.year-block .era-preview {
  grid-area: era;
}

.year-hint {
  grid-area: hint;
  margin: 0;
}

.conditions-dt {
  margin-top: 0.35rem;
}

.conditions-dt :deep(.p-datatable-wrapper) {
  background: #0b1118;
  border: 1px solid #6b7c8d;
  border-radius: 8px;
}

.conditions-dt :deep(.p-datatable-thead > tr > th),
.conditions-dt :deep(.p-datatable-tbody > tr > td) {
  background: #1c2632;
  color: #f8fbff;
  border-color: #4d5d6c;
  padding: 0.4rem 0.5rem;
  vertical-align: middle;
}

.conditions-dt :deep(.p-datatable-thead > tr > th) {
  background: #2d3d4e;
  font-weight: 700;
}

.conditions-dt :deep(.p-datatable-tbody > tr:nth-child(odd) > td) {
  background: #151d27;
}

.conditions-dt :deep(.dt-axis) {
  background: #3a4c5e !important;
  font-weight: 700;
  min-width: 7.2rem;
}

.axis-label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.axis-info {
  color: #9ec4e8;
  cursor: help;
  font-size: 0.85rem;
}

.conditions-dt :deep(.p-slider) {
  background: #4d5d6c;
}

.conditions-dt :deep(.p-slider .p-slider-range) {
  background: #7ec4ff;
}

.conditions-dt :deep(.p-slider .p-slider-handle) {
  border-color: #7ec4ff;
  background: #e8f4ff;
}

.pop-slider {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  width: 100%;
  min-width: 5.5rem;
  padding: 0.15rem 0.2rem 0;
}

.pop-slider-value {
  font-size: 0.7rem;
  line-height: 1.2;
  color: #d5e4f2;
}

.bg-table {
  margin-top: 0.55rem;
  border: 1px solid #6b7c8d;
  border-radius: 8px;
  overflow: auto;
  min-height: 0;
  background: #0b1118;
}

.bg-row {
  display: grid;
  grid-template-columns: minmax(5.8rem, 7.2rem) repeat(5, minmax(7.5rem, 1fr));
  min-width: 52rem;
}

.bg-row + .bg-row {
  border-top: 1px solid #4d5d6c;
}

.bg-row:nth-child(odd):not(.bg-head) {
  background: #151d27;
}

.bg-row:nth-child(even):not(.bg-head) {
  background: #1c2632;
}

.bg-head {
  background: #2d3d4e;
}

.bg-stub,
.bg-cell {
  padding: 0.48rem 0.55rem;
  font-size: 0.8rem;
  line-height: 1.4;
  color: #f8fbff;
}

.bg-stub {
  font-weight: 700;
  color: #ffffff;
  background: #3a4c5e;
  border-right: 1px solid #6b7c8d;
}

.bg-head .bg-stub {
  background: #44586b;
}

.bg-head .bg-cell {
  font-weight: 700;
  color: #ffffff;
}

.col-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.12rem;
}

.col-sub {
  font-weight: 500;
  font-size: 0.72rem;
  color: #d5e4f2;
}

.bg-focus {
  font-size: 0.72rem;
  line-height: 1.35;
  color: #e8f1fa;
}

.bg-form .bg-cell {
  display: flex;
  align-items: center;
  padding: 0.35rem 0.4rem;
}

.bg-form :deep(.p-dropdown) {
  height: 2rem;
}

.conditions-section {
  min-width: 0;
}

.conditions-grid {
  display: grid;
  gap: 0.35rem 0.85rem;
  align-items: start;
}

.conditions-grid-stage {
  grid-template-columns: minmax(0, 1.15fr) minmax(12rem, 1.1fr);
}

.conditions-grid-land {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 0.4rem;
}

.conditions-grid-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.conditions-grid-replay {
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 16rem);
  align-items: end;
}

.conditions-group {
  margin: 0 0 0.12rem;
  padding: 0;
  border: 0;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #e8eef4;
}

.conditions-lead {
  margin: 0 0 0.28rem;
  font-size: 0.72rem;
  line-height: 1.3;
  color: #d0dae4;
}

.conditions-field label {
  margin: 0 0 0.15rem;
  color: #f0f4f8;
}

.conditions-grid-stage .era-preview {
  margin-top: 0;
}

.conditions-modal .hint {
  font-size: 0.66rem;
  line-height: 1.25;
  color: #cdd6e0;
  opacity: 1;
}

.viewport {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}

.map-heading {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-width: 0;
}

.map-tabs {
  display: flex;
  border: 1px solid var(--line);
  border-radius: 7px;
  overflow: hidden;
}

.map-tab {
  margin: 0;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 0.72rem;
  padding: 0.18rem 0.55rem;
  cursor: pointer;
}

.map-tab.active {
  background: color-mix(in srgb, var(--accent) 22%, var(--panel));
  color: var(--text);
}

.panel-heading h2 {
  margin: 0;
  color: var(--text);
}

.conditions-modal .events-heading {
  margin-bottom: 0.4rem;
  flex: 0 0 auto;
}

.events-heading {
  margin-bottom: 0.75rem;
}

.events-heading-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.events-modal {
  position: fixed;
  right: 0.85rem;
  bottom: 0.85rem;
  z-index: 30;
  width: min(24rem, calc(100vw - 1.7rem));
  height: min(70vh, 36rem);
  display: flex;
  flex-direction: column;
  background: #1c252f;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}

.digest-heading {
  margin-bottom: 0.35rem;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.digest-heading h2 {
  margin: 0;
}

.digest-one-liner {
  margin: 0 0 0.4rem;
  font-size: 0.78rem;
  line-height: 1.4;
  font-weight: 650;
  color: var(--text);
  flex: 0 0 auto;
}

.digest-story-p,
.digest-opening-text,
.digest-outcome-text {
  margin: 0 0 0.35rem;
  font-size: 0.72rem;
  line-height: 1.5;
  color: var(--text);
}

.digest-opening-text {
  white-space: pre-line;
}

.digest-region-story {
  margin: 0 0 0.35rem;
  font-size: 0.71rem;
  line-height: 1.45;
  color: color-mix(in srgb, var(--text) 92%, #9ec9ff);
}

.digest-collapse-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin: 0;
  padding: 0.2rem 0;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 0.68rem;
  font-weight: 700;
  cursor: pointer;
}

.digest-meters-details {
  margin: 0.25rem 0;
}

.digest-meters-details summary {
  cursor: pointer;
  font-size: 0.64rem;
  color: var(--muted);
  margin-bottom: 0.2rem;
}

.digest-section-compact .digest-setup {
  -webkit-line-clamp: 3;
}

.digest-body {
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 0;
  padding-right: 0.15rem;
  -webkit-overflow-scrolling: touch;
}

.digest-tabs {
  display: flex;
  gap: 0.35rem;
  margin: 0.45rem 0 0.5rem;
  flex: 0 0 auto;
}

.digest-tab {
  flex: 1 1 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.38rem 0.5rem;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--line) 85%, transparent);
  background: color-mix(in srgb, var(--panel) 88%, #0b1218);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 650;
  cursor: pointer;
}

.digest-tab.active {
  color: var(--text);
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
  background: color-mix(in srgb, var(--accent) 12%, var(--panel));
}

.digest-tab-badge {
  min-width: 1.1rem;
  padding: 0.05rem 0.3rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent) 35%, transparent);
  color: #e8f4ff;
  font-size: 0.62rem;
  font-variant-numeric: tabular-nums;
}

.digest-tab-panel {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  min-height: 0;
}

.digest-tab-panel-events {
  flex: 1 1 auto;
  overflow-y: auto;
}

.digest-region-picker {
  display: flex;
  flex-wrap: nowrap;
  gap: 0.28rem;
  margin-bottom: 0.45rem;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  padding-bottom: 0.15rem;
  scrollbar-width: thin;
}

.digest-region-slider {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.digest-region-slider-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
}

.digest-region-slider-btn {
  width: 1.75rem;
  height: 1.75rem;
  flex: 0 0 auto;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--line) 85%, transparent);
  background: color-mix(in srgb, var(--panel) 90%, #0b1218);
  color: var(--text);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}

.digest-region-slider-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.digest-region-slider-pos {
  flex: 1 1 auto;
  text-align: center;
  font-size: 0.68rem;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
}

.digest-region-slider-stage {
  position: relative;
  overflow: hidden;
  touch-action: pan-y;
}

.region-slide-left-enter-active,
.region-slide-left-leave-active,
.region-slide-right-enter-active,
.region-slide-right-leave-active {
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.region-slide-left-enter-from {
  opacity: 0;
  transform: translateX(1.25rem);
}

.region-slide-left-leave-to {
  opacity: 0;
  transform: translateX(-1.25rem);
}

.region-slide-right-enter-from {
  opacity: 0;
  transform: translateX(-1.25rem);
}

.region-slide-right-leave-to {
  opacity: 0;
  transform: translateX(1.25rem);
}

.digest-region-chip {
  display: inline-flex;
  align-items: flex-start;
  gap: 0.28rem;
  padding: 0.28rem 0.42rem;
  min-width: 3.4rem;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
  background: color-mix(in srgb, var(--panel) 90%, #0b1218);
  color: var(--text);
  font-size: 0.62rem;
  font-weight: 650;
  cursor: pointer;
  line-height: 1.15;
  flex: 0 0 auto;
}

.digest-region-chip.active {
  border-color: color-mix(in srgb, var(--region-color, var(--accent)) 55%, var(--line));
  background: color-mix(in srgb, var(--region-color, var(--accent)) 14%, var(--panel));
}

.digest-region-chip-dot {
  width: 0.42rem;
  height: 0.42rem;
  margin-top: 0.12rem;
  border-radius: 50%;
  background: var(--region-color, var(--accent));
  flex: 0 0 auto;
}

.digest-region-chip-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.08rem;
  min-width: 0;
}

.digest-region-chip-name {
  font-size: 0.64rem;
  font-weight: 700;
  white-space: nowrap;
}

.digest-region-chip-sub {
  font-size: 0.58rem;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
}

.digest-section {
  flex: 0 0 auto;
}

.digest-section h3 {
  margin: 0 0 0.15rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text);
}

.digest-section-setup .digest-setup {
  margin: 0;
  font-size: 0.68rem;
  line-height: 1.35;
  color: var(--muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.digest-summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}

.digest-chips {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.22rem;
}

.digest-chips li {
  padding: 0.12rem 0.35rem;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
  background: color-mix(in srgb, var(--panel) 70%, #0b1218);
  font-size: 0.66rem;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

.digest-notable-line {
  margin: 0;
  font-size: 0.7rem;
  line-height: 1.35;
  color: var(--text);
}

.digest-section-obs {
  flex: 0 0 auto;
  min-height: 0;
}

.digest-obs-source {
  margin-left: 0.4rem;
  font-size: 0.62rem;
  font-weight: 650;
  color: #9ec9ff;
}

.digest-region-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.55rem;
}

@media (min-width: 720px) {
  .digest-region-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.digest-region-card {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.55rem 0.6rem 0.5rem;
  border: 1px solid color-mix(in srgb, var(--line) 85%, transparent);
  border-radius: 10px;
  background:
    linear-gradient(160deg, color-mix(in srgb, #1a2733 55%, transparent), transparent 55%),
    color-mix(in srgb, var(--panel) 88%, #0b1218);
}

.digest-region-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.4rem;
}

.digest-region-head strong {
  font-size: 0.82rem;
  font-weight: 700;
}

.digest-region-pop {
  font-size: 0.62rem;
  color: var(--muted);
}

.digest-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.22rem;
}

.digest-flow-chip {
  display: inline-flex;
  max-width: 100%;
  padding: 0.18rem 0.4rem;
  border-radius: 999px;
  font-size: 0.62rem;
  font-weight: 650;
  line-height: 1.2;
}

.digest-flow-chip.signal {
  color: #d9ecff;
  background: color-mix(in srgb, #2f5f86 55%, transparent);
}

.digest-flow-chip.trajectory {
  color: #fff4d6;
  background: color-mix(in srgb, #8a6a28 50%, transparent);
}

.digest-flow-chip.trajectory[data-traj='war'] {
  color: #ffe0db;
  background: color-mix(in srgb, #a3453a 55%, transparent);
}

.digest-flow-chip.trajectory[data-traj='industry'] {
  color: #dff8e8;
  background: color-mix(in srgb, #2f7a4e 55%, transparent);
}

.digest-flow-chip.trajectory[data-traj='reform'] {
  color: #e7e0ff;
  background: color-mix(in srgb, #5a4ea0 55%, transparent);
}

.digest-flow-chip.archetype {
  color: #ffe9c8;
  background: color-mix(in srgb, #9a6230 55%, transparent);
}

.digest-flow-arrow {
  color: var(--muted);
  font-size: 0.7rem;
}

.digest-meters {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.22rem;
}

.digest-meters li {
  display: grid;
  grid-template-columns: 2.4rem minmax(0, 1fr) 2rem;
  gap: 0.28rem;
  align-items: center;
  font-size: 0.6rem;
  color: var(--muted);
}

.digest-meters em {
  font-style: normal;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

.digest-meter-track {
  height: 0.38rem;
  border-radius: 999px;
  background: color-mix(in srgb, #0d141c 70%, var(--line));
  overflow: hidden;
}

.digest-meter-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #6ea8d8;
}

.digest-meter-fill.hot {
  background: linear-gradient(90deg, #d15a4a, #ff8b6e);
}

.digest-meter-fill.warm {
  background: linear-gradient(90deg, #c49a3c, #efc15a);
}

.digest-meter-fill.cool,
.digest-meter-fill.dim {
  background: linear-gradient(90deg, #3d5f78, #7aa7c7);
}

.digest-meter-fill.good {
  background: linear-gradient(90deg, #2f8f5b, #6dcaa0);
}

.digest-region-summary {
  margin: 0;
  font-size: 0.68rem;
  line-height: 1.35;
  color: color-mix(in srgb, var(--text) 88%, #b7d7ff);
}

.digest-region-polity {
  margin: 0;
  font-size: 0.58rem;
  color: var(--muted);
}

.events-close {
  margin: 0;
  border: 0;
  background: transparent;
  color: var(--text);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  padding: 0.1rem 0.35rem;
  opacity: 0.85;
}

.events-close:disabled {
  cursor: default;
  opacity: 0.4;
}

.event-chat {
  margin: 0;
  padding: 0;
  list-style: none;
  overflow-y: auto;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.event-bubble {
  padding: 0.45rem 0.55rem;
  border-radius: 10px;
  background: color-mix(in srgb, var(--panel) 70%, #0b1218);
  border: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
}

.event-bubble.event-llm {
  border-color: color-mix(in srgb, #6db6ff 55%, var(--line));
  background: color-mix(in srgb, #163048 35%, var(--panel));
}

.event-bubble-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.75rem;
}

.event-llm-badge {
  margin-left: auto;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 650;
  letter-spacing: 0.04em;
  color: #cfe7ff;
  background: color-mix(in srgb, #2a6cad 70%, transparent);
}

.event-bubble .event-text {
  margin: 0.25rem 0 0;
  font-size: 0.78rem;
  line-height: 1.4;
}

.event-bubble .event-reason {
  margin: 0.2rem 0 0;
  font-size: 0.72rem;
  line-height: 1.35;
  color: color-mix(in srgb, var(--text) 72%, #9ec9ff);
  font-style: italic;
}

label {
  display: block;
  margin: 0.7rem 0 0.25rem;
  color: var(--text);
  font-size: 0.8rem;
}

.hint {
  margin: 0.2rem 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.45;
  opacity: 1;
}

.field-control {
  width: 100%;
  max-width: 100%;
}

.conditions-modal :deep(.p-inputnumber),
.conditions-modal :deep(.p-dropdown) {
  width: 100%;
  max-width: 100%;
  display: inline-flex;
  align-items: stretch;
  height: 2.15rem;
}

.year-row :deep(.p-dropdown),
.year-row :deep(.p-inputnumber) {
  width: 100%;
  height: 2.15rem;
}

.conditions-modal :deep(.p-inputnumber-input) {
  min-width: 0;
  flex: 1 1 auto;
  height: 100%;
  box-sizing: border-box;
}

.conditions-modal :deep(.p-dropdown) {
  min-width: 0;
  flex: 1 1 auto;
}

.conditions-modal :deep(.p-dropdown .p-dropdown-label),
.conditions-modal :deep(.p-dropdown .p-dropdown-trigger) {
  display: flex;
  align-items: center;
}

.conditions-modal :deep(.p-inputnumber-button-group) {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-self: stretch;
  height: 100%;
}

.conditions-modal :deep(.p-inputnumber-button) {
  flex: 1 1 0;
  width: 2rem;
  margin: 0;
  padding: 0;
  height: auto !important;
  min-height: 0;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0;
  padding-bottom: 0;
}

.action-btn {
  width: 100%;
}

.action-btn :deep(.p-button-label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-stats {
  margin: 0;
  color: var(--text);
  font-size: 0.75rem;
  text-align: right;
  line-height: 1.35;
}

.map-legend {
  margin-bottom: 0.55rem;
}

.map-stage {
  position: relative;
  flex: 1 1 auto;
  min-height: 280px;
  padding-bottom: 0;
  overflow: hidden;
}

.map-stage :deep(.map-wrap) {
  position: absolute;
  inset: 0;
  flex: none;
  min-height: 0;
  height: auto;
}

.event-actor {
  font-weight: 700;
}

.error {
  color: #ff8f8f;
  font-size: 0.85rem;
}

.experiment-worlds {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.35rem;
}

.experiment-worlds-label {
  font-size: 0.68rem;
  color: var(--muted);
}

.experiment-world-btn {
  font-size: 0.68rem;
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: color-mix(in srgb, var(--panel) 80%, #0b1218);
  color: var(--text);
  cursor: pointer;
}

.experiment-world-btn.active {
  border-color: color-mix(in srgb, var(--primary) 60%, var(--line));
  background: color-mix(in srgb, var(--primary) 18%, var(--panel));
}

.experiment-compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.68rem;
}

.experiment-compare-table th,
.experiment-compare-table td {
  border: 1px solid var(--line);
  padding: 0.25rem 0.35rem;
  text-align: left;
}

.experiment-fixed,
.experiment-unexpected {
  font-size: 0.68rem;
}

.experiment-unexpected {
  margin-top: 0.35rem;
  color: var(--primary);
}

.spotlight-name {
  margin: 0.25rem 0;
  font-size: 0.78rem;
}

.spotlight-id {
  color: var(--muted);
  font-size: 0.65rem;
}

.spotlight-trait-list {
  margin: 0.25rem 0;
  padding-left: 1rem;
  font-size: 0.68rem;
}

.spotlight-why {
  margin: 0.35rem 0 0;
  font-size: 0.68rem;
  line-height: 1.4;
}

.digest-section-group {
  border: 1px solid color-mix(in srgb, var(--primary) 35%, var(--line));
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
  background: color-mix(in srgb, var(--primary) 8%, var(--panel));
}

.digest-focus-card {
  border: 1px solid color-mix(in srgb, var(--accent) 40%, var(--line));
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
  margin-bottom: 0.5rem;
  background: color-mix(in srgb, var(--accent) 10%, var(--panel));
}

.digest-focus-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.digest-focus-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.digest-focus-clear {
  margin: 0;
  border: 0;
  background: transparent;
  color: var(--accent);
  font-size: 0.65rem;
  cursor: pointer;
  padding: 0;
}

.digest-focus-clear:hover {
  text-decoration: underline;
}

.digest-focus-title {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 700;
  line-height: 1.35;
}

.digest-focus-body {
  margin: 0.35rem 0 0;
  font-size: 0.72rem;
  line-height: 1.5;
  color: var(--text);
}

.digest-world-brief {
  margin: 0 0 0.5rem;
}

.digest-story-btn {
  width: 100%;
  margin: 0.35rem 0;
}

.digest-story-block {
  margin-bottom: 0.5rem;
}

.digest-emergence,
.scenario-emergence {
  margin: 0 0 0.5rem;
  padding: 0.45rem 0.55rem;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--line));
  background: color-mix(in srgb, var(--accent) 10%, var(--panel));
  font-size: 0.68rem;
  line-height: 1.45;
}

.event-feed-simple {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.event-feed-item {
  padding: 0.35rem 0.45rem;
  border-radius: 6px;
  background: color-mix(in srgb, var(--panel) 88%, var(--line));
  font-size: 0.72rem;
  line-height: 1.4;
}

.event-feed-simple .event-bubble-meta {
  margin-bottom: 0.15rem;
}

.event-turn-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--muted);
}

.event-alert-red {
  border-left: 3px solid #ff5c48;
}

.event-alert-yellow {
  border-left: 3px solid #ffd640;
}

.digest-more-btn {
  width: 100%;
  margin-bottom: 0.35rem;
}

.digest-more {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.digest-region-grid-compact {
  gap: 0.35rem;
}

.digest-region-card-compact {
  padding: 0.4rem 0.5rem;
}

.digest-region-card-compact .digest-region-summary {
  margin: 0.25rem 0 0;
  font-size: 0.68rem;
}

.group-name {
  margin: 0.25rem 0;
  font-size: 0.82rem;
}

.group-facts {
  margin: 0.35rem 0;
  padding-left: 1rem;
  font-size: 0.68rem;
}

.group-context,
.group-policy {
  margin: 0.35rem 0 0;
  font-size: 0.68rem;
  line-height: 1.45;
}

.group-events {
  margin-top: 0.45rem;
  font-size: 0.68rem;
}

.group-event-list {
  margin: 0.25rem 0 0;
  padding-left: 1rem;
}

.experiment-variant-list {
  margin: 0.5rem 0 0;
  padding-left: 1.1rem;
  font-size: 0.72rem;
}

@media (max-width: 900px) {
  .grid-with-digest {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(220px, 1fr) min(36vh, 22rem);
  }

  .grid-with-digest .digest-sidebar {
    order: 2;
  }

  .grid-with-digest .viewport {
    order: 1;
  }
}

@media (max-width: 1100px) {
  .continent-grid,
  .continent-grid-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .conditions-modal {
    width: min(52rem, calc(100vw - 1.25rem));
    height: calc((100dvh - 1.25rem) * 0.8);
    max-height: calc((100dvh - 1.25rem) * 0.8);
    overflow: hidden;
  }
}

@media (max-width: 720px) {
  .conditions-grid-stage,
  .conditions-grid-land,
  .conditions-grid-4,
  .conditions-grid-replay,
  .continent-grid,
  .year-block {
    grid-template-columns: 1fr;
  }

  .year-block {
    grid-template-areas:
      'year'
      'era'
      'hint';
  }

  .era-preview {
    flex-wrap: wrap;
    white-space: normal;
  }
}
</style>
