<script setup lang="ts">
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

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
const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

const sim = ref<Simulation | null>(null)
const busy = ref(false)
const error = ref('')
const canvasRef = ref<HTMLCanvasElement | null>(null)
const autoPlaying = ref(false)
let autoTimer: ReturnType<typeof setInterval> | null = null

const calendarEra = ref<'bc' | 'ad'>('ad')
const calendarYear = ref(700)
const population = ref(8)
const seed = ref(42)
const taxRate = ref(0.1)
const education = ref(0.5)
/** API には英語キーのまま送る */
const institution = ref('democracy')

const institutionOptions = computed(() => [
  { label: t('institutions.democracy'), value: 'democracy' },
  { label: t('institutions.autocracy'), value: 'autocracy' },
  { label: t('institutions.anarchy'), value: 'anarchy' },
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
const totalWealth = computed(() =>
  (sim.value?.agents ?? []).filter((a) => a.alive).reduce((sum, a) => sum + a.wealth, 0),
)
const initialWealth = computed(() => sim.value?.world.initial_total_wealth ?? totalWealth.value)
const wealthDelta = computed(() => totalWealth.value - initialWealth.value)
const meanHappiness = computed(() => {
  const alive = (sim.value?.agents ?? []).filter((a) => a.alive)
  if (!alive.length) return 0
  return alive.reduce((sum, a) => sum + a.happiness, 0) / alive.length
})
const notableCount = computed(
  () => (sim.value?.agents ?? []).filter((a) => a.alive && (a.traits?.length ?? 0) > 0).length,
)

function formatDelta(value: number, digits = 0): string {
  const n = Number(value.toFixed(digits))
  if (n > 0) return `+${digits ? n.toFixed(digits) : n}`
  if (n < 0) return digits ? n.toFixed(digits) : String(n)
  return digits ? n.toFixed(digits) : '0'
}

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
        resource_pool: 100,
      },
    })
    await nextTick()
    drawMap()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

async function tick(n = 1) {
  if (!sim.value) return
  busy.value = true
  error.value = ''
  try {
    sim.value = await api<Simulation>(`/simulations/${sim.value.id}/tick`, {
      method: 'POST',
      body: { n },
    })
    await nextTick()
    drawMap()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
    stopAutoPlay()
  } finally {
    busy.value = false
  }
}

async function toggleAutoPlay() {
  if (autoPlaying.value) {
    stopAutoPlay()
    return
  }
  if (!sim.value) return
  autoPlaying.value = true
  await tick(1)
  if (!autoPlaying.value) return
  autoTimer = setInterval(() => {
    if (busy.value || !sim.value || !autoPlaying.value) return
    void tick(1)
  }, AUTO_INTERVAL_MS)
}

const SETTLEMENT_HUES = [0, 207, 122, 48, 291, 174, 16, 231, 187, 88]

function settlementHue(id: string | null): number {
  if (!id) return 210
  const match = id.match(/(\d+)$/)
  const idx = match ? Number(match[1]) - 1 : 0
  return SETTLEMENT_HUES[((idx % SETTLEMENT_HUES.length) + SETTLEMENT_HUES.length) % SETTLEMENT_HUES.length]
}

function settlementColor(id: string | null, role: 'base' | 'member' | 'leader' = 'base'): string {
  const hue = settlementHue(id)
  if (!id) return 'hsl(210 12% 52%)'
  if (role === 'leader') return `hsl(${hue} 78% 38%)`
  if (role === 'member') return `hsl(${hue} 52% 68%)`
  return `hsl(${hue} 65% 56%)`
}

function agentFill(agent: Agent, isLeader: boolean): string {
  if (agent.settlement_id) return settlementColor(agent.settlement_id, isLeader ? 'leader' : 'member')
  let hash = 0
  for (let i = 0; i < agent.id.length; i++) hash = (hash * 31 + agent.id.charCodeAt(i)) >>> 0
  const sat = (agent.traits?.length ?? 0) > 0 ? 48 : 28
  const light = (agent.traits?.length ?? 0) > 0 ? 46 : 58
  return `hsl(${hash % 360} ${sat}% ${light}%)`
}

function agentMark(agent: Agent): string {
  const traits = agent.traits ?? []
  let mark = ''
  if (traits.includes('charisma')) mark += '★'
  if (traits.includes('genius')) mark += '◆'
  return mark
}

