<script setup lang="ts">
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import { polityKind, settlementColor } from '~/utils/groupColors'
import WorldMap2D from '~/components/WorldMap2D.vue'

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
}

type Metrics = {
  inequality: number
  mean_trust: number
  cooperation_rate: number
  authority: number
  mean_happiness: number
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
}

type Settlement = {
  id: string
  position: { x: number; y: number }
  member_ids: string[]
  leader_id?: string | null
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
    terrain?: Terrain
    initial_population?: number
    initial_total_wealth?: number
    population_cap?: number
  }
  agents: Agent[]
  settlements?: Settlement[]
  events: EventRow[]
  last_metrics: Metrics | null
}

const AUTO_INTERVAL_MS = 800

const { t, locale, setLocale } = useI18n()

useHead(() => ({
  title: t('brand'),
}))

const conditionsOpen = ref(true)
const eventsOpen = ref(false)

const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

const sim = ref<Simulation | null>(null)
const busy = ref(false)
const error = ref('')
const autoPlaying = ref(false)
let autoTimer: ReturnType<typeof setInterval> | null = null
let tickInFlight = false

const calendarEra = ref<'bc' | 'ad'>('ad')
const calendarYear = ref(700)
const population = ref(8)
const seed = ref(42)
const taxRate = ref(0.1)
const education = ref(0.5)
const resourcePool = ref(100)
const cooperation = ref(0.5)
const authorityAcceptance = ref(0.5)
const ambition = ref(0.5)
const inequality = ref(0.35)
/** API には英語キーのまま送る */
const institution = ref('democracy')
const geography = ref('asia')
const landform = ref('continent')
const climate = ref('temperate')

const institutionOptions = computed(() => [
  { label: t('institutions.democracy'), value: 'democracy' },
  { label: t('institutions.autocracy'), value: 'autocracy' },
  { label: t('institutions.anarchy'), value: 'anarchy' },
])

const geographyOptions = computed(() => [
  { label: t('geographies.asia'), value: 'asia' },
  { label: t('geographies.europe'), value: 'europe' },
  { label: t('geographies.middle_east'), value: 'middle_east' },
  { label: t('geographies.america'), value: 'america' },
])

const landformOptions = computed(() => [
  { label: t('landforms.continent'), value: 'continent' },
  { label: t('landforms.island'), value: 'island' },
])

const climateOptions = computed(() => [
  { label: t('climates.temperate'), value: 'temperate' },
  { label: t('climates.cold'), value: 'cold' },
  { label: t('climates.wetland'), value: 'wetland' },
  { label: t('climates.arid'), value: 'arid' },
])

const calendarEraOptions = computed(() => [
  { label: t('calendarEra.bc'), value: 'bc' as const },
  { label: t('calendarEra.ad'), value: 'ad' as const },
])

const draftAstroYear = computed(() => toAstronomicalYear(calendarEra.value, calendarYear.value))

const currentAstroYear = computed(() => {
  if (!sim.value) return draftAstroYear.value
  const start = sim.value.world.start_year ?? draftAstroYear.value
  return start + sim.value.world.turn
})

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

const recentEvents = computed(() => (sim.value?.events ?? []).slice(-40).reverse())

const aliveCount = computed(() => (sim.value?.agents ?? []).filter((a) => a.alive).length)
const totalAgents = computed(() => sim.value?.agents.length ?? 0)
const initialPopulation = computed(
  () => sim.value?.world.initial_population ?? population.value,
)
const populationCap = computed(() => sim.value?.world.population_cap ?? 100)
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

const statusLabel = computed(() => {
  if (!sim.value) return ''
  const key = `status.${sim.value.status}` as const
  const translated = t(key)
  return translated === key ? sim.value.status : translated
})

const turnStatusLabel = computed(() => {
  if (!sim.value) return ''
  return t('turnStatus', { turn: sim.value.world.turn, status: statusLabel.value })
})

const turnOnlyLabel = computed(() => {
  if (!sim.value) return ''
  return t('turnLabel', { turn: sim.value.world.turn })
})

