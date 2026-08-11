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
  success?: boolean | null
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
  }
  agents: Agent[]
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
  const agent = sim.value?.agents.find((a) => a.id === actorId)
  return agent?.name ?? actorId
}

function actionLabel(action: string): string {
  const key = `actionTypes.${action}`
  const translated = t(key)
  return translated === key ? action : translated
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

function settlementColor(id: string | null): string {
  if (!id) return '#8ab4f8'
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  const hue = hash % 360
  return `hsl(${hue} 65% 62%)`
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

  for (const agent of current.agents) {
    if (!agent.alive) continue
    const x = (agent.position.x / 100) * w
    const y = (agent.position.y / 100) * h
    const r = 5 + Math.min(8, agent.wealth / 4)
    ctx.beginPath()
    ctx.fillStyle = settlementColor(agent.settlement_id)
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = '#dce7f3'
    ctx.font = '11px sans-serif'
    ctx.fillText(agent.name, x + r + 2, y + 3)
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
      </div>
      <div class="header-right">
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
        <div class="status-slot">
          <Tag v-if="sim" :value="turnStatusLabel" severity="info" />
        </div>
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
          <Button :label="t('actions.tick')" icon="pi pi-step-forward" class="action-btn" :disabled="!sim || autoPlaying" :loading="busy && !autoPlaying" severity="success" @click="tick(1)" />
          <Button :label="t('actions.tick5')" icon="pi pi-forward" class="action-btn" :disabled="!sim || autoPlaying" :loading="busy && !autoPlaying" severity="help" @click="tick(5)" />
          <Button
            :label="autoPlaying ? t('actions.autoStop') : t('actions.autoPlay')"
            :icon="autoPlaying ? 'pi pi-stop' : 'pi pi-play'"
            class="action-btn"
            :disabled="!sim"
            :severity="autoPlaying ? 'danger' : 'secondary'"
            @click="toggleAutoPlay"
          />
        </div>
        <p class="hint">{{ t('autoPlayHint') }}</p>

        <p v-if="error" class="error">{{ error }}</p>

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
      </aside>

      <main class="viewport panel">
        <div class="panel-heading">
          <h2>{{ t('map.title') }}</h2>
          <p v-if="sim" class="map-stats">
            {{ t('map.alive', { alive: aliveCount, total: totalAgents }) }}
            ·
            {{ t('map.resources', { value: sim.world.resource_pool.toFixed(1) }) }}
          </p>
        </div>
        <p class="hint map-legend">{{ t('map.legend') }}</p>
        <canvas ref="canvasRef" width="720" height="520" class="map" />
      </main>

      <section class="panel events">
        <div class="panel-heading events-heading">
          <h2>{{ t('events.title') }}</h2>
          <Tag v-if="sim" :value="turnOnlyLabel" severity="secondary" />
        </div>
        <p v-if="!recentEvents.length" class="hint">{{ t('events.empty') }}</p>
        <DataTable v-else :value="recentEvents" size="small" scrollable scroll-height="480px" class="events-table">
          <Column :header="t('events.actor')" style="width: 3.5rem">
            <template #body="{ data }">
              {{ actorLabel(data.actor_id) }}
            </template>
          </Column>
          <Column :header="t('events.action')" style="width: 4.5rem">
            <template #body="{ data }">
              {{ actionLabel(data.action) }}
            </template>
          </Column>
          <Column field="detail" :header="t('events.detail')" />
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
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: end;
  gap: 0.5rem 1rem;
  min-height: 0;
  padding-top: 0.25rem;
  margin-bottom: 0.6rem;
  flex: 0 0 auto;
}

.header-left {
  min-width: 0;
}

.header-era {
  display: flex;
  flex-wrap: nowrap;
  align-items: baseline;
  gap: 0.35rem 0.55rem;
  min-width: 0;
  overflow: hidden;
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: color-mix(in srgb, var(--panel) 85%, #1e2a38);
  font-size: 0.8rem;
  line-height: 1.3;
  color: var(--text);
  white-space: nowrap;
  text-overflow: ellipsis;
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
  width: 168px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.45rem;
  flex: 0 0 auto;
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

.status-slot {
  min-height: 1.6rem;
  max-width: 168px;
  display: flex;
  justify-content: flex-end;
}

.status-slot :deep(.p-tag) {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  margin-top: 1.25rem;
}

.metrics ul {
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--text);
}

.metrics li {
  margin-bottom: 0.85rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
}

.metrics li:last-child {
  border-bottom: 0;
  margin-bottom: 0;
  padding-bottom: 0;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: baseline;
}

.metric-name {
  font-weight: 600;
  font-size: 0.88rem;
}

.metric-value {
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-size: 0.9rem;
}

.map-stats {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
  white-space: nowrap;
}

.map-legend {
  margin-bottom: 0.55rem;
}

.map {
  width: 100%;
  height: auto;
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