function drawMap() {
  const canvas = canvasRef.value
  const current = sim.value
  if (!canvas || !current) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const w = canvas.width
  const h = canvas.height
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = '#101820'
  ctx.fillRect(0, 0, w, h)

  ctx.strokeStyle = '#243041'
  ctx.lineWidth = 1
  for (let i = 0; i <= 10; i++) {
    const x = (i / 10) * w
    const y = (i / 10) * h
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, h)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(w, y)
    ctx.stroke()
  }

  // Axes labels for world coordinates
  ctx.fillStyle = '#6b7c8f'
  ctx.font = '10px sans-serif'
  ctx.fillText('0', 4, h - 4)
  ctx.fillText('100', w - 22, h - 4)
  ctx.fillText('100', 4, 12)

  for (const settlement of current.settlements ?? []) {
    const sx = (settlement.position.x / 100) * w
    const sy = (settlement.position.y / 100) * h
    const color = settlementColor(settlement.id)
    ctx.beginPath()
    ctx.fillStyle = color
    ctx.globalAlpha = 0.16
    ctx.arc(sx, sy, 28 + settlement.member_ids.length * 2, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalAlpha = 1
    ctx.fillStyle = color
    ctx.font = '11px sans-serif'
    ctx.fillText(settlement.id, sx + 10, sy - 10)
  }

  const leaders = new Set(
    (current.settlements ?? []).map((s) => s.leader_id).filter((id): id is string => Boolean(id)),
  )

  for (const agent of current.agents) {
    if (!agent.alive) continue
    const isLeader = leaders.has(agent.id)
    const x = (agent.position.x / 100) * w
    const y = (agent.position.y / 100) * h
    const r = (isLeader ? 7 : 5) + Math.min(8, agent.wealth / 4)
    ctx.beginPath()
    ctx.fillStyle = agentFill(agent, isLeader)
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
    if (agent.settlement_id) {
      ctx.strokeStyle = isLeader ? '#f4f0d8' : settlementColor(agent.settlement_id, 'base')
      ctx.lineWidth = isLeader ? 2.5 : 1.5
      ctx.stroke()
    }
    const mark = agentMark(agent)
    ctx.fillStyle = '#dce7f3'
    ctx.font = isLeader ? 'bold 11px sans-serif' : '11px sans-serif'
    ctx.fillText(`${agent.name}${mark}`, x + r + 2, y + 3)
  }
}

onMounted(() => {
  drawMap()
})

onBeforeUnmount(() => {
  stopAutoPlay()
})