const metricItems = computed(() => {
  const m = sim.value?.last_metrics
  if (!m) return []
  return [
    { key: 'inequality', value: m.inequality, hint: 'metrics.inequalityHint' },
    { key: 'trust', value: m.mean_trust, hint: 'metrics.trustHint' },
    { key: 'cooperationRate', value: m.cooperation_rate, hint: 'metrics.cooperationRateHint' },
    { key: 'authority', value: m.authority, hint: 'metrics.authorityHint' },
    { key: 'happiness', value: m.mean_happiness, hint: 'metrics.happinessHint' },
  ] as const
})

function actorLabel(actorId: string): string {
  if (actorId === 'world') return t('events.world')
  if (actorId === 'lone') return t('events.lone')
  if (actorId.startsWith('s')) return actorId
  const agent = sim.value?.agents.find((a) => a.id === actorId)
  return agent?.name ?? actorId
}

function eventGroupId(actorId: string): string | null {
  if (!actorId || actorId === 'world' || actorId === 'lone') return null
  if (actorId.startsWith('s')) return actorId
  return sim.value?.agents.find((a) => a.id === actorId)?.settlement_id ?? null
}

function eventActorColor(actorId: string): string {
  return settlementColor(eventGroupId(actorId))
}

function isGroupId(id: string | null | undefined): boolean {
  return !id || id === 'world' || id === 'lone' || id.startsWith('s')
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

function eventDetail(row: EventRow): string {
  const key = `eventDetails.${inferDetailKey(row)}`
  const personId = isGroupId(row.target_id) ? row.actor_id : (row.target_id || row.actor_id)
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
  })
  return translated === key ? row.detail : translated
}

async function onLocaleChange(code: string) {
  if (!code || code === locale.value) return
  await setLocale(code)
}

async function api<T>(path: string, options?: Parameters<typeof $fetch<T>>[1]): Promise<T> {
  return await $fetch<T>(`${apiBase}${path}`, options)
}

function stopAutoPlay() {
  autoPlaying.value = false
  if (autoTimer != null) {
    clearInterval(autoTimer)
    autoTimer = null
  }
}

async function createSimulation() {
  stopAutoPlay()
  busy.value = true
  error.value = ''
  try {
    sim.value = await api<Simulation>('/simulations', {
      method: 'POST',
      body: {
        seed: seed.value,
        population: population.value,
        tax_rate: taxRate.value,
        education_level: education.value,
        institution: institution.value,
        start_year: draftAstroYear.value,
        geography: geography.value,
        landform: landform.value,
        climate: climate.value,
        resource_pool: resourcePool.value,
        initial_values: {
          cooperation: cooperation.value,
          authority_acceptance: authorityAcceptance.value,
          ambition: ambition.value,
          inequality: inequality.value,
        },
      },
    })
    conditionsOpen.value = false
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

async function tick(n = 1, opts?: { silent?: boolean }) {
  if (!sim.value || tickInFlight) return
  tickInFlight = true
  if (!opts?.silent) busy.value = true
  error.value = ''
  try {
    sim.value = await api<Simulation>(`/simulations/${sim.value.id}/tick`, {
      method: 'POST',
      body: { n },
    })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
    stopAutoPlay()
  } finally {
    tickInFlight = false
    if (!opts?.silent) busy.value = false
  }
}

async function toggleAutoPlay() {
  if (autoPlaying.value) {
    stopAutoPlay()
    return
  }
  if (!sim.value) return
  autoPlaying.value = true
  await tick(1, { silent: true })
  if (!autoPlaying.value) return
  autoTimer = setInterval(() => {
    if (!sim.value || !autoPlaying.value) return
    void tick(1, { silent: true })
  }, AUTO_INTERVAL_MS)
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
          <h1>{{ t('consoleTitle') }}</h1>
        </div>
        <div class="header-right">
        <div class="header-controls">
          <Button
            :label="conditionsOpen ? t('layout.hideConditions') : t('layout.showConditions')"
            icon="pi pi-sliders-h"
            class="header-btn"
            :severity="conditionsOpen ? 'info' : 'secondary'"
            @click="conditionsOpen = !conditionsOpen"
          />
          <Button
            :label="t('events.title')"
            icon="pi pi-comments"
            class="header-btn"
            :severity="eventsOpen ? 'info' : 'secondary'"
            @click="eventsOpen = !eventsOpen"
          />
          <Button
            :label="t('actions.tick')"
            icon="pi pi-step-forward"
            class="header-btn"
            :disabled="!sim || autoPlaying"
            :loading="busy && !autoPlaying"
            severity="success"
            @click="tick(1)"
          />
          <Button
            :label="t('actions.tick5')"
            icon="pi pi-forward"
            class="header-btn"
            :disabled="!sim || autoPlaying"
            :loading="busy && !autoPlaying"
            severity="help"
            @click="tick(5)"
          />
          <Button
            :label="autoPlaying ? t('actions.autoStop') : t('actions.autoPlay')"
            :icon="autoPlaying ? 'pi pi-stop' : 'pi pi-play'"
            class="header-btn"
            :disabled="!sim"
            :severity="autoPlaying ? 'danger' : 'secondary'"
            @click="toggleAutoPlay"
          />
        </div>
        <Tag v-if="sim" :value="turnStatusLabel" severity="info" />
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

    <div class="grid">
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
            {{ t(`geographies.${sim.world.geography}`) }}
            ·
            {{ t(`landforms.${sim.world.landform ?? 'continent'}`) }}
            ·
            {{ t(`climates.${sim.world.climate ?? 'temperate'}`) }}
          </p>
        </div>
        <p class="hint map-legend">{{ t('map.legend') }} {{ t('map.zoomHintFlat') }}</p>
        <div class="map-stage">
          <WorldMap2D :sim="sim" :geography="geography" :landform="landform" :climate="climate" :seed="seed" />
        </div>
        <div v-if="metricItems.length" class="metrics">
          <h2>{{ t('metrics.title') }}</h2>
          <ul>
            <li v-for="item in metricItems" :key="item.key">
              <div class="metric-row">
                <span class="metric-name">{{ t(`metrics.${item.key}`) }}</span>
                <span class="metric-value">{{ item.value.toFixed(3) }}</span>
              </div>
              <p class="hint">{{ t(item.hint) }}</p>
            </li>
          </ul>
        </div>
      </main>
    </div>

    <div v-if="conditionsOpen" class="modal-backdrop" @click="conditionsOpen = false" />
    <aside
      v-if="conditionsOpen"
      class="conditions-modal panel"
      role="dialog"
      aria-modal="true"
      :aria-label="t('initialConditions')"
    >
      <div class="panel-heading events-heading">
        <h2>{{ t('initialConditions') }}</h2>
        <button type="button" class="events-close" :aria-label="t('layout.closeConditions')" @click="conditionsOpen = false">×</button>
      </div>
      <div class="conditions-form">
        <section class="conditions-section">
          <p class="conditions-group">{{ t('conditionGroups.stage') }}</p>
          <div class="conditions-grid conditions-grid-stage">
            <div class="conditions-field">
              <label>{{ t('calendarYear') }}</label>
              <div class="year-row">
                <Dropdown
                  v-model="calendarEra"
                  :options="calendarEraOptions"
                  option-label="label"
                  option-value="value"
                  class="era-select"
                />
                <InputNumber v-model="calendarYear" :min="1" :max="50000" show-buttons class="year-input" />
              </div>
              <p class="hint">{{ t('calendarYearHint') }}</p>
            </div>
            <div class="era-preview">
              <p class="era-preview-title">{{ t('eraPreview.title') }}</p>
              <p><span class="era-k">{{ t('eraPreview.year', { label: draftYearLabel }) }}</span></p>
              <p><span class="era-k">{{ t('eraPreview.japan') }}</span> {{ draftJapanEra }}</p>
              <p><span class="era-k">{{ t('eraPreview.world') }}</span> {{ draftWorldEra }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('geography') }}</label>
              <Dropdown v-model="geography" :options="geographyOptions" option-label="label" option-value="value" class="field-control" />
              <p class="hint">{{ t('geographyHint') }}</p>
            </div>
          </div>
        </section>

        <section class="conditions-section">
          <p class="conditions-group">{{ t('conditionGroups.land') }}</p>
          <div class="conditions-grid conditions-grid-2">
            <div class="conditions-field">
              <label>{{ t('landform') }}</label>
              <Dropdown v-model="landform" :options="landformOptions" option-label="label" option-value="value" class="field-control" />
              <p class="hint">{{ t('landformHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('climate') }}</label>
              <Dropdown v-model="climate" :options="climateOptions" option-label="label" option-value="value" class="field-control" />
              <p class="hint">{{ t('climateHint') }}</p>
            </div>
          </div>
        </section>

        <section class="conditions-section">
          <p class="conditions-group">{{ t('conditionGroups.society') }}</p>
          <p class="conditions-lead">{{ t('conditionGroups.societyLead') }}</p>
          <div class="conditions-grid conditions-grid-4">
            <div class="conditions-field">
              <label>{{ t('population') }}</label>
              <InputNumber v-model="population" :min="2" :max="100" show-buttons class="field-control" />
              <p class="hint">{{ t('populationHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('institution') }}</label>
              <Dropdown v-model="institution" :options="institutionOptions" option-label="label" option-value="value" class="field-control" />
              <p class="hint">{{ t('institutionHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('taxRate') }}</label>
              <InputNumber v-model="taxRate" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
              <p class="hint">{{ t('taxRateHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('education') }}</label>
              <InputNumber v-model="education" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
              <p class="hint">{{ t('educationHint') }}</p>
            </div>
          </div>
        </section>

        <section class="conditions-section">
          <p class="conditions-group">{{ t('conditionGroups.people') }}</p>
          <p class="conditions-lead">{{ t('conditionGroups.peopleLead') }}</p>
          <div class="conditions-grid conditions-grid-4">
            <div class="conditions-field">
              <label>{{ t('resourcePool') }}</label>
              <InputNumber v-model="resourcePool" :min="20" :max="300" :step="10" show-buttons class="field-control" />
              <p class="hint">{{ t('resourcePoolHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('cooperation') }}</label>
              <InputNumber v-model="cooperation" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
              <p class="hint">{{ t('cooperationHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('authorityAcceptance') }}</label>
              <InputNumber v-model="authorityAcceptance" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
              <p class="hint">{{ t('authorityAcceptanceHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('ambition') }}</label>
              <InputNumber v-model="ambition" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
              <p class="hint">{{ t('ambitionHint') }}</p>
            </div>
            <div class="conditions-field">
              <label>{{ t('inequality') }}</label>
              <InputNumber v-model="inequality" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
              <p class="hint">{{ t('inequalityHint') }}</p>
            </div>
          </div>
        </section>

        <section class="conditions-section">
          <p class="conditions-group">{{ t('conditionGroups.replay') }}</p>
          <div class="conditions-grid conditions-grid-replay">
            <div class="conditions-field">
              <label>{{ t('seed') }}</label>
              <InputNumber v-model="seed" show-buttons class="field-control" />
              <p class="hint">{{ t('seedHint') }}</p>
            </div>
            <div class="actions">
              <Button :label="t('actions.create')" icon="pi pi-plus" class="action-btn" :loading="busy && !autoPlaying" @click="createSimulation" />
            </div>
          </div>
        </section>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </aside>

    <aside v-if="eventsOpen" class="events-modal panel" role="dialog" :aria-label="t('events.title')">
      <div class="panel-heading events-heading">
        <h2>{{ t('events.title') }}</h2>
        <div class="events-heading-actions">
          <Tag v-if="sim" :value="turnOnlyLabel" severity="secondary" />
          <button type="button" class="events-close" :aria-label="t('layout.closeEvents')" @click="eventsOpen = false">×</button>
        </div>
      </div>
      <p v-if="!recentEvents.length" class="hint">{{ t('events.empty') }}</p>
      <ol v-else class="event-chat">
        <li v-for="(row, idx) in recentEvents" :key="`${row.turn}-${row.actor_id}-${row.action}-${idx}`" class="event-bubble">
          <div class="event-bubble-meta">
            <span class="event-actor" :style="{ color: eventActorColor(row.actor_id) }">{{ actorLabel(row.actor_id) }}</span>
            <span class="event-action" :style="{ color: eventActorColor(row.actor_id) }">{{ actionLabel(row.action) }}</span>
          </div>
          <p class="event-text">{{ eventDetail(row) }}</p>
        </li>
      </ol>
    </aside>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-width: 0;
}

.header-left {
  min-width: 0;
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
  color: var(--muted);
  font-size: 0.72rem;
  margin-right: 0.25rem;
}

.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  min-width: 0;
  flex: 0 0 auto;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.3rem;
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

.header-right :deep(.p-tag) {
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
  margin-top: 0;
  padding: 0.45rem 0.6rem;
  border-radius: 8px;
  border: 1px dashed var(--line);
  background: color-mix(in srgb, var(--panel) 70%, #121820);
  min-width: 0;
}

.era-preview-title {
  margin: 0 0 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--muted);
}

.era-preview p {
  margin: 0.15rem 0;
  font-size: 0.82rem;
  line-height: 1.4;
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
  color: var(--muted);
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

.conditions-modal {
  position: fixed;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 40;
  width: min(84rem, calc(100vw - 2rem));
  max-height: calc(100vh - 2rem);
  display: flex;
  flex-direction: column;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
}

.conditions-form {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  overflow: visible;
  min-height: 0;
  flex: 0 0 auto;
}

.conditions-section {
  min-width: 0;
}

.conditions-grid {
  display: grid;
  gap: 0.55rem 1rem;
  align-items: start;
}

.conditions-grid-stage {
  grid-template-columns: minmax(0, 1.15fr) minmax(12rem, 1.1fr) minmax(0, 1fr);
}

.conditions-grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.conditions-grid-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.conditions-grid-replay {
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 16rem);
  align-items: end;
}

.conditions-group {
  margin: 0 0 0.2rem;
  padding: 0;
  border: 0;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}

.conditions-lead {
  margin: 0 0 0.4rem;
  font-size: 0.72rem;
  line-height: 1.35;
  color: var(--muted);
}

.conditions-field label {
  margin: 0 0 0.2rem;
}

.conditions-grid-stage .era-preview {
  margin-top: 1.35rem;
}

.conditions-modal .hint {
  font-size: 0.68rem;
  line-height: 1.3;
}

.viewport {
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
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}

.events-close {
  margin: 0;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  padding: 0.1rem 0.35rem;
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

.event-bubble-meta {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.75rem;
}

.event-bubble .event-text {
  margin: 0.25rem 0 0;
  font-size: 0.78rem;
  line-height: 1.4;
}

label {
  display: block;
  margin: 0.7rem 0 0.25rem;
  color: var(--muted);
  font-size: 0.8rem;
}

.hint {
  margin: 0.2rem 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.45;
  opacity: 0.9;
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
  height: 2.5rem;
}

.year-row :deep(.p-dropdown),
.year-row :deep(.p-inputnumber) {
  width: 100%;
  height: 2.5rem;
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
  padding-bottom: 1.15rem;
}

.action-btn {
  width: 100%;
}

.action-btn :deep(.p-button-label) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metrics {
  margin-top: 0.7rem;
  flex: 0 0 auto;
  min-height: 0;
}

.metrics h2 {
  margin: 0 0 0.45rem;
}

.metrics ul {
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--text);
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.45rem;
}

.metrics li {
  margin: 0;
  padding: 0.4rem 0.45rem;
  border: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
  border-radius: 8px;
  min-width: 0;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  gap: 0.35rem;
  align-items: baseline;
}

.metric-name {
  font-weight: 600;
  font-size: 0.78rem;
}

.metric-value {
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-size: 0.82rem;
}

.metrics .hint {
  font-size: 0.66rem;
  line-height: 1.3;
}

.map-stats {
  margin: 0;
  color: var(--muted);
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

@media (max-width: 1100px) {
  .conditions-grid-stage,
  .conditions-grid-2,
  .conditions-grid-4,
  .conditions-grid-replay {
    grid-template-columns: 1fr 1fr;
  }

  .conditions-modal {
    width: min(52rem, calc(100vw - 1.5rem));
    max-height: calc(100vh - 1.5rem);
    overflow: auto;
  }
}

@media (max-width: 720px) {
  .conditions-grid-stage,
  .conditions-grid-2,
  .conditions-grid-4,
  .conditions-grid-replay {
    grid-template-columns: 1fr;
  }
}
</style>