watch(sim, async () => {
  await nextTick()
  drawMap()
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
      <div class="header-left">
        <p class="eyebrow">{{ t('brand') }}</p>
        <h1>{{ t('consoleTitle') }}</h1>
      </div>
      <div v-if="sim" class="header-era" aria-live="polite">
        <span class="era-banner-year">{{ liveYearLabel }}</span>
        <span class="header-era-sep" aria-hidden="true">·</span>
        <span><span class="era-k">{{ t('eraPreview.japan') }}</span>{{ liveJapanEra }}</span>
        <span class="header-era-sep" aria-hidden="true">·</span>
        <span><span class="era-k">{{ t('eraPreview.world') }}</span>{{ liveWorldEra }}</span>
        <span class="header-era-sep" aria-hidden="true">·</span>
        <span>
          <span class="era-k">{{ t('headerStats.population') }}</span>
          {{ aliveCount }}
          <span class="stat-delta" :class="populationDelta >= 0 ? 'up' : 'down'">{{ formatDelta(populationDelta) }}</span>
        </span>
        <span class="header-era-sep" aria-hidden="true">·</span>
        <span>
          <span class="era-k">{{ t('headerStats.wealth') }}</span>
          {{ totalWealth.toFixed(0) }}
          <span class="stat-delta" :class="wealthDelta >= 0 ? 'up' : 'down'">{{ formatDelta(wealthDelta, 0) }}</span>
        </span>
        <span class="header-era-sep" aria-hidden="true">·</span>
        <span>
          <span class="era-k">{{ t('headerStats.happiness') }}</span>
          {{ meanHappiness.toFixed(2) }}
        </span>
        <span class="header-era-sep" aria-hidden="true">·</span>
        <span>
          <span class="era-k">{{ t('headerStats.notables') }}</span>
          {{ notableCount }}
        </span>
      </div>
      <div class="header-right">
        <div class="header-controls">
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
    </header>

    <div class="grid">
      <aside class="panel sidebar">
        <h2>{{ t('initialConditions') }}</h2>
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
        <div class="era-preview">
          <p class="era-preview-title">{{ t('eraPreview.title') }}</p>
          <p><span class="era-k">{{ t('eraPreview.year', { label: draftYearLabel }) }}</span></p>
          <p><span class="era-k">{{ t('eraPreview.japan') }}</span> {{ draftJapanEra }}</p>
          <p><span class="era-k">{{ t('eraPreview.world') }}</span> {{ draftWorldEra }}</p>
        </div>
        <label>{{ t('population') }}</label>
        <InputNumber v-model="population" :min="2" :max="100" show-buttons class="field-control" />
        <p class="hint">{{ t('populationHint') }}</p>
        <label>{{ t('seed') }}</label>
        <InputNumber v-model="seed" show-buttons class="field-control" />
        <p class="hint">{{ t('seedHint') }}</p>
        <label>{{ t('taxRate') }}</label>
        <InputNumber v-model="taxRate" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
        <p class="hint">{{ t('taxRateHint') }}</p>
        <label>{{ t('education') }}</label>
        <InputNumber v-model="education" :min="0" :max="1" :step="0.05" :max-fraction-digits="2" show-buttons class="field-control" />
        <p class="hint">{{ t('educationHint') }}</p>
        <label>{{ t('institution') }}</label>
        <Dropdown v-model="institution" :options="institutionOptions" option-label="label" option-value="value" class="field-control" />

        <div class="actions">
          <Button :label="t('actions.create')" icon="pi pi-plus" class="action-btn" :loading="busy && !autoPlaying" @click="createSimulation" />
        </div>

        <p v-if="error" class="error">{{ error }}</p>
      </aside>

      <main class="viewport panel">
        <div class="panel-heading">
          <h2>{{ t('map.title') }}</h2>
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
          </p>
        </div>
        <p class="hint map-legend">{{ t('map.legend') }}</p>
        <canvas ref="canvasRef" width="720" height="520" class="map" />
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

      <section class="panel events">
        <div class="panel-heading events-heading">
          <h2>{{ t('events.title') }}</h2>
          <Tag v-if="sim" :value="turnOnlyLabel" severity="secondary" />
        </div>
        <p v-if="!recentEvents.length" class="hint">{{ t('events.empty') }}</p>
        <DataTable v-else :value="recentEvents" size="small" scrollable scroll-height="480px" class="events-table">
          <Column :header="t('events.actor')" style="width: 4.2rem">
            <template #body="{ data }">
              {{ actorLabel(data.actor_id) }}
            </template>
          </Column>
          <Column :header="t('events.action')" style="width: 4.5rem">
            <template #body="{ data }">
              {{ actionLabel(data.action) }}
            </template>
          </Column>
          <Column :header="t('events.detail')">
            <template #body="{ data }">
              {{ eventDetail(data) }}
            </template>
          </Column>
        </DataTable>
      </section>
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
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.5rem 1rem;
  min-height: 0;
  padding-top: 0.25rem;
  padding-right: 4.25rem;
  margin-bottom: 0.6rem;
  flex: 0 0 auto;
}

.header-left {
  min-width: 0;
}

.header-era {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.35rem 0.55rem;
  height: var(--header-bar-h);
  min-width: 0;
  overflow: hidden;
  padding: 0 0.7rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 85%, #1e2a38);
  font-size: 0.8rem;
  line-height: 1;
  color: var(--text);
  white-space: nowrap;
  text-overflow: ellipsis;
  box-sizing: border-box;
}

.header-era > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-era-sep {
  color: var(--muted);
  opacity: 0.55;
  flex: 0 0 auto;
}

.stat-delta {
  margin-left: 0.2rem;
  font-variant-numeric: tabular-nums;
  font-size: 0.72rem;
}

.stat-delta.up {
  color: #7dcea0;
}

.stat-delta.down {
  color: #f1948a;
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
  margin-top: 0.55rem;
  padding: 0.55rem 0.65rem;
  border-radius: 8px;
  border: 1px dashed var(--line);
  background: color-mix(in srgb, var(--panel) 70%, #121820);
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
  grid-template-columns: minmax(400px, 440px) minmax(0, 1fr) minmax(360px, 400px);
  gap: 0.75rem;
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

.sidebar {
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  align-self: stretch;
  max-height: 100%;
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

.panel-heading h2 {
  margin: 0;
}

.events-heading {
  margin-bottom: 0.75rem;
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

.sidebar :deep(.p-inputnumber),
.sidebar :deep(.p-dropdown) {
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

.sidebar :deep(.p-inputnumber-input) {
  min-width: 0;
  flex: 1 1 auto;
  height: 100%;
  box-sizing: border-box;
}

.sidebar :deep(.p-dropdown) {
  min-width: 0;
  flex: 1 1 auto;
}

.sidebar :deep(.p-dropdown .p-dropdown-label),
.sidebar :deep(.p-dropdown .p-dropdown-trigger) {
  display: flex;
  align-items: center;
}

.sidebar :deep(.p-inputnumber-button-group) {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-self: stretch;
  height: 100%;
}

.sidebar :deep(.p-inputnumber-button) {
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
  margin-top: 1rem;
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

.map {
  width: 100%;
  height: auto;
  min-height: 0;
  flex: 1 1 auto;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid var(--line);
  display: block;
}

.events-table :deep(.p-datatable-tbody > tr > td) {
  word-break: keep-all;
  overflow-wrap: anywhere;
  line-break: strict;
  vertical-align: top;
}

.events-table :deep(.p-datatable-tbody > tr > td:last-child) {
  font-size: 0.7rem;
  line-height: 1.4;
  color: var(--text);
}

.events-table :deep(.p-datatable-thead > tr > th) {
  white-space: nowrap;
}

.error {
  color: #ff8f8f;
  font-size: 0.85rem;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .sidebar {
    max-height: none;
    overflow-y: visible;
  }

  .header {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
  }

  .header-era {
    grid-column: 1 / -1;
    order: 3;
    flex-wrap: wrap;
    white-space: normal;
  }
}
</style>
